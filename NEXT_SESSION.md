# Next Session Handoff

## Completed Milestones

The first collection/EDA milestone from `plan.md` is complete, and the project has been reframed for staff-facing insight generation.

- Created the Python package structure under `src/pipc`.
- Implemented `.env` loading, Law Open API client, raw XML collection, XML parsing, preliminary label extraction, CLI commands, and EDA generation.
- Created the CAG draft at `skills/pipc_privacy_law/SKILL.md`.
- Created and installed a local virtual environment at `.venv`.
- Downloaded all PIPC list pages and decision XML files.
- Parsed all collected XML into CSV and Parquet.
- Generated the first EDA report and summary tables.
- Added a staff-facing analysis roadmap at `reports/analysis_plan.md`.
- Added `document_category` genre classification to processed decisions.
- Added a broader insight report generator at `src/pipc/insights.py`.
- Generated `reports/insights.md` and additional tables for multi-angle analysis.
- Performed sample label review using `reports/tables/review_samples.csv`.
- Fixed label issues found in review:
  - data provision requests mentioning fines as a purpose are no longer treated as sanctions;
  - law-violation titles are prioritized as enforcement over inspection context;
  - privacy impact reviews do not receive breach case-type labels.
- Added mobile-friendly HTML section reports at `reports/html/`.
- Added detailed section-by-section full reports at `reports/full_html/`.
- Added full-report support tables under `reports/tables/full/`.
- Added external issue scan from Law Times, academic sources, and Korean news:
  - `reports/external_issue_scan.md`
  - `reports/tables/external_issue_candidates.csv`
  - `reports/tables/external_issue_sources.csv`
  - `reports/tables/external_issue_match_counts.csv`
- Added global/local issue taxonomy in `src/pipc/issue_taxonomy.py`.
- Implemented decision clustering in `src/pipc/clustering.py` and generated 18 clusters.
- Implemented cluster-by-cluster full HTML reports in `src/pipc/cluster_reports.py`.
- Implemented a separate 11-issue global issue report in `src/pipc/global_issue_report.py`.

## Current Data Status

- List pages: `data/raw/list_pages/page_1.xml` through `page_40.xml`
- List rows parsed: 3,990
- Unique list decision IDs: 3,990
- Raw decision XML files: 3,990
- Decision rows parsed: 3,990
- Unique parsed decision IDs: 3,990
- Duplicate parsed decision IDs: 0
- Collection failures: 0
- Document categories:
  - `privacy_impact_review`: 2,421
  - `enforcement`: 882
  - `public_system_inspection`: 186
  - `data_provision_request`: 115
  - `complaint_or_interpretation`: 150
  - `prior_review`: 8
  - `other`: 228

## Main Outputs

- `data/processed/list.csv`
- `data/processed/list.parquet`
- `data/processed/decisions.csv`
- `data/processed/decisions.parquet`
- `data/processed/failed_decisions.csv`
- `reports/eda.md`
- `reports/analysis_plan.md`
- `reports/insights.md`
- `reports/tables/year_counts.csv`
- `reports/tables/meeting_type_counts.csv`
- `reports/tables/decision_type_counts.csv`
- `reports/tables/missing_rates.csv`
- `reports/tables/sanction_type_counts.csv`
- `reports/tables/article_counts.csv`
- `reports/tables/keyword_counts.csv`
- `reports/tables/document_category_counts.csv`
- `reports/tables/year_category_counts.csv`
- `reports/tables/category_missing_rates.csv`
- `reports/tables/category_length_summary.csv`
- `reports/tables/enforcement_sanction_strength.csv`
- `reports/tables/enforcement_sanction_types.csv`
- `reports/tables/enforcement_articles.csv`
- `reports/tables/enforcement_case_types.csv`
- `reports/tables/factor_counts.csv`
- `reports/tables/monetary_amount_by_year.csv`
- `reports/tables/top_monetary_cases.csv`
- `reports/tables/impact_review_applicants.csv`
- `reports/tables/impact_review_recommendation_by_year.csv`
- `reports/tables/data_request_applicants.csv`
- `reports/tables/public_system_applicants.csv`
- `reports/tables/article_by_category.csv`
- `reports/tables/title_templates.csv`
- `reports/tables/citation_index.csv`
- `reports/tables/review_samples.csv`
- `reports/tables/label_review_findings.csv`
- `reports/html/index.html`
- `reports/html/overview.html`
- `reports/html/enforcement.html`
- `reports/html/privacy_impact.html`
- `reports/html/public_system.html`
- `reports/html/data_provision.html`
- `reports/html/interpretation_other.html`
- `reports/html/data_quality.html`
- `reports/html/style.css`
- `reports/full_html/index.html`
- `reports/full_html/overview.html`
- `reports/full_html/enforcement.html`
- `reports/full_html/privacy_impact.html`
- `reports/full_html/public_system.html`
- `reports/full_html/data_provision.html`
- `reports/full_html/interpretation_other.html`
- `reports/full_html/data_quality.html`
- `reports/full_html/style.css`
- `reports/tables/full/category_period_counts.csv`
- `reports/tables/full/enforcement_package_counts.csv`
- `reports/tables/full/enforcement_article_pairs.csv`
- `reports/tables/full/enforcement_money_bands.csv`
- `reports/tables/full/impact_review_issue_terms.csv`
- `reports/tables/full/impact_review_laws.csv`
- `reports/tables/full/data_provision_outcomes.csv`
- `reports/tables/full/data_provision_issue_terms.csv`
- `reports/tables/full/public_system_title_families.csv`
- `reports/external_issue_scan.md`
- `reports/tables/external_issue_candidates.csv`
- `reports/tables/external_issue_sources.csv`
- `reports/tables/external_issue_match_counts.csv`
- `reports/tables/clusters/cluster_assignments.csv`
- `reports/tables/clusters/cluster_summary.csv`
- `reports/tables/clusters/cluster_issue_candidates.csv`
- `reports/tables/clusters/cluster_representative_decisions.csv`
- `reports/cluster_full_html/index.html`
- `reports/cluster_full_html/cluster_00.html` through `cluster_17.html`
- `reports/cluster_full_html/style.css`
- `reports/global_issues.html`
- `reports/style.css`
- `reports/tables/global_issue_quant_summary.csv`
- `reports/tables/global_issue_decision_examples.csv`

