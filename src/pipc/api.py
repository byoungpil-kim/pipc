from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import Settings


LAW_SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
LAW_SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"


class LawApiError(RuntimeError):
    pass


class LawApiClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def fetch_list_page(self, page: int, display: int = 100) -> bytes:
        params = {
            "OC": self.settings.oc,
            "target": "ppc",
            "type": "XML",
            "display": str(display),
            "page": str(page),
            "sort": "ddes",
        }
        return self._get(LAW_SEARCH_URL, params)

    def fetch_decision(self, decision_id: str) -> bytes:
        params = {
            "OC": self.settings.oc,
            "target": "ppc",
            "type": "XML",
            "ID": decision_id,
        }
        return self._get(LAW_SERVICE_URL, params)

    def save_list_page(self, page: int, path: Path, force: bool = False) -> bool:
        return self._save(path, lambda: self.fetch_list_page(page), force)

    def save_decision(self, decision_id: str, path: Path, force: bool = False) -> bool:
        return self._save(path, lambda: self.fetch_decision(decision_id), force)

    def _get(self, url: str, params: dict[str, str]) -> bytes:
        full_url = f"{url}?{urlencode(params)}"
        request = Request(full_url, headers={"User-Agent": "pipc-collector/0.1"})
        try:
            with urlopen(request, timeout=self.settings.request_timeout) as response:
                body = response.read()
        except HTTPError as exc:
            raise LawApiError(f"HTTP {exc.code} while requesting {url}") from exc
        except URLError as exc:
            raise LawApiError(f"Network error while requesting {url}: {exc.reason}") from exc

        if b"<result>" in body and (
            "사용자 정보 검증에 실패".encode("utf-8") in body
            or b"Authentication" in body
        ):
            raise LawApiError("API authentication failed. Check OC and registered IP/domain.")
        return body

    @staticmethod
    def _save(path: Path, fetcher, force: bool = False) -> bool:
        if path.exists() and not force:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fetcher())
        return True
