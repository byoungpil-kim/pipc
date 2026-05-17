from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


LIST_FIELDS = [
    "decision_id",
    "title",
    "agenda_no",
    "meeting_type",
    "decision_type",
    "decision_date",
    "detail_url",
]

DECISION_FIELDS = [
    "decision_id",
    "agency",
    "title",
    "agenda_no",
    "meeting_type",
    "decision_type",
    "decision_date",
    "applicant",
    "order_text",
    "reason_text",
    "background_text",
    "summary_text",
    "main_text",
    "objection_text",
    "signature_text",
    "appendix_text",
    "raw_xml_path",
]


LIST_ALIASES = {
    "decision_id": ["ID", "id", "판례일련번호", "결정문일련번호", "일련번호"],
    "title": ["사건명", "title", "제목", "안건명"],
    "agenda_no": ["의안번호", "안건번호"],
    "meeting_type": ["회의종류", "회의구분"],
    "decision_type": ["의결구분", "결정구분", "처분구분"],
    "decision_date": ["의결일", "의결일자", "결정일자", "선고일자", "ddes"],
    "detail_url": ["결정문상세링크", "상세링크", "detail_url", "법령상세링크"],
}

DECISION_ALIASES = {
    "decision_id": ["ID", "id", "결정문일련번호", "일련번호"],
    "agency": ["기관명", "소관부처", "agency"],
    "title": ["사건명", "제목", "안건명"],
    "agenda_no": ["의안번호", "안건번호"],
    "meeting_type": ["회의종류", "회의구분"],
    "decision_type": ["결정", "의결구분", "결정구분", "처분구분"],
    "decision_date": ["의결일", "의결일자", "의결연월일", "결정일자", "선고일자"],
    "applicant": ["청구인", "신청인", "피심인", "처분대상"],
    "order_text": ["주문"],
    "reason_text": ["이유", "판단이유"],
    "background_text": ["처분의 경위", "사건의 개요", "배경"],
    "summary_text": ["결정요지", "요약"],
    "main_text": ["주요내용", "본문", "내용"],
    "objection_text": ["이의제기방법및기간", "불복절차", "이의신청"],
    "signature_text": ["위원서명", "서명", "날인"],
    "appendix_text": ["별지", "첨부", "붙임"],
}


@dataclass(frozen=True)
class ParsedList:
    rows: list[dict[str, str]]
    total_count: int | None


def parse_xml(path: Path) -> ET.Element:
    return ET.fromstring(path.read_bytes())


def parse_list_file(path: Path) -> ParsedList:
    root = parse_xml(path)
    rows = [normalize_record(node, LIST_ALIASES, LIST_FIELDS) for node in find_record_nodes(root)]
    rows = [row for row in rows if any(row.values())]
    return ParsedList(rows=rows, total_count=find_total_count(root))


def parse_decision_file(path: Path) -> dict[str, str]:
    root = parse_xml(path)
    record = normalize_record(root, DECISION_ALIASES, DECISION_FIELDS)
    if not record["decision_id"]:
        record["decision_id"] = path.stem
    record["raw_xml_path"] = str(path)
    return record


def find_record_nodes(root: ET.Element) -> list[ET.Element]:
    ppc_nodes = [
        node
        for node in root.iter()
        if strip_ns(node.tag).lower() == "ppc" and node.attrib.get("id")
    ]
    if ppc_nodes:
        return ppc_nodes

    candidates = []
    for node in root.iter():
        tag = strip_ns(node.tag).lower()
        if tag in {"law", "item", "result", "decision"}:
            children_text = "".join((child.text or "") for child in list(node))
            if children_text.strip():
                candidates.append(node)
    if candidates:
        return candidates
    return [node for node in root if list(node)] or [root]


def find_total_count(root: ET.Element) -> int | None:
    for node in root.iter():
        if strip_ns(node.tag).lower() in {"totalcnt", "총건수"} and node.text:
            digits = re.sub(r"\D", "", node.text)
            return int(digits) if digits else None
    return None


def normalize_record(root: ET.Element, aliases: dict[str, list[str]], fields: Iterable[str]) -> dict[str, str]:
    flat = flatten_xml(root)
    row = {field: "" for field in fields}
    for field, names in aliases.items():
        row[field] = first_value(flat, names)
    if "decision_date" in row:
        row["decision_date"] = normalize_date(row["decision_date"])
    return row


def flatten_xml(root: ET.Element) -> dict[str, str]:
    values: dict[str, list[str]] = {}
    for node in root.iter():
        text = collect_text(node)
        if not text:
            continue
        tag = strip_ns(node.tag)
        values.setdefault(tag, []).append(text)
    return {key: "\n".join(dict.fromkeys(items)) for key, items in values.items()}


def collect_text(node: ET.Element) -> str:
    return normalize_space(" ".join(part for part in node.itertext() if part and part.strip()))


def first_value(flat: dict[str, str], names: Iterable[str]) -> str:
    lowered = {key.lower(): value for key, value in flat.items()}
    for name in names:
        if name in flat and flat[name]:
            return flat[name]
        value = lowered.get(name.lower())
        if value:
            return value
    return ""


def normalize_date(value: str) -> str:
    dotted = re.match(r"\s*(\d{4})\.(\d{1,2})\.(\d{1,2})\.?\s*$", value)
    if dotted:
        return f"{int(dotted.group(1)):04d}-{int(dotted.group(2)):02d}-{int(dotted.group(3)):02d}"
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return value.strip()


def normalize_space(value: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", value).strip()


def strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
