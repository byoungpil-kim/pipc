from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalIssue:
    issue_id: int
    issue: str
    korean_label: str
    pattern: str
    legal_focus: str
    source_note: str


EXTERNAL_ISSUES = [
    ExternalIssue(
        1,
        "Behavioral advertising, consent, and platform control",
        "행태정보·맞춤형 광고·플랫폼 통제",
        r"행태정보|맞춤형\s*광고|온라인\s*광고|광고\s*식별자|쿠키|SDK|퍼블리셔|맞춤형",
        "동의의 명확성, 개인정보처리자 지위, 플랫폼의 실질적 통제, 제3자 제공·국외이전 구조",
        "구글·메타 과징금 소송과 KCI 맞춤형 광고 논문에서 핵심 쟁점으로 확인됨",
    ),
    ExternalIssue(
        2,
        "Mega-leak enforcement and fine proportionality",
        "대규모 유출과 과징금 비례성",
        r"유출|해킹|악성프로그램|침해사고|통지\s*지연|대규모|정보주체\s*수|다크웹",
        "유출 규모, 안전조치 위반 정도, 통지 지연, 과징금 산정과 비례성",
        "SKT 대규모 유출과 역대 최대 과징금 보도에서 확인됨",
    ),
    ExternalIssue(
        3,
        "Causation and adequacy of safety measures",
        "안전조치 충분성·인과관계",
        r"안전조치|접근통제|접속기록|암호화|취약점|패치|관리자\s*계정|인과관계|방화벽",
        "제29조 안전조치의무, 충분한 보호조치 항변, 유출과 위반 사이 인과관계",
        "KT 판결과 서울고법 판결 요지에서 반복 확인됨",
    ),
    ExternalIssue(
        4,
        "Overseas transfer, cloud, and data sovereignty",
        "국외이전·클라우드·데이터 주권",
        r"국외\s*이전|해외\s*이전|클라우드|국외|위탁|보관|제3자\s*제공|국외의",
        "국외이전 요건, 위탁·보관과 제3자 제공 구분, 고지·동의와 적정성·안전조치",
        "KCI 국외이전 논문과 테무 보도에서 확인됨",
    ),
    ExternalIssue(
        5,
        "Automated decisions, AI, and explainability",
        "자동화된 결정·AI·설명가능성",
        r"인공지능|AI|자동화된\s*결정|프로파일링|알고리즘|설명\s*요구|거부권|생성형",
        "자동화된 결정에 대한 거부·설명 요구권, AI 처리 투명성, 차별·편향 위험",
        "법률신문 자동화된 결정 고시와 RISS/KLI 문헌에서 확인됨",
    ),
    ExternalIssue(
        6,
        "Preventive inspection versus ex post sanctions",
        "사전 실태점검과 사후 제재",
        r"사전\s*실태점검|실태점검|집중관리시스템|공공시스템|예방|이행실태|사전적정성",
        "예방 중심 감독, 점검대상 선정, 점검 결과의 개선권고·시정조치 연결",
        "국감 보도와 공공시스템 안전조치 보도에서 확인됨",
    ),
    ExternalIssue(
        7,
        "CCTV and video information boundaries",
        "CCTV·영상정보 경계",
        r"CCTV|영상정보|폐쇄회로|개인영상정보|관제|열람|영상자료|블랙박스",
        "목적 외 이용·제3자 제공, 수사·공공안전 예외, 정보주체 열람권, 설치장소 민감성",
        "CCTV 논문, 보안뉴스 기획, ZDNet 보도에서 확인됨",
    ),
    ExternalIssue(
        8,
        "Children's data and legal representative consent",
        "아동 개인정보·법정대리인 동의",
        r"아동|만\s*14세|법정대리인|미성년|청소년|어린이",
        "만 14세 미만 아동의 개인정보 수집, 법정대리인 동의, 연령확인 설계",
        "식음료·앱 서비스 제재 보도에서 확인됨",
    ),
    ExternalIssue(
        9,
        "Privacy policy evaluation, CPO governance, and accountability",
        "처리방침 평가·CPO·책임성",
        r"처리방침|CPO|개인정보\s*보호책임자|책임자|책임성|관리\s*감독|내부관리계획",
        "처리방침 적정성, CPO 요건, 수탁자 관리감독, 내부관리계획과 책임성",
        "법률신문 CPO 요건, 처리방침 평가 기사와 로펌 업데이트에서 확인됨",
    ),
    ExternalIssue(
        10,
        "Victim remedies, collective dispute resolution, and use of fines",
        "피해구제·분쟁조정·과징금 활용",
        r"피해구제|분쟁조정|손해배상|배상|과징금|피해자|통지|공표",
        "유출 피해자 구제, 집단분쟁조정, 공표명령, 과징금의 피해자 활용 논쟁",
        "SKT 피해구제와 과징금 기금화 보도에서 확인됨",
    ),
    ExternalIssue(
        11,
        "Sector-specific privacy risk waves",
        "섹터별 개인정보 위험 파동",
        r"통신|식음료|의료|병원|모빌리티|자동차|플랫폼|프랜차이즈|공공기관|금융|카드|게임|숙박|호텔|커피|버거",
        "업권별 반복 위반, 조사 파동, 섹터별 체크리스트와 예방감독",
        "통신·식음료·호텔·공공시스템 보도에서 확인됨",
    ),
]


LOCAL_ISSUE_PATTERNS = {
    "동의·고지": r"동의|고지|알림|선택권|거부",
    "목적 외 이용·제공": r"목적\s*외|제3자\s*제공|제삼자\s*제공|제공받을",
    "안전조치": r"안전조치|접근통제|접속기록|암호화|취약점|권한",
    "유출·침해": r"유출|침해|해킹|노출|다크웹",
    "보유기간·파기": r"보유기간|보존기간|파기|삭제",
    "위탁·수탁": r"위탁|수탁|처리위탁|관리\s*감독",
    "국외이전": r"국외\s*이전|해외\s*이전|국외|클라우드",
    "영상정보": r"영상정보|CCTV|폐쇄회로|블랙박스|관제",
    "아동": r"아동|만\s*14세|법정대리인|미성년",
    "민감·고유식별정보": r"민감정보|고유식별정보|주민등록번호|계좌번호",
    "정보주체 권리": r"열람|정정|삭제|처리정지|권리|설명",
    "사전점검·개선권고": r"사전\s*실태점검|개선권고|실태점검|이행실태",
    "처리방침·책임성": r"처리방침|보호책임자|내부관리계획|책임성",
    "금액 제재·공표": r"과징금|과태료|공표|시정명령|고발",
    "AI·자동화": r"인공지능|AI|자동화된\s*결정|알고리즘|프로파일링",
}


def issue_pattern_by_id() -> dict[int, str]:
    return {issue.issue_id: issue.pattern for issue in EXTERNAL_ISSUES}
