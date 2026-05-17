# PIPC Decision Insight Plan

## Purpose

This project should help Personal Information Protection Commission staff understand the full decision corpus, not just search individual decisions. The analysis should therefore separate different decision genres, preserve citations to decision IDs, and turn 3,990 decisions into reusable operational knowledge.

## Core Questions

1. What kinds of decisions has the Commission produced over time?
2. Which legal provisions, sanctions, and issue types recur most often?
3. How do enforcement cases differ from legislative privacy impact reviews, public-sector data provision requests, inspections, and other decisions?
4. Which factors appear to raise sanction strength or monetary sanctions?
5. Which agencies, sectors, or decision types generate recurring issues?
6. Where is the corpus sparse, noisy, or structurally incomplete?
7. How can the corpus support RAG/CAG workflows for staff-facing research, drafting, and precedent comparison?

## Decision Genre Taxonomy

- `enforcement`: 법규 위반행위, 시정조치, 과징금, 과태료, 공표명령 등 제재 중심 사건
- `privacy_impact_review`: 법령 제·개정안 개인정보 침해요인 평가
- `public_system_inspection`: 공공시스템 또는 집중관리시스템 실태점검 및 후속 조치
- `data_provision_request`: 개인정보 또는 영상정보 제공 요청 안건
- `prior_review`: 사전적정성 검토
- `complaint_or_interpretation`: 민원, 질의, 해석, 의견제시 성격 안건
- `other`: 위 유형에 명확히 들어가지 않는 결정

This genre split is essential because the same word, such as `침해`, means different things in an impact review title and in an enforcement decision.

## Analysis Tracks

### Corpus Map

- decision counts by year, genre, meeting type, and decision type
- missingness and document length by genre
- repeated title templates and how they changed over time

### Enforcement Analysis

- sanction types and combinations
- sanction strength distribution
- monetary amount distribution and top monetary cases
- violated article frequency and article co-occurrence
- issue/factor frequency by sanction strength
- public/private and sector clues where extractable

### Privacy Impact Review Analysis

- requesting ministries and agencies
- laws most frequently reviewed
- recommendation versus original-consent patterns
- recurring personal data categories, sensitive information, unique identifiers, retention, linkage, and delegation issues

### Public Sector And Data Provision Analysis

- public system inspection trends
- agencies and systems repeatedly appearing
- data provision request purposes and requested data types
- video information cases and statutory basis patterns

### Text And Similarity Analysis

- keyword and phrase extraction by genre
- document embeddings at decision and chunk level
- clustering to identify recurring fact patterns
- representative decisions per cluster
- cluster-specific article and sanction profiles

### Regression And Explainability

- ordered sanction strength model for enforcement decisions
- binary monetary sanction model
- monetary amount model for amount-bearing enforcement cases
- coefficient interpretation with legal caution
- residual and outlier review through decision citations

### Staff-Facing Products

- `reports/insights.md`: executive briefing and tables
- `reports/regression.md`: model results and interpretation cautions
- `reports/clusters.md`: cluster inventory and representative decisions
- local RAG index with decision ID and paragraph citations
- `skills/pipc_privacy_law/SKILL.md`: compressed CAG workflow and coding rules

## Immediate Implementation Priorities

1. Add `document_category` to processed decisions.
2. Re-run parsing and EDA.
3. Generate a broader `reports/insights.md` report.
4. Improve case type and factor rules separately for enforcement decisions and impact reviews.
5. Build embedding and clustering over normalized text.
6. Use clusters and enforcement labels to prepare regression input.
