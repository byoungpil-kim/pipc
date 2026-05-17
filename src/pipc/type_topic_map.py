from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

import hdbscan
import numpy as np
import pandas as pd
import umap

from .config import load_env
from .insights import CATEGORY_LABELS, ensure_columns, split_items


OPENROUTER_URL = "https://openrouter.ai/api/v1"
EMBED_MODEL = "openai/text-embedding-3-large"
LABEL_MODEL = "anthropic/claude-opus-4.7"
EMBED_BATCH_SIZE = 20
HTTP_TIMEOUT = 90
COLORS = ["#1e40af", "#059669", "#dc2626", "#7c3aed", "#0d9488", "#b45309", "#475569", "#be185d"]
NOISE_COLOR = "#8a8a8a"


def generate_type_topic_maps(processed_path: Path, reports_dir: Path, categories: list[str] | None = None) -> tuple[Path, Path]:
    df = pd.read_csv(processed_path)
    ensure_columns(df)
    api_key = openrouter_key()
    out_dir = reports_dir / "tables" / "type_topic_maps"
    cache_dir = processed_path.parents[1] / "cache" / "type_topic_maps"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    targets = categories or sorted(df["document_category"].fillna("other").unique())
    assignment_rows: list[dict[str, object]] = []
    cluster_rows: list[dict[str, object]] = []
    for category in targets:
        group = df[df["document_category"].fillna("other") == category].copy()
        if len(group) < 12:
            continue
        result = build_category(category, group, api_key, cache_dir)
        (out_dir / f"{category}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        for cluster in result["clusters"]:
            cluster_rows.append({"document_category": category, **cluster})
        for page in result["pages"]:
            assignment_rows.append({"document_category": category, **page})

    clusters_path = out_dir / "clusters.csv"
    assignments_path = out_dir / "assignments.csv"
    pd.DataFrame(cluster_rows).to_csv(clusters_path, index=False)
    pd.DataFrame(assignment_rows).to_csv(assignments_path, index=False)
    return clusters_path, assignments_path


def build_category(category: str, df: pd.DataFrame, api_key: str, cache_dir: Path) -> dict:
    docs = [doc_from_row(row) for _, row in df.iterrows()]
    embed_cache_path = cache_dir / f"{category}_embeddings.json"
    label_cache_path = cache_dir / f"{category}_labels.json"
    embed_cache = load_json(embed_cache_path)
    X = fetch_embeddings(docs, api_key, embed_cache)
    save_json(embed_cache_path, embed_cache)
    coords = normalize_to_box(reduce_to_2d(X))
    labels, best = auto_tune(coords, len(docs))
    label_cache = load_json(label_cache_path)
    clusters = label_clusters(docs, labels, coords, api_key, label_cache)
    save_json(label_cache_path, label_cache)

    color_by_cluster = {int(c["cluster_idx"]): c["color"] for c in clusters}
    pages = []
    for doc, point, label in zip(docs, coords, labels):
        cid = int(label)
        pages.append(
            {
                "decision_id": doc["decision_id"],
                "title": doc["title"],
                "decision_date": doc["decision_date"],
                "cluster": cid,
                "color": color_by_cluster.get(cid, NOISE_COLOR),
                "x": float(point[0]),
                "y": float(point[1]),
                "amount": doc["amount"],
                "case_type": doc["case_type"],
            }
        )
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "document_category": category,
        "category_label": CATEGORY_LABELS.get(category, category),
        "method": f"{EMBED_MODEL} + UMAP(cosine) + HDBSCAN(auto-tuned) + {LABEL_MODEL}",
        "settings": best,
        "n_pages": len(docs),
        "n_clusters": len(clusters),
        "n_noise": int((labels == -1).sum()),
        "clusters": clusters,
        "pages": pages,
    }


