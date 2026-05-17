from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from .html_reports import html_document, horizontal_bar, metric_cards, note, section, table, vertical_bar, write_css
from .issue_taxonomy import EXTERNAL_ISSUES, ExternalIssue


FACTOR_PREFIXES = ("factor_", "case_", "sector_")


@dataclass(frozen=True)
class ModelResult:
    ok: bool
    auc: float | None
    coefficients: pd.DataFrame
    message: str


TYPE_SPECS = {
    "enforcement": {
        "label": "법규 위반·제재",
        "outcome": "outcome_high_sanction",
        "outcome_label": "고강도 제재",
        "root": "enforcement",
        "help": "제재 강도와 금액 제재를 높이는 반복 factor를 우선순위화하는 데 직접 도움이 된다.",
    },
    "privacy_impact_review": {
        "label": "침해요인 평가",
        "outcome": "outcome_has_recommendation",
        "outcome_label": "권고성 주문",
        "root": "privacy_impact",
        "help": "법령 설계 단계에서 어떤 분야·개인정보 처리요소가 권고로 연결되는지 점검하는 데 도움이 된다.",
    },
    "data_provision_request": {
        "label": "개인정보 제공 요청",
        "outcome": "outcome_data_request_allowed",
        "outcome_label": "제공 허용",
        "root": "data_provision",
        "help": "목적 외 제공 요청에서 허용·불허 판단의 반복 패턴을 분리하는 데 도움이 된다.",
    },
    "public_system_inspection": {
        "label": "공공시스템·실태점검",
        "outcome": "outcome_has_recommendation",
        "outcome_label": "개선권고",
        "root": "public_system",
        "help": "공공시스템 예방감독 checklist와 반복 취약점 관리에 도움이 된다.",
    },
    "interpretation_other": {
        "label": "민원·해석·기타",
        "outcome": "outcome_has_recommendation",
        "outcome_label": "권고·개선 신호",
        "root": "interpretation_other",
        "help": "제재 선례보다 해석 기준과 재분류 후보를 찾는 데 도움이 된다.",
    },
}


def generate_deep_quant_reports(reports_dir: Path) -> list[Path]:
    deep_dir = reports_dir / "deep_quant"
    issues_dir = deep_dir / "issues"
    types_dir = deep_dir / "types"
    issues_dir.mkdir(parents=True, exist_ok=True)
    types_dir.mkdir(parents=True, exist_ok=True)
    write_css(reports_dir / "style.css")

    features = pd.read_csv(reports_dir / "tables" / "deep" / "decision_features.csv")
    issue_paths = []
    issue_summaries = []
    for issue in EXTERNAL_ISSUES:
        path = issues_dir / f"issue_{issue.issue_id:02d}.html"
        summary = issue_summary(features, issue)
        path.write_text(render_issue_report(features, issue, summary), encoding="utf-8")
        issue_paths.append(path)
        issue_summaries.append(summary)

    type_paths = []
    type_summaries = []
    for key in TYPE_SPECS:
        path = types_dir / f"{key}.html"
        summary = type_summary(features, key)
        path.write_text(render_type_report(features, key, summary), encoding="utf-8")
        type_paths.append(path)
        type_summaries.append(summary)

    index_path = deep_dir / "index.html"
    index_path.write_text(render_index(features, issue_summaries, type_summaries), encoding="utf-8")
    return [index_path] + issue_paths + type_paths


