from __future__ import annotations

from html import escape
from pathlib import Path
from textwrap import dedent

import pandas as pd

from .html_reports import format_won, horizontal_bar, metric_cards, note, section, table, vertical_bar, write_css
from .insights import CATEGORY_LABELS, ensure_columns, split_items


def generate_cluster_reports(processed_path: Path, reports_dir: Path) -> list[Path]:
    df = pd.read_csv(processed_path)
    ensure_columns(df)
    tables_dir = reports_dir / "tables" / "clusters"
    assignments = pd.read_csv(tables_dir / "cluster_assignments.csv")
    summary = pd.read_csv(tables_dir / "cluster_summary.csv")
    issues = pd.read_csv(tables_dir / "cluster_issue_candidates.csv")

    df = df.merge(assignments[["decision_id", "cluster_id"]], on="decision_id", how="left")
    out_dir = reports_dir / "cluster_full_html"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_css(out_dir / "style.css")

    representatives = representative_decision_table(df)
    representatives.to_csv(tables_dir / "cluster_representative_decisions.csv", index=False)

    written = []
    index_path = out_dir / "index.html"
    index_path.write_text(render_index(summary, issues), encoding="utf-8")
    written.append(index_path)

    for cluster_id in sorted(summary["cluster_id"].astype(int).unique()):
        group = df[df["cluster_id"] == cluster_id].copy()
        cluster_summary = summary[summary["cluster_id"].astype(int) == cluster_id].iloc[0]
        cluster_issues = issues[issues["cluster_id"].astype(int) == cluster_id].sort_values("rank")
        reps = representatives[representatives["cluster_id"].astype(int) == cluster_id].head(12)
        path = out_dir / f"cluster_{cluster_id:02d}.html"
        path.write_text(render_cluster_page(cluster_id, group, cluster_summary, cluster_issues, reps), encoding="utf-8")
        written.append(path)
    return written


def render_index(summary: pd.DataFrame, issues: pd.DataFrame) -> str:
    summary = summary.copy()
    summary["category_label"] = summary["dominant_category"].map(CATEGORY_LABELS).fillna(summary["dominant_category"])
    cards = metric_cards(
        [
            ("클러스터", f"{len(summary):,}", "비지도 묶음"),
            ("최대 클러스터", f"{int(summary['size'].max()):,}", "결정문 수"),
            ("쟁점 후보", f"{len(issues):,}", "클러스터별 상위 쟁점"),
            ("글로벌 쟁점 포함", f"{int((issues['issue_type'] == 'global').sum()):,}", "외부 논쟁 기반"),
        ]
    )
    listing = summary.sort_values("cluster_id").copy()
    listing["cluster"] = listing["cluster_id"].map(lambda x: f"<a href='cluster_{int(x):02d}.html'>Cluster {int(x):02d}</a>")
    display = listing[
        ["cluster_id", "size", "category_label", "year_min", "year_max", "title_keywords", "top_case_types", "top_articles"]
    ].rename(
        columns={
            "cluster_id": "cluster",
            "size": "건수",
            "category_label": "주요 장르",
            "year_min": "시작연도",
            "year_max": "종료연도",
            "title_keywords": "제목 키워드",
            "top_case_types": "사건유형",
            "top_articles": "주요 조문",
        }
    ).fillna("")
    body = cards + section("클러스터 목록", linked_table(display, listing["cluster"].tolist()))
    body += note("클러스터는 통계적 묶음이므로 법적 결론이 아니라 탐색 단위다. 각 페이지의 쟁점 후보는 문서 내 용어 매칭과 외부 쟁점 taxonomy를 결합한 것이다.")
    return report_page("클러스터 Full Report", "결정문 유사 묶음별 쟁점과 대표 사례", body, "index")


