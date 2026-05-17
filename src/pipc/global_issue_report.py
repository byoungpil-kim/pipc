from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path
from textwrap import dedent

import pandas as pd

from .html_reports import (
    format_won,
    horizontal_bar,
    html_document,
    metric_cards,
    note,
    section,
    table,
    vertical_bar,
    write_css,
)
from .insights import CATEGORY_LABELS, ensure_columns, split_items
from .issue_taxonomy import EXTERNAL_ISSUES, ExternalIssue


TEXT_COLUMNS = ["title", "order_text", "reason_text", "summary_text", "appendix_text", "case_type", "factors", "violated_articles"]


def generate_global_issue_report(processed_path: Path, reports_dir: Path) -> Path:
    df = pd.read_csv(processed_path)
    ensure_columns(df)
    tables_dir = reports_dir / "tables"
    candidates_path = tables_dir / "external_issue_candidates.csv"
    candidates = pd.read_csv(candidates_path) if candidates_path.exists() else pd.DataFrame()

    quant = global_quant_summary(df)
    examples = global_examples(df)
    quant.to_csv(tables_dir / "global_issue_quant_summary.csv", index=False)
    examples.to_csv(tables_dir / "global_issue_decision_examples.csv", index=False)

    out_dir = reports_dir / "issues"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_css(reports_dir / "style.css")
    path = out_dir / "index.html"
    path.write_text(render_report(df, quant, examples, candidates), encoding="utf-8")
    for issue in EXTERNAL_ISSUES:
        q = quant[quant["issue_id"] == issue.issue_id].iloc[0]
        issue_examples = examples[examples["issue_id"] == issue.issue_id].drop(columns=["issue_id", "issue_label"], errors="ignore")
        matched = matched_df(df, issue.pattern)
        issue_path = out_dir / f"issue_{issue.issue_id:02d}.html"
        issue_path.write_text(render_issue_page(issue, q, matched, issue_examples, source_urls(issue.issue_id, candidates)), encoding="utf-8")
    legacy = reports_dir / "global_issues.html"
    legacy.write_text(redirect_page("issues/index.html"), encoding="utf-8")
    return path


def render_report(df: pd.DataFrame, quant: pd.DataFrame, examples: pd.DataFrame, candidates: pd.DataFrame) -> str:
    total_matches = int(quant["matched_decisions"].sum())
    body = metric_cards(
        [
            ("주요 쟁점", f"{len(EXTERNAL_ISSUES):,}", "외부 논쟁 기반"),
            ("누적 매칭", f"{total_matches:,}", "중복 포함"),
            ("최대 쟁점", top_issue_label(quant), "매칭 결정문 수 기준"),
            ("개별 페이지", f"{len(EXTERNAL_ISSUES):,}", "쟁점별 상세 분석"),
        ]
    )
    body += section("쟁점별 매칭 규모", horizontal_bar(quant["issue_label"], quant["matched_decisions"], "건수"))
    body += section(
        "읽는 방법",
        insight_list(
            [
                "이 리포트는 법률신문·논문·국내 언론에서 논란이 확인된 11개 주요 쟁점을 결정문 코퍼스에 다시 투영한 결과다.",
                "매칭 수는 정규식 기반 신호이므로 쟁점 존재 가능성을 보여주며, 최종 법적 결론은 원문 검수가 필요하다.",
                "각 쟁점은 별도 페이지에서 법적 초점, 정량 분포, 정성 해석, 대표 결정문 시각화를 함께 제시한다.",
            ]
        ),
    )
    body += section("쟁점별 상세 페이지", issue_cards(quant))
    body += note("이 산출물은 내부 검토용 분석 초안이다. 쟁점별 regex 매칭, 금액 추출, 대표 사례 선정은 직원 검수와 결합될 때 가장 높은 품질을 낸다.")
    return html_document("주요 쟁점 리포트", "11개 논쟁 쟁점에 대한 개보위 결정문 기반 분석", body, "issues", "../")


