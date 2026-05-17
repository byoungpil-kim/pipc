# PIPC Privacy Law Decision Analysis

Use this skill when classifying, analyzing, or answering questions about Personal Information Protection Commission decisions.

## Workflow

1. Identify the decision ID, decision date, title, order, reasons, summary, and cited articles.
2. Classify the case type using the taxonomy below.
3. Extract factors that affected violation findings or sanction strength.
4. Code sanction strength from the order and decision type.
5. Cite decision IDs, specific text spans, and legal articles for every substantive claim.
6. Separate observations supported by decisions from general legal interpretation.

## Case Type Taxonomy

- 유출·침해
- 동의·고지 위반
- 목적 외 이용
- 제3자 제공
- 국외이전
- 안전조치 미흡
- 보유기간·파기 위반
- 영상정보 처리
- 아동 개인정보
- 민감정보·고유식별정보
- 접근권한·내부통제
- 처리위탁
- 정보주체 권리보장

## Factor Taxonomy

- 정보주체 규모
- 민감정보 포함 여부
- 고유식별정보 포함 여부
- 반복성
- 고의 또는 중과실
- 피해 발생 또는 위험 발생
- 사후 시정 노력
- 내부통제 및 안전조치 수준
- 위반 기간
- 수집·이용 목적 명확성
- 동의 적법성
- 제3자 제공 또는 위탁 구조
- 국외이전 고지·동의 여부
- 금전 제재 여부
- 공표 또는 시정명령 여부

## Sanction Strength Coding

- `0`: no sanction detected, dismissal, closure, or purely procedural decision
- `1`: warning, recommendation, improvement recommendation
- `2`: corrective order, publication order, deletion or suspension order
- `3`: administrative fine, criminal referral, or similarly coercive non-surcharge sanction
- `4`: penalty surcharge or substantial monetary sanction

When multiple sanctions appear, code the highest level and retain all sanction types.

## Citation Rules

- Cite PIPC decision IDs for every decision-based statement.
- Cite legal provisions in normalized form such as `제15조`, `제17조`, `제29조`, or `제39조의15`.
- For RAG answers, include both retrieved decision IDs and article citations.
- Do not present unsupported generalizations as if they came from the corpus.

## RAG Answer Rules

- Start from retrieved decision text, then synthesize.
- State common factors only when they appear across cited decisions.
- If evidence is thin, say which part is uncertain.
- Prefer concise Korean legal analysis with citations in parentheses.

## Regression Interpretation Notes

- Treat coefficients as association, not causal proof.
- Check whether sanction labels were rule-derived before interpreting model outputs.
- Inspect representative cases when a coefficient direction conflicts with legal expectations.
- Monetary amount models can be skewed by a small number of large sanctions.

## New Decision Classification Procedure

1. Read the title, order, reasons, and summary.
2. Extract sanctions and code sanction strength.
3. Extract cited articles and normalize article notation.
4. Match case type keywords, then confirm against reasoning text.
5. Mark factors only when supported by text.
6. Return a compact record with decision ID, case type, factors, sanction code, sanctions, amount, and citations.
