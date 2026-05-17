from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path
import re

import pandas as pd

from .html_reports import (
    count_category,
    exploded,
    format_won,
    horizontal_bar,
    metric_cards,
    note,
    page,
    pct,
    section,
    stacked_bar,
    table,
    top_money,
    top_values,
    vertical_bar,
    write_css,
    year_category_counts,
    year_counts,
)
from .insights import CATEGORY_LABELS, ensure_columns, filter_category, split_items


ISSUE_TERMS = {
    "민감정보": r"민감정보",
    "고유식별정보": r"고유식별정보|주민등록번호|여권번호|운전면허",
    "보유기간": r"보유기간|보존기간",
    "파기": r"파기",
    "위탁": r"위탁|수탁",
    "제3자 제공": r"제3자\s*제공|제삼자\s*제공",
    "목적 외 이용": r"목적\s*외",
    "동의": r"동의",
    "국외이전": r"국외\s*이전|해외\s*이전",
    "영상정보": r"영상정보|CCTV|폐쇄회로",
    "아동": r"아동|만\s*14세",
    "안전조치": r"안전조치|접근통제|암호화|관리적·?기술적",
}


def generate_full_reports(processed_path: Path, reports_dir: Path) -> list[Path]:
    df = pd.read_csv(processed_path)
    ensure_columns(df)
    out_dir = reports_dir / "full_html"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_css(out_dir / "style.css")

    tables_dir = reports_dir / "tables" / "full"
    tables_dir.mkdir(parents=True, exist_ok=True)
    write_full_tables(df, tables_dir)

    pages = [
        ("index.html", render_full_index(df)),
        ("overview.html", render_full_overview(df)),
        ("enforcement.html", render_full_enforcement(df)),
        ("privacy_impact.html", render_full_privacy_impact(df)),
        ("public_system.html", render_full_public_system(df)),
        ("data_provision.html", render_full_data_provision(df)),
        ("interpretation_other.html", render_full_interpretation_other(df)),
        ("data_quality.html", render_full_data_quality(df)),
    ]

    written = []
    for filename, html in pages:
        path = out_dir / filename
        path.write_text(html, encoding="utf-8")
        written.append(path)
    return written


def write_full_tables(df: pd.DataFrame, tables_dir: Path) -> None:
    enforcement = filter_category(df, "enforcement")
    impact = filter_category(df, "privacy_impact_review")
    provision = filter_category(df, "data_provision_request")
    public = filter_category(df, "public_system_inspection")

    enforcement_package_counts(enforcement).to_csv(tables_dir / "enforcement_package_counts.csv", index=False)
    article_pair_counts(enforcement).to_csv(tables_dir / "enforcement_article_pairs.csv", index=False)
    money_bands(enforcement).to_csv(tables_dir / "enforcement_money_bands.csv", index=False)
    issue_term_counts(impact).to_csv(tables_dir / "impact_review_issue_terms.csv", index=False)
    law_name_counts(impact).to_csv(tables_dir / "impact_review_laws.csv", index=False)
    provision_outcomes(provision).to_csv(tables_dir / "data_provision_outcomes.csv", index=False)
    issue_term_counts(provision).to_csv(tables_dir / "data_provision_issue_terms.csv", index=False)
    title_family_counts(public).to_csv(tables_dir / "public_system_title_families.csv", index=False)
    category_period_counts(df).to_csv(tables_dir / "category_period_counts.csv", index=False)


def render_full_index(df: pd.DataFrame) -> str:
    body = metric_cards(
        [
            ("전체 결정문", f"{len(df):,}", "수집·파싱 완료"),
            ("상세 섹션", "7", "장르별 보고서"),
            ("제재 분석", f"{len(filter_category(df, 'enforcement')):,}", "전용 트랙"),
            ("침해요인 평가", f"{len(filter_category(df, 'privacy_impact_review')):,}", "전용 트랙"),
        ]
    )
    body += section(
        "Full Report 구성",
        table(
            pd.DataFrame(
                [
                    ["전체 구조", "장르별 비중, 시기별 변화, 코퍼스 구조"],
                    ["법규 위반·제재", "제재 조합, 금액구간, 조문쌍, 사건유형·factor"],
                    ["침해요인 평가", "신청기관, 법령명, 권고율, 반복 쟁점"],
                    ["공공시스템·실태점검", "실태점검 흐름, 개선권고, 기관·제목군"],
                    ["개인정보 제공 요청", "허용/불허, 영상정보, 목적 외 제공 쟁점"],
                    ["민원·해석·기타", "해석성 안건, 정책성 안건, 조문 중심 쟁점"],
                    ["데이터 품질", "결측, 중복, 라벨 검수, 다음 개선 대상"],
                ],
                columns=["섹션", "분석 관점"],
            )
        ),
    )
    body += note("이 보고서는 규칙 기반 1차 분석이다. 표본 검수로 주요 오탐을 줄였지만, 직원 공유 전 고액 제재·기타 장르를 중심으로 추가 검수가 필요하다.")
    return page("Full Insight Report", "섹션별 상세 분석 보고서", body, "index")