def render_issue(issue: ExternalIssue, q: pd.Series, examples: pd.DataFrame, urls: list[str]) -> str:
    cards = metric_cards(
        [
            ("매칭 결정문", f"{int(q['matched_decisions']):,}", "중복 없는 결정문"),
            ("제재 사건", f"{int(q['enforcement_count']):,}", "법규 위반·제재"),
            ("금액 사건", f"{int(q['monetary_count']):,}", "금액 추출"),
            ("최대 금액", q["max_amount"], "주문문 기준"),
        ]
    )
    details = insight_list(
        [
            f"법적 분석: {issue.legal_focus}.",
            f"정량 분석: 전체 {int(q['matched_decisions']):,}건이 매칭됐고, 장르 분포는 {q['category_mix']}이다.",
            qualitative_analysis(issue, q),
            f"외부 논쟁 연결: {issue.source_note}.",
        ]
    )
    source_html = source_list(urls)
    content = cards
    content += section("법적·정량·정성 분석", details)
    if q["top_articles"]:
        content += section(
            "결정문 내 법적 신호",
            table(pd.DataFrame([["주요 조문", q["top_articles"]], ["사건유형", q["top_case_types"]]], columns=["항목", "내용"])),
        )
    content += section("대표 결정문 예시", table(examples))
    if source_html:
        content += section("참고 외부 쟁점 출처", source_html)
    return section(f"{issue.issue_id}. {issue.korean_label}", content)


def render_issue_page(issue: ExternalIssue, q: pd.Series, matched: pd.DataFrame, examples: pd.DataFrame, urls: list[str]) -> str:
    money = matched["monetary_amount"].dropna()
    body = metric_cards(
        [
            ("매칭 결정문", f"{int(q['matched_decisions']):,}", "중복 없는 결정문"),
            ("제재 사건", f"{int(q['enforcement_count']):,}", "법규 위반·제재"),
            ("금액 중앙값", format_won(money.median()) if not money.empty else "n/a", "추출 금액"),
            ("최대 금액", q["max_amount"] or "n/a", "주문문 기준"),
        ]
    )
    body += section(
        "쟁점 독해",
        insight_list(
            [
                f"법적 초점: {issue.legal_focus}.",
                f"결정문 분포: {q['category_mix']}.",
                qualitative_analysis(issue, q),
                f"외부 논쟁 연결: {issue.source_note}.",
            ]
        ),
    )
    body += section(
        "정량 지도",
        "<div class='split'>"
        + horizontal_bar(*category_chart_data(matched), "건수")
        + issue_stat_table(matched, money)
        + "</div>",
    )
    body += section("연도별 매칭 흐름", vertical_bar(*year_chart_data(matched), "건수"))
    body += section(
        "법적 신호",
        "<div class='split'>"
        + horizontal_bar(*split_chart_data(matched, "violated_articles", 10), "건수")
        + horizontal_bar(*split_chart_data(matched, "case_type", 10), "건수")
        + "</div>",
    )
    if not money.empty:
        body += section("금액 구간", vertical_bar(*money_band_data(money), "건수"))
    body += section("대표 결정문 읽기", decision_cards(examples))
    if urls:
        body += section("참고 외부 쟁점 출처", source_list(urls))
    body += note("대표 결정문은 전체 사건목록이 아니라 쟁점을 빠르게 이해하기 위한 고신호 표본이다. 원문 검수 전에는 자동 추출 금액과 쟁점 매칭을 확정값으로 보지 않아야 한다.")
    return html_document(f"{issue.korean_label}", "주요 쟁점 상세 분석", body, "issues", "../", compact=True)


