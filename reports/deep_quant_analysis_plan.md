# PIPC 결정문 심층 계량분석 계획서

## 1. 분석 전환의 목적

기존 산출물은 3,990건 결정문의 전체 구조, 주요 쟁점, 유형별 토픽 지도를 보여주는 1차 지형도다. 다음 단계는 계산사회과학 관점에서 결정문 텍스트를 계량화하고, 주요 쟁점과 결정문 유형별로 검증 가능한 가설을 세워 통계모형으로 검토하는 것이다.

직원용 성과물의 목표는 단순 빈도표가 아니라 다음 질문에 답하는 것이다.

- 어떤 쟁점이 언제, 어떤 유형의 사건에서 증가하거나 감소했는가?
- 어떤 사실관계·법리·절차 factor가 제재 강도, 금액 제재, 권고 여부, 제공 허용 여부와 연결되는가?
- 동일한 법적 쟁점이라도 공공/민간, 업권, 신청기관, 시기별로 판단 패턴이 달라지는가?
- 감독·제도개선 관점에서 어떤 factor가 예방 우선순위로 볼 수 있는가?

## 2. 공통 데이터셋 설계

### 2.1 분석 단위

- 기본 단위: 결정문 1건.
- 보조 단위: 결정문-쟁점 매칭 1건, 결정문-유형 sub cluster 1건, 결정문-조문 1건.
- 텍스트 필드: `title`, `order_text`, `reason_text`, `summary_text`, `appendix_text`.
- 기본 메타데이터: `decision_id`, `decision_date`, `document_category`, `meeting_type`, `decision_type`, `applicant`.
- 기존 라벨: `sanction_strength`, `sanction_types`, `monetary_amount`, `violated_articles`, `case_type`, `factors`.

### 2.2 파생 변수

- 시간: `year`, `post_2020`, `post_2022`, `period`(2012-2017, 2018-2021, 2022-2026).
- 제재 결과: 금액 제재 여부, 과징금 여부, 과태료 여부, 시정명령 여부, 공표명령 여부, 개선권고 여부, 고발 여부, 금액 로그값.
- 권고/허용 결과: 침해요인 평가 권고 여부, 제공 요청 허용/불허/조건부 여부.
- 텍스트 신호: 쟁점 regex, 조문 언급, factor dictionary, TF-IDF keyword, sub topic cluster, 문서 길이, 이유/주문 비율.
- 주체 신호: 공공/민간 추정, 신청기관/피심인 표준화, 업권 keyword.

### 2.3 공통 방법론

- 기술통계: 연도별 빈도, 유형별 비중, 조문·factor 동시출현, 금액 분포.
- 차이 검정: 카이제곱 검정, Fisher exact test, t-test/Mann-Whitney, Kruskal-Wallis.
- 회귀모형:
  - 이진 결과: logistic regression.
  - 다범주 결과: multinomial logistic regression.
  - 순서형 제재 강도: ordered logit 대체로 ordinal encoding + robust logistic/linear 비교.
  - 건수 결과: Poisson/negative binomial regression.
  - 금액 결과: log monetary amount OLS/Huber regression.
- 설명력 평가: pseudo R2, adjusted R2, permutation importance, bootstrap confidence interval.
- 시간 변화: 연도 fixed effect, period interaction, rolling share, joinpoint 후보 탐색.
- 텍스트 모델: TF-IDF, dictionary factor score, OpenRouter 기반 sub topic, UMAP/HDBSCAN cluster label.
- 검수: 대표 결정문 citation, 고영향 outlier 표본, residual review.

## 3. 주요 쟁점별 분석 계획

각 쟁점 리포트는 `현황 가설`, `원인 가설`, `해결책 가설`을 세우고, 정량 결과와 대표 결정문을 함께 제시한다.

### Issue 01. 행태정보·맞춤형 광고·플랫폼 통제

- 현황 가설: 맞춤형 광고 사건은 전체 결정문에서는 적지만, 매칭 사건은 고액 제재와 복수 위반 조문에 집중된다.
- 원인 가설: 단순 동의 문구보다 제3자 제공, 국외이전, 처리자 지위, 플랫폼 통제 신호가 결합될수록 제재 강도가 높다.
- 해결책 가설: 명시적 동의와 데이터 흐름 공개 factor가 있으면 공표명령·고액 과징금 위험이 낮아진다.
- 검정: 쟁점 매칭 여부를 독립변수로 한 고액 제재 logistic, log 금액 OLS, 동의/국외이전/제3자 제공 interaction, 대표 사건 residual review.

### Issue 02. 대규모 유출과 과징금 비례성

