from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

import pandas as pd


CATEGORY_LABELS = {
    "enforcement": "법규 위반·제재",
    "privacy_impact_review": "침해요인 평가",
    "public_system_inspection": "공공시스템·실태점검",
    "data_provision_request": "개인정보 제공 요청",
    "prior_review": "사전적정성 검토",
    "complaint_or_interpretation": "민원·해석",
    "other": "기타",
}


def generate_insights(processed_path: Path, reports_dir: Path) -> Path:
    df = pd.read_csv(processed_path)
    reports_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = reports_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    ensure_columns(df)
    tables = {
        "document_category_counts": document_category_counts(df),
        "year_category_counts": year_category_counts(df),
        "category_missing_rates": category_missing_rates(df),
        "category_length_summary": category_length_summary(df),
        "enforcement_sanction_strength": enforcement_sanction_strength(df),
        "enforcement_sanction_types": exploded_counts(filter_category(df, "enforcement"), "sanction_types"),
        "enforcement_articles": exploded_counts(filter_category(df, "enforcement"), "violated_articles"),
        "enforcement_case_types": exploded_counts(filter_category(df, "enforcement"), "case_type"),
        "factor_counts": exploded_counts(filter_category(df, "enforcement"), "factors"),
        "monetary_amount_by_year": monetary_amount_by_year(filter_category(df, "enforcement")),
        "top_monetary_cases": top_monetary_cases(filter_category(df, "enforcement")),
        "impact_review_applicants": top_values(filter_category(df, "privacy_impact_review"), "applicant", 30),
        "impact_review_recommendation_by_year": impact_review_recommendation_by_year(df),
        "data_request_applicants": top_values(filter_category(df, "data_provision_request"), "applicant", 30),
        "public_system_applicants": top_values(filter_category(df, "public_system_inspection"), "applicant", 30),
        "article_by_category": article_by_category(df),
        "title_templates": title_templates(df),
        "citation_index": citation_index(df),
        "review_samples": review_samples(df),
    }
    for name, table in tables.items():
        table.to_csv(tables_dir / f"{name}.csv", index=False)

    report = reports_dir / "insights.md"
    report.write_text(render_report(df, tables), encoding="utf-8")
    return report


def ensure_columns(df: pd.DataFrame) -> None:
    for column in ["document_category", "sanction_types", "violated_articles", "case_type", "factors"]:
        if column not in df:
            df[column] = ""
    for column in ["title", "order_text", "reason_text", "summary_text", "applicant", "decision_date"]:
        if column not in df:
            df[column] = ""
    df["year"] = df["decision_date"].fillna("").astype(str).str[:4]
    df.loc[~df["year"].str.match(r"\d{4}", na=False), "year"] = ""
    df["category_label"] = df["document_category"].fillna("other").map(CATEGORY_LABELS).fillna(df["document_category"])