def issue_summary(features: pd.DataFrame, issue: ExternalIssue) -> dict:
    col = f"issue_{issue.issue_id:02d}"
    matched = features[features[col] == 1].copy()
    rest = features[features[col] == 0].copy()
    enforcement = features[features["document_category"] == "enforcement"].copy()
    matched_enforcement = matched[matched["document_category"] == "enforcement"].copy()

    high_rate = rate(matched_enforcement, "outcome_high_sanction")
    base_high_rate = rate(enforcement, "outcome_high_sanction")
    fine_rate = rate(matched_enforcement, "outcome_has_fine")
    base_fine_rate = rate(enforcement, "outcome_has_fine")
    post_rate = rate(matched, "post_2022")
    rest_post_rate = rate(rest, "post_2022")
    high_or, high_p = odds_ratio_test(enforcement[col], enforcement["outcome_high_sanction"])
    post_or, post_p = odds_ratio_test(features[col], features["post_2022"])

    model = issue_factor_model(matched_enforcement)
    top_factors = top_binary_columns(matched, "factor_", 8)
    top_categories = matched["category_label"].fillna(matched["document_category"]).value_counts().head(6).reset_index()
    top_categories.columns = ["결정문 유형", "건수"]

    status = {
        "현황": decide_status(
            matched=len(matched),
            text=(
                f"{len(matched):,}건이 매칭되며 전체의 {len(matched) / len(features):.1%}이다. "
                f"2022년 이후 비중은 {post_rate:.1%}로 비매칭 결정문 {rest_post_rate:.1%}와 비교된다. "
                f"시기 집중성 OR={post_or:.2f}, p={format_p(post_p)}."
            ),
            confirmed=len(matched) >= 40 and (post_p < 0.05 or abs(post_rate - rest_post_rate) >= 0.08),
            not_found=f"{issue.korean_label}의 시기적 집중 또는 충분한 매칭 규모를 검증했는데 확인되지 못함.",
        ),
        "원인": decide_status(
            matched=len(matched_enforcement),
            text=(
                f"제재 사건 내부에서 고강도 제재율은 {high_rate:.1%}이며 제재 전체 기준 {base_high_rate:.1%}와 비교된다. "
                f"쟁점 매칭과 고강도 제재의 OR={high_or:.2f}, p={format_p(high_p)}. "
                f"factor 모형은 {model.message}"
            ),
            confirmed=(high_p < 0.05 and high_or > 1.2) or model.ok,
            not_found=f"{issue.korean_label}와 제재 강도 또는 factor 설명력의 연결을 검증했는데 확인되지 못함.",
        ),
        "해결책": decide_status(
            matched=len(matched_enforcement),
            text=solution_statement(model, matched_enforcement),
            confirmed=solution_confirmed(model),
            not_found=f"{issue.korean_label}에서 사후 시정 노력 또는 관리체계 factor가 제재 완화 방향으로 작동하는지 검증했는데 확인되지 못함.",
        ),
    }

    return {
        "issue": issue,
        "n": len(matched),
        "enforcement_n": len(matched_enforcement),
        "high_rate": high_rate,
        "base_high_rate": base_high_rate,
        "fine_rate": fine_rate,
        "base_fine_rate": base_fine_rate,
        "post_rate": post_rate,
        "status": status,
        "top_factors": top_factors,
        "top_categories": top_categories,
        "model": model,
    }


def render_issue_report(features: pd.DataFrame, issue: ExternalIssue, summary: dict) -> str:
    matched = features[features[f"issue_{issue.issue_id:02d}"] == 1].copy()
    model = summary["model"]
    cards = metric_cards(
        [
            ("매칭 결정문", f"{summary['n']:,}", "쟁점 regex 기준"),
            ("제재 사건", f"{summary['enforcement_n']:,}", "법규 위반·제재"),
            ("고강도 제재율", pct(summary["high_rate"]), f"제재 전체 {pct(summary['base_high_rate'])}"),
            ("금액 제재율", pct(summary["fine_rate"]), f"제재 전체 {pct(summary['base_fine_rate'])}"),
        ]
    )
    body = cards
    body += section("현황", status_box(summary["status"]["현황"]))
    body += section("원인", status_box(summary["status"]["원인"]) + model_table(model))
    body += section("해결책", status_box(summary["status"]["해결책"]))
    body += section("결정문 유형 분포", table(summary["top_categories"]))
    body += section("상위 Factor", horizontal_bar(summary["top_factors"]["label"], summary["top_factors"]["count"], "건수"))
    body += section("연도별 매칭", vertical_bar(*year_counts(matched), "건수"))
    body += section("검수용 대표 결정문", table(representative_decisions(matched)))
    body += note("이 분석은 결정문 텍스트의 자동 라벨과 사전 기반 factor를 사용한다. 계수는 법적 인과효과가 아니라 문서상 판단 구조의 통계적 신호로 해석해야 한다.")
    return html_document(f"{issue.korean_label} 심층 계량분석", "현황·원인·해결책 검토", body, f"issue-{issue.issue_id:02d}", "../../", compact=True)


def type_summary(features: pd.DataFrame, key: str) -> dict:
    spec = TYPE_SPECS[key]
    if key == "interpretation_other":
        subset = features[features["document_category"].isin(["complaint_or_interpretation", "prior_review", "other"])].copy()
    else:
        subset = features[features["document_category"] == key].copy()
    outcome = spec["outcome"]
    model = fit_logistic_model(subset, outcome, predictor_columns(subset))
    subtypes = subtype_table(subset, outcome)
    factors = factor_weight_table(model)
    periods = period_factor_change(subset)
    subjects = subject_difference_table(subset, outcome)
    useful = model.ok and (model.auc or 0) >= 0.6 and len(subtypes) >= 3
    return {
        "key": key,
        "spec": spec,
        "n": len(subset),
        "outcome_rate": rate(subset, outcome),
        "model": model,
        "subtypes": subtypes,
        "factors": factors,
        "periods": periods,
        "subjects": subjects,
        "useful": useful,
    }