def render_full_overview(df: pd.DataFrame) -> str:
    category_counts = count_category(df)
    periods = category_period_counts(df)
    pivot = periods.pivot_table(index="period", columns="category_label", values="count", fill_value=0).reset_index()
    body = metric_cards(
        [
            ("결정문", f"{len(df):,}", "전체 코퍼스"),
            ("최대 장르", "침해요인 평가", f"{len(filter_category(df, 'privacy_impact_review')):,}건"),
            ("2022년 이후", f"{post_2022_count(df):,}", "결정문 증가 구간"),
            ("기타 장르", f"{len(filter_category(df, 'other')):,}", "추가 정제 대상"),
        ]
    )
    body += section("핵심 인사이트", insight_list(overview_insights(df)))
    body += section("장르 구성", horizontal_bar(category_counts["label"], category_counts["count"], "건수"))
    body += section("연도별 장르 변화", stacked_bar(year_category_counts(df), "year", "category_label", "count"))
    body += section("시기별 장르 구성", table(pivot))
    body += note("2022년 이후 결정문 수가 급증하므로, 단순 전체 비율보다 시기별·장르별로 분리해 봐야 실무적 변화가 보인다.")
    return page("전체 구조 Full Report", "코퍼스 지도와 시기별 변화", body, "overview")


def render_full_enforcement(df: pd.DataFrame) -> str:
    subset = filter_category(df, "enforcement")
    money = subset["monetary_amount"].dropna()
    package_counts = enforcement_package_counts(subset)
    pairs = article_pair_counts(subset).head(15)
    bands = money_bands(subset)
    body = metric_cards(
        [
            ("제재 사건", f"{len(subset):,}", "법규 위반·제재"),
            ("금액 사건", f"{len(money):,}", "과징금·과태료 추출"),
            ("금액 중앙값", format_won(money.median()) if not money.empty else "n/a", "주문문 기준"),
            ("고액 10억+", f"{int((money >= 1_000_000_000).sum()):,}", "추출 금액 기준"),
        ]
    )
    body += section("핵심 인사이트", insight_list(enforcement_insights(subset)))
    body += section("제재 패키지", horizontal_bar(package_counts["sanction_package"].head(12), package_counts["count"].head(12), "건수"))
    body += section("금액 구간", vertical_bar(bands["money_band"], bands["count"], "건수"))
    body += section("조문 동시 출현 쌍", horizontal_bar(pairs["article_pair"], pairs["count"], "건수"))
    body += section("사건 유형", horizontal_bar(*exploded(subset, "case_type", 15), title="건수"))
    body += section("Factor", horizontal_bar(*exploded(subset, "factors", 15), title="건수"))
    body += section("상위 금액 사건", table(top_money(subset, 20)))
    body += note("제재 금액은 주문문 우선 정규식 추출이다. 다수 피심인 사건, 병합 의결, 표 이미지 내 금액은 별도 검수해야 한다.")
    return page("법규 위반·제재 Full Report", "제재 조합, 금액, 조문, 사건유형", body, "enforcement")