## Validation

Commands run successfully:

```bash
.venv/bin/python -m pytest -q
.venv/bin/pipc smoke --force
.venv/bin/pipc collect-list
.venv/bin/pipc collect-decisions
.venv/bin/pipc parse
.venv/bin/pipc eda
.venv/bin/pipc insights
.venv/bin/pipc html-reports
.venv/bin/pipc full-reports
.venv/bin/pipc cluster --n-clusters 18
.venv/bin/pipc cluster-reports
.venv/bin/pipc global-issue-report
```

Latest test result:

```text
6 passed
```

Latest `reports/eda.md` headline values:

- 전체 결정문 수: 3,990
- 수집 성공 수: 3,990
- 수집 실패 수: 0
- 중복 `decision_id` 수: 0
- 금액 추출 가능 사건 수: 753

Latest `reports/insights.md` headline values:

- 전체 결정문 수: 3,990
- 침해요인 평가: 2,421
- 법규 위반·제재: 882
- 공공시스템·실태점검: 186
- 개인정보 제공 요청: 115
- 제재 장르 중 금액 추출 가능 사건: 728

## Important Implementation Notes

- `src/pipc/parse.py` was updated for the real API XML structure:
  - list records are `<ppc id="...">` under root `<Ppc>`;
  - list dates use `<의결일>`;
  - detail links use `<결정문상세링크>`;
  - decision bodies use tags such as `<결정>`, `<의결연월일>`, `<위원서명>`, and `<이의제기방법및기간>`.
- `src/pipc/eda.py` now reads `data/processed/failed_decisions.csv` and prints the actual failure count in `reports/eda.md`.
- The label extraction in `src/pipc/labels.py` is preliminary keyword/rule logic.
- `src/pipc/labels.py` now classifies `document_category` before case types. This is important because words such as `침해` mean different things in impact reviews and enforcement cases.
- `monetary_amount` extraction prioritizes `order_text` and only fills when monetary sanction terms such as `과징금` or `과태료` are detected.
- `src/pipc/html_reports.py` generates responsive static HTML with SVG charts and no browser/server dependency.
- `src/pipc/full_reports.py` generates detailed HTML reports with section-specific insight extraction:
  - overview: corpus periods and genre transitions;
  - enforcement: sanction packages, money bands, article pairs, case types, factors;
  - privacy impact review: recommendation rates, ministries, law names, recurring issue terms;
  - public system: title families, yearly concentration, recurring issue terms;
  - data provision: allow/deny outcome estimates, video information, issue terms;
  - interpretation/other: article and issue term profile;
  - data quality: missingness and review priority.
- `src/pipc/clustering.py` uses char n-gram TF-IDF and MiniBatchKMeans to group decisions into 18 exploratory clusters.
- `reports/tables/clusters/cluster_issue_candidates.csv` stores around 10 issues per cluster, mixing global external issues and cluster-local issue patterns.
- `reports/cluster_full_html/` provides a separate full report for each cluster with metrics, issue candidates, charts, representative decisions, and text signals.
- `reports/global_issues.html` is intentionally separate from section and cluster reports. It covers 11 global controversies and, for each, provides legal focus, quantitative distribution, qualitative interpretation, representative decision examples, and external source links.
- Generated HTML pages were checked for viewport metadata, CSS linkage, and valid internal links.
- `reports/tables/review_samples.csv` is intended for manual validation by staff or researchers.
- `reports/tables/citation_index.csv` is a lightweight decision ID index for browsing and RAG preparation.

## Known Follow-Up Quality Issues

- Case type extraction is now disabled for `privacy_impact_review`, but enforcement case type and factor extraction are still rule-based and need sample validation.
- Some fields are genuinely absent for subsets of decisions. See `reports/tables/missing_rates.csv`.
- `reports/figures` is still empty; the first EDA currently generates markdown and CSV tables only.
- `tests/__pycache__` exists from test execution and can be ignored.

## Recommended Next Work

Proceed with these staff-facing analysis steps:

1. Continue manual review beyond `review_samples.csv`, especially high-amount enforcement cases and ambiguous `other` cases.
2. Add persistent `external_issue_tags` and `cluster_issue_tags` columns to processed decisions instead of keeping issue matches only as derived report tables.
3. Improve the full section reports so they link directly to relevant cluster pages and global issue anchors.
4. Add genre-specific extractors:
   - enforcement: sector, respondent type, leakage scale, sensitive/unique identifier flags, corrective measures
   - impact review: reviewed law name, requesting ministry, recommendation reason, personal data item, retention/delegation/linkage issues
   - data provision request: requesting agency, providing agency, purpose, legal basis, data type
5. Implement embeddings in `src/pipc/embeddings.py`.
6. Implement regression dataset creation and `reports/regression.md` for enforcement decisions.
7. Build paragraph/chunk-level citation data for RAG.
8. Add staff review workflow: issue-by-issue accept/reject flags, corrected legal tags, and representative quote approval.

Useful commands:

```bash
source .venv/bin/activate
pipc parse
pipc eda
pipc insights
pipc cluster --n-clusters 18
pipc cluster-reports
pipc global-issue-report
```