def render_report(df: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> str:
    total = len(df)
    categories = tables["document_category_counts"]
    enforcement = filter_category(df, "enforcement")
    impact = filter_category(df, "privacy_impact_review")
    inspections = filter_category(df, "public_system_inspection")
    data_requests = filter_category(df, "data_provision_request")
    money = enforcement["monetary_amount"].dropna()
    max_case = tables["top_monetary_cases"].head(1)

    lines = [
        "# PIPC Decision Insights",
        "",
        "## Executive Summary",
        "",
        f"- 분석 대상은 개인정보보호위원회 결정문 {total:,}건이다.",
        f"- 가장 큰 장르는 침해요인 평가 {len(impact):,}건, 법규 위반·제재 {len(enforcement):,}건, 공공시스템·실태점검 {len(inspections):,}건이다.",
        f"- 제재 장르 중 금액 추출 가능 사건은 {int(money.notna().sum()):,}건이며, 중앙값은 {format_won(money.median()) if not money.empty else 'n/a'}이다.",
        f"- 개인정보 제공 요청 장르는 {len(data_requests):,}건으로, 목적 외 제공·영상정보 제공 쟁점을 별도 트랙으로 볼 필요가 있다.",
        "- 같은 단어라도 장르에 따라 의미가 달라진다. 예를 들어 침해요인 평가는 제목상 `침해`가 포함되지만 유출·침해 사건으로 해석하면 안 된다.",
        "",
        "## Corpus Composition",
        "",
        markdown_table(categories),
        "",
        "## Time Trend",
        "",
        "- 2022년 이후 결정문 수가 크게 증가하며, 특히 침해요인 평가와 법규 위반·제재 안건이 전체 구조를 좌우한다.",
        "- 연도별·장르별 원자료는 `reports/tables/year_category_counts.csv`에 있다.",
        "",
        "## Enforcement Track",
        "",
        f"- 법규 위반·제재 장르는 {len(enforcement):,}건이다.",
        "- 제재 강도 분포:",
        "",
        markdown_table(tables["enforcement_sanction_strength"]),
        "",
        "- 주요 제재 유형:",
        "",
        markdown_table(tables["enforcement_sanction_types"].head(12)),
        "",
        "- 주요 조문:",
        "",
        markdown_table(tables["enforcement_articles"].head(15)),
        "",
        "- 주요 사건 유형:",
        "",
        markdown_table(tables["enforcement_case_types"].head(15)),
        "",
        "- 주요 factor:",
        "",
        markdown_table(tables["factor_counts"].head(15)),
        "",
    ]

    if not max_case.empty:
        row = max_case.iloc[0]
        lines.extend(
            [
                f"- 최대 금액 추출 사건은 decision_id `{row['decision_id']}`이며 추출 금액은 {format_won(row['monetary_amount'])}이다.",
                "",
            ]
        )

    lines.extend(
        [
            "## Privacy Impact Review Track",
            "",
            f"- 침해요인 평가는 {len(impact):,}건으로 전체의 {len(impact) / total:.1%}를 차지한다.",
            "- 신청기관 상위:",
            "",
            markdown_table(tables["impact_review_applicants"].head(15)),
            "",
            "- 연도별 권고성 주문 비율은 `reports/tables/impact_review_recommendation_by_year.csv`에서 확인한다.",
            "",
            "## Public Sector And Data Provision Track",
            "",
            f"- 공공시스템·실태점검 장르는 {len(inspections):,}건, 개인정보 제공 요청 장르는 {len(data_requests):,}건이다.",
            "- 이 트랙은 민간 제재 사건과 별도로, 공공부문 시스템 관리·법정 업무수행 근거·목적 외 제공 통제 관점에서 분석해야 한다.",
            "",
            "## Data Quality And Use Notes",
            "",
            "- 일부 과거 결정문은 제목 필드에 본문이 결합되어 있거나 제목이 비어 있다. 장기적으로 원문 구조별 보정 규칙이 필요하다.",
            "- `background_text`와 `main_text`는 현재 API XML에서 대부분 비어 있다. 실질 본문은 주로 `order_text`, `reason_text`, `summary_text`, `appendix_text`에 있다.",
            "- 금액 추출은 정규식 기반이므로 과징금·과태료 합산표가 있는 결정문에서는 최대값 중심의 보수적 지표로 해석해야 한다.",
            "- 현재 사건유형·factor는 규칙 기반 1차 라벨이다. 직원 공유 전에는 장르별 표본 검수와 규칙 보강이 필요하다.",
            "- `reports/tables/review_samples.csv`는 장르별 표본 검수용이고, `reports/tables/citation_index.csv`는 결정문 ID 기반 탐색용이다.",
            "",
            "## Recommended Next Analyses",
            "",
            "1. 제재 사건만 대상으로 사건유형·factor 라벨을 정밀화한다.",
            "2. 침해요인 평가 별지에서 개인정보 항목, 민감정보, 고유식별정보, 보유기간, 위탁, 연계 쟁점을 별도 추출한다.",
            "3. 문장 또는 문단 단위 청크를 만들어 조문·쟁점·제재별 검색 가능한 RAG 인덱스를 구축한다.",
            "4. 임베딩 클러스터링으로 반복 사실관계와 대표 결정문을 도출한다.",
            "5. 제재 장르에 한정해 제재 강도와 금액 제재 여부 회귀 분석을 수행한다.",
        ]
    )
    return "\n".join(lines) + "\n"


def document_category_counts(df: pd.DataFrame) -> pd.DataFrame:
    counts = (
        df.assign(document_category=df["document_category"].fillna("other"))
        .groupby(["document_category", "category_label"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    counts["share"] = counts["count"] / counts["count"].sum()
    return counts


def year_category_counts(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df[df["year"] != ""]
        .groupby(["year", "document_category", "category_label"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["year", "count"], ascending=[True, False])
    )


def category_missing_rates(df: pd.DataFrame) -> pd.DataFrame:
    fields = ["title", "agenda_no", "meeting_type", "applicant", "order_text", "reason_text", "summary_text", "appendix_text"]
    rows = []
    for category, group in df.groupby("document_category", dropna=False):
        for field in fields:
            rows.append(
                {
                    "document_category": category,
                    "field": field,
                    "missing_rate": group[field].isna().mean(),
                }
            )
    return pd.DataFrame(rows)


def category_length_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for category, group in df.groupby("document_category", dropna=False):
        for field in ["order_length", "reason_length", "document_length"]:
            if field in group:
                rows.append(
                    {
                        "document_category": category,
                        "field": field,
                        "count": len(group),
                        "mean": group[field].mean(),
                        "median": group[field].median(),
                        "max": group[field].max(),
                    }
                )
    return pd.DataFrame(rows)


def enforcement_sanction_strength(df: pd.DataFrame) -> pd.DataFrame:
    subset = filter_category(df, "enforcement")
    if subset.empty:
        return pd.DataFrame(columns=["sanction_strength", "count", "share"])
    out = subset["sanction_strength"].fillna(0).astype(int).value_counts().sort_index().reset_index()
    out.columns = ["sanction_strength", "count"]
    out["share"] = out["count"] / out["count"].sum()
    return out


def monetary_amount_by_year(df: pd.DataFrame) -> pd.DataFrame:
    subset = df[df["monetary_amount"].notna() & (df["year"] != "")]
    if subset.empty:
        return pd.DataFrame(columns=["year", "count", "median", "mean", "max"])
    return (
        subset.groupby("year")["monetary_amount"]
        .agg(["count", "median", "mean", "max"])
        .reset_index()
    )


def top_monetary_cases(df: pd.DataFrame, limit: int = 30) -> pd.DataFrame:
    columns = ["decision_id", "decision_date", "title", "monetary_amount", "sanction_types", "violated_articles", "case_type"]
    subset = df[df["monetary_amount"].notna()].sort_values("monetary_amount", ascending=False)
    return subset[columns].head(limit)


def impact_review_recommendation_by_year(df: pd.DataFrame) -> pd.DataFrame:
    subset = filter_category(df, "privacy_impact_review")
    if subset.empty:
        return pd.DataFrame(columns=["year", "count", "recommendation_count", "recommendation_rate"])
    rec = subset["order_text"].fillna("").str.contains(r"권고|변경|보완|개선", regex=True)
    out = subset.assign(is_recommendation=rec).groupby("year").agg(
        count=("decision_id", "size"),
        recommendation_count=("is_recommendation", "sum"),
    ).reset_index()
    out = out[out["year"] != ""]
    out["recommendation_rate"] = out["recommendation_count"] / out["count"]
    return out


def article_by_category(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        category = row.get("document_category", "other")
        for article in split_items(row.get("violated_articles", "")):
            rows.append({"document_category": category, "article": article})
    if not rows:
        return pd.DataFrame(columns=["document_category", "article", "count"])
    return pd.DataFrame(rows).value_counts(["document_category", "article"]).reset_index(name="count")


def title_templates(df: pd.DataFrame) -> pd.DataFrame:
    values = df["title"].fillna("(missing)").replace("", "(missing)").value_counts().head(100)
    return values.rename_axis("title").reset_index(name="count")


def citation_index(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "decision_id",
        "decision_date",
        "document_category",
        "title",
        "applicant",
        "sanction_strength",
        "sanction_types",
        "monetary_amount",
        "violated_articles",
        "case_type",
        "raw_xml_path",
    ]
    return df[columns].sort_values(["document_category", "decision_date", "decision_id"])


def review_samples(df: pd.DataFrame, per_category: int = 12) -> pd.DataFrame:
    samples = []
    sort_columns = ["document_category", "decision_date", "decision_id"]
    for category, group in df.sort_values(sort_columns).groupby("document_category", dropna=False):
        candidates = group.copy()
        if category == "enforcement":
            candidates = candidates.sort_values(["sanction_strength", "monetary_amount"], ascending=[False, False])
        samples.append(candidates.head(per_category))
    if not samples:
        return pd.DataFrame()
    columns = [
        "decision_id",
        "decision_date",
        "document_category",
        "title",
        "applicant",
        "order_text",
        "sanction_strength",
        "sanction_types",
        "monetary_amount",
        "violated_articles",
        "case_type",
        "factors",
    ]
    return pd.concat(samples, ignore_index=True)[columns]


def top_values(df: pd.DataFrame, column: str, limit: int) -> pd.DataFrame:
    if df.empty or column not in df:
        return pd.DataFrame(columns=[column, "count"])
    values = df[column].fillna("(missing)").replace("", "(missing)").value_counts().head(limit)
    return values.rename_axis(column).reset_index(name="count")


def exploded_counts(df: pd.DataFrame, column: str) -> pd.DataFrame:
    counter: Counter[str] = Counter()
    if df.empty or column not in df:
        return pd.DataFrame(columns=[column, "count"])
    for value in df[column].fillna("").astype(str):
        for item in split_items(value):
            counter[item] += 1
    return pd.DataFrame(counter.most_common(), columns=[column, "count"])


def split_items(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return [item for item in str(value).split(";") if item and item.lower() != "nan"]


def filter_category(df: pd.DataFrame, category: str) -> pd.DataFrame:
    return df[df["document_category"].fillna("other") == category].copy()


def format_won(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    value = int(value)
    if value >= 100_000_000:
        return f"{value / 100_000_000:.1f}억원"
    if value >= 10_000:
        return f"{value / 10_000:.0f}만원"
    return f"{value:,}원"


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    display = df.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else f"{value:.4g}")
        else:
            display[column] = display[column].fillna("").astype(str)
    headers = [str(column) for column in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in display.iterrows():
        values = [str(row[column]).replace("|", "\\|").replace("\n", " ") for column in display.columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)
