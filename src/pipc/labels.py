from __future__ import annotations

import re
from dataclasses import dataclass


SANCTION_PATTERNS = {
    "과징금": re.compile(r"과\s*징\s*금\s*(?:[:：]|\d|을\s*부과|를\s*부과|부과한다)"),
    "과태료": re.compile(r"과\s*태\s*료\s*(?:[:：]|\d|을\s*부과|를\s*부과|부과한다)"),
    "시정명령": re.compile(r"시정\s*명령|시정조치(?:를\s*)?명"),
    "공표명령": re.compile(r"공표\s*명령|공표할\s*것|홈페이지에\s*공표"),
    "개선권고": re.compile(r"개선\s*권고|개선을\s*권고|권고한다"),
    "주의": re.compile(r"주의\s*처분|주의를\s*촉구"),
    "고발": re.compile(r"고발"),
}

CASE_TYPE_PATTERNS = {
    "유출·침해": re.compile(r"유출|침해|해킹|노출"),
    "동의·고지 위반": re.compile(r"동의|고지"),
    "목적 외 이용": re.compile(r"목적\s*외"),
    "제3자 제공": re.compile(r"제3자\s*제공|제삼자\s*제공"),
    "국외이전": re.compile(r"국외\s*이전|해외\s*이전"),
    "안전조치 미흡": re.compile(r"안전조치|접근통제|암호화|관리적·?기술적"),
    "보유기간·파기 위반": re.compile(r"보유기간|파기"),
    "영상정보 처리": re.compile(r"영상정보|CCTV|폐쇄회로"),
    "아동 개인정보": re.compile(r"아동|만\s*14세"),
    "민감정보·고유식별정보": re.compile(r"민감정보|고유식별정보|주민등록번호"),
    "접근권한·내부통제": re.compile(r"접근권한|내부통제"),
    "처리위탁": re.compile(r"처리위탁|수탁자|위탁"),
    "정보주체 권리보장": re.compile(r"열람|정정|삭제|처리정지|권리"),
}

ARTICLE_RE = re.compile(r"제\s*\d+\s*조(?:의\s*\d+)?")
MONEY_RE = re.compile(r"((?:\d{1,3}(?:,\d{3})+|\d+)\s*(?:억\s*)?(?:만\s*)?원)")


@dataclass(frozen=True)
class DerivedLabels:
    document_category: str
    sanction_strength: int
    sanction_types: str
    monetary_amount: int | None
    violated_articles: str
    case_type: str
    factors: str


def derive_labels(text: str, amount_text: str | None = None, title_text: str | None = None) -> DerivedLabels:
    category = classify_document_category(text, title_text=title_text)
    sanction_source = amount_text or text
    sanction_types = derive_sanction_types(sanction_source, category)
    case_types = derive_case_types(text, category)
    amount = None
    if any(item in sanction_types for item in {"과징금", "과태료"}):
        amount = extract_max_money(amount_text or "") or extract_max_money(text)
    articles = sorted(set(match.group(0).replace(" ", "") for match in ARTICLE_RE.finditer(text)))
    return DerivedLabels(
        document_category=category,
        sanction_strength=sanction_strength(sanction_types, amount),
        sanction_types=";".join(sanction_types),
        monetary_amount=amount,
        violated_articles=";".join(articles),
        case_type=";".join(case_types),
        factors=derive_factors(text, sanction_types),
    )


def classify_document_category(text: str, title_text: str | None = None) -> str:
    title = title_text or ""
    title_first = title if title else text[:500]
    if re.search(r"침해요인\s*평가|일부개정안|제정안|의견\s*조회", title_first):
        return "privacy_impact_review"
    if re.search(r"사전적정성\s*검토", title_first):
        return "prior_review"
    if re.search(r"개인정보\s*제공\s*요청|영상정보\s*제공\s*요청|보유\s*개인정보\s*제공|개인정보\s*제공에\s*관한", title_first):
        return "data_provision_request"
    if re.search(r"법규\s*위반행위|시정조치|과징금|과태료|공표명령|고발", title_first):
        return "enforcement"
    if re.search(r"실태점검|집중관리시스템|공공시스템|시행계획", title_first):
        return "public_system_inspection"
    if re.search(r"민원|질의|의견제시|법령해석|유권해석", title_first):
        return "complaint_or_interpretation"
    if re.search(r"법규\s*위반행위|시정조치|과징금|과태료|공표명령|고발", text[:1200]):
        return "enforcement"
    return "other"


def derive_sanction_types(text: str, category: str) -> list[str]:
    if category in {"data_provision_request", "prior_review"}:
        return []
    return [name for name, pattern in SANCTION_PATTERNS.items() if pattern.search(text)]


def derive_case_types(text: str, category: str) -> list[str]:
    if category == "privacy_impact_review":
        return []
    if category == "data_provision_request":
        if re.search(r"영상정보|CCTV|폐쇄회로", text):
            return ["영상정보 처리"]
        return ["목적 외 이용"]
    return [name for name, pattern in CASE_TYPE_PATTERNS.items() if pattern.search(text)]


def sanction_strength(types: list[str], amount: int | None) -> int:
    if amount or "과징금" in types:
        return 4
    if "과태료" in types or "고발" in types:
        return 3
    if "시정명령" in types or "공표명령" in types:
        return 2
    if "개선권고" in types or "주의" in types:
        return 1
    return 0


def extract_max_money(text: str) -> int | None:
    amounts = [parse_money(match.group(1)) for match in MONEY_RE.finditer(text)]
    amounts = [amount for amount in amounts if amount is not None]
    return max(amounts) if amounts else None


def parse_money(value: str) -> int | None:
    compact = value.replace(",", "").replace(" ", "")
    match = re.match(r"(?:(\d+)억)?(?:(\d+)만)?원|(\d+)원", compact)
    if not match:
        return None
    if match.group(3):
        return int(match.group(3))
    total = 0
    if match.group(1):
        total += int(match.group(1)) * 100_000_000
    if match.group(2):
        total += int(match.group(2)) * 10_000
    return total or None


def derive_factors(text: str, sanction_types: list[str]) -> str:
    factors = []
    checks = {
        "정보주체 규모": r"\d+\s*(?:명|건)|대량",
        "민감정보 포함 여부": r"민감정보",
        "고유식별정보 포함 여부": r"고유식별정보|주민등록번호|여권번호|운전면허",
        "반복성": r"반복|재차|수차례",
        "고의 또는 중과실": r"고의|중과실|중대한\s*과실",
        "피해 발생 또는 위험 발생": r"피해|위험|침해",
        "사후 시정 노력": r"시정|개선|재발방지",
        "내부통제 및 안전조치 수준": r"내부통제|안전조치|접근통제|암호화",
        "위반 기간": r"\d+\s*(?:년|개월|일)\s*간",
        "수집·이용 목적 명확성": r"수집·?이용\s*목적|목적",
        "동의 적법성": r"동의",
        "제3자 제공 또는 위탁 구조": r"제3자|위탁|수탁",
        "국외이전 고지·동의 여부": r"국외\s*이전|해외\s*이전",
    }
    for name, pattern in checks.items():
        if re.search(pattern, text):
            factors.append(name)
    if any(item in sanction_types for item in {"과징금", "과태료"}):
        factors.append("금전 제재 여부")
    if any(item in sanction_types for item in {"공표명령", "시정명령"}):
        factors.append("공표 또는 시정명령 여부")
    return ";".join(dict.fromkeys(factors))
