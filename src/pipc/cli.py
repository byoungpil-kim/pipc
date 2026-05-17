from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .api import LawApiClient
from .collect import collect_decisions, collect_list_pages
from .config import get_settings, require_oc
from .labels import derive_labels
from .parse import DECISION_FIELDS, LIST_FIELDS, parse_decision_file, parse_list_file


DERIVED_FIELDS = [
    "document_category",
    "sanction_strength",
    "sanction_types",
    "monetary_amount",
    "violated_articles",
    "case_type",
    "factors",
    "document_length",
    "order_length",
    "reason_length",
]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipc")
    sub = parser.add_subparsers(dest="command")

    smoke = sub.add_parser("smoke", help="Fetch list page 1 and one decision for API validation.")
    smoke.add_argument("--force", action="store_true")
    smoke.set_defaults(func=cmd_smoke)

    collect_list = sub.add_parser("collect-list", help="Collect raw list page XML files.")
    collect_list.add_argument("--max-pages", type=int)
    collect_list.add_argument("--force", action="store_true")
    collect_list.set_defaults(func=cmd_collect_list)

    collect_body = sub.add_parser("collect-decisions", help="Collect raw decision XML files from parsed list pages.")
    collect_body.add_argument("--force", action="store_true")
    collect_body.set_defaults(func=cmd_collect_decisions)

    parse = sub.add_parser("parse", help="Parse raw XML into standard CSV and Parquet datasets.")
    parse.set_defaults(func=cmd_parse)

    eda = sub.add_parser("eda", help="Generate reports/eda.md and summary tables.")
    eda.set_defaults(func=cmd_eda)

    insights = sub.add_parser("insights", help="Generate a staff-facing multi-angle insights report.")
    insights.set_defaults(func=cmd_insights)

    html_reports = sub.add_parser("html-reports", help="Generate mobile-friendly HTML insight reports.")
    html_reports.set_defaults(func=cmd_html_reports)

    full_reports = sub.add_parser("full-reports", help="Generate detailed section-by-section full HTML reports.")
    full_reports.set_defaults(func=cmd_full_reports)

    global_issue_report = sub.add_parser("global-issue-report", help="Generate the separate global issue HTML report.")
    global_issue_report.set_defaults(func=cmd_global_issue_report)

    type_topic_maps = sub.add_parser("type-topic-maps", help="Build OpenRouter/UMAP/HDBSCAN topic maps inside each decision type.")
    type_topic_maps.add_argument("--category", action="append", help="Limit to one document_category. Can be repeated.")
    type_topic_maps.set_defaults(func=cmd_type_topic_maps)

    return parser


def cmd_smoke(args: argparse.Namespace) -> int:
    settings = get_settings()
    require_oc(settings)
    client = LawApiClient(settings)
    list_path = settings.raw_dir / "list_pages" / "page_1.xml"
    client.save_list_page(1, list_path, force=args.force)
    parsed = parse_list_file(list_path)
    if not parsed.rows:
        raise RuntimeError("List page smoke test succeeded at HTTP level but no decision rows were parsed.")
    decision_id = parsed.rows[0]["decision_id"]
    if not decision_id:
        raise RuntimeError("Could not find decision_id from the first list row.")
    decision_path = settings.raw_dir / "decisions" / f"{decision_id}.xml"
    client.save_decision(decision_id, decision_path, force=args.force)
    parse_decision_file(decision_path)
    print(f"OK list={list_path} decision_id={decision_id} decision={decision_path}")
    return 0


def cmd_collect_list(args: argparse.Namespace) -> int:
    settings = get_settings()
    require_oc(settings)
    client = LawApiClient(settings)
    paths = collect_list_pages(client, settings, max_pages=args.max_pages, force=args.force)
    print(f"Collected {len(paths)} list page XML files.")
    return 0


def cmd_collect_decisions(args: argparse.Namespace) -> int:
    settings = get_settings()
    require_oc(settings)
    ids = read_decision_ids(settings.raw_dir / "list_pages")
    client = LawApiClient(settings)
    successes, failures = collect_decisions(client, settings, ids, force=args.force)
    print(f"Collected decisions success={len(successes)} failure={len(failures)}")
    return 0 if not failures else 1