def render_type_report(features: pd.DataFrame, key: str, summary: dict) -> str:
    spec = summary["spec"]
    model = summary["model"]
    cards = metric_cards(
        [
            ("분석 결정문", f"{summary['n']:,}", spec["label"]),
            (spec["outcome_label"], pct(summary["outcome_rate"]), "주요 결과변수"),
            ("Sub 유형", f"{len(summary['subtypes']):,}", "토픽 기반 병합"),
            ("모형 AUC", f"{model.auc:.2f}" if model.auc is not None else "n/a", "훈련자료 내부 판별력"),
        ]
    )
    judgement = "이 유형별 분석은 개인정보위 공무원에게 도움이 되는 신호를 제공한다." if summary["useful"] else "이 유형별 분석은 탐색적 설명에는 도움이 되지만, 예측적 판단 근거로 쓰기에는 추가 라벨 검수가 필요하다."
    body = cards
    body += section("공무원 활용성 평가", f"<div class='summary-box'><strong>{escape(spec['label'])}</strong><p>{escape(judgement)} {escape(spec['help'])}</p></div>")
    body += section("Sub 유형", table(summary["subtypes"]))
    body += section("중요 Factor 가중치", model_table(model))
    body += section("시간에 따른 Factor 변화", table(summary["periods"]))
    body += section("주체별 차이", table(summary["subjects"]))
    body += note("Sub 유형은 OpenRouter 기반 토픽 라벨을 계량분석용으로 병합한 것이다. 표본 수가 작은 sub 유형은 해석보다 검수 우선순위로 보는 것이 적절하다.")
    return html_document(f"{spec['label']} 심층 계량분석", "Sub 유형·factor 가중치·시간/주체 차이", body, "types", "../../", compact=True)


def render_index(features: pd.DataFrame, issue_summaries: list[dict], type_summaries: list[dict]) -> str:
    issue_rows = []
    for summary in issue_summaries:
        issue = summary["issue"]
        issue_rows.append(
            {
                "쟁점": f"<a href='issues/issue_{issue.issue_id:02d}.html'>{issue.issue_id}. {escape(issue.korean_label)}</a>",
                "매칭": f"{summary['n']:,}",
                "제재": f"{summary['enforcement_n']:,}",
                "고강도 제재율": pct(summary["high_rate"]),
                "판정": "; ".join(f"{k}: {v['label']}" for k, v in summary["status"].items()),
            }
        )
    type_rows = []
    for summary in type_summaries:
        key = summary["key"]
        spec = summary["spec"]
        type_rows.append(
            {
                "유형": f"<a href='types/{key}.html'>{escape(spec['label'])}</a>",
                "건수": f"{summary['n']:,}",
                "결과변수": spec["outcome_label"],
                "결과율": pct(summary["outcome_rate"]),
                "AUC": f"{summary['model'].auc:.2f}" if summary["model"].auc is not None else "n/a",
            }
        )
    body = metric_cards(
        [
            ("결정문", f"{len(features):,}", "계량분석 데이터마트"),
            ("주요 쟁점", f"{len(issue_summaries):,}", "현황·원인·해결책"),
            ("결정문 유형", f"{len(type_summaries):,}", "sub 유형 회귀"),
            ("Feature", f"{len(features.columns):,}", "라벨·factor·outcome"),
        ]
    )
    body += section("주요 쟁점별 상세 분석", raw_table(pd.DataFrame(issue_rows)))
    body += section("유형별 상세 분석", raw_table(pd.DataFrame(type_rows)))
    body += note("최종 리포트는 '현황', '원인', '해결책' 구조로 작성했다. 확인되지 않은 항목은 검증했으나 확인되지 못한 것으로 표시했다.")
    return html_document("심층 계량분석", "결정문 텍스트 기반 계산사회과학 분석", body, "types", "../")


def issue_factor_model(df: pd.DataFrame) -> ModelResult:
    if len(df) < 40:
        return ModelResult(False, None, pd.DataFrame(), "표본 수가 작아 회귀계수 해석을 보류한다.")
    return fit_logistic_model(df, "outcome_high_sanction", predictor_columns(df))


