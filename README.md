# PIPC Decision Collection

This project collects, parses, and analyzes Personal Information Protection Commission decisions from the Korean Law Open API.

## Current Outputs

The repository currently includes 3,990 collected decisions, parsed datasets, analysis tables, and staff-facing HTML reports.

- GitHub Pages site: https://byoungpil-kim.github.io/pipc/
- Major issue report: [`reports/issues/index.html`](reports/issues/index.html)
- Decision type report index: [`reports/full_html/index.html`](reports/full_html/index.html)
- Mobile-friendly summary report index: [`reports/html/index.html`](reports/html/index.html)
- Handoff and next work log: [`NEXT_SESSION.md`](NEXT_SESSION.md)

Open the HTML files locally for the rendered report experience, or inspect them directly in GitHub as versioned artifacts.

For the simplest GitHub Pages setup, use `Settings` -> `Pages` -> `Deploy from a branch`, then select `main` and `/root`.

## Setup

```bash
cd ~/pipc
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Create `.env` in the project root:

```text
OC=your_law_api_oc_value
```

The server IP or domain must be registered with the Law Open API before collection.

## Common Commands

```bash
pipc smoke
pipc collect-list --max-pages 1
pipc collect-decisions
pipc parse
pipc eda
pipc insights
pipc html-reports
pipc full-reports
pipc type-topic-maps
pipc global-issue-report
```

Raw XML is stored under `data/raw` and parsed outputs are written to `data/processed`.
