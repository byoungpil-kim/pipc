from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    oc: str
    root: Path = PROJECT_ROOT
    raw_dir: Path = PROJECT_ROOT / "data" / "raw"
    processed_dir: Path = PROJECT_ROOT / "data" / "processed"
    reports_dir: Path = PROJECT_ROOT / "reports"
    request_timeout: int = 30


def load_env(path: Path | None = None) -> dict[str, str]:
    env_path = path or PROJECT_ROOT / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_settings(env_path: Path | None = None) -> Settings:
    values = load_env(env_path)
    oc = values.get("OC")
    if not oc:
        raise RuntimeError("Missing OC in .env. Expected a line like OC=...")
    return Settings(oc=oc)
