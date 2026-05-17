from __future__ import annotations

from html import escape
from pathlib import Path
from textwrap import dedent

import pandas as pd

from .insights import CATEGORY_LABELS, ensure_columns, filter_category, split_items


PALETTE = ["#2563eb", "#059669", "#dc2626", "#7c3aed", "#d97706", "#0891b2", "#4b5563"]


def generate_html_reports(processed_path: Path, reports_dir: Path) -> list[Path]:
    df = pd.read_csv(processed_path)
    ensure_columns(df)
    out_dir = reports_dir / "html"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_css(out_dir / "style.css")

    findings = label_review_findings()
    (reports_dir / "tables" / "label_review_findings.csv").parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(findings).to_csv(reports_dir / "tables" / "label_review_findings.csv", index=False)

    pages = [
        ("index.html", render_index(df, findings)),
        ("overview.html", render_overview(df, findings)),
        ("enforcement.html", render_enforcement(df)),
        ("privacy_impact.html", render_privacy_impact(df)),
        ("public_system.html", render_public_system(df)),
        ("data_provision.html", render_data_provision(df)),
        ("interpretation_other.html", render_interpretation_other(df)),
        ("data_quality.html", render_data_quality(df, findings)),
    ]
    written = []
    for filename, html in pages:
        path = out_dir / filename
        path.write_text(html, encoding="utf-8")
        written.append(path)
    return written


def render_index(df: pd.DataFrame, findings: list[dict[str, str]]) -> str:
    cards = metric_cards(
        [
            ("전체 결정문", f"{len(df):,}", "수집·파싱 완료"),
            ("침해요인 평가", f"{len(filter_category(df, 'privacy_impact_review')):,}", "최대 장르"),
            ("법규 위반·제재", f"{len(filter_category(df, 'enforcement')):,}", "제재 분석 대상"),
            ("표본 검수", f"{sum(1 for item in findings if item['status'] == 'fixed')}/{len(findings)}", "보정 완료 항목"),
        ]
    )
    links = [
        ("overview.html", "전체 구조", "장르 구성, 시계열, 표본 검수 요약"),
        ("enforcement.html", "법규 위반·제재", "제재 강도, 금액, 조문, 사건유형"),
        ("privacy_impact.html", "침해요인 평가", "신청기관, 권고율, 연도 추세"),
        ("public_system.html", "공공시스템·실태점검", "실태점검·개선권고 흐름"),
        ("data_provision.html", "개인정보 제공 요청", "목적 외 제공·영상정보 제공 쟁점"),
        ("interpretation_other.html", "민원·해석·기타", "해석성 안건과 기타 정책 안건"),
        ("data_quality.html", "데이터 품질", "결측, 문서 길이, 라벨 검수"),
    ]
    body = cards + "<section><h2>섹션별 리포트</h2><div class='link-grid'>"
    for href, title, desc in links:
        body += f"<a class='report-link' href='{href}'><strong>{escape(title)}</strong><span>{escape(desc)}</span></a>"
    body += "</div></section>"
    return page("PIPC 결정문 인사이트", "직원 공유용 분석 리포트 모음", body, "index")


def render_overview(df: pd.DataFrame, findings: list[dict[str, str]]) -> str:
    category_counts = count_category(df)
    year_category = year_category_counts(df)
    body = metric_cards(
        [
            ("결정문", f"{len(df):,}", "전체 코퍼스"),
            ("장르", f"{df['document_category'].nunique():,}", "분석 트랙"),
            ("수집 실패", "0", "현재 원본 기준"),
            ("중복 ID", f"{df['decision_id'].duplicated().sum():,}", "파싱 데이터"),
        ]
    )
    body += section("장르 구성", horizontal_bar(category_counts["label"], category_counts["count"], "건수"))
    body += section("연도별 장르 변화", stacked_bar(year_category, "year", "category_label", "count"))
    body += section("표본 검수 결과", table(pd.DataFrame(findings)))
    body += note("검수 결과, 개인정보 제공 요청의 과태료 목적 문구와 실태점검 기반 제재 사건의 장르 우선순위를 보정했다.")
    return page("전체 구조", "3,990건 결정문의 장르 지도와 검수 결과", body, "overview")


