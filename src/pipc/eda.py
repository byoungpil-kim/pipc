from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

import pandas as pd


KEYWORD_RE = re.compile(r"[가-힣A-Za-z0-9]{2,}")
STOPWORDS = {
    "개인정보",
    "보호법",
    "제조",
    "위원회",
    "처분",
    "결정",
    "대하여",
    "따라",
    "있는",
    "없는",
    "한다",
}


def generate_eda(processed_path: Path, reports_dir: Path) -> Path:
    df = pd.read_csv(processed_path)
    failure_count = read_failure_count(processed_path.parent / "failed_decisions.csv")
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "tables").mkdir(parents=True, exist_ok=True)

    add_lengths(df)
    write_table(reports_dir, "year_counts", year_counts(df))
    write_table(reports_dir, "meeting_type_counts", count_column(df, "meeting_type"))
    write_table(reports_dir, "decision_type_counts", count_column(df, "decision_type"))
    write_table(reports_dir, "missing_rates", missing_rates(df))
    write_table(reports_dir, "sanction_type_counts", exploded_counts(df, "sanction_types"))
    write_table(reports_dir, "article_counts", exploded_counts(df, "violated_articles"))
    write_table(reports_dir, "keyword_counts", keyword_counts(df))

    report = reports_dir / "eda.md"
    report.write_text(render_report(df, failure_count), encoding="utf-8")
    return report


def add_lengths(df: pd.DataFrame) -> None:
    for source, target in [
        ("title", "title_length"),
        ("order_text", "order_length"),
        ("reason_text", "reason_length"),
        ("summary_text", "summary_length"),
    ]:
        df[target] = df.get(source, "").fillna("").astype(str).str.len()
    df["document_length"] = (
        df.get("order_text", "").fillna("").astype(str)
        + df.get("reason_text", "").fillna("").astype(str)
        + df.get("summary_text", "").fillna("").astype(str)
        + df.get("main_text", "").fillna("").astype(str)
    ).str.len()


def render_report(df: pd.DataFrame, failure_count: int = 0) -> str:
    duplicate_count = int(df["decision_id"].duplicated().sum()) if "decision_id" in df else 0
    money_count = int(df.get("monetary_amount", pd.Series(dtype=float)).notna().sum())
    lines = [
        "# PIPC EDA Report",
        "",
        f"- 전체 결정문 수: {len(df):,}",
        f"- 수집 성공 수: {len(df):,}",
        f"- 수집 실패 수: {failure_count:,}",
        f"- 중복 decision_id 수: {duplicate_count:,}",
        f"- 금액 추출 가능 사건 수: {money_count:,}",
        "",
        "## Tables",
        "",
        "- `reports/tables/year_counts.csv`",
        "- `reports/tables/meeting_type_counts.csv`",
        "- `reports/tables/decision_type_counts.csv`",
        "- `reports/tables/missing_rates.csv`",
        "- `reports/tables/sanction_type_counts.csv`",
        "- `reports/tables/article_counts.csv`",
        "- `reports/tables/keyword_counts.csv`",
        "",
        "## Length Summary",
        "",
        df[["title_length", "order_length", "reason_length", "summary_length", "document_length"]]
        .describe()
        .to_string(),
    ]
    return "\n".join(lines) + "\n"


def read_failure_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def year_counts(df: pd.DataFrame) -> pd.DataFrame:
    years = df.get("decision_date", pd.Series(dtype=str)).fillna("").astype(str).str[:4]
    return years[years.str.match(r"\d{4}")].value_counts().sort_index().rename_axis("year").reset_index(name="count")


def count_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in df:
        return pd.DataFrame(columns=[column, "count"])
    return df[column].fillna("").replace("", "(missing)").value_counts().rename_axis(column).reset_index(name="count")


def missing_rates(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.isna()
        .mean()
        .rename("missing_rate")
        .reset_index()
        .rename(columns={"index": "field"})
    )


def exploded_counts(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in df:
        return pd.DataFrame(columns=[column, "count"])
    counter: Counter[str] = Counter()
    for value in df[column].fillna("").astype(str):
        for item in value.split(";"):
            if item:
                counter[item] += 1
    return pd.DataFrame(counter.most_common(), columns=[column, "count"])


def keyword_counts(df: pd.DataFrame, limit: int = 100) -> pd.DataFrame:
    text = " ".join(
        df.get(column, pd.Series(dtype=str)).fillna("").astype(str).str.cat(sep=" ")
        for column in ["title", "order_text", "reason_text", "summary_text"]
    )
    counter = Counter(
        token
        for token in KEYWORD_RE.findall(text)
        if token not in STOPWORDS and not token.isdigit()
    )
    return pd.DataFrame(counter.most_common(limit), columns=["keyword", "count"])


def write_table(reports_dir: Path, name: str, df: pd.DataFrame) -> None:
    df.to_csv(reports_dir / "tables" / f"{name}.csv", index=False)