def fit_logistic_model(df: pd.DataFrame, outcome: str, predictors: list[str]) -> ModelResult:
    data = df[[outcome] + predictors].dropna().copy()
    data = data.loc[:, ~data.columns.duplicated()]
    y = data[outcome].astype(int)
    predictors = [column for column in predictors if column in data.columns and data[column].nunique(dropna=True) > 1]
    if len(data) < 35 or len(predictors) < 2 or y.nunique() < 2:
        return ModelResult(False, None, pd.DataFrame(), "표본 또는 결과변수 변동이 부족하여 회귀계수 해석을 보류한다.")
    x = data[predictors].fillna(0).astype(float)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)
    model = LogisticRegression(max_iter=2000, class_weight="balanced", C=0.8)
    model.fit(x_scaled, y)
    prob = model.predict_proba(x_scaled)[:, 1]
    auc = roc_auc_score(y, prob) if y.nunique() == 2 else None
    coef = pd.DataFrame({"factor": predictors, "coefficient": model.coef_[0]})
    coef["direction"] = np.where(coef["coefficient"] >= 0, "증가", "감소")
    coef["abs_coefficient"] = coef["coefficient"].abs()
    coef = coef.sort_values("abs_coefficient", ascending=False).head(12)
    ok = auc is not None and auc >= 0.58 and not coef.empty
    message = f"AUC {auc:.2f}로 내부 판별력을 보이며 상위 factor는 {', '.join(clean_feature(x) for x in coef.head(3)['factor'])}이다." if auc is not None else "AUC 산출이 어렵다."
    return ModelResult(ok, auc, coef, message)


def predictor_columns(df: pd.DataFrame) -> list[str]:
    cols = [column for column in df.columns if column.startswith(FACTOR_PREFIXES)]
    leakage_terms = ["금전_제재", "공표_또는_시정명령"]
    cols = [column for column in cols if not any(term in column for term in leakage_terms)]
    cols += ["post_2022", "document_length", "reason_length"]
    topic_dummies = pd.get_dummies(df.get("topic_label", pd.Series(dtype=str)).fillna("").astype(str), prefix="topic")
    for column in topic_dummies.columns:
        if column not in df:
            df[column] = topic_dummies[column].astype(int)
    cols += [column for column in topic_dummies.columns if topic_dummies[column].sum() >= 8]
    return [column for column in cols if column in df.columns and pd.api.types.is_numeric_dtype(df[column])]


def factor_weight_table(model: ModelResult) -> pd.DataFrame:
    if model.coefficients.empty:
        return pd.DataFrame(columns=["factor", "coefficient", "direction"])
    out = model.coefficients[["factor", "coefficient", "direction"]].copy()
    out["factor"] = out["factor"].map(clean_feature)
    out["coefficient"] = out["coefficient"].map(lambda x: f"{x:.2f}")
    return out