def render_cluster_page(
    cluster_id: int,
    group: pd.DataFrame,
    cluster_summary: pd.Series,
    issues: pd.DataFrame,
    representatives: pd.DataFrame,
) -> str:
    category_mix = category_counts(group)
    years = year_counts(group)
    money = group["monetary_amount"].dropna()
    dominant = str(cluster_summary["dominant_category"])
    issue_names = issues["issue"].head(4).tolist()
    cards = metric_cards(
        [
            ("결정문", f"{len(group):,}", "클러스터 규모"),
            ("주요 장르", CATEGORY_LABELS.get(dominant, dominant), "최빈 라벨"),
            ("기간", f"{cluster_summary['year_min']}-{cluster_summary['year_max']}", "결정일 기준"),
            ("최대 금액", format_won(money.max()) if not money.empty else "n/a", "추출 금액 기준"),
        ]
    )
    body = cards
    body += section("해석 요약", insight_list(cluster_insights(group, cluster_summary, issue_names)))
    body += section("클러스터 쟁점 후보", table(issue_display(issues)))
    if not issues.empty:
        body += section("쟁점별 매칭 결정문 수", horizontal_bar(issues["issue"].head(10), issues["matched_decisions"].head(10), "건수"))
    body += section("장르 구성", horizontal_bar(category_mix["label"], category_mix["count"], "건수"))
    body += section("연도별 흐름", vertical_bar(years["year"], years["count"], "건수"))
    body += section("대표 결정문", table(representatives.drop(columns=["cluster_id"], errors="ignore")))
    body += section(
        "텍스트 신호",
        table(
            pd.DataFrame(
                [
                    ["상위 TF-IDF/문자 n-gram", cluster_summary.get("top_terms", "")],
                    ["제목 키워드", cluster_summary.get("title_keywords", "")],
                    ["사건유형", cluster_summary.get("top_case_types", "")],
                    ["주요 조문", cluster_summary.get("top_articles", "")],
                ],
                columns=["항목", "내용"],
            )
        ),
    )
    body += note("대표 결정문은 금액 제재가 있으면 금액을 우선하고, 그 외에는 본문 길이와 최신성을 기준으로 골랐다. 실제 법적 의미 확정 전에는 원문 검수가 필요하다.")
    return report_page(f"Cluster {cluster_id:02d} Full Report", "클러스터별 정량·정성 분석", body, f"cluster_{cluster_id:02d}")


def report_page(title: str, subtitle: str, body: str, active: str) -> str:
    nav = "<a class='active' href='index.html'>클러스터 홈</a><a href='../global_issues.html'>글로벌 쟁점</a><a href='../full_html/index.html'>섹션 리포트</a>"
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
              <p class="eyebrow">PIPC Decision Cluster Insights</p>
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


def representative_decision_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cluster_id, group in df.dropna(subset=["cluster_id"]).groupby("cluster_id"):
        reps = group.sort_values(["monetary_amount", "document_length", "decision_date"], ascending=[False, False, False], na_position="last").head(15)
        for _, row in reps.iterrows():
            rows.append(
                {
                    "cluster_id": int(cluster_id),
                    "decision_id": row["decision_id"],
                    "decision_date": clean_value(row.get("decision_date", "")),
                    "category": CATEGORY_LABELS.get(row.get("document_category", ""), row.get("document_category", "")),
                    "title": clean_value(row.get("title", "")),
                    "sanctions": clean_value(row.get("sanction_types", "")),
                    "amount": format_won(row["monetary_amount"]) if pd.notna(row.get("monetary_amount")) else "",
                    "articles": clean_value(row.get("violated_articles", "")),
                    "case_type": clean_value(row.get("case_type", "")),
                    "snippet": snippet(row),
                }
            )
    return pd.DataFrame(rows)


def snippet(row: pd.Series, limit: int = 180) -> str:
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


def category_counts(group: pd.DataFrame) -> pd.DataFrame:
    counts = group["document_category"].fillna("other").value_counts().reset_index()
    counts.columns = ["document_category", "count"]
    counts["label"] = counts["document_category"].map(CATEGORY_LABELS).fillna(counts["document_category"])
    return counts