- 현황 가설: 유출 사건은 제재 사건의 핵심 축이며 2022년 이후 금액 제재 비중이 상승했다.
- 원인 가설: 정보주체 규모, 안전조치 미흡, 통지·신고, 반복성, 사후 시정 노력이 제재 강도와 금액을 설명한다.
- 해결책 가설: 통지·신고와 재발방지 조치가 빠르게 확인되는 사건은 동일 유출 신호에서도 공표·고발 가능성이 낮다.
- 검정: sanction_strength ordinal/linear model, log 금액 회귀, period interaction, 유출+안전조치 동시출현 효과.

### Issue 03. 안전조치 충분성·인과관계

- 현황 가설: 안전조치 쟁점은 단독으로보다 유출·접근권한·접속기록·암호화와 결합해 나타난다.
- 원인 가설: 접근권한, 접속기록, 암호화, 취약점 패치 신호는 서로 다른 제재 결과와 연결된다.
- 해결책 가설: 내부통제·접속기록 점검 factor가 명확할수록 고발보다 시정명령 중심으로 수렴한다.
- 검정: 안전조치 세부 dictionary factor의 coefficient 비교, 조문쌍 네트워크, 공공/민간 interaction.

### Issue 04. 국외이전·클라우드·데이터 주권

- 현황 가설: 국외이전 쟁점은 제재 사건뿐 아니라 침해요인 평가와 해석 사건에도 넓게 분포한다.
- 원인 가설: 국외이전 사건의 법적 쟁점은 이전 자체보다 위탁/보관/제3자 제공 구분과 고지·동의 신호에 의해 갈린다.
- 해결책 가설: 국외이전 고지·동의와 수탁자 관리감독 factor가 명확하면 제재 강도가 낮다.
- 검정: 유형별 매칭률 비교, 국외이전 x 위탁 interaction, 침해요인 평가 권고 여부 logistic.

### Issue 05. 자동화된 결정·AI·설명가능성

- 현황 가설: 현재 결정문에서는 직접 AI 신호가 희소하지만, 정책·해석·침해요인 평가에서 선행 신호가 나타난다.
- 원인 가설: AI 직접 언급보다 자동화, 프로파일링, 설명 요구, 거부권 신호가 향후 분화될 가능성이 높다.
- 해결책 가설: 현행 corpus에서는 감독 우선순위보다 taxonomy 구축과 신규 결정문 모니터링이 더 중요하다.
- 검정: 희소 event 분석, keyword-in-context, 유사 토픽 검색, zero-inflated count 모델 후보.

### Issue 06. 사전 실태점검과 사후 제재

- 현황 가설: 사전 실태점검은 2023년 이후 공공시스템 장르와 함께 급증한다.
- 원인 가설: 집중관리시스템, 공공기관, 접근권한·접속기록 factor가 실태점검과 제재를 연결한다.
- 해결책 가설: 실태점검 후 개선권고가 반복되는 sub 유형은 사후 제재보다 예방 체크리스트가 효과적이다.
- 검정: 공공시스템 cluster별 factor prevalence, 개선권고 여부 logistic, 전후 period trend.

### Issue 07. CCTV·영상정보 경계

- 현황 가설: 영상정보 쟁점은 제공 요청·해석 사건에서 가장 뚜렷하고, 제재 사건에서는 안전조치와 결합된다.
- 원인 가설: 수사·소방·교통·방범 목적, 정보주체 열람, 목적 외 제공 신호가 허용/불허 판단을 좌우한다.
- 해결책 가설: 요청 목적과 법정 업무 근거가 명확한 제공 요청은 허용 가능성이 높다.
- 검정: 제공 요청 결과 multinomial/logistic, 요청기관 fixed effect, 영상정보 x 목적외 제공 interaction.

### Issue 08. 아동 개인정보·법정대리인 동의

- 현황 가설: 사건 수는 적지만 식음료·앱·서비스 분야에서 사회적 민감도가 높은 고신호 사건으로 나타난다.
- 원인 가설: 법정대리인 동의, 연령확인, 고유식별정보, 마케팅 동의가 결합될 때 제재 가능성이 커진다.
- 해결책 가설: 연령확인 설계와 동의 분리 factor는 제재 강도를 낮추는 방향으로 작동한다.
- 검정: exact test, 희소 logistic, 사례군 대조표본 matching.

### Issue 09. 처리방침 평가·CPO·책임성

- 현황 가설: 책임성 쟁점은 단독 위반보다 안전조치·위탁관리·내부관리계획 위반의 기반 factor로 나타난다.
- 원인 가설: CPO, 처리방침, 내부관리계획, 수탁자 관리감독 신호는 공표명령 및 개선권고와 연결된다.
- 해결책 가설: 책임성 factor가 명확히 개선된 사건은 금액보다 시정명령·개선권고 중심으로 귀결된다.
- 검정: factor bundle regression, 공표명령 logistic, mediation-like decomposition(안전조치와 책임성 동시투입).

