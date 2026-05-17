from __future__ import annotations

from pathlib import Path
import math
import re

import pandas as pd

from .insights import ensure_columns, split_items
from .issue_taxonomy import EXTERNAL_ISSUES


TEXT_COLUMNS = ["title", "order_text", "reason_text", "summary_text", "appendix_text"]

SECTOR_PATTERNS = {
    "통신": r"통신|이동통신|기간통신|텔레콤|SKT|KT|LG유플러스",
    "플랫폼·광고": r"플랫폼|광고|행태정보|맞춤형|쿠키|SDK|구글|메타|페이스북|인스타그램",
    "공공": r"공공기관|지방자치단체|시청|구청|군청|부처|위원회|공단|공사|교육청",
    "의료·보건": r"병원|의료|보건|질병|환자|건강|국민건강보험",
    "금융·보험": r"금융|은행|보험|카드|증권|대출",
    "식음료·프랜차이즈": r"식음료|프랜차이즈|커피|버거|음식|배달",
    "숙박·여행": r"숙박|호텔|여행|관광|예약",
    "교육·아동": r"학교|교육|아동|청소년|어린이|학생",
    "모빌리티·교통": r"자동차|교통|주차|운전|차량|모빌리티",
    "게임·콘텐츠": r"게임|콘텐츠|음악|영상|스포츠",
}


def generate_deep_quant_tables(processed_path: Path, reports_dir: Path) -> list[Path]:
    df = pd.read_csv(processed_path)
    ensure_columns(df)
    out_dir = reports_dir / "tables" / "deep"
    out_dir.mkdir(parents=True, exist_ok=True)

    features = decision_features(df, reports_dir)
    issue_panel = issue_panel_table(features)
    subtype_panel = subtype_panel_table(features)
    work_queue = analysis_work_queue()

    outputs = [
        (out_dir / "decision_features.csv", features),
        (out_dir / "issue_panel.csv", issue_panel),
        (out_dir / "type_subtype_panel.csv", subtype_panel),
        (out_dir / "analysis_work_queue.csv", work_queue),
        (out_dir / "feature_dictionary.csv", feature_dictionary(features)),
    ]
    for path, table in outputs:
        table.to_csv(path, index=False)
    return [path for path, _ in outputs]


def decision_features(df: pd.DataFrame, reports_dir: Path) -> pd.DataFrame:
    data = df.copy()
    data["analysis_text"] = composite_text(data)
    data["year_num"] = pd.to_numeric(data["year"], errors="coerce")
    data["period"] = data["year_num"].map(period_label)
    data["post_2020"] = (data["year_num"] >= 2020).astype(int)
    data["post_2022"] = (data["year_num"] >= 2022).astype(int)

    add_split_flags(data, "sanction_types", "sanction")
    add_split_flags(data, "case_type", "case")
    add_split_flags(data, "factors", "factor")
    add_issue_flags(data)
    add_sector_flags(data)
    add_outcomes(data)
    add_topic_clusters(data, reports_dir)

    keep = [
        "decision_id",
        "decision_date",
        "year",
        "year_num",
        "period",
        "post_2020",
        "post_2022",
        "document_category",
        "category_label",
        "meeting_type",
        "decision_type",
        "applicant",
        "title",
        "sanction_strength",
        "monetary_amount",
        "log_monetary_amount",
        "has_monetary_amount",
        "document_length",
        "order_length",
        "reason_length",
        "topic_cluster",
        "topic_label",
        "topic_subtitle",
    ]
    generated = [column for column in data.columns if column.startswith(("sanction_", "case_", "factor_", "issue_", "sector_", "outcome_"))]
    ordered = []
    for column in keep + generated:
        if column in data.columns and column not in ordered:
            ordered.append(column)
    return data[ordered]


def composite_text(df: pd.DataFrame) -> pd.Series:
    text = pd.Series([""] * len(df), index=df.index)
    for column in TEXT_COLUMNS:
        if column in df:
            text = text + "\n" + df[column].fillna("").astype(str)
    return text


def period_label(year: float) -> str:
    if pd.isna(year):
        return "unknown"
    value = int(year)
    if value <= 2017:
        return "2012-2017"
    if value <= 2021:
        return "2018-2021"
    return "2022-2026"


def add_split_flags(df: pd.DataFrame, column: str, prefix: str) -> None:
    values = sorted({item for value in df[column].fillna("") for item in split_items(value)})
    for value in values:
        safe = safe_name(value)
        df[f"{prefix}_{safe}"] = df[column].fillna("").map(lambda raw, item=value: int(item in split_items(raw)))


def add_issue_flags(df: pd.DataFrame) -> None:
    for issue in EXTERNAL_ISSUES:
        df[f"issue_{issue.issue_id:02d}"] = df["analysis_text"].str.contains(issue.pattern, regex=True, na=False).astype(int)


def add_sector_flags(df: pd.DataFrame) -> None:
    for sector, pattern in SECTOR_PATTERNS.items():
        df[f"sector_{safe_name(sector)}"] = df["analysis_text"].str.contains(pattern, regex=True, na=False).astype(int)