def cmd_parse(_args: argparse.Namespace) -> int:
    import pandas as pd

    settings = get_settings()
    list_rows = read_list_rows(settings.raw_dir / "list_pages")
    decision_rows = [
        enrich_decision_row(parse_decision_file(path))
        for path in sorted((settings.raw_dir / "decisions").glob("*.xml"))
    ]

    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    write_csv(settings.processed_dir / "list.csv", LIST_FIELDS, list_rows)
    write_csv(settings.processed_dir / "decisions.csv", DECISION_FIELDS + DERIVED_FIELDS, decision_rows)

    pd.DataFrame(list_rows).to_parquet(settings.processed_dir / "list.parquet", index=False)
    pd.DataFrame(decision_rows).to_parquet(settings.processed_dir / "decisions.parquet", index=False)
    print(f"Parsed list_rows={len(list_rows)} decision_rows={len(decision_rows)}")
    return 0


def cmd_eda(_args: argparse.Namespace) -> int:
    from .eda import generate_eda

    settings = get_settings()
    report = generate_eda(settings.processed_dir / "decisions.csv", settings.reports_dir)
    print(f"Wrote {report}")
    return 0


def cmd_insights(_args: argparse.Namespace) -> int:
    from .insights import generate_insights

    settings = get_settings()
    report = generate_insights(settings.processed_dir / "decisions.csv", settings.reports_dir)
    print(f"Wrote {report}")
    return 0


def cmd_html_reports(_args: argparse.Namespace) -> int:
    from .html_reports import generate_html_reports

    settings = get_settings()
    paths = generate_html_reports(settings.processed_dir / "decisions.csv", settings.reports_dir)
    print(f"Wrote {len(paths)} HTML reports under {settings.reports_dir / 'html'}")
    return 0


def cmd_full_reports(_args: argparse.Namespace) -> int:
    from .full_reports import generate_full_reports

    settings = get_settings()
    paths = generate_full_reports(settings.processed_dir / "decisions.csv", settings.reports_dir)
    print(f"Wrote {len(paths)} full HTML reports under {settings.reports_dir / 'full_html'}")
    return 0


def cmd_global_issue_report(_args: argparse.Namespace) -> int:
    from .global_issue_report import generate_global_issue_report

    settings = get_settings()
    path = generate_global_issue_report(settings.processed_dir / "decisions.csv", settings.reports_dir)
    print(f"Wrote {path}")
    return 0


def cmd_type_topic_maps(args: argparse.Namespace) -> int:
    from .type_topic_map import generate_type_topic_maps

    settings = get_settings()
    clusters_path, assignments_path = generate_type_topic_maps(
        settings.processed_dir / "decisions.csv",
        settings.reports_dir,
        categories=args.category,
    )
    print(f"Wrote {clusters_path}")
    print(f"Wrote {assignments_path}")
    return 0


def read_list_rows(list_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(list_dir.glob("page_*.xml")):
        rows.extend(parse_list_file(path).rows)
    return rows


def read_decision_ids(list_dir: Path) -> list[str]:
    ids = [row["decision_id"] for row in read_list_rows(list_dir) if row.get("decision_id")]
    return list(dict.fromkeys(ids))


def enrich_decision_row(row: dict[str, str]) -> dict[str, object]:
    text = "\n".join(
        str(row.get(column, ""))
        for column in ["title", "order_text", "reason_text", "background_text", "summary_text", "main_text"]
    )
    labels = derive_labels(
        text,
        amount_text=str(row.get("order_text", "")),
        title_text=str(row.get("title", "")),
    )
    enriched: dict[str, object] = dict(row)
    enriched.update(
        {
            "sanction_strength": labels.sanction_strength,
            "document_category": labels.document_category,
            "sanction_types": labels.sanction_types,
            "monetary_amount": labels.monetary_amount,
            "violated_articles": labels.violated_articles,
            "case_type": labels.case_type,
            "factors": labels.factors,
            "document_length": len(text),
            "order_length": len(str(row.get("order_text", ""))),
            "reason_length": len(str(row.get("reason_text", ""))),
        }
    )
    return enriched


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