### Issue 10. 피해구제·분쟁조정·과징금 활용

- 현황 가설: 결정문은 피해자 배상보다 행정제재, 공표, 통지, 재발방지 중심으로 구성된다.
- 원인 가설: 피해자 규모와 통지·공표 신호가 과징금 규모와 공표명령을 설명한다.
- 해결책 가설: 피해구제 언급이 강한 사건은 공표·통지 명령이 동반될 가능성이 높다.
- 검정: 공표명령 logistic, log 금액 회귀, 피해자/통지 dictionary score, 유출 사건 내부 subset 분석.

### Issue 11. 업권별 반복 유출·위반 리스크

- 현황 가설: 통신, 공공, 식음료, 숙박, 의료 등 업권별 반복 패턴이 서로 다른 factor 조합을 가진다.
- 원인 가설: 업권별로 유출 원인과 제재 패키지가 다르며, 통신은 대규모·고액, 공공은 시스템·접근권한, 식음료는 동의·아동 신호가 강하다.
- 해결책 가설: 업권별 체크리스트를 분리하면 일반 checklist보다 예방감독 우선순위가 선명해진다.
- 검정: sector keyword classification, 업권 x factor interaction, cluster별 recurring risk profile.

## 4. 결정문 유형별 분석 계획

각 유형 리포트는 내부 sub 유형을 10개 내외로 정리하고, sub 유형별 중요 factor와 outcome을 모델링한다. OpenRouter 기반 기존 topic map을 출발점으로 하되, 통계 분석에서는 표본 수가 작은 cluster를 병합한다.

### Type A. 법규 위반·제재

- 대상: `document_category = enforcement`, 약 912건.
- 권장 sub 유형:
  1. 대규모 유출·해킹
  2. 안전조치·접근통제 미흡
  3. 동의·고지 위반
  4. 목적 외 이용·제3자 제공
  5. 위탁·수탁 관리감독
  6. 보유기간·파기 위반
  7. 민감정보·고유식별정보
  8. 영상정보 처리
  9. 공공시스템·공공기관 제재
  10. 복합 위반·고액 제재
- 주요 outcome: `sanction_strength`, 금액 제재 여부, log 금액, 공표명령 여부, 고발 여부.
- factor: 정보주체 규모, 민감/고유식별정보, 반복성, 고의·중과실, 피해 위험, 사후 시정, 내부통제, 위반기간, 동의 적법성, 제3자 제공/위탁, 국외이전.
- 모형: ordered/linear sanction model, logistic monetary model, log amount OLS/Huber, sub 유형 fixed effect, year fixed effect.
- 핵심 산출: factor 가중치표, 고액 사건 예측 residual, 시기별 factor 변화, 공공/민간 차이.

### Type B. 침해요인 평가

- 대상: `privacy_impact_review`, 약 2,419건.
- 권장 sub 유형:
  1. 보건의료 법령
  2. 고용·노동 법령
  3. 교육·아동·청소년 법령
  4. 소방·재난안전 법령
  5. 농림축산식품 법령
  6. 문화·체육·관광 법령
  7. 복지·사회보장 법령
  8. 행정·인허가·자격 법령
  9. 정보연계·시스템 구축
  10. 고유식별·민감정보 처리
- 주요 outcome: 권고성 주문 여부, 개인정보 항목 최소화 신호, 보유기간·파기 신호, 위탁/연계 신호.
- factor: 수집항목, 민감정보, 고유식별정보, 보유기간, 목적 명확성, 제3자 제공, 위탁, 정보시스템 연계, 법령명/부처.
- 모형: 권고 여부 logistic, 부처/분야 fixed effect, period trend, factor importance.
- 핵심 산출: 어떤 법령 분야에서 어떤 개인정보 설계 쟁점이 반복되는지.

### Type C. 공공시스템·실태점검

- 대상: `public_system_inspection`, 약 111건.
- 권장 sub 유형:
  1. 집중관리시스템 점검
  2. 공공시스템 운영기관 시정조치
  3. 접근권한 관리
  4. 접속기록 점검
  5. 개인정보취급자 관리
  6. 내부관리계획
  7. 개선권고 이행
  8. 부처·지자체 시스템
  9. 산하기관·공공기관 시스템
  10. 반복 점검 대상
- 주요 outcome: 개선권고 여부, 시정조치 여부, 공표/제재 연결 여부.
- factor: 접근권한, 접속기록, 시스템 규모, 공공기관 유형, 점검연도, 반복성, 이행결과 제출.
- 모형: 개선권고 logistic, cluster별 factor prevalence, 기관군별 차이 검정.
- 핵심 산출: 예방감독 checklist와 고위험 공공시스템 factor.