def subtype_table(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    data = df.copy()
    data["subtype"] = data["topic_label"].fillna("")
    data.loc[data["subtype"].eq(""), "subtype"] = "미분류"
    grouped = (
        data.groupby("subtype", dropna=False)
        .agg(count=("decision_id", "size"), outcome_rate=(outcome, "mean"), median_amount=("monetary_amount", "median"))
        .reset_index()
        .sort_values("count", ascending=False)
        .head(10)
    )
    grouped["outcome_rate"] = grouped["outcome_rate"].map(pct)
    grouped["median_amount"] = grouped["median_amount"].map(lambda x: "" if pd.isna(x) else f"{x:,.0f}원")
    grouped.columns = ["Sub 유형", "건수", "결과율", "금액 중앙값"]
    return grouped


def period_factor_change(df: pd.DataFrame) -> pd.DataFrame:
    factors = top_binary_columns(df, "factor_", 6)["column"].tolist()
    rows = []
    for period, group in df.groupby("period", dropna=False):
        item = {"시기": period, "건수": len(group)}
        for factor in factors:
            item[clean_feature(factor)] = pct(group[factor].mean() if len(group) else 0)
        rows.append(item)
    return pd.DataFrame(rows).sort_values("시기")


def subject_difference_table(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    rows = []
    for column in [c for c in df.columns if c.startswith("sector_")]:
        subset = df[df[column] == 1]
        if len(subset) >= 20:
            rows.append({"주체/업권": clean_feature(column), "건수": len(subset), "결과율": pct(rate(subset, outcome))})
    out = pd.DataFrame(rows).sort_values("건수", ascending=False).head(10) if rows else pd.DataFrame(columns=["주체/업권", "건수", "결과율"])
    return out


def solution_statement(model: ModelResult, df: pd.DataFrame) -> str:
    if model.coefficients.empty:
        return "사후 시정 노력, 내부통제, 관리체계 관련 factor의 완화 방향을 검증했는데 확인되지 못함."
    coef = model.coefficients.set_index("factor")["coefficient"].to_dict()
    candidates = {
        "factor_사후_시정_노력": "사후 시정 노력",
        "factor_내부통제_및_안전조치_수준": "내부통제 및 안전조치",
        "factor_공표_또는_시정명령_여부": "공표 또는 시정명령",
    }
    reducing = [label for key, label in candidates.items() if coef.get(key, 0) < -0.1]
    if reducing:
        return f"{', '.join(reducing)} factor가 고강도 제재를 낮추는 방향의 계수로 나타났다. 다만 자동 라벨 기반이므로 대표 결정문 검수와 결합해야 한다."
    return "사후 시정 노력 또는 관리체계 factor가 고강도 제재를 낮추는 방향으로 작동하는지 검증했는데 확인되지 못함."


def solution_confirmed(model: ModelResult) -> bool:
    if model.coefficients.empty:
        return False
    coef = model.coefficients.set_index("factor")["coefficient"].to_dict()
    return any(coef.get(key, 0) < -0.1 for key in ["factor_사후_시정_노력", "factor_내부통제_및_안전조치_수준"])


def decide_status(matched: int, text: str, confirmed: bool, not_found: str) -> dict:
    if confirmed:
        return {"label": "확인됨", "text": text}
    return {"label": "확인되지 못함", "text": not_found if matched >= 10 else f"표본이 {matched:,}건으로 적어 {not_found}"}


def status_box(status: dict) -> str:
    return f"<div class='summary-box'><strong>{escape(status['label'])}</strong><p>{escape(status['text'])}</p></div>"


def model_table(model: ModelResult) -> str:
    if model.coefficients.empty:
        return f"<p>{escape(model.message)}</p>"
    return table(factor_weight_table(model))


def top_binary_columns(df: pd.DataFrame, prefix: str, limit: int) -> pd.DataFrame:
    rows = []
    for column in [c for c in df.columns if c.startswith(prefix)]:
        count = int(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())
        if count:
            rows.append({"column": column, "label": clean_feature(column), "count": count})
    return pd.DataFrame(rows).sort_values("count", ascending=False).head(limit) if rows else pd.DataFrame(columns=["column", "label", "count"])


def representative_decisions(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_id", "decision_date", "category_label", "title", "monetary_amount", "sanction_strength"]
    out = df.sort_values(["monetary_amount", "document_length"], ascending=[False, False], na_position="last").head(10)
    out = out[[c for c in cols if c in out.columns]].copy()
    if "monetary_amount" in out:
        out["monetary_amount"] = out["monetary_amount"].map(lambda x: "" if pd.isna(x) else f"{x:,.0f}원")
    return out


def year_counts(df: pd.DataFrame):
    counts = df[df["year"].fillna("") != ""].groupby("year").size().reset_index(name="count")
    return counts["year"], counts["count"]


def odds_ratio_test(flag: pd.Series, outcome: pd.Series) -> tuple[float, float]:
    x = pd.to_numeric(flag, errors="coerce").fillna(0).astype(int)
    y = pd.to_numeric(outcome, errors="coerce").fillna(0).astype(int)
    a = int(((x == 1) & (y == 1)).sum())
    b = int(((x == 1) & (y == 0)).sum())
    c = int(((x == 0) & (y == 1)).sum())
    d = int(((x == 0) & (y == 0)).sum())
    odds = ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))
    try:
        _, p, _, _ = chi2_contingency([[a, b], [c, d]])
    except ValueError:
        p = 1.0
    return odds, float(p)


def rate(df: pd.DataFrame, column: str) -> float:
    if df.empty or column not in df:
        return 0.0
    return float(pd.to_numeric(df[column], errors="coerce").fillna(0).mean())


def pct(value: float) -> str:
    return f"{value:.1%}" if pd.notna(value) else "n/a"


def format_p(value: float) -> str:
    if value < 0.001:
        return "<0.001"
    return f"{value:.3f}"


def clean_feature(value: str) -> str:
    for prefix in ["factor_", "case_", "sector_", "sanction_", "topic_"]:
        if value.startswith(prefix):
            value = value[len(prefix) :]
    return value.replace("_", " ")


def raw_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "<p>No rows.</p>"
    html = "<div class='table-wrap'><table><thead><tr>"
    html += "".join(f"<th>{escape(str(column))}</th>" for column in df.columns)
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr>" + "".join(f"<td>{row[column]}</td>" for column in df.columns) + "</tr>"
    html += "</tbody></table></div>"
    return html