def global_quant_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for issue in EXTERNAL_ISSUES:
        matched = matched_df(df, issue.pattern)
        money = matched["monetary_amount"].dropna()
        rows.append(
            {
                "issue_id": issue.issue_id,
                "issue_label": issue.korean_label,
                "matched_decisions": len(matched),
                "enforcement_count": int((matched["document_category"] == "enforcement").sum()),
                "monetary_count": len(money),
                "median_amount": format_won(money.median()) if not money.empty else "",
                "max_amount": format_won(money.max()) if not money.empty else "",
                "category_mix": category_mix(matched),
                "top_articles": top_split(matched, "violated_articles", 6),
                "top_case_types": top_split(matched, "case_type", 6),
            }
        )
    return pd.DataFrame(rows).sort_values("matched_decisions", ascending=False)


def global_examples(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for issue in EXTERNAL_ISSUES:
        matched = matched_df(df, issue.pattern)
        reps = matched.sort_values(["monetary_amount", "document_length", "decision_date"], ascending=[False, False, False], na_position="last").head(8)
        for _, row in reps.iterrows():
            rows.append(
                {
                    "issue_id": issue.issue_id,
                    "issue_label": issue.korean_label,
                    "decision_id": row["decision_id"],
                    "decision_date": clean_value(row.get("decision_date", "")),
                    "category": CATEGORY_LABELS.get(row.get("document_category", ""), row.get("document_category", "")),
                    "title": clean_value(row.get("title", "")),
                    "amount": format_won(row["monetary_amount"]) if pd.notna(row.get("monetary_amount")) else "",
                    "articles": clean_value(row.get("violated_articles", "")),
                    "case_type": clean_value(row.get("case_type", "")),
                    "example_text": snippet(row),
                }
            )
    return pd.DataFrame(rows)


def matched_df(df: pd.DataFrame, pattern: str) -> pd.DataFrame:
    text = composite_text(df)
    return df[text.str.contains(pattern, regex=True, na=False)].copy()


def composite_text(df: pd.DataFrame) -> pd.Series:
    text = pd.Series([""] * len(df), index=df.index)
    for column in TEXT_COLUMNS:
        if column in df.columns:
            text = text + "\n" + df[column].fillna("").astype(str)
    return text


def category_mix(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    counts = df["document_category"].fillna("other").value_counts().head(5)
    return "; ".join(f"{CATEGORY_LABELS.get(key, key)} {value:,}건" for key, value in counts.items())


def top_split(df: pd.DataFrame, column: str, limit: int) -> str:
    counter: Counter[str] = Counter()
    if column not in df:
        return ""
    for value in df[column].fillna(""):
        counter.update(split_items(value))
    return "; ".join(f"{item}({count:,})" for item, count in counter.most_common(limit))


def qualitative_analysis(issue: ExternalIssue, q: pd.Series) -> str:
    matched = int(q["matched_decisions"])
    enforcement = int(q["enforcement_count"])
    category = str(q["category_mix"])
    if issue.issue_id == 1:
        return f"정성 분석: 결정문 신호는 많지 않지만({matched:,}건), 플랫폼·광고 사건은 동의 문구 자체보다 처리자 지위, 제3자 제공, 국외이전 구조가 함께 검토될 가능성이 크다."
    if issue.issue_id == 2:
        return f"정성 분석: 유출 쟁점은 제재 사건 {enforcement:,}건과 강하게 연결된다. 개보위 결정은 피해 규모만이 아니라 안전조치 위반, 통지, 재발방지 조치의 조합을 보는 방향으로 읽힌다."
    if issue.issue_id == 3:
        return "정성 분석: 안전조치 사건은 접근통제·접속기록·암호화 같은 항목별 의무가 사실관계와 결합된다. 인과관계 다툼이 예상되는 사건은 조치의 충분성 문단을 별도로 추출해야 한다."
    if issue.issue_id == 4:
        return f"정성 분석: 국외이전·클라우드 쟁점은 {category}에 넓게 퍼져 있다. 단순 이전 여부보다 위탁·보관·제3자 제공의 법적 성격 구분이 중요하다."
    if issue.issue_id == 5:
        return "정성 분석: AI·자동화 쟁점은 아직 직접 매칭 규모가 작아 선제적 정책·해석 쟁점에 가깝다. 향후 자동화된 결정 권리, 설명 요구, 거부권 사례를 별도 태그로 관리할 필요가 있다."
    if issue.issue_id == 6:
        return "정성 분석: 사전 실태점검은 사후 제재와 다른 예방감독 트랙이다. 점검 결과가 개선권고, 시정조치, 후속 제재로 어떻게 이어지는지 연결 분석 가치가 높다."
    if issue.issue_id == 7:
        return "정성 분석: 영상정보는 제공 요청과 제재를 모두 관통한다. 열람·제공 허용 범위, 수사·공공안전 예외, 설치·운영 관리 의무를 분리해 봐야 한다."
    if issue.issue_id == 8:
        return "정성 분석: 아동 쟁점은 법정대리인 동의와 연령확인 설계가 핵심이다. 매칭 사건은 많지 않아도 위반 시 반복 가능성과 사회적 민감도가 높다."
    if issue.issue_id == 9:
        return "정성 분석: 처리방침·CPO·책임성은 단독 쟁점보다 안전조치, 위탁, 내부관리계획 위반의 기반 사유로 나타나는 경향이 있다."
    if issue.issue_id == 10:
        return "정성 분석: 피해구제 쟁점은 과징금·공표·통지와 연결된다. 현 결정문은 피해자 배상 자체보다 행정제재와 재발방지 명령 중심으로 읽힌다."
    return "정성 분석: 섹터별 파동은 개별 법리보다 반복 위반 업권을 드러낸다. 직원용 도구에서는 업권 필터와 체크리스트 기반 비교 화면으로 전환할 가치가 있다."


def snippet(row: pd.Series, limit: int = 220) -> str:
    text = first_text(row, ["order_text", "reason_text", "summary_text"])
    text = " ".join(text.split())
    return text[:limit] + ("..." if len(text) > limit else "")


def first_text(row: pd.Series, columns: list[str]) -> str:
    for column in columns:
        value = row.get(column, "")
        if pd.notna(value) and str(value).strip():
            return str(value)
    return ""


def clean_value(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def source_urls(issue_id: int, candidates: pd.DataFrame) -> list[str]:
    if candidates.empty or "issue_id" not in candidates.columns or "source_urls" not in candidates.columns:
        return []
    row = candidates[candidates["issue_id"].astype(int) == issue_id]
    if row.empty:
        return []
    value = str(row.iloc[0]["source_urls"])
    return [part.strip() for part in value.split("|") if part.strip()]


def source_list(urls: list[str]) -> str:
    if not urls:
        return ""
    items = []
    for url in urls:
        safe = escape(url)
        items.append(f"<li><a href='{safe}'>{safe}</a></li>")
    return "<ul class='insight-list'>" + "".join(items) + "</ul>"


def issue_cards(quant: pd.DataFrame) -> str:
    rows = quant.sort_values("issue_id")
    html = "<div class='issue-grid'>"
    for _, row in rows.iterrows():
        issue_id = int(row["issue_id"])
        html += (
            f"<a class='issue-card' href='issue_{issue_id:02d}.html'>"
            f"<strong>{issue_id}. {escape(str(row['issue_label']))}</strong>"
            f"<span>{int(row['matched_decisions']):,}건 매칭 · 제재 {int(row['enforcement_count']):,}건</span>"
            f"<span>{escape(str(row['category_mix']))}</span>"
            "</a>"
        )
    return html + "</div>"


def category_chart_data(df: pd.DataFrame):
    if df.empty:
        return [], []
    counts = df["document_category"].fillna("other").value_counts().head(8)
    return [CATEGORY_LABELS.get(k, k) for k in counts.index], counts.values


def year_chart_data(df: pd.DataFrame):
    if df.empty:
        return [], []
    years = df["decision_date"].fillna("").astype(str).str[:4]
    counts = years[years.str.match(r"^\d{4}$", na=False)].value_counts().sort_index()
    return counts.index, counts.values


def split_chart_data(df: pd.DataFrame, column: str, limit: int):
    counter: Counter[str] = Counter()
    for value in df[column].fillna(""):
        counter.update(split_items(value))
    items = counter.most_common(limit)
    return [item for item, _ in items], [count for _, count in items]


def money_band_data(money: pd.Series):
    bins = [
        (0, 1_000_000, "100만원 미만"),
        (1_000_000, 10_000_000, "100만-1천만원"),
        (10_000_000, 100_000_000, "1천만-1억원"),
        (100_000_000, 1_000_000_000, "1억-10억원"),
        (1_000_000_000, 10_000_000_000, "10억-100억원"),
        (10_000_000_000, float("inf"), "100억원 이상"),
    ]
    labels, values = [], []
    for low, high, label in bins:
        labels.append(label)
        values.append(int(((money >= low) & (money < high)).sum()))
    return labels, values


def issue_stat_table(df: pd.DataFrame, money: pd.Series) -> str:
    rows = [
        ["전체 매칭", f"{len(df):,}건"],
        ["제재 비율", f"{((df['document_category'] == 'enforcement').mean() * 100):.1f}%" if len(df) else "n/a"],
        ["금액 사건", f"{len(money):,}건"],
        ["금액 합계", format_won(money.sum()) if not money.empty else "n/a"],
        ["평균 본문 길이", f"{df['document_length'].mean():,.0f}자" if len(df) else "n/a"],
    ]
    return table(pd.DataFrame(rows, columns=["지표", "값"]))


def decision_cards(examples: pd.DataFrame) -> str:
    if examples.empty:
        return "<p>No rows.</p>"
    html = "<div class='decision-grid'>"
    for _, row in examples.iterrows():
        html += (
            "<article class='decision-card'>"
            f"<div class='meta'>{escape(str(row.get('decision_date', '')))} · ID {escape(str(row.get('decision_id', '')))} · {escape(str(row.get('category', '')))}</div>"
            f"<div class='title'>{escape(str(row.get('title', '') or '(제목 없음)'))}</div>"
            f"<div class='amount'>{escape(str(row.get('amount', '') or '금액 없음'))}</div>"
            f"<p>{escape(str(row.get('example_text', '')))}</p>"
            f"<div class='meta'>{escape(str(row.get('case_type', '')))}</div>"
            "</article>"
        )
    return html + "</div>"


def top_issue_label(quant: pd.DataFrame) -> str:
    if quant.empty:
        return "n/a"
    top = quant.sort_values("matched_decisions", ascending=False).iloc[0]
    return f"{top['issue_label']} {int(top['matched_decisions']):,}건"


def insight_list(items: list[str]) -> str:
    return "<ul class='insight-list'>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def report_page(title: str, subtitle: str, body: str) -> str:
    nav = "<a class='active' href='issues/index.html'>주요 쟁점</a><a href='full_html/index.html'>유형별 분석</a>"
    return dedent(
        f"""\
        <!doctype html>
        <html lang="ko">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>{escape(title)} | PIPC 결정문 인사이트</title>
          <link rel="stylesheet" href="style.css">
        </head>
        <body>
          <header>
            <div>
              <p class="eyebrow">PIPC Global Issue Insights</p>
              <h1>{escape(title)}</h1>
              <p class="subtitle">{escape(subtitle)}</p>
            </div>
          </header>
          <nav>{nav}</nav>
          <main>{body}</main>
        </body>
        </html>
        """
    )


def redirect_page(target: str) -> str:
    return dedent(
        f"""\
        <!doctype html>
        <html lang="ko">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <meta http-equiv="refresh" content="0; url={escape(target)}">
          <title>주요 쟁점으로 이동</title>
        </head>
        <body><p><a href="{escape(target)}">주요 쟁점 리포트로 이동</a></p></body>
        </html>
        """
    )