def render_full_privacy_impact(df: pd.DataFrame) -> str:
    subset = filter_category(df, "privacy_impact_review")
    rec = recommendation_flags(subset)
    laws = law_name_counts(subset)
    issues = issue_term_counts(subset)
    by_year = recommendation_by_year(subset)
    body = metric_cards(
        [
            ("침해요인 평가", f"{len(subset):,}", "법령 제·개정 검토"),
            ("권고성 주문", f"{int(rec.sum()):,}", "권고·변경·보완"),
            ("권고율", pct(rec.mean()), "주문문 기준"),
            ("법령명 추출", f"{len(laws):,}", "따옴표 제목 기준"),
        ]
    )
    body += section("핵심 인사이트", insight_list(impact_insights(subset)))
    body += section("연도별 권고율", vertical_bar(by_year["year"], by_year["recommendation_rate"] * 100, "%"))
    body += section("신청기관 상위", horizontal_bar(*top_counts_safe(subset, "applicant", 15), title="건수"))
    body += section("반복 검토 법령명", table(laws.head(20)))
    body += section("반복 쟁점 키워드", horizontal_bar(issues["issue"].head(15), issues["count"].head(15), "건수"))
    body += note("침해요인 평가는 원문 별지에 실질 쟁점이 많이 들어 있다. 다음 단계는 별지 텍스트에서 개인정보 항목·보유기간·위탁·연계 쟁점을 구조화하는 것이다.")
    return page("침해요인 평가 Full Report", "신청기관, 권고율, 반복 쟁점", body, "privacy")


def render_full_public_system(df: pd.DataFrame) -> str:
    subset = filter_category(df, "public_system_inspection")
    families = title_family_counts(subset)
    issues = issue_term_counts(subset)
    body = metric_cards(
        [
            ("공공점검", f"{len(subset):,}", "실태점검·시행계획"),
            ("개선권고", f"{contains_text(subset, 'sanction_types', '개선권고'):,}", "주문문 기준"),
            ("2023년 이후", f"{len(subset[subset['year'] >= '2023']):,}", "집중 구간"),
            ("제목군", f"{len(families):,}", "반복 업무 유형"),
        ]
    )
    body += section("핵심 인사이트", insight_list(public_system_insights(subset)))
    body += section("연도별 건수", vertical_bar(*year_counts(subset), title="건수"))
    body += section("제목군", horizontal_bar(families["title_family"].head(12), families["count"].head(12), "건수"))
    body += section("반복 쟁점 키워드", horizontal_bar(issues["issue"].head(12), issues["count"].head(12), "건수"))
    body += section("대표 표본", table(subset[["decision_id", "decision_date", "title", "order_text"]].head(15)))
    return page("공공시스템·실태점검 Full Report", "공공부문 관리·점검 트랙", body, "public")


def render_full_data_provision(df: pd.DataFrame) -> str:
    subset = filter_category(df, "data_provision_request")
    outcomes = provision_outcomes(subset)
    issues = issue_term_counts(subset)
    video_count = int(subset["case_type"].fillna("").str.contains("영상정보 처리").sum())
    body = metric_cards(
        [
            ("제공 요청", f"{len(subset):,}", "목적 외 제공 판단"),
            ("영상정보", f"{video_count:,}", "CCTV 등"),
            ("불허/제한", f"{int(outcomes[outcomes['outcome'] == '불허·제한']['count'].sum()):,}", "주문문 추정"),
            ("허용", f"{int(outcomes[outcomes['outcome'] == '허용']['count'].sum()):,}", "주문문 추정"),
        ]
    )
    body += section("핵심 인사이트", insight_list(data_provision_insights(subset, outcomes)))
    body += section("허용 여부", horizontal_bar(outcomes["outcome"], outcomes["count"], "건수"))
    body += section("연도별 건수", vertical_bar(*year_counts(subset), title="건수"))
    body += section("쟁점 키워드", horizontal_bar(issues["issue"].head(12), issues["count"].head(12), "건수"))
    body += section("요청기관 상위", horizontal_bar(*top_counts_safe(subset, "applicant", 15), title="건수"))
    body += note("제공 요청은 제재 사건이 아니라 법정 업무수행, 목적 외 이용·제공, 영상정보 제공 가능성 판단이 핵심이다.")
    return page("개인정보 제공 요청 Full Report", "허용/불허와 제공 근거 쟁점", body, "provision")