### Type D. 개인정보 제공 요청

- 대상: `data_provision_request`, 약 127건.
- 권장 sub 유형:
  1. 수사·감사 목적 제공
  2. 소방·재난·안전 목적 제공
  3. 복지·지원 대상자 발굴
  4. 조세·징수·환수
  5. 보훈·연금·보험
  6. 교통·자동차·주차
  7. CCTV·영상정보 제공
  8. 통계·연구 목적
  9. 외국인·출입국·병역
  10. 조건부·범위 제한 제공
- 주요 outcome: 허용, 불허/제한, 조건부 허용.
- factor: 요청기관, 제공기관, 목적 외 이용, 법정 업무 근거, 영상정보, 민감/고유식별정보, 필요한 범위.
- 모형: multinomial/logistic outcome model, 요청기관군 fixed effect, 영상정보 interaction.
- 핵심 산출: 제공 요청 판단에서 허용 가능성을 높이는 요건과 불허 요건.

### Type E. 민원·해석·사전검토·기타

- 대상: `complaint_or_interpretation`, `prior_review`, `other`, 약 421건.
- 권장 sub 유형:
  1. 목적 외 이용·제공 해석
  2. 영상정보 설치·제공 질의
  3. 정보주체 권리 민원
  4. 공공기관 개인정보 처리 질의
  5. 사전적정성 검토
  6. 정책·제도 보고
  7. 법령해석 일반
  8. 개인정보 처리방침·책임성
  9. 연구·통계 목적 처리
  10. 기타 저신호/재분류 후보
- 주요 outcome: 허용/불허 해석, 권고/의견제시 여부, 재분류 필요 여부.
- factor: 목적 외 이용, 영상정보, 고유식별정보, 공공기관, 정보주체 권리, 연구·통계, 법령근거.
- 모형: sub 유형 classification, rule+topic label validation, low-n descriptive model.
- 핵심 산출: RAG에서 유사 제재가 아니라 판단 기준 검색에 써야 할 해석형 지식 구조.

## 5. 실행 순서

### Phase 1. 분석 데이터마트 구축

- `reports/tables/deep/decision_features.csv`
- `reports/tables/deep/issue_panel.csv`
- `reports/tables/deep/type_subtype_panel.csv`
- 텍스트 dictionary score와 기존 topic cluster 병합.

### Phase 2. 쟁점별 계량분석

1. Issue 02 대규모 유출과 과징금 비례성
2. Issue 03 안전조치 충분성·인과관계
3. Issue 01 행태정보·맞춤형 광고·플랫폼 통제
4. Issue 04 국외이전·클라우드·데이터 주권
5. Issue 07 CCTV·영상정보 경계
6. Issue 06 사전 실태점검과 사후 제재
7. Issue 09 처리방침·CPO·책임성
8. Issue 10 피해구제·분쟁조정·과징금 활용
9. Issue 11 업권별 반복 유출·위반 리스크
10. Issue 08 아동 개인정보·법정대리인 동의
11. Issue 05 자동화된 결정·AI·설명가능성

우선순위는 표본 수, 정책 중요도, 제재 결과와의 연결 가능성을 기준으로 정했다.

### Phase 3. 유형별 계량분석

1. 법규 위반·제재: factor 가중치와 제재 강도.
2. 침해요인 평가: 권고 여부와 법령 분야별 반복 쟁점.
3. 개인정보 제공 요청: 허용/불허 판단 factor.
4. 공공시스템·실태점검: 예방감독 checklist.
5. 민원·해석·기타: 해석형 지식 분류와 재라벨링.

### Phase 4. 리포트 통합

- 각 주요 쟁점 HTML에 가설, 모형, 계수/효과크기, 대표 결정문 residual 검토를 추가.
- 각 유형별 Full Report에 sub 유형별 factor weight, 시계열 변화, 주체별 차이를 추가.
- 직원용 요약: “감독 우선순위”, “반복 리스크”, “결정문 검색·비교에 바로 쓸 수 있는 factor checklist”.

## 6. 해석상 주의

- 결정문 텍스트는 행정문서이며, 원자료가 사건 전체 사실관계를 완전히 대표하지 않을 수 있다.
- 자동 라벨과 regex는 측정오차가 있으므로 계수는 법적 인과효과가 아니라 문서상 판단 구조의 통계적 신호로 해석한다.
- 희소 쟁점은 회귀보다 exact test, 표본검수, 대표 결정문 정성분석과 결합한다.
- OpenRouter 라벨은 sub 유형 명명에 쓰고, 통계 검정의 핵심 변수는 재현 가능한 dictionary/factor로 별도 저장한다.