def render_enforcement(df: pd.DataFrame) -> str:
    subset = filter_category(df, "enforcement")
    money = subset["monetary_amount"].dropna()
    body = metric_cards(
        [
            ("제재 장르", f"{len(subset):,}", "법규 위반·시정조치"),
            ("금액 추출", f"{len(money):,}", "과징금·과태료 맥락"),
            ("중앙값", format_won(money.median()) if not money.empty else "n/a", "금액 제재"),
            ("최대값", format_won(money.max()) if not money.empty else "n/a", "주문문 기준"),
        ]
    )
    strength = subset["sanction_strength"].fillna(0).astype(int).value_counts().sort_index().reset_index()
    strength.columns = ["strength", "count"]
    body += section("제재 강도 분포", vertical_bar(strength["strength"].astype(str), strength["count"], "건수"))
    body += section("주요 제재 유형", horizontal_bar(*exploded(subset, "sanction_types", 10), title="건수"))
    body += section("주요 조문", horizontal_bar(*exploded(subset, "violated_articles", 15), title="언급 건수"))
    body += section("사건 유형", horizontal_bar(*exploded(subset, "case_type", 12), title="건수"))
    body += section("금액 제재 연도별 추세", money_by_year_chart(subset))
    body += section("상위 금액 사건", table(top_money(subset, 15)))
    return page("법규 위반·제재", "제재 강도, 금액, 조문, 사건유형 분석", body, "enforcement")


def render_privacy_impact(df: pd.DataFrame) -> str:
    subset = filter_category(df, "privacy_impact_review")
    rec = subset["order_text"].fillna("").str.contains(r"권고|변경|보완|개선", regex=True)
    body = metric_cards(
        [
            ("침해요인 평가", f"{len(subset):,}", "전체의 주요 장르"),
            ("권고성 주문", f"{int(rec.sum()):,}", "권고·변경·보완"),
            ("권고율", pct(rec.mean()), "주문문 기준"),
            ("신청기관", f"{subset['applicant'].nunique():,}", "결측 제외 전"),
        ]
    )
    body += section("신청기관 상위", horizontal_bar(*top_counts(subset, "applicant", 15), title="건수"))
    body += section("연도별 권고율", recommendation_chart(subset))
    body += section("연도별 처리 건수", vertical_bar(*year_counts(subset), title="건수"))
    body += note("침해요인 평가는 법규 위반 사건이 아니므로 사건유형 라벨을 비워 두고 별도 쟁점 추출기를 만드는 것이 타당하다.")
    return page("침해요인 평가", "법령 제·개정안 검토 흐름과 신청기관 분포", body, "privacy")


def render_public_system(df: pd.DataFrame) -> str:
    subset = filter_category(df, "public_system_inspection")
    body = metric_cards(
        [
            ("실태점검", f"{len(subset):,}", "공공시스템·시행계획 포함"),
            ("개선권고", f"{contains_count(subset, 'sanction_types', '개선권고'):,}", "주문문 기준"),
            ("평균 본문", f"{subset['document_length'].mean():.0f}", "문자 수"),
            ("신청기관", f"{subset['applicant'].nunique():,}", "결측 제외 전"),
        ]
    )
    body += section("연도별 건수", vertical_bar(*year_counts(subset), title="건수"))
    body += section("상위 기관", horizontal_bar(*top_counts(subset, "applicant", 12), title="건수"))
    body += section("주요 조문", horizontal_bar(*exploded(subset, "violated_articles", 12), title="언급 건수"))
    body += note("표본 검수 결과, 법규 위반행위 제목을 가진 사건은 제재 장르로 재분류했고, 실태점검 장르는 개선권고·시행계획 중심으로 남겼다.")
    return page("공공시스템·실태점검", "공공부문 관리·점검 트랙", body, "public")


def render_data_provision(df: pd.DataFrame) -> str:
    subset = filter_category(df, "data_provision_request")
    video = subset["case_type"].fillna("").str.contains("영상정보 처리")
    body = metric_cards(
        [
            ("제공 요청", f"{len(subset):,}", "목적 외 제공 판단"),
            ("영상정보", f"{int(video.sum()):,}", "CCTV 등"),
            ("비영상", f"{len(subset) - int(video.sum()):,}", "개인정보 제공"),
            ("제재 오탐", "0", "표본 검수 후"),
        ]
    )
    body += section("연도별 건수", vertical_bar(*year_counts(subset), title="건수"))
    body += section("요청기관 상위", horizontal_bar(*top_counts(subset, "applicant", 12), title="건수"))
    body += section("쟁점 유형", horizontal_bar(*exploded(subset, "case_type", 6), title="건수"))
    body += note("표본에서 '과태료 부과를 위한 개인정보 제공' 문구가 제재로 오탐된 문제를 보정했다. 이 장르는 허용/불허 판단 기준 추출이 핵심이다.")
    return page("개인정보 제공 요청", "목적 외 이용·제3자 제공 판단 트랙", body, "provision")


