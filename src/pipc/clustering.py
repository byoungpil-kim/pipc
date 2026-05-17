from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from .insights import ensure_columns, split_items
from .issue_taxonomy import EXTERNAL_ISSUES, LOCAL_ISSUE_PATTERNS


def run_clustering(processed_path: Path, reports_dir: Path, n_clusters: int = 18) -> tuple[Path, Path, Path]:
    df = pd.read_csv(processed_path)
    ensure_columns(df)
    texts = build_texts(df)
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 5),
        min_df=3,
        max_df=0.85,
        max_features=30_000,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(texts)
    model = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, n_init=20, batch_size=512)
    labels = model.fit_predict(matrix)
    df["cluster_id"] = labels

    tables_dir = reports_dir / "tables" / "clusters"
    tables_dir.mkdir(parents=True, exist_ok=True)

    assignments_path = tables_dir / "cluster_assignments.csv"
    summary_path = tables_dir / "cluster_summary.csv"
    issues_path = tables_dir / "cluster_issue_candidates.csv"

    assignment_cols = [
        "decision_id",
        "cluster_id",
        "document_category",
        "decision_date",
        "title",
        "applicant",
        "sanction_strength",
        "sanction_types",
        "monetary_amount",
        "case_type",
        "violated_articles",
    ]
    df[assignment_cols].to_csv(assignments_path, index=False)
    summarize_clusters(df, vectorizer, model).to_csv(summary_path, index=False)
    cluster_issues(df).to_csv(issues_path, index=False)
    return assignments_path, summary_path, issues_path


def build_texts(df: pd.DataFrame) -> pd.Series:
    return (
        df["document_category"].fillna("")
        + "\n"
        + df["title"].fillna("")
        + "\n"
        + df["order_text"].fillna("")
        + "\n"
        + df["reason_text"].fillna("").str.slice(0, 4_000)
        + "\n"
        + df["summary_text"].fillna("")
        + "\n"
        + df["case_type"].fillna("")
        + "\n"
        + df["factors"].fillna("")
        + "\n"
        + df["violated_articles"].fillna("")
    )


def summarize_clusters(df: pd.DataFrame, vectorizer: TfidfVectorizer, model: MiniBatchKMeans) -> pd.DataFrame:
    feature_names = vectorizer.get_feature_names_out()
    rows = []
    for cluster_id in sorted(df["cluster_id"].unique()):
        group = df[df["cluster_id"] == cluster_id].copy()
        center = model.cluster_centers_[cluster_id]
        top_terms = [feature_names[i] for i in center.argsort()[-18:][::-1]]
        category_counts = group["document_category"].value_counts().head(3).to_dict()
        title_terms = top_word_counts(group["title"].fillna(" ").str.cat(sep=" "), 12)
        rows.append(
            {
                "cluster_id": cluster_id,
                "size": len(group),
                "dominant_category": group["document_category"].mode().iloc[0] if not group.empty else "",
                "category_mix": "; ".join(f"{key}:{value}" for key, value in category_counts.items()),
                "year_min": group["decision_date"].fillna("").astype(str).str[:4].replace("", pd.NA).dropna().min(),
                "year_max": group["decision_date"].fillna("").astype(str).str[:4].replace("", pd.NA).dropna().max(),
                "top_terms": "; ".join(clean_terms(top_terms)),
                "title_keywords": "; ".join(title_terms),
                "top_case_types": top_split(group, "case_type", 8),
                "top_articles": top_split(group, "violated_articles", 8),
                "representative_decisions": representative_decisions(group),
            }
        )
    return pd.DataFrame(rows).sort_values(["dominant_category", "size"], ascending=[True, False])