def year_counts(group: pd.DataFrame) -> pd.DataFrame:
    data = group.copy()
    data["year"] = data["decision_date"].fillna("").astype(str).str[:4]
    out = data[data["year"].str.match(r"^\d{4}$", na=False)]["year"].value_counts().sort_index().reset_index()
    out.columns = ["year", "count"]
    return out


def issue_display(issues: pd.DataFrame) -> pd.DataFrame:
    if issues.empty:
        return pd.DataFrame(columns=["순위", "유형", "쟁점", "매칭 결정문", "표현 빈도", "법적 초점"])
    return issues[["rank", "issue_type", "issue", "matched_decisions", "count", "legal_focus"]].rename(
        columns={
            "rank": "순위",
            "issue_type": "유형",
            "issue": "쟁점",
            "matched_decisions": "매칭 결정문",
            "count": "표현 빈도",
            "legal_focus": "법적 초점",
        }
    )


def cluster_insights(group: pd.DataFrame, cluster_summary: pd.Series, issue_names: list[str]) -> list[str]:
    dominant = str(cluster_summary["dominant_category"])
    category_label = CATEGORY_LABELS.get(dominant, dominant)
    issue_text = ", ".join(issue_names) if issue_names else "명시적 쟁점 후보 부족"
    top_articles = clean_value(cluster_summary.get("top_articles", "")) or "조문 신호 약함"
    top_cases = clean_value(cluster_summary.get("top_case_types", "")) or "사건유형 신호 약함"
    money_count = int(group["monetary_amount"].notna().sum())
    return [
        f"이 클러스터는 {category_label} 중심의 {len(group):,}건 묶음이며, 제목·본문 신호상 {issue_text}가 우선 검토 대상이다.",
        f"주요 사건유형 신호는 {top_cases}이고, 조문 신호는 {top_articles}이다.",
        f"금액 제재가 추출된 결정문은 {money_count:,}건이므로, 금액이 많은 클러스터는 제재 비례성과 병합 사건 여부를 함께 봐야 한다.",
        cluster_category_guidance(dominant),
    ]


def cluster_category_guidance(category: str) -> str:
    mapping = {
        "enforcement": "제재 클러스터에서는 위반행위, 조문, 제재 패키지, 금액 산정 사유를 나란히 비교하는 방식이 실무 활용도가 높다.",
        "privacy_impact_review": "침해요인 평가 클러스터에서는 법령안의 처리 근거, 처리 항목, 보유기간, 위탁·연계 구조를 별지 중심으로 재검수해야 한다.",
        "public_system_inspection": "공공점검 클러스터에서는 반복 취약점과 개선권고 이행 여부를 기관·시스템 단위로 추적하는 관점이 필요하다.",
        "data_provision_request": "제공 요청 클러스터에서는 허용·불허 결론보다 법정 업무수행 근거와 필요한 범위 판단을 구조화해야 한다.",
    }
    return mapping.get(category, "혼합 클러스터는 장르 라벨을 추가 검수해 해석·정책·제재 사건이 섞였는지 확인해야 한다.")


def insight_list(items: list[str]) -> str:
    return "<ul class='insight-list'>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def linked_table(df: pd.DataFrame, links: list[str]) -> str:
    html = "<div class='table-wrap'><table><thead><tr>"
    for col in df.columns:
        html += f"<th>{escape(str(col))}</th>"
    html += "</tr></thead><tbody>"
    for i, (_, row) in enumerate(df.iterrows()):
        html += "<tr>"
        for col in df.columns:
            value = row[col]
            if col == "cluster":
                value = links[i]
                html += f"<td>{value}</td>"
            else:
                html += f"<td>{escape(str(value))}</td>"
        html += "</tr>"
    return html + "</tbody></table></div>"