def render_interpretation_other(df: pd.DataFrame) -> str:
    subset = pd.concat(
        [
            filter_category(df, "complaint_or_interpretation"),
            filter_category(df, "prior_review"),
            filter_category(df, "other"),
        ],
        ignore_index=True,
    )
    body = metric_cards(
        [
            ("대상", f"{len(subset):,}", "민원·해석·기타·사전검토"),
            ("민원·해석", f"{len(filter_category(df, 'complaint_or_interpretation')):,}", "법령해석 포함"),
            ("사전적정성", f"{len(filter_category(df, 'prior_review')):,}", "신청 결과"),
            ("기타", f"{len(filter_category(df, 'other')):,}", "정책·보고 등"),
        ]
    )
    body += section("세부 장르", horizontal_bar(count_category(subset)["label"], count_category(subset)["count"], "건수"))
    body += section("주요 조문", horizontal_bar(*exploded(subset, "violated_articles", 15), title="언급 건수"))
    body += section("반복 제목", table(top_values(subset, "title", 15)))
    return page("민원·해석·기타", "해석성 안건과 정책성 안건의 별도 분석", body, "interpretation")


def render_data_quality(df: pd.DataFrame, findings: list[dict[str, str]]) -> str:
    missing = df.isna().mean().sort_values(ascending=False).head(15).reset_index()
    missing.columns = ["field", "missing_rate"]
    lengths = pd.DataFrame(
        {
            "metric": ["order_text", "reason_text", "summary_text", "document"],
            "median_length": [
                df["order_length"].median(),
                df["reason_length"].median(),
                df["summary_text"].fillna("").str.len().median(),
                df["document_length"].median(),
            ],
        }
    )
    body = metric_cards(
        [
            ("원본 XML", "3,990", "결정문 본문"),
            ("중복 ID", f"{df['decision_id'].duplicated().sum():,}", "품질 점검"),
            ("제목 결측", pct(df["title"].isna().mean()), "파서 기준"),
            ("본문 중앙값", f"{df['document_length'].median():.0f}", "문자 수"),
        ]
    )
    body += section("필드 결측률", horizontal_bar(missing["field"], missing["missing_rate"] * 100, "%"))
    body += section("본문 길이", vertical_bar(lengths["metric"], lengths["median_length"], "중앙값 문자 수"))
    body += section("라벨 검수 로그", table(pd.DataFrame(findings)))
    body += note("HTML 리포트는 현재 정적 산출물이다. 다음 단계에서는 장르별 수작업 검수 결과를 다시 규칙에 반영하고, 문단 citation을 붙이는 것이 우선이다.")
    return page("데이터 품질", "결측, 길이, 라벨 검수 결과", body, "quality")


def label_review_findings() -> list[dict[str, str]]:
    return [
        {
            "area": "data_provision_request",
            "finding": "과태료 부과 목적 문구가 실제 제재로 오탐됨",
            "action": "제공 요청·사전적정성 장르는 sanction_types를 비움",
            "status": "fixed",
        },
        {
            "area": "public_system_inspection",
            "finding": "법규 위반행위 제목이 있는 사건 일부가 실태점검으로 분류됨",
            "action": "제목 기반 장르 판정에서 법규 위반·시정조치를 우선",
            "status": "fixed",
        },
        {
            "area": "privacy_impact_review",
            "finding": "침해요인 평가의 '침해'가 유출·침해 사건으로 오탐될 수 있음",
            "action": "침해요인 평가 장르에서는 case_type을 비움",
            "status": "fixed",
        },
        {
            "area": "enforcement",
            "finding": "사건유형과 factor는 여전히 규칙 기반 다중 라벨",
            "action": "상위 금액·상위 조문 사건부터 추가 표본 검수 필요",
            "status": "open",
        },
    ]