def doc_from_row(row: pd.Series) -> dict:
    title = clean(row.get("title", "")) or f"decision-{row['decision_id']}"
    text = "\n".join(
        clean(row.get(col, ""))
        for col in ["title", "summary_text", "order_text", "reason_text", "case_type", "violated_articles"]
    )
    if not strip_text(text):
        text = title
    return {
        "slug": str(row["decision_id"]),
        "decision_id": str(row["decision_id"]),
        "title": title[:140],
        "decision_date": clean(row.get("decision_date", "")),
        "text": strip_text(text)[:6000],
        "amount": float(row["monetary_amount"]) if pd.notna(row.get("monetary_amount")) else None,
        "case_type": clean(row.get("case_type", "")),
        "articles": clean(row.get("violated_articles", "")),
    }


def openrouter_key() -> str:
    values = load_env()
    for key, value in values.items():
        os.environ.setdefault(key, value)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY in .env.")
    return api_key


def fetch_embeddings(docs: list[dict], api_key: str, cache: dict) -> np.ndarray:
    out: list[np.ndarray | None] = [None] * len(docs)
    pending: list[tuple[int, str]] = []
    for i, doc in enumerate(docs):
        h = doc_hash(doc)
        cached = cache.get(doc["decision_id"])
        if cached and cached.get("hash") == h:
            out[i] = np.asarray(cached["embedding"], dtype=np.float32)
        else:
            pending.append((i, doc["text"]))
    headers = openrouter_headers(api_key, "PIPC decision type topic map")
    for start in range(0, len(pending), EMBED_BATCH_SIZE):
        batch = pending[start : start + EMBED_BATCH_SIZE]
        items = fetch_embedding_batch(headers, [text for _, text in batch], len(batch))
        indices = [idx for idx, _ in batch]
        for item in items:
            i = indices[int(item.get("index", 0))]
            emb = np.asarray(item["embedding"], dtype=np.float32)
            out[i] = emb
            cache[docs[i]["decision_id"]] = {"hash": doc_hash(docs[i]), "embedding": emb.tolist()}
        print(f"embedded batch {start // EMBED_BATCH_SIZE + 1}/{max(1, (len(pending) + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE)}")
    return np.vstack([np.asarray(item, dtype=np.float32) for item in out])


def fetch_embedding_batch(headers: dict, texts: list[str], expected: int) -> list[dict]:
    last_error = ""
    for attempt in range(1, 5):
        resp = http_post_json(
            f"{OPENROUTER_URL}/embeddings",
            headers,
            {"model": EMBED_MODEL, "input": texts},
        )
        items = resp.get("data") or []
        if len(items) == expected:
            return items
        last_error = json.dumps(resp, ensure_ascii=False)[:500]
        time.sleep(2 * attempt)
    raise RuntimeError(f"embedding batch returned wrong size after retries. expected={expected} last={last_error}")


def reduce_to_2d(X: np.ndarray) -> np.ndarray:
    reducer = umap.UMAP(n_components=2, random_state=42, metric="cosine", n_neighbors=min(12, max(2, len(X) - 1)), min_dist=0.25)
    return reducer.fit_transform(X)


