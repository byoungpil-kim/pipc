# PIPC 결정문 수집·분석·RAG/CAG 개발 계획

## Summary

- 실제 구현과 실행은 IP 접속이 허용된 Linux 서버에서 Codex로 진행한다.
- Linux 서버의 작업 위치는 `~/pipc`로 둔다.
- `.env` 파일은 `~/pipc/.env`에 두며, 국가법령정보 API 인증값을 `OC=...` 형식으로 저장한다.
- API 호출은 국가법령정보 공동활용에 Linux 서버의 IP 또는 도메인이 등록된 뒤 수행한다.
- 대상 데이터는 개인정보보호위원회 결정문이며, API 대상값은 `target=ppc`이다.
- 1차 마일스톤은 전체 결정문 다운로드와 탐색적 분석 리포트 생성이다.
- 이후 임베딩·클러스터링, 사건 유형별 factor 추출, 제재 강도 회귀, 개인정보 보호법 RAG, CAG 방식 `SKILL.md` 생성을 순차 진행한다.

## Linux 서버 이전 후 초기 작업


   ```bash
   cd ~/pipc
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   ```

 이후 Codex를 `~/pipc`에서 실행하고, 이 계획에 따라 구현을 시작한다.

## Project Structure

Linux 서버에서 다음 구조를 만든다.

```text
~/pipc/
  .env
  plan.md
  pyproject.toml
  README.md
  src/
    pipc/
      __init__.py
      cli.py
      config.py
      api.py
      parse.py
      labels.py
      collect.py
      eda.py
      embeddings.py
      clustering.py
      regression.py
      rag.py
  data/
    raw/
      list_pages/
      decisions/
    processed/
  notebooks/
  reports/
  models/
  skills/
    pipc_privacy_law/
      SKILL.md
```

## API Collection

- 목록 API:

  ```text
  https://www.law.go.kr/DRF/lawSearch.do?target=ppc&type=XML&display=100&page={page}&sort=ddes
  ```

- 본문 API:

  ```text
  https://www.law.go.kr/DRF/lawService.do?target=ppc&type=XML&ID={decision_id}
  ```

- 공통 파라미터:
  - `OC`: `.env`에서 읽는다.
  - `target=ppc`
  - `type=XML`

- 수집 원칙:
  - 원본 XML은 `data/raw`에 수정 없이 보존한다.
  - 목록 XML은 `data/raw/list_pages/page_{page}.xml`에 저장한다.
  - 본문 XML은 `data/raw/decisions/{decision_id}.xml`에 저장한다.
  - 파싱 결과는 `data/processed`에 CSV와 Parquet로 저장한다.
  - 재실행 시 이미 받은 원본 XML은 기본적으로 건너뛰되, `--force` 옵션으로 재다운로드할 수 있게 한다.
  - API 오류 응답은 원본과 별도로 로그에 남기고, 실패 ID는 재시도 목록으로 저장한다.

## Standard Schema

목록 데이터 필드:

- `decision_id`
- `title`
- `agenda_no`
- `meeting_type`
- `decision_type`
- `decision_date`
- `detail_url`

본문 데이터 필드:

- `decision_id`
- `agency`
- `title`
- `agenda_no`
- `meeting_type`
- `decision_type`
- `decision_date`
- `applicant`
- `order_text`
- `reason_text`
- `background_text`
- `summary_text`
- `main_text`
- `objection_text`
- `signature_text`
- `appendix_text`
- `raw_xml_path`

분석 파생 필드:

- `sanction_strength`
- `sanction_types`
- `monetary_amount`
- `violated_articles`
- `case_type`
- `factors`
- `document_length`
- `order_length`
- `reason_length`

## Exploratory Analysis

1차 EDA에서 반드시 산출할 항목:

- 전체 결정문 수, 수집 성공 수, 수집 실패 수
- 연도별 결정문 건수
- 회의종류별 건수
- 결정구분별 건수
- 필드별 결측률
- 중복 `decision_id` 점검
- 제목·주문·이유·결정요지 문서 길이 분포
- 주문·이유·결정요지 기반 주요 키워드
- 개인정보 보호법 조문 언급 빈도
- 과징금, 과태료, 시정명령, 공표명령, 개선권고 등 제재 유형 빈도
- 금액 추출 가능 사건 수와 금액 분포

EDA 산출물:

- `reports/eda.md`
- `reports/tables/*.csv`
- 필요 시 `reports/figures/*.png`

## Case Types And Factors

초기 사건 유형 taxonomy:

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

초기 factor taxonomy:

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

## Embedding And Clustering

- 로컬 Korean/SBERT 계열 임베딩 모델을 우선 사용한다.
- OpenAI API는 비교 실험 또는 품질 보완 옵션으로만 둔다.
- 문서 단위 임베딩과 청크 단위 임베딩을 모두 생성한다.
- 임베딩 결과는 `models/embeddings` 또는 `data/processed/embeddings`에 저장한다.
- 클러스터링은 다음 조합을 비교한다.
  - PCA 또는 UMAP 차원축소
  - KMeans
  - HDBSCAN
- 클러스터별 산출물:
  - 대표 결정문
  - 대표 키워드
  - 주요 조문
  - 주요 제재 유형
  - 사건 유형 후보명

## Regression

- 1차 종속변수는 `sanction_strength`로 둔다.
- `sanction_strength`는 주문과 결정구분에서 추출한 제재 수준을 순서형 값으로 코딩한다.
- 초기 독립변수:
  - 사건 유형
  - factor taxonomy
  - 개인정보 보호법 조문
  - 결정 연도
  - 회의종류
  - 문서 길이
  - 금액 제재 여부
