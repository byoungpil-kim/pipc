from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path
import re
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
        write_decision_pages(issue, matched, issue_examples, out_dir)
    legacy = reports_dir / "global_issues.html"
    legacy.write_text(redirect_page("issues/index.html"), encoding="utf-8")
    return path


def render_report(df: pd.DataFrame, quant: pd.DataFrame, examples: pd.DataFrame, candidates: pd.DataFrame) -> str:
    total_matches = int(quant["matched_decisions"].sum())
    body = metric_cards(
        [
            ("주요 쟁점", f"{len(EXTERNAL_ISSUES):,}", "외부 논쟁 기반"),
            ("누적 매칭", f"{total_matches:,}", "중복 포함"),
            ("개별 페이지", f"{len(EXTERNAL_ISSUES):,}", "쟁점별 상세 분석"),
            ("대표 결정문", f"{len(examples):,}", "HTML 변환 링크"),
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
        "이 쟁점의 의미",
        f"<div class='summary-box'><strong>{escape(issue.korean_label)}</strong><p>{escape(issue_meaning(issue))}</p></div>",
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
    body += section("대표 결정문 읽기", decision_cards(issue, examples))
    if urls:
        body += section("참고 외부 쟁점 출처", source_list(urls))
    body += note("대표 결정문은 전체 사건목록이 아니라 쟁점을 빠르게 이해하기 위한 고신호 표본이다. 원문 검수 전에는 자동 추출 금액과 쟁점 매칭을 확정값으로 보지 않아야 한다.")
    return html_document(f"{issue.korean_label}", "주요 쟁점 상세 분석", body, f"issue-{issue.issue_id:02d}", "../", compact=True)


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
    return "정성 분석: 업권별 반복 리스크는 개별 법리보다 유사한 사고·위반이 특정 업권에서 되풀이되는 양상을 드러낸다. 직원용 도구에서는 업권 필터와 체크리스트 기반 비교 화면으로 전환할 가치가 있다."


def issue_meaning(issue: ExternalIssue) -> str:
    meanings = {
        1: "맞춤형 광고와 플랫폼 사건은 단순 동의 문구의 문제가 아니라, 누가 처리자인지, 플랫폼이 데이터 흐름을 얼마나 통제하는지, 제3자 제공·국외이전 구조가 어떻게 결합되는지를 함께 봐야 하는 쟁점이다.",
        2: "대규모 유출 사건은 피해 규모, 안전조치 위반, 통지·신고, 재발방지 조치가 과징금 산정과 비례성 판단에 어떻게 반영되는지를 보여준다.",
        3: "안전조치 쟁점은 접근통제·접속기록·암호화 같은 조치가 실제 사고를 막기에 충분했는지, 그리고 위반과 유출 사이의 연결이 어떻게 판단되는지를 묻는다.",
        4: "국외이전과 클라우드 쟁점은 데이터가 해외에 저장·처리되는 사실 자체보다 위탁, 보관, 제3자 제공, 고지·동의 요건을 어떻게 구분하는지가 핵심이다.",
        5: "AI와 자동화된 결정 쟁점은 아직 결정문 내 직접 사례가 적지만, 설명 요구권·거부권·프로파일링 투명성이 향후 감독 기준으로 커질 수 있는 영역이다.",
        6: "사전 실태점검은 사후 제재와 달리 예방감독의 성격이 강하다. 점검 결과가 개선권고와 후속 제재로 이어지는 연결 구조를 보는 것이 중요하다.",
        7: "영상정보 쟁점은 CCTV·블랙박스·관제 영상의 열람, 제공, 목적 외 이용, 수사 협조 예외를 구분해 판단해야 하는 반복 실무 영역이다.",
        8: "아동 개인정보 쟁점은 법정대리인 동의와 연령확인 설계가 핵심이며, 사건 수가 많지 않아도 사회적 민감도와 반복 가능성이 높다.",
        9: "처리방침과 CPO 책임성은 독립 위반뿐 아니라 안전조치, 위탁관리, 내부관리계획 위반을 뒷받침하는 운영 책임의 지표로 작동한다.",
        10: "피해구제 쟁점은 행정제재가 실제 피해자 회복과 어떻게 연결되는지, 집단분쟁조정·손해배상·과징금 활용 논의와 어떤 거리를 갖는지 살피는 영역이다.",
        11: "업권별 반복 유출·위반 리스크는 통신, 숙박, 식음료, 공공 등 특정 분야에서 비슷한 사고와 위반이 반복되는지를 비교해 예방감독 우선순위를 찾는 쟁점이다.",
    }
    return meanings.get(issue.issue_id, issue.legal_focus)


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
        issue = next((item for item in EXTERNAL_ISSUES if item.issue_id == issue_id), None)
        meaning = issue_meaning(issue) if issue else str(row["category_mix"])
        html += (
            f"<a class='issue-card' href='issue_{issue_id:02d}.html'>"
            f"<strong>{issue_id}. {escape(str(row['issue_label']))}</strong>"
            f"<span>{escape(meaning)}</span>"
            f"<span class='issue-count'>{int(row['matched_decisions']):,}건 · 제재 {int(row['enforcement_count']):,}건</span>"
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


def decision_cards(issue: ExternalIssue, examples: pd.DataFrame) -> str:
    if examples.empty:
        return "<p>No rows.</p>"
    html = "<div class='decision-grid'>"
    for _, row in examples.iterrows():
        decision_id = escape(str(row.get("decision_id", "")))
        href = f"decisions/issue_{issue.issue_id:02d}_decision_{decision_id}.html"
        html += (
            "<article class='decision-card'>"
            f"<div class='meta'>{escape(str(row.get('decision_date', '')))} · ID {escape(str(row.get('decision_id', '')))} · {escape(str(row.get('category', '')))}</div>"
            f"<a class='title' href='{href}'>{escape(str(row.get('title', '') or '(제목 없음)'))}</a>"
            f"<div class='amount'>{escape(str(row.get('amount', '') or '금액 없음'))}</div>"
            f"<p>{escape(str(row.get('example_text', '')))}</p>"
            f"<div class='meta'>{escape(str(row.get('case_type', '')))}</div>"
            "</article>"
        )
    return html + "</div>"


def write_decision_pages(issue: ExternalIssue, matched: pd.DataFrame, examples: pd.DataFrame, out_dir: Path) -> None:
    decisions_dir = out_dir / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    if examples.empty:
        return
    wanted = {str(item) for item in examples["decision_id"].astype(str)}
    for _, row in matched[matched["decision_id"].astype(str).isin(wanted)].iterrows():
        decision_id = clean_value(row.get("decision_id", ""))
        path = decisions_dir / f"issue_{issue.issue_id:02d}_decision_{decision_id}.html"
        path.write_text(render_decision_page(issue, row), encoding="utf-8")


def render_decision_page(issue: ExternalIssue, row: pd.Series) -> str:
    title = clean_value(row.get("title", "")) or "(제목 없음)"
    amount = format_won(row["monetary_amount"]) if pd.notna(row.get("monetary_amount")) else "금액 없음"
    body = (
        "<section class='doc-section'>"
        + table(
            pd.DataFrame(
                [
                    ["결정문 ID", clean_value(row.get("decision_id", ""))],
                    ["결정일", clean_value(row.get("decision_date", ""))],
                    ["결정문 유형", CATEGORY_LABELS.get(row.get("document_category", ""), row.get("document_category", ""))],
                    ["추출 금액", amount],
                    ["사건유형", clean_value(row.get("case_type", ""))],
                    ["주요 조문", clean_value(row.get("violated_articles", ""))],
                ],
                columns=["항목", "내용"],
            )
        )
        + "</section>"
    )
    body += decision_summary_section(issue, row, amount)
    body += document_text_section("주문", clean_value(row.get("order_text", "")))
    body += document_text_section("이유", clean_value(row.get("reason_text", "")))
    body += document_text_section("결정요지", clean_value(row.get("summary_text", "")))
    body += document_text_section("별지", clean_value(row.get("appendix_text", "")))
    return html_document(title, "대표 결정문 HTML 보기", body, f"issue-{issue.issue_id:02d}", "../../", compact=True)


def decision_summary_section(issue: ExternalIssue, row: pd.Series, amount: str) -> str:
    summaries = [
        ("전체 요약", build_overall_summary(issue, row, amount)),
        ("중요 쟁점", build_key_issue_summary(issue, row)),
        ("사실관계 요약", build_fact_summary(row)),
        ("법리 요약", build_legal_summary(issue, row)),
        ("결론 요약", build_conclusion_summary(row, amount)),
    ]
    cards = "".join(summary_card(title, text) for title, text in summaries if text)
    return f"<section class='doc-section'><h2>결정문 요약</h2><div class='summary-grid'>{cards}</div></section>"


def summary_card(title: str, text: str) -> str:
    return f"<div class='summary-box decision-summary'><strong>{escape(title)}</strong><p>{escape(text)}</p></div>"


def build_overall_summary(issue: ExternalIssue, row: pd.Series, amount: str) -> str:
    date = clean_value(row.get("decision_date", ""))
    title = clean_value(row.get("title", "")) or "제목 없는 결정문"
    category = CATEGORY_LABELS.get(row.get("document_category", ""), row.get("document_category", ""))
    conclusion = build_conclusion_summary(row, amount, limit=180)
    return compact_text(
        f"{date} {category} 결정문으로, '{title}' 사건이다. {issue.korean_label} 쟁점에서는 {issue.legal_focus}가 핵심 독해축이다. {conclusion}",
        520,
    )


def build_key_issue_summary(issue: ExternalIssue, row: pd.Series) -> str:
    factors = clean_value(row.get("factors", ""))
    case_type = clean_value(row.get("case_type", ""))
    articles = clean_value(row.get("violated_articles", ""))
    elements = [f"{issue.korean_label}: {issue_meaning(issue).rstrip('.')}"]
    if case_type:
        elements.append(f"사건유형은 {case_type}로 분류된다")
    if articles:
        elements.append(f"주요 조문 신호는 {articles}이다")
    if factors:
        elements.append(f"판단 요소로 {factors}가 함께 나타난다")
    return compact_text(". ".join(elements) + ".", 560)


def build_fact_summary(row: pd.Series) -> str:
    text = decision_text(row, ["reason_text", "summary_text", "appendix_text", "order_text"])
    extracted = extract_relevant_passage(
        text,
        [
            "피심인",
            "신청",
            "조사",
            "사실",
            "현황",
            "수집",
            "이용",
            "제공",
            "유출",
            "접근",
            "보관",
            "위탁",
            "영상",
            "정보주체",
            "이용자",
            "시스템",
        ],
    )
    if extracted:
        return compact_text(extracted, 620)
    return compact_text(snippet(row, 520), 620)


def build_legal_summary(issue: ExternalIssue, row: pd.Series) -> str:
    articles = clean_value(row.get("violated_articles", ""))
    factors = clean_value(row.get("factors", ""))
    reason = extract_relevant_passage(
        decision_text(row, ["reason_text", "summary_text", "order_text"]),
        ["위반", "법", "조", "동의", "안전조치", "목적", "제공", "처리", "보호위원회", "판단", "해당"],
        max_parts=2,
    )
    pieces = []
    if articles:
        pieces.append(f"주요 조문은 {articles}이다")
    pieces.append(f"이 결정문은 {issue.legal_focus}를 중심으로 읽을 수 있다")
    if factors:
        pieces.append(f"자동 라벨상 판단 요소는 {factors}이다")
    if reason:
        pieces.append(f"원문상 법리 판단 근거는 '{compact_text(reason, 260)}' 부분에 압축되어 있다")
    return compact_text(". ".join(pieces) + ".", 620)


def build_conclusion_summary(row: pd.Series, amount: str, limit: int = 520) -> str:
    sanctions = clean_value(row.get("sanction_types", ""))
    order = extract_relevant_passage(
        clean_value(row.get("order_text", "")),
        ["시정", "과징금", "과태료", "공표", "권고", "개선", "제공", "수 있다", "수 없다", "부과", "명령", "통지"],
        max_parts=3,
    )
    pieces = []
    if sanctions:
        pieces.append(f"결론 유형은 {sanctions}이다")
    if amount and amount != "금액 없음":
        pieces.append(f"금액 제재 신호는 {amount}로 추출됐다")
    if order:
        pieces.append(f"주문 요지는 '{compact_text(order, 300)}'이다")
    if not pieces:
        pieces.append(compact_text(first_text(row, ["order_text", "summary_text", "reason_text"]), 360))
    return compact_text(". ".join(pieces) + ".", limit)


def extract_relevant_passage(text: str, keywords: list[str], max_parts: int = 3) -> str:
    cleaned = normalize_decision_text(text)
    if not cleaned or is_heading_like(cleaned):
        return ""
    parts = split_summary_units(cleaned)
    if not parts:
        return ""
    selected = [part for part in parts if any(keyword in part for keyword in keywords)]
    if not selected:
        selected = parts
    return " ".join(selected[:max_parts])


def split_summary_units(text: str) -> list[str]:
    candidates = re.split(r"(?<=[.。다])\s+|\n+|(?=\b[0-9]+\.\s)|(?=[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\.\s)", text)
    units = []
    for candidate in candidates:
        item = strip_heading_prefix(candidate.strip())
        if len(item) < 18:
            continue
        if is_heading_like(item):
            continue
        units.append(item)
    return units


def decision_text(row: pd.Series, columns: list[str]) -> str:
    values = []
    for column in columns:
        value = clean_value(row.get(column, ""))
        if value and not is_heading_like(normalize_decision_text(value)):
            values.append(value)
    return "\n".join(values)


def strip_heading_prefix(text: str) -> str:
    text = re.sub(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\.\s*[가-힣A-Za-zㆍ·\s]{1,24}(?=\s|$)", "", text).strip()
    text = re.sub(r"^[0-9]+\.\s*[가-힣A-Za-zㆍ·\s]{1,24}(?=\s|$)", "", text).strip()
    return text


def is_heading_like(text: str) -> bool:
    if len(text) < 36 and re.fullmatch(r"[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩIVX0-9.\s()가-힣A-Za-zㆍ·-]+", text):
        return True
    return bool(re.fullmatch(r"(기초 사실|인정 사실|판단|결론|주문|이유|검토|개요|조사 배경)", text))


def normalize_decision_text(text: str) -> str:
    text = re.sub(r"<img\b[^>]*>", " ", text or "", flags=re.IGNORECASE)
    text = re.sub(r"\(각주:[^)]+\)", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compact_text(text: str, limit: int = 260) -> str:
    cleaned = normalize_decision_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def document_text_section(title: str, text: str) -> str:
    if not text.strip():
        return ""
    chunks = paragraph_chunks(text)
    html = f"<section class='doc-section'><h2>{escape(title)}</h2>"
    for chunk in chunks:
        html += f"<p>{escape(chunk)}</p>"
    return html + "</section>"


def paragraph_chunks(text: str, limit: int = 1200) -> list[str]:
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return []
    chunks = []
    current = ""
    for para in normalized.split("\n"):
        if len(current) + len(para) + 1 > limit and current:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n{para}".strip()
    if current:
        chunks.append(current)
    return chunks


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