def auto_tune(coords: np.ndarray, n: int):
    target_min, target_max = (3, 9) if n < 200 else (5, 14)
    candidates = []
    for mcs in range(3, min(30, max(4, n // 12)) + 1):
        for method in ("eom", "leaf"):
            for eps in (0.0, 0.05, 0.10, 0.20):
                labels = hdbscan.HDBSCAN(min_cluster_size=mcs, min_samples=1, cluster_selection_method=method, cluster_selection_epsilon=eps).fit_predict(coords)
                ids = set(int(x) for x in labels) - {-1}
                if not ids:
                    continue
                sizes = [int((labels == cid).sum()) for cid in ids]
                candidates.append(
                    {
                        "labels": labels,
                        "mcs": mcs,
                        "method": method,
                        "eps": eps,
                        "k": len(ids),
                        "noise": int((labels == -1).sum()),
                        "max_pct": max(sizes) / n,
                    }
                )
    pool = [c for c in candidates if target_min <= c["k"] <= target_max and c["max_pct"] <= 0.35] or candidates
    pool.sort(key=lambda c: (c["noise"], c["max_pct"], abs(c["k"] - target_max), -c["mcs"]))
    best = pool[0]
    labels = best.pop("labels")
    return labels, best


def label_clusters(docs: list[dict], labels: np.ndarray, coords: np.ndarray, api_key: str, cache: dict) -> list[dict]:
    clusters = []
    ids = sorted(set(int(x) for x in labels) - {-1})
    for i, cid in enumerate(ids):
        members = [doc for doc, label in zip(docs, labels) if int(label) == cid]
        h = cluster_hash(members)
        cached = cache.get(h)
        if cached:
            label_text = cached["label"]
            subtitle = cached["subtitle"]
        else:
            try:
                labeled = llm_label_cluster(members[:20], api_key)
                label_text = labeled.get("label") or f"Cluster {cid}"
                subtitle = labeled.get("subtitle") or ""
            except Exception as exc:  # noqa: BLE001
                label_text = fallback_label(members)
                subtitle = f"자동 라벨 실패: {exc}"
            cache[h] = {"label": label_text, "subtitle": subtitle}
        mask = labels == cid
        clusters.append(
            {
                "cluster_idx": cid,
                "label": label_text,
                "subtitle": subtitle,
                "size": int(mask.sum()),
                "color": COLORS[i % len(COLORS)],
                "x": float(coords[mask, 0].mean()),
                "y": float(coords[mask, 1].mean()),
                "top_case_types": top_split(members, "case_type"),
            }
        )
    return clusters


def llm_label_cluster(members: list[dict], api_key: str) -> dict:
    lines = [f"[{i}] {m['title']} — {m['case_type']}" for i, m in enumerate(members, 1)]
    prompt = (
        "다음 개인정보보호위원회 결정문들은 한 유형 내부에서 의미적으로 가깝게 묶였다.\n\n"
        + "\n".join(lines)
        + "\n\n공통 주제를 한국어 JSON 한 줄로만 답하라. "
        "스키마: {\"label\":\"5~14자 명사구\", \"subtitle\":\"15~35자 설명\"}"
    )
    resp = http_post_json(
        f"{OPENROUTER_URL}/chat/completions",
        openrouter_headers(api_key, "PIPC cluster labeling"),
        {
            "model": LABEL_MODEL,
            "messages": [
                {"role": "system", "content": "Return JSON only. No prose, no markdown fences."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 300,
            "temperature": 0.2,
        },
    )
    text = resp["choices"][0]["message"]["content"].strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def http_post_json(url: str, headers: dict, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={**headers, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        msg = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {msg}") from None


def openrouter_headers(api_key: str, title: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "HTTP-Referer": "https://byoungpil-kim.github.io/pipc/", "X-Title": title}


def normalize_to_box(coords: np.ndarray, margin: float = 6.0) -> np.ndarray:
    xs, ys = coords[:, 0], coords[:, 1]
    def norm(values):
        rng = values.max() - values.min()
        if rng < 1e-9:
            return np.full_like(values, 50.0)
        return margin + (100 - 2 * margin) * (values - values.min()) / rng
    return np.column_stack([norm(xs), norm(ys)])


def strip_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def doc_hash(doc: dict) -> str:
    return hashlib.sha256(doc["text"].encode("utf-8")).hexdigest()


def cluster_hash(members: list[dict]) -> str:
    h = hashlib.sha256()
    for member in sorted(members, key=lambda item: item["decision_id"]):
        h.update(member["decision_id"].encode("utf-8"))
    return h.hexdigest()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def top_split(members: list[dict], column: str, limit: int = 5) -> str:
    counter: Counter[str] = Counter()
    for member in members:
        counter.update(split_items(member.get(column, "")))
    return "; ".join(item for item, _ in counter.most_common(limit))


def fallback_label(members: list[dict]) -> str:
    words = Counter()
    for member in members:
        words.update(re.findall(r"[가-힣A-Za-z0-9]{2,}", member["title"]))
    for stop in ["개인정보", "보호", "법규", "위반행위", "시정조치", "관한"]:
        words.pop(stop, None)
    return words.most_common(1)[0][0] if words else "유형 내부 묶음"
