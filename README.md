# PIPC Decision Collection

This project collects, parses, and analyzes Personal Information Protection Commission decisions from the Korean Law Open API.

## Current Outputs

The repository currently includes 3,990 collected decisions, parsed datasets, analysis tables, and staff-facing HTML reports.

- Global issue report: [`reports/global_issues.html`](reports/global_issues.html)
- Cluster full report index: [`reports/cluster_full_html/index.html`](reports/cluster_full_html/index.html)
- Section full report index: [`reports/full_html/index.html`](reports/full_html/index.html)
- Mobile-friendly summary report index: [`reports/html/index.html`](reports/html/index.html)
- Handoff and next work log: [`NEXT_SESSION.md`](NEXT_SESSION.md)

Open the HTML files locally for the rendered report experience, or inspect them directly in GitHub as versioned artifacts.

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
pipc cluster --n-clusters 18
pipc cluster-reports
pipc global-issue-report
```

Raw XML is stored under `data/raw` and parsed outputs are written to `data/processed`.