def cluster_issues(df: pd.DataFrame, limit_per_cluster: int = 10) -> pd.DataFrame:
    rows = []
    for cluster_id in sorted(df["cluster_id"].unique()):
        group = df[df["cluster_id"] == cluster_id]
        text = cluster_text(group)
        candidates: list[dict[str, object]] = []
        for issue in EXTERNAL_ISSUES:
            count = len(re.findall(issue.pattern, text))
            matched_docs = doc_match_count(group, issue.pattern)
            if count:
                candidates.append(
                    {
                        "cluster_id": cluster_id,
                        "issue_type": "global",
                        "issue": issue.korean_label,
                        "count": count,
                        "matched_decisions": matched_docs,
                        "legal_focus": issue.legal_focus,
                    }
                )
        for issue, pattern in LOCAL_ISSUE_PATTERNS.items():
            count = len(re.findall(pattern, text))
            matched_docs = doc_match_count(group, pattern)
            if count:
                candidates.append(
                    {
                        "cluster_id": cluster_id,
                        "issue_type": "cluster",
                        "issue": issue,
                        "count": count,
                        "matched_decisions": matched_docs,
                        "legal_focus": local_focus(issue),
                    }
                )
        selected = sorted(candidates, key=lambda item: (item["matched_decisions"], item["count"]), reverse=True)[:limit_per_cluster]
        for rank, item in enumerate(selected, start=1):
            item["rank"] = rank
            rows.append(item)
    return pd.DataFrame(rows)


def cluster_text(group: pd.DataFrame) -> str:
    columns = ["title", "order_text", "reason_text", "summary_text", "case_type", "factors", "violated_articles"]
    return "\n".join(group[col].fillna("").astype(str).str.cat(sep="\n") for col in columns)


def doc_match_count(group: pd.DataFrame, pattern: str) -> int:
    text = (
        group["title"].fillna("")
        + "\n"
        + group["order_text"].fillna("")
        + "\n"
        + group["reason_text"].fillna("")
        + "\n"
        + group["summary_text"].fillna("")
        + "\n"
        + group["case_type"].fillna("")
        + "\n"
        + group["factors"].fillna("")
    )
    return int(text.str.contains(pattern, regex=True).sum())


def representative_decisions(group: pd.DataFrame, limit: int = 8) -> str:
    sort_cols = ["monetary_amount", "document_length", "decision_date"]
    reps = group.sort_values(sort_cols, ascending=[False, False, False], na_position="last").head(limit)
    return "; ".join(str(value) for value in reps["decision_id"].tolist())


def top_split(group: pd.DataFrame, column: str, limit: int) -> str:
    counter: Counter[str] = Counter()
    for value in group[column].fillna(""):
        counter.update(split_items(value))
    return "; ".join(item for item, _ in counter.most_common(limit))


def top_word_counts(text: str, limit: int) -> list[str]:
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
    stop = {"개인정보", "보호", "관한", "대한", "법규", "위반행위", "시정조치", "일부개정안", "침해요인", "평가"}
    counter = Counter(word for word in words if word not in stop and not word.isdigit())
    return [word for word, _ in counter.most_common(limit)]


def clean_terms(terms: list[str]) -> list[str]:
    cleaned = []
    for term in terms:
        value = term.strip()
        if len(value) < 2 or value in cleaned:
            continue
        cleaned.append(value)
    return cleaned[:12]


def local_focus(issue: str) -> str:
    mapping = {
        "동의·고지": "정보주체에게 제공된 정보와 동의의 명확성",
        "목적 외 이용·제공": "수집 목적 범위와 제17조·제18조상 제공 근거",
        "안전조치": "접근통제, 접속기록, 암호화, 취약점 관리",
        "유출·침해": "유출 규모, 유출 경위, 통지와 피해 확산 방지",
        "보유기간·파기": "목적 달성 후 보관과 파기 지연",
        "위탁·수탁": "수탁자 관리감독과 위탁 구조",
        "국외이전": "국외 이전 고지·동의와 위탁·보관 구조",
        "영상정보": "CCTV 설치·열람·제공과 목적 외 이용",
        "아동": "만 14세 미만 아동과 법정대리인 동의",
        "민감·고유식별정보": "주민등록번호 등 고위험 정보 처리",
        "정보주체 권리": "열람·정정·삭제·처리정지·설명 요구",
        "사전점검·개선권고": "예방적 감독과 개선권고 이행",
        "처리방침·책임성": "처리방침, CPO, 내부관리계획",
        "금액 제재·공표": "제재 패키지와 공표명령",
        "AI·자동화": "AI 처리와 자동화된 결정 권리",
    }
    return mapping.get(issue, "클러스터별 반복 쟁점")
