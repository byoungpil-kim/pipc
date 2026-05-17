from __future__ import annotations

import csv
from pathlib import Path

from .api import LawApiClient, LawApiError
from .config import Settings
from .parse import parse_list_file


def collect_list_pages(
    client: LawApiClient,
    settings: Settings,
    max_pages: int | None = None,
    force: bool = False,
) -> list[Path]:
    paths: list[Path] = []
    page = 1
    total_count: int | None = None
    while True:
        path = settings.raw_dir / "list_pages" / f"page_{page}.xml"
        client.save_list_page(page, path, force=force)
        paths.append(path)
        parsed = parse_list_file(path)
        if total_count is None:
            total_count = parsed.total_count
        if max_pages and page >= max_pages:
            break
        if total_count and page * 100 >= total_count:
            break
        if not parsed.rows:
            break
        page += 1
    return paths


def collect_decisions(
    client: LawApiClient,
    settings: Settings,
    decision_ids: list[str],
    force: bool = False,
) -> tuple[list[str], list[tuple[str, str]]]:
    successes: list[str] = []
    failures: list[tuple[str, str]] = []
    for decision_id in decision_ids:
        path = settings.raw_dir / "decisions" / f"{decision_id}.xml"
        try:
            client.save_decision(decision_id, path, force=force)
            successes.append(decision_id)
        except LawApiError as exc:
            failures.append((decision_id, str(exc)))
    write_failures(settings.processed_dir / "failed_decisions.csv", failures)
    return successes, failures


def write_failures(path: Path, failures: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["decision_id", "error"])
        writer.writerows(failures)