def render_full_interpretation_other(df: pd.DataFrame) -> str:
    subset = pd.concat(
        [
            filter_category(df, "complaint_or_interpretation"),
            filter_category(df, "prior_review"),
            filter_category(df, "other"),
        ],
        ignore_index=True,
    )
    issues = issue_term_counts(subset)
    body = metric_cards(
        [
            ("대상", f"{len(subset):,}", "해석·기타·사전검토"),
            ("민원·해석", f"{len(filter_category(df, 'complaint_or_interpretation')):,}", "질의·법령해석"),
            ("사전적정성", f"{len(filter_category(df, 'prior_review')):,}", "신청 결과"),
            ("기타", f"{len(filter_category(df, 'other')):,}", "정책·보고 등"),
        ]
    )
    body += section("핵심 인사이트", insight_list(interpretation_insights(subset)))
    body += section("세부 장르", horizontal_bar(count_category(subset)["label"], count_category(subset)["count"], "건수"))
    body += section("주요 조문", horizontal_bar(*exploded(subset, "violated_articles", 15), title="건수"))
    body += section("쟁점 키워드", horizontal_bar(issues["issue"].head(12), issues["count"].head(12), "건수"))
    body += section("반복 제목", table(top_values(subset, "title", 20)))
    body += note("기타 장르는 라벨 정제 여지가 크다. 정책 보고, 개선의견, 해석성 안건을 세분화하면 지식베이스 가치가 커진다.")
    return page("민원·해석·기타 Full Report", "해석성·정책성 안건 분석", body, "interpretation")


def render_full_data_quality(df: pd.DataFrame) -> str:
    missing = df.isna().mean().sort_values(ascending=False).reset_index()
    missing.columns = ["field", "missing_rate"]
    category_missing = (
        df.groupby("document_category")[["title", "applicant", "order_text", "reason_text", "summary_text"]]
        .apply(lambda g: g.isna().mean())
        .reset_index()
    )
    body = metric_cards(
        [
            ("원본 XML", "3,990", "결정문 본문"),
            ("중복 ID", f"{df['decision_id'].duplicated().sum():,}", "품질 점검"),
            ("기타 장르", f"{len(filter_category(df, 'other')):,}", "라벨 정제 대상"),
            ("본문 0자", f"{int((df['document_length'] == 0).sum()):,}", "파서 기준"),
        ]
    )
    body += section("핵심 인사이트", insight_list(data_quality_insights(df)))
    body += section("전체 필드 결측률", horizontal_bar(missing["field"].head(18), missing["missing_rate"].head(18) * 100, "%"))
    body += section("장르별 주요 결측률", table(category_missing))
    body += section("추가 검수 우선순위", table(review_priority(df)))
    body += note("데이터 품질 보고서는 RAG와 회귀분석 전에 반드시 확인해야 한다. 특히 제목 결측·기타 장르·고액 사건은 수작업 검수 가치가 높다.")
    return page("데이터 품질 Full Report", "결측, 장르 품질, 검수 우선순위", body, "quality")


def overview_insights(df: pd.DataFrame) -> list[str]:
    top = count_category(df).iloc[0]
    post = post_2022_count(df)
    return [
        f"전체 {len(df):,}건 중 최대 장르는 {top['label']}이며 {top['count']:,}건이다.",
        f"2022년 이후 결정문은 {post:,}건으로 전체의 {post / len(df):.1%}를 차지한다.",
        "장르를 분리하지 않으면 침해요인 평가의 '침해'와 제재 사건의 침해가 섞여 해석 오류가 발생한다.",
        "실무 활용은 전체 검색보다 장르별 검색·요약·비교 화면을 제공하는 방향이 적합하다.",
    ]


def enforcement_insights(df: pd.DataFrame) -> list[str]:
    money = df["monetary_amount"].dropna()
    top_types = top_split_items(df, "sanction_types", 3)
    top_articles = top_split_items(df, "violated_articles", 3)
    return [
        f"제재 사건 {len(df):,}건 중 금액 제재가 추출된 사건은 {len(money):,}건이다.",
        f"가장 자주 나타나는 제재 유형은 {', '.join(top_types)} 순이다.",
        f"상위 조문은 {', '.join(top_articles)}로, 제재 근거·조사 절차·안전조치 관련 조문이 함께 등장한다.",
        "고액 사건은 대체로 복수 제재 패키지와 다수 조문이 함께 나타나므로, 단일 조문보다 조문 조합과 사실관계 조합을 봐야 한다.",
    ]