def page(title: str, subtitle: str, body: str, active: str) -> str:
    nav = [
        ("index", "index.html", "홈"),
        ("overview", "overview.html", "전체"),
        ("enforcement", "enforcement.html", "제재"),
        ("privacy", "privacy_impact.html", "침해요인"),
        ("public", "public_system.html", "공공점검"),
        ("provision", "data_provision.html", "제공요청"),
        ("interpretation", "interpretation_other.html", "해석·기타"),
        ("quality", "data_quality.html", "품질"),
    ]
    nav_html = "".join(
        f"<a class='{'active' if key == active else ''}' href='{href}'>{label}</a>"
        for key, href, label in nav
    )
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
              <p class="eyebrow">PIPC Decision Insights</p>
              <h1>{escape(title)}</h1>
              <p class="subtitle">{escape(subtitle)}</p>
            </div>
          </header>
          <nav>{nav_html}</nav>
          <main>{body}</main>
        </body>
        </html>
        """
    )


def write_css(path: Path) -> None:
    path.write_text(
        dedent(
            """\
            :root {
              color-scheme: light;
              --bg: #f7f8fa;
              --panel: #ffffff;
              --text: #172033;
              --muted: #667085;
              --line: #d9dee8;
              --accent: #2563eb;
            }
            * { box-sizing: border-box; }
            body {
              margin: 0;
              background: var(--bg);
              color: var(--text);
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif;
              line-height: 1.55;
            }
            header { background: #172033; color: white; padding: 28px clamp(16px, 4vw, 48px); }
            header h1 { margin: 4px 0 6px; font-size: clamp(28px, 5vw, 48px); letter-spacing: 0; }
            .eyebrow { margin: 0; color: #9fb7ff; font-weight: 700; font-size: 13px; text-transform: uppercase; }
            .subtitle { margin: 0; color: #d8deea; max-width: 760px; }
            nav {
              position: sticky; top: 0; z-index: 10;
              display: flex; gap: 6px; overflow-x: auto;
              background: rgba(255,255,255,.96); border-bottom: 1px solid var(--line);
              padding: 8px clamp(12px, 4vw, 48px);
            }
            nav a { white-space: nowrap; color: #344054; text-decoration: none; padding: 8px 10px; border-radius: 6px; font-size: 14px; }
            nav a.active { background: #e9efff; color: #1d4ed8; font-weight: 700; }
            main { width: min(1180px, 100%); margin: 0 auto; padding: 20px clamp(12px, 3vw, 28px) 48px; }
            section { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 18px; margin: 14px 0; overflow: hidden; }
            h2 { margin: 0 0 14px; font-size: clamp(20px, 3vw, 26px); letter-spacing: 0; }
            .cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 14px 0; }
            .card { background: white; border: 1px solid var(--line); border-radius: 8px; padding: 16px; min-width: 0; }
            .card .label { color: var(--muted); font-size: 13px; }
            .card .value { font-size: clamp(24px, 4vw, 34px); font-weight: 800; margin: 4px 0; }
            .card .hint { color: var(--muted); font-size: 13px; }
            .chart-wrap { width: 100%; overflow-x: auto; }
            svg.chart { width: 100%; height: auto; min-width: 520px; }
            .axis, .tick { fill: #667085; font-size: 12px; }
            .bar-label { fill: #172033; font-size: 12px; }
            .note { border-left: 4px solid var(--accent); background: #eef4ff; padding: 12px 14px; border-radius: 6px; color: #243b63; }
            .insight-list { margin: 0; padding-left: 20px; }
            .insight-list li { margin: 8px 0; }
            table { width: 100%; border-collapse: collapse; font-size: 14px; }
            th, td { text-align: left; border-bottom: 1px solid var(--line); padding: 8px; vertical-align: top; }
            th { background: #f1f4f9; font-weight: 700; }
            .table-wrap { overflow-x: auto; }
            .link-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
            .report-link { display: block; background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 16px; text-decoration: none; color: var(--text); }
            .report-link strong { display: block; margin-bottom: 4px; }
            .report-link span { color: var(--muted); font-size: 14px; }
            @media (max-width: 760px) {
              .cards, .link-grid { grid-template-columns: 1fr; }
              section { padding: 14px; }
              svg.chart { min-width: 440px; }
              th, td { font-size: 13px; }
            }
            """
        ),
        encoding="utf-8",
    )


def metric_cards(items: list[tuple[str, str, str]]) -> str:
    html = "<div class='cards'>"
    for label, value, hint in items:
        html += (
            "<div class='card'>"
            f"<div class='label'>{escape(label)}</div>"
            f"<div class='value'>{escape(value)}</div>"
            f"<div class='hint'>{escape(hint)}</div>"
            "</div>"
        )
    return html + "</div>"


def section(title: str, content: str) -> str:
    return f"<section><h2>{escape(title)}</h2>{content}</section>"


def note(text: str) -> str:
    return f"<section><p class='note'>{escape(text)}</p></section>"


def horizontal_bar(labels, values, title: str) -> str:
    labels = [str(x) for x in labels]
    values = [float(x) for x in values]
    width, row_h = 900, 34
    height = max(90, 44 + row_h * len(labels))
    max_v = max(values) if values else 1
    rows = []
    for i, (label, value) in enumerate(zip(labels, values)):
        y = 28 + i * row_h
        bar_w = 610 * (value / max_v if max_v else 0)
        color = PALETTE[i % len(PALETTE)]
        rows.append(f"<text x='8' y='{y+18}' class='tick'>{escape(label[:36])}</text>")
        rows.append(f"<rect x='250' y='{y}' width='{bar_w:.1f}' height='22' rx='3' fill='{color}'></rect>")
        rows.append(f"<text x='{260+bar_w:.1f}' y='{y+16}' class='bar-label'>{value:,.0f}{escape(title) if title in ['%', '건수'] and title == '%' else ''}</text>")
    return f"<div class='chart-wrap'><svg class='chart' viewBox='0 0 {width} {height}' role='img'>{''.join(rows)}</svg></div>"


def vertical_bar(labels, values, title: str) -> str:
    labels = [str(x) for x in labels]
    values = [float(x) for x in values]
    width, height = 900, 360
    left, bottom, top = 54, 56, 28
    plot_w = width - left - 24
    plot_h = height - top - bottom
    max_v = max(values) if values else 1
    bar_gap = 8
    bar_w = max(12, (plot_w - bar_gap * max(len(values) - 1, 0)) / max(len(values), 1))
    parts = [f"<text x='{left}' y='18' class='axis'>{escape(title)}</text>"]
    for i, (label, value) in enumerate(zip(labels, values)):
        x = left + i * (bar_w + bar_gap)
        h = plot_h * (value / max_v if max_v else 0)
        y = top + plot_h - h
        parts.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_w:.1f}' height='{h:.1f}' rx='3' fill='{PALETTE[i % len(PALETTE)]}'></rect>")
        parts.append(f"<text x='{x + bar_w/2:.1f}' y='{y - 5:.1f}' text-anchor='middle' class='bar-label'>{value:,.0f}</text>")
        parts.append(f"<text x='{x + bar_w/2:.1f}' y='{height - 22}' text-anchor='middle' class='tick'>{escape(label[-8:])}</text>")
    parts.append(f"<line x1='{left}' y1='{top + plot_h}' x2='{width-16}' y2='{top + plot_h}' stroke='#d9dee8'></line>")
    return f"<div class='chart-wrap'><svg class='chart' viewBox='0 0 {width} {height}' role='img'>{''.join(parts)}</svg></div>"


def stacked_bar(df: pd.DataFrame, x_col: str, stack_col: str, value_col: str) -> str:
    if df.empty:
        return "<p>No data.</p>"
    years = sorted(df[x_col].astype(str).unique())
    stacks = list(df.groupby(stack_col)[value_col].sum().sort_values(ascending=False).head(7).index)
    pivot = df[df[stack_col].isin(stacks)].pivot_table(index=x_col, columns=stack_col, values=value_col, aggfunc="sum", fill_value=0).reindex(years)
    totals = pivot.sum(axis=1)
    width, height = 900, 380
    left, top, bottom = 48, 24, 72
    plot_w, plot_h = width - left - 18, height - top - bottom
    max_total = max(totals.max(), 1)
    gap = 6
    bar_w = max(14, (plot_w - gap * (len(years) - 1)) / len(years))
    parts = []
    for i, year in enumerate(years):
        x = left + i * (bar_w + gap)
        y_base = top + plot_h
        for j, stack in enumerate(stacks):
            value = float(pivot.loc[year, stack]) if stack in pivot else 0
            h = plot_h * value / max_total
            y_base -= h
            parts.append(f"<rect x='{x:.1f}' y='{y_base:.1f}' width='{bar_w:.1f}' height='{h:.1f}' fill='{PALETTE[j % len(PALETTE)]}'></rect>")
        parts.append(f"<text x='{x + bar_w/2:.1f}' y='{height-32}' text-anchor='middle' class='tick'>{escape(year)}</text>")
    legend = []
    for j, stack in enumerate(stacks):
        lx = left + (j % 3) * 240
        ly = height - 14 - (j // 3) * 18
        legend.append(f"<rect x='{lx}' y='{ly-10}' width='10' height='10' fill='{PALETTE[j % len(PALETTE)]}'></rect><text x='{lx+15}' y='{ly}' class='tick'>{escape(str(stack))}</text>")
    parts.append(f"<line x1='{left}' y1='{top+plot_h}' x2='{width-16}' y2='{top+plot_h}' stroke='#d9dee8'></line>")
    return f"<div class='chart-wrap'><svg class='chart' viewBox='0 0 {width} {height}' role='img'>{''.join(parts + legend)}</svg></div>"


def table(df: pd.DataFrame, limit: int | None = None) -> str:
    if limit:
        df = df.head(limit)
    if df.empty:
        return "<p>No rows.</p>"
    html = "<div class='table-wrap'><table><thead><tr>"
    for col in df.columns:
        html += f"<th>{escape(str(col))}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr>"
        for col in df.columns:
            value = row[col]
            if pd.isna(value):
                value = ""
            elif isinstance(value, float):
                value = f"{value:,.3g}"
            html += f"<td>{escape(str(value))}</td>"
        html += "</tr>"
    return html + "</tbody></table></div>"


def count_category(df: pd.DataFrame) -> pd.DataFrame:
    out = df["document_category"].fillna("other").value_counts().rename_axis("document_category").reset_index(name="count")
    out["label"] = out["document_category"].map(CATEGORY_LABELS).fillna(out["document_category"])
    return out


def year_category_counts(df: pd.DataFrame) -> pd.DataFrame:
    data = df[df["year"] != ""].copy()
    data["category_label"] = data["document_category"].map(CATEGORY_LABELS).fillna(data["document_category"])
    return data.groupby(["year", "category_label"]).size().reset_index(name="count")


def top_counts(df: pd.DataFrame, column: str, limit: int):
    data = top_values(df, column, limit)
    return data[column], data["count"]


def top_values(df: pd.DataFrame, column: str, limit: int) -> pd.DataFrame:
    values = df[column].fillna("(missing)").replace("", "(missing)").value_counts().head(limit)
    return values.rename_axis(column).reset_index(name="count")


def exploded(df: pd.DataFrame, column: str, limit: int):
    counts: dict[str, int] = {}
    for value in df[column].fillna(""):
        for item in split_items(value):
            counts[item] = counts.get(item, 0) + 1
    out = pd.DataFrame(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit], columns=[column, "count"])
    return out[column] if not out.empty else [], out["count"] if not out.empty else []


def year_counts(df: pd.DataFrame):
    out = df[df["year"] != ""]["year"].value_counts().sort_index().reset_index()
    out.columns = ["year", "count"]
    return out["year"], out["count"]


def recommendation_chart(df: pd.DataFrame) -> str:
    if df.empty:
        return "<p>No data.</p>"
    data = df[df["year"] != ""].copy()
    data["recommended"] = data["order_text"].fillna("").str.contains(r"권고|변경|보완|개선", regex=True)
    out = data.groupby("year").agg(count=("decision_id", "size"), recommended=("recommended", "sum")).reset_index()
    out["rate"] = out["recommended"] / out["count"] * 100
    return vertical_bar(out["year"], out["rate"], "%")


def money_by_year_chart(df: pd.DataFrame) -> str:
    data = df[df["monetary_amount"].notna() & (df["year"] != "")]
    if data.empty:
        return "<p>No monetary amount extracted.</p>"
    out = data.groupby("year")["monetary_amount"].median().reset_index()
    out["million_won"] = out["monetary_amount"] / 1_000_000
    return vertical_bar(out["year"], out["million_won"], "중앙값(백만원)")


def top_money(df: pd.DataFrame, limit: int) -> pd.DataFrame:
    columns = ["decision_id", "decision_date", "title", "monetary_amount", "sanction_types", "case_type"]
    out = df[df["monetary_amount"].notna()].sort_values("monetary_amount", ascending=False)[columns].head(limit).copy()
    out["monetary_amount"] = out["monetary_amount"].map(format_won)
    return out


def contains_count(df: pd.DataFrame, column: str, text: str) -> int:
    return int(df[column].fillna("").str.contains(text, regex=False).sum())


def pct(value: float) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{value * 100:.1f}%"


def format_won(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    value = int(value)
    if value >= 100_000_000:
        return f"{value / 100_000_000:.1f}억원"
    if value >= 10_000:
        return f"{value / 10_000:.0f}만원"
    return f"{value:,}원"
