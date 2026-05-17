# PIPC Decision Collection

This project collects, parses, and analyzes Personal Information Protection Commission decisions from the Korean Law Open API.

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
```

Raw XML is stored under `data/raw` and parsed outputs are written to `data/processed`.