def impact_insights(df: pd.DataFrame) -> list[str]:
    rec = recommendation_flags(df)
    top_applicants = top_values(df, "applicant", 3)["applicant"].tolist()
    issues = issue_term_counts(df).head(3)["issue"].tolist()
    return [
        f"침해요인 평가 {len(df):,}건 중 권고성 주문은 {int(rec.sum()):,}건으로 추정된다.",
        f"상위 신청기관은 {', '.join(map(str, top_applicants))}이다.",
        f"반복 쟁점 키워드는 {', '.join(issues)}가 두드러진다.",
        "이 장르는 제재 분석보다 법령 설계 단계의 개인정보 처리 근거·항목·보유기간 점검에 초점을 맞춰야 한다.",
    ]


def public_system_insights(df: pd.DataFrame) -> list[str]:
    return [
        f"공공시스템·실태점검 장르는 {len(df):,}건이며 2023년 이후 집중적으로 증가했다.",
        "표본 검수 후 법규 위반 제목의 제재 사건은 별도 제재 장르로 분리했다.",
        "공공부문 리포트는 개별 제재보다 시스템 관리, 개선권고 이행, 반복 취약점 추적에 적합하다.",
    ]


def data_provision_insights(df: pd.DataFrame, outcomes: pd.DataFrame) -> list[str]:
    video = int(df["case_type"].fillna("").str.contains("영상정보 처리").sum())
    dominant = outcomes.sort_values("count", ascending=False).iloc[0]["outcome"] if not outcomes.empty else "n/a"
    return [
        f"개인정보 제공 요청 {len(df):,}건 중 영상정보 처리 사건은 {video:,}건이다.",
        f"주문문 기준 가장 많은 결론 유형은 {dominant}이다.",
        "이 장르는 과징금·과태료 제재가 아니라 목적 외 이용·제공의 허용요건과 법정 업무수행 근거가 핵심이다.",
    ]


def interpretation_insights(df: pd.DataFrame) -> list[str]:
    articles = top_split_items(df, "violated_articles", 3)
    return [
        f"해석·기타 묶음은 {len(df):,}건이며, 세부 장르 정제가 추가로 필요하다.",
        f"자주 등장하는 조문은 {', '.join(articles)}이다.",
        "해석성 안건은 RAG에서 '유사 제재'보다 '판단 기준' 검색에 더 높은 가치가 있다.",
    ]


def data_quality_insights(df: pd.DataFrame) -> list[str]:
    return [
        "원본 XML은 모두 수집됐지만 일부 과거 문서는 제목 필드에 본문이 결합되어 있다.",
        "배경·주요내용 필드는 API XML에서 대부분 비어 있어 본문 분석은 주문·이유·결정요지·별지를 중심으로 해야 한다.",
        "기타 장르와 고액 제재 사건은 다음 라벨 검수의 우선순위다.",
    ]


def insight_list(items: list[str]) -> str:
    return "<ul class='insight-list'>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def post_2022_count(df: pd.DataFrame) -> int:
    return int((df["year"] >= "2022").sum())