- 기본 모델:
  - 순서형 제재 강도: ordered logit 또는 ordinal regression
  - 이진 제재 여부: logistic regression
  - 금전 제재 금액: OLS 또는 GLM
- 산출물:
  - `reports/regression.md`
  - 회귀 입력 데이터셋
  - 계수표
  - 해석상 주의사항

## RAG Model

RAG 코퍼스:

- 개인정보보호위원회 결정문 청크
- 개인정보 보호법 조문
- 개인정보 보호법 시행령 조문
- 사건 유형 taxonomy
- factor taxonomy

검색:

- 기본은 로컬 벡터 인덱스다.
- FAISS 또는 Chroma 중 Linux 서버 설치와 운영이 단순한 쪽을 선택한다.
- 모든 응답에는 근거 결정문 ID, 조문, 문단 citation을 포함한다.

초기 질의 예:

- 안전조치의무 위반 사건에서 제재 강도를 높이는 요소는 무엇인가?
- 과징금이 부과된 개인정보 유출 사건의 공통 factor는 무엇인가?
- 동의 없는 제3자 제공 사건의 주요 판단 기준은 무엇인가?
- 국외이전 관련 결정례에서 반복적으로 등장하는 쟁점은 무엇인가?

## CAG Skill

생성 위치:

```text
~/pipc/skills/pipc_privacy_law/SKILL.md
```

`SKILL.md`에는 다음 내용을 포함한다.

- 개인정보보호위원회 결정문 분석 workflow
- 사건 유형 taxonomy
- factor taxonomy
- 제재 강도 코딩 기준
- 조문·결정문 citation 규칙
- RAG 답변 작성 규칙
- 회귀 분석 시 해석 주의사항
- 새 결정문을 분류하고 factor를 추출하는 절차

목적:

- 반복 분석 시 매번 전체 코퍼스를 다시 읽지 않고 압축된 도메인 지식과 절차를 사용한다.
- Codex가 결정문 분석, factor 추출, RAG 답변 생성에서 일관된 기준을 따르도록 한다.

## Test Plan

API 인증 테스트:

- `.env`의 `OC`로 목록 1페이지 호출이 성공해야 한다.
- 목록에서 얻은 `decision_id` 1건으로 본문 호출이 성공해야 한다.
- API 응답이 `<Response><result>사용자 정보 검증에 실패...</result>` 형태이면 IP/도메인 등록 문제로 판단한다.

수집 테스트:

- 목록 API의 `totalCnt`와 실제 수집한 목록 행 수가 일치해야 한다.
- 본문 XML 수집 성공 건수와 실패 건수를 기록해야 한다.
- 실패 ID는 재시도 가능해야 한다.

파싱 테스트:

- 목록 XML의 개인정보보호위원회 필드가 표준 스키마로 매핑되어야 한다.
- 본문 XML의 `주문`, `이유`, `배경`, `주요내용`, `결정요지`가 누락 없이 추출되어야 한다.
- 날짜는 가능한 경우 ISO 형식 `YYYY-MM-DD`로 정규화한다.

EDA 검증:

- 결측률, 중복률, 연도별 건수, 제재 유형 추출 결과가 `reports/eda.md`에 포함되어야 한다.
- 금액 추출 정규식 결과는 샘플 검토가 가능해야 한다.

모델 검증:

- 클러스터 대표문서가 해당 클러스터 주제를 대표하는지 수작업으로 검토한다.
- factor 라벨 샘플을 수작업 검토한다.
- 회귀 계수 방향성이 법적·상식적 해석과 크게 충돌하지 않는지 sanity check를 수행한다.

RAG 검증:

- 질의 20개 내외의 golden set을 만든다.
- 응답에 근거 결정문 ID와 조문 citation이 포함되는지 확인한다.
- 근거 없는 일반론 답변은 실패로 처리한다.

Skill 검증:

- `SKILL.md`만 참조해도 같은 기준으로 새 결정문의 사건 유형과 factor를 분류할 수 있어야 한다.

## Implementation Order For Codex On Linux

1. `~/pipc`에서 이 `plan.md`를 읽고 프로젝트 구조를 생성한다.
2. `pyproject.toml`과 기본 패키지 구조를 만든다.
3. `.env` 로더와 API 클라이언트를 구현한다.
4. 목록 1페이지와 본문 1건으로 인증·파싱 smoke test를 수행한다.
5. 전체 목록 수집기를 구현한다.
6. 전체 본문 수집기를 구현한다.
7. 표준 스키마 파서를 구현한다.
8. EDA 리포트 생성기를 구현한다.
9. 1차 마일스톤인 `reports/eda.md`를 생성한다.
10. 임베딩·클러스터링 모듈을 구현한다.
11. factor 추출과 제재 강도 코딩을 구현한다.
12. regression 리포트를 생성한다.
13. RAG 인덱스와 질의 CLI를 구현한다.
14. `skills/pipc_privacy_law/SKILL.md`를 생성한다.

## Assumptions

- Linux 서버에서 국가법령정보 공동활용 API 접속 IP 또는 도메인 등록이 완료된다.
- `.env`는 `~/pipc/.env`에 있으며 `OC=...` 형식을 사용한다.
- 초기 회귀 종속변수는 제재 강도이다.
- 임베딩과 RAG는 로컬 모델을 우선 사용한다.
- 원본 XML은 수정하지 않고 재현 가능한 원천 데이터로 보존한다.
- Windows 작업폴더에서는 우선 이 `plan.md`만 이전용 산출물로 관리한다.