def add_outcomes(df: pd.DataFrame) -> None:
    amount = pd.to_numeric(df["monetary_amount"], errors="coerce")
    df["has_monetary_amount"] = amount.notna().astype(int)
    df["log_monetary_amount"] = amount.where(amount > 0).map(lambda value: pd.NA if pd.isna(value) else math.log1p(float(value)))
    df["outcome_high_sanction"] = (pd.to_numeric(df["sanction_strength"], errors="coerce").fillna(0) >= 3).astype(int)
    df["outcome_has_fine"] = df.get("sanction_types", "").fillna("").str.contains("과징금|과태료", regex=True).astype(int)
    df["outcome_has_publication"] = df.get("sanction_types", "").fillna("").str.contains("공표명령", regex=False).astype(int)
    df["outcome_has_correction"] = df.get("sanction_types", "").fillna("").str.contains("시정명령", regex=False).astype(int)
    df["outcome_has_recommendation"] = df.get("order_text", "").fillna("").str.contains("권고|개선", regex=True).astype(int)
    df["outcome_data_request_allowed"] = df.get("order_text", "").fillna("").str.contains(r"수\s*있다|제공받을\s*수\s*있|제공할\s*수\s*있", regex=True).astype(int)
    df["outcome_data_request_denied"] = df.get("order_text", "").fillna("").str.contains(r"수\s*없다|제공받을\s*수\s*없|제공할\s*수\s*없", regex=True).astype(int)


def add_topic_clusters(df: pd.DataFrame, reports_dir: Path) -> None:
    path = reports_dir / "tables" / "type_topic_maps" / "assignments.csv"
    clusters_path = reports_dir / "tables" / "type_topic_maps" / "clusters.csv"
    df["topic_cluster"] = pd.NA
    df["topic_label"] = ""
    df["topic_subtitle"] = ""
    if not path.exists():
        return
    assignments = pd.read_csv(path)
    clusters = pd.read_csv(clusters_path) if clusters_path.exists() else pd.DataFrame()
    assignments["decision_id"] = assignments["decision_id"].astype(str)
    merge_cols = ["document_category", "decision_id", "cluster"]
    merged = assignments[merge_cols].rename(columns={"cluster": "topic_cluster"})
    if not clusters.empty:
        clusters = clusters.rename(columns={"cluster_idx": "topic_cluster"})
        merged = merged.merge(
            clusters[["document_category", "topic_cluster", "label", "subtitle"]],
            on=["document_category", "topic_cluster"],
            how="left",
        )
    df["decision_id"] = df["decision_id"].astype(str)
    out = df[["decision_id", "document_category"]].merge(merged, on=["decision_id", "document_category"], how="left")
    df["topic_cluster"] = out["topic_cluster"].values
    df["topic_label"] = out.get("label", pd.Series([""] * len(df))).fillna("").values
    df["topic_subtitle"] = out.get("subtitle", pd.Series([""] * len(df))).fillna("").values


def issue_panel_table(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    base_cols = ["decision_id", "decision_date", "year", "document_category", "sanction_strength", "monetary_amount"]
    outcome_cols = [column for column in features.columns if column.startswith("outcome_")]
    for issue in EXTERNAL_ISSUES:
        issue_col = f"issue_{issue.issue_id:02d}"
        subset = features[features[issue_col] == 1]
        for _, row in subset.iterrows():
            item = {column: row.get(column, "") for column in base_cols + outcome_cols}
            item.update({"issue_id": issue.issue_id, "issue_label": issue.korean_label})
            rows.append(item)
    return pd.DataFrame(rows)


def subtype_panel_table(features: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "decision_id",
        "decision_date",
        "year",
        "document_category",
        "topic_cluster",
        "topic_label",
        "topic_subtitle",
        "sanction_strength",
        "monetary_amount",
    ]
    factor_cols = [column for column in features.columns if column.startswith("factor_")]
    outcome_cols = [column for column in features.columns if column.startswith("outcome_")]
    return features[[column for column in cols + factor_cols + outcome_cols if column in features.columns]].copy()


def analysis_work_queue() -> pd.DataFrame:
    rows = []
    issue_order = [2, 3, 1, 4, 7, 6, 9, 10, 11, 8, 5]
    for rank, issue_id in enumerate(issue_order, start=1):
        issue = next(item for item in EXTERNAL_ISSUES if item.issue_id == issue_id)
        rows.append({"phase": "issue", "rank": rank, "target": f"issue_{issue_id:02d}", "label": issue.korean_label})
    type_order = [
        ("enforcement", "법규 위반·제재"),
        ("privacy_impact_review", "침해요인 평가"),
        ("data_provision_request", "개인정보 제공 요청"),
        ("public_system_inspection", "공공시스템·실태점검"),
        ("interpretation_other", "민원·해석·기타"),
    ]
    for rank, (target, label) in enumerate(type_order, start=1):
        rows.append({"phase": "type", "rank": rank, "target": target, "label": label})
    return pd.DataFrame(rows)


def feature_dictionary(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in features.columns:
        if column.startswith("issue_"):
            kind = "issue flag"
        elif column.startswith("factor_"):
            kind = "factor flag"
        elif column.startswith("case_"):
            kind = "case type flag"
        elif column.startswith("sector_"):
            kind = "sector flag"
        elif column.startswith("outcome_"):
            kind = "outcome"
        elif column.startswith("sanction_"):
            kind = "sanction flag"
        else:
            kind = "metadata"
        rows.append({"feature": column, "kind": kind, "non_null": int(features[column].notna().sum())})
    return pd.DataFrame(rows)


def safe_name(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z가-힣]+", "_", value.strip()).strip("_")
    return text or "unknown"