def category_period_counts(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["period"] = data["year"].map(period_label)
    data["category_label"] = data["document_category"].map(CATEGORY_LABELS).fillna(data["document_category"])
    return data.groupby(["period", "document_category", "category_label"]).size().reset_index(name="count")


def period_label(year: str) -> str:
    if not isinstance(year, str) or not year.isdigit():
        return "unknown"
    value = int(year)
    if value <= 2017:
        return "2012-2017"
    if value <= 2021:
        return "2018-2021"
    return "2022-2026"


def enforcement_package_counts(df: pd.DataFrame) -> pd.DataFrame:
    packages = []
    for value in df["sanction_types"].fillna(""):
        items = split_items(value)
        packages.append("+".join(items) if items else "(none)")
    return pd.Series(packages).value_counts().rename_axis("sanction_package").reset_index(name="count")


def article_pair_counts(df: pd.DataFrame) -> pd.DataFrame:
    counter: Counter[str] = Counter()
    for value in df["violated_articles"].fillna(""):
        items = sorted(set(split_items(value)))
        for left, right in combinations(items, 2):
            counter[f"{left}+{right}"] += 1
    return pd.DataFrame(counter.most_common(), columns=["article_pair", "count"])


def money_bands(df: pd.DataFrame) -> pd.DataFrame:
    bins = [
        (0, 1_000_000, "100만원 미만"),
        (1_000_000, 10_000_000, "100만-1천만원"),
        (10_000_000, 100_000_000, "1천만-1억원"),
        (100_000_000, 1_000_000_000, "1억-10억원"),
        (1_000_000_000, 10_000_000_000, "10억-100억원"),
        (10_000_000_000, float("inf"), "100억원 이상"),
    ]
    amounts = df["monetary_amount"].dropna()
    rows = []
    for low, high, label in bins:
        rows.append({"money_band": label, "count": int(((amounts >= low) & (amounts < high)).sum())})
    return pd.DataFrame(rows)


def recommendation_flags(df: pd.DataFrame) -> pd.Series:
    return df["order_text"].fillna("").str.contains(r"권고|변경|보완|개선", regex=True)


def recommendation_by_year(df: pd.DataFrame) -> pd.DataFrame:
    data = df[df["year"] != ""].copy()
    data["recommendation"] = recommendation_flags(data)
    out = data.groupby("year").agg(count=("decision_id", "size"), recommendation_count=("recommendation", "sum")).reset_index()
    out["recommendation_rate"] = out["recommendation_count"] / out["count"]
    return out


def law_name_counts(df: pd.DataFrame) -> pd.DataFrame:
    names = []
    for title in df["title"].fillna(""):
        match = re.search(r"「([^」]+)」", title)
        if match:
            names.append(match.group(1).strip())
    return pd.Series(names).value_counts().rename_axis("law_name").reset_index(name="count")


def issue_term_counts(df: pd.DataFrame) -> pd.DataFrame:
    text = (
        df["title"].fillna("")
        + "\n"
        + df["order_text"].fillna("")
        + "\n"
        + df["reason_text"].fillna("")
        + "\n"
        + df["summary_text"].fillna("")
        + "\n"
        + df["appendix_text"].fillna("")
    )
    rows = []
    for issue, pattern in ISSUE_TERMS.items():
        rows.append({"issue": issue, "count": int(text.str.contains(pattern, regex=True).sum())})
    return pd.DataFrame(rows).sort_values("count", ascending=False)


def title_family_counts(df: pd.DataFrame) -> pd.DataFrame:
    families = df["title"].fillna("(missing)").map(normalize_title_family)
    return families.value_counts().rename_axis("title_family").reset_index(name="count")


def normalize_title_family(title: str) -> str:
    if "사전 실태점검" in title:
        return "공공기관 사전 실태점검"
    if "집중관리시스템" in title:
        return "집중관리시스템"
    if "공공시스템" in title:
        return "공공시스템 운영기관"
    if "시행계획" in title:
        return "개인정보보호 시행계획"
    if not title or title == "(missing)":
        return "(missing)"
    return title[:40]


def provision_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    outcomes = df["order_text"].fillna("").map(classify_provision_outcome)
    return outcomes.value_counts().rename_axis("outcome").reset_index(name="count")


def classify_provision_outcome(text: str) -> str:
    if re.search(r"수\s*없다|제공받을\s*수\s*없|제공할\s*수\s*없|이용할\s*수\s*없", text):
        return "불허·제한"
    if re.search(r"수\s*있다|제공받을\s*수\s*있|제공할\s*수\s*있|이용할\s*수\s*있", text):
        return "허용"
    if re.search(r"일부|범위|조건|필요한\s*범위", text):
        return "조건부·범위 제한"
    return "판정 불명"


def top_split_items(df: pd.DataFrame, column: str, limit: int) -> list[str]:
    counter: Counter[str] = Counter()
    for value in df[column].fillna(""):
        counter.update(split_items(value))
    return [item for item, _ in counter.most_common(limit)]


def top_counts_safe(df: pd.DataFrame, column: str, limit: int):
    out = top_values(df, column, limit)
    return out[column], out["count"]


def contains_text(df: pd.DataFrame, column: str, text: str) -> int:
    return int(df[column].fillna("").str.contains(text, regex=False).sum())


def review_priority(df: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "priority": 1,
            "target": "고액 제재 사건",
            "count": int((filter_category(df, "enforcement")["monetary_amount"].fillna(0) >= 1_000_000_000).sum()),
            "reason": "금액 추출과 병합 사건 검수가 필요",
        },
        {
            "priority": 2,
            "target": "기타 장르",
            "count": len(filter_category(df, "other")),
            "reason": "정책·해석·제공요청이 섞였을 가능성",
        },
        {
            "priority": 3,
            "target": "제목 결측",
            "count": int(df["title"].isna().sum()),
            "reason": "과거 XML 구조 보정 필요",
        },
    ]
    return pd.DataFrame(rows)
