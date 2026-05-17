# External Issue Scan For PIPC Decision Analysis

## Purpose

This note supplements the internal 3,990-decision corpus analysis with issues repeatedly discussed in legal media, Korean news articles, and academic literature. The goal is to add issue lenses that PIPC staff may care about when interpreting the corpus and designing staff-facing tools.

## Method

Sources reviewed include Law Times articles, KCI/RISS academic records, Korean news coverage, court/government materials, and professional legal updates. This is not a complete literature review; it is an issue scan for prioritizing the next round of corpus analysis.

## Additional Issues

### 1. Behavioral Advertising, Consent, And Platform Control

- External signal: Law Times and other media treat the Google/Meta matter as a major test of whether global platforms can collect behavioral data for targeted advertising without valid consent.
- Academic signal: KCI literature on the Google/Meta case focuses on whether platform operators hold real control over behavioral information processing and whether consent UI/information provision satisfies Korean law.
- Corpus mapping: high-value enforcement cases with `동의·고지 위반`, `맞춤형 광고`, `행태정보`, `제3자 제공`, `국외이전`, high monetary sanctions.
- Additional extraction target: behavioral-advertising cases, consent UI defects, third-party publisher/platform role allocation, controller-like control indicators.
- Sources:
  - https://www.lawtimes.co.kr/news/205969
  - https://www.lawtimes.co.kr/news/197377
  - https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART003161930
  - https://www.donga.com/news/Economy/article/all/20220914/115450664/1

### 2. Mega-Leak Enforcement And Proportionality Of Administrative Fines

- External signal: SKT's large-scale leak and follow-on litigation made fine size, proportionality, and calculation method a public controversy.
- Corpus mapping: enforcement cases with high `monetary_amount`, `제29조`, `유출·침해`, `안전조치 미흡`, notification delay, and public anxiety factors.
- Additional extraction target: leakage scale, duration of vulnerable state, delayed notification, security patch age, affected identifier type, penalty calculation basis.
- Sources:
  - https://www.segye.com/newsView/20250828516111
  - https://www.khan.co.kr/article/202508282051025
  - https://www.etnews.com/20260119000417
  - https://www.mt.co.kr/tech/2025/08/28/2025082808104349505

### 3. Causation And Adequacy Of Safety Measures

- External signal: Law Times' KT ruling coverage and court summaries show continuing controversy over when safety measures are sufficient and whether causation between violation and leak is required.
- Corpus mapping: `제29조`, access control, log retention/inspection, encryption, breach cases that also involve litigation or cancellation risk.
- Additional extraction target: court-review risk marker, safety-measure subtypes, causal language, "sufficient measures" defense, discretion abuse arguments.
- Sources:
  - https://www.lawtimes.co.kr/news/172772
  - https://slgodung.scourt.go.kr/dcboard/new/DcNewsViewAction.work?cbub_code=000200&gubun=44&pageIndex=1&searchWord=&seqnum=25540

### 4. Overseas Transfer, Cloud, And Data Sovereignty

- External signal: KCI scholarship frames overseas transfer as a tension between data sovereignty/enforcement and global data flows. News on Temu and PIPC guidance shows this remains enforcement-relevant.
- Corpus mapping: `국외이전`, cloud/storage/consignment cases, global platform cases, overseas processors, foreign recipient disclosures.
- Additional extraction target: transfer type, recipient country, consignment vs third-party provision, notice/consent basis, adequacy/safeguard language, suspension order risk.
- Sources:
  - https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002540745
  - https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART001764632
  - https://scholar.korea.ac.kr/handle/2021.sw.korea/110585
  - https://dailian.co.kr/news/view/1497946

### 5. Automated Decisions, AI, And Explainability

- External signal: Law Times and academic sources identify automated decisions as a new rights and compliance field after the Personal Information Protection Act amendments.
- Corpus mapping: currently likely underrepresented in old decisions; should be tracked in new decisions, prior reviews, impact reviews, and AI pre-inspection records.
- Additional extraction target: automated decision, profiling, refusal/explanation request, human review, AI model/data use, discrimination or bias risk.
- Sources:
  - https://www.lawtimes.co.kr/LawFirm-NewsLetter/198691
  - https://www.riss.kr/search/detail/ssoSkipDetailView.do?control_no=603c33d0633c7e0dd18150b21a227875&p_mat_type=1a0202e37d52c72d
  - https://biz.chosun.com/it-science/ict/2024/02/19/UDKSYYLUDRGR5MYT3GMVGNG2B4/
  - https://www.kli.re.kr/pdfPreviewDownload?fileName=F6EDCE04416A373949258DCB002C74CC_4.pdf&fileNameOrg=%EC%9D%B8%EA%B3%B5%EC%A7%80%EB%8A%A5%EA%B3%BC+%EB%85%B8%EC%82%AC%EA%B4%80%EA%B3%84%EC%9D%98+%EB%B3%80%ED%99%94%EC%99%80+%EC%9F%81%EC%A0%90_web.pdf&filePath1=jsphome%2FDATA%2FpblctList%2Fissue%2FF6EDCE04416A373949258DCB002C74CC

### 6. Preventive Inspection Versus Ex Post Sanctions

- External signal: Korean news and policy materials criticize limited use of preventive inspection and emphasize public-system safety checks.
- Corpus mapping: `public_system_inspection`, `prior_review`, `사전 실태점검`, `집중관리시스템`, and enforcement cases following public-system failures.
- Additional extraction target: preventive vs ex post posture, inspection target sector, whether inspection produced recommendation only or enforcement, follow-up requirement.
- Sources:
  - https://www.mt.co.kr/tech/2025/10/14/2025101408513035134
  - https://www.fnnews.com/news/202409121202240156
  - https://www.evaluation.go.kr/upload2/atch/eval/20240603134618828.pdf

### 7. CCTV And Video Information: Access, Third-Party Provision, And Surveillance Boundaries

- External signal: academic writing and news coverage show persistent disputes over CCTV provision to investigators, emergency/public safety exceptions, data subject access, and improper installation.
- Corpus mapping: `영상정보 처리`, `목적 외 이용`, `제3자 제공`, `제18조`, `제25조`, data provision request track.
- Additional extraction target: CCTV requester, purpose, legal basis, emergency/public-safety exception, data subject access/refusal reason, installation location sensitivity.
- Sources:
  - https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002450923
  - https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002691897
  - https://www.boannews.com/media/view.asp?idx=121613
  - https://www.newsis.com/view/NISX20220810_0001974027
  - https://zdnet.co.kr/view/?no=20250616102733

### 8. Children's Data And Legal Representative Consent

- External signal: recent F&B/platform and app enforcement coverage repeatedly highlights unlawful collection of data from children under 14.
- Corpus mapping: `아동 개인정보`, `동의·고지 위반`, legal representative consent, online membership/service signup.
- Additional extraction target: under-14 user count, age-screening design, legal representative verification, marketing consent bundling, service refusal due to non-consent.
- Sources:
  - https://view.asiae.co.kr/article/2026021210573280495
  - https://www.hankyung.com/article/202408293351i
  - https://www.kjtimes.com/news/article.html?no=78871

### 9. Privacy Policy Evaluation, CPO Governance, And Accountability

- External signal: legal media and professional updates emphasize strengthened CPO requirements and processing-policy evaluation, especially for AI, minors, large-scale processing, and past leaks.
- Corpus mapping: `개선권고`, `처리방침`, `CPO`, `개인정보 보호책임자`, large-scale processors, repeat or high-risk entities.
- Additional extraction target: governance failure, CPO status, policy disclosure defects, policy-evaluation target criteria, accountability remediation orders.
- Sources:
  - https://www.lawtimes.co.kr/LawFirm-NewsLetter/197740
  - https://biz.chosun.com/it-science/ict/2024/02/19/UDKSYYLUDRGR5MYT3GMVGNG2B4/
  - https://www.shinkim.com/kor/media/newsletter/pdf/2452

### 10. Victim Remedies, Collective Dispute Resolution, And Use Of Fines

- External signal: post-SKT coverage raised whether administrative fines should remain general treasury revenue or support victims, and how collective dispute resolution should work.
- Corpus mapping: high-scale breach cases, notification delay, remedial measures, dispute mediation references, publication orders.
- Additional extraction target: affected person count, notification/remediation, dispute mediation, compensation recommendation, fund/victim-use policy marker.
- Sources:
  - https://www.mt.co.kr/tech/2025/09/11/2025091109180344318
  - https://www.asiae.co.kr/article/IT/2025091515464252534
  - https://www.newsprime.co.kr/news/article/?no=711222

### 11. Sector-Specific Privacy Risk: F&B, Mobility, Medical, Telecom, Public Services

- External signal: news coverage shows sector waves: telecom mega-leaks, F&B platform membership/children/retention issues, hospitality/automotive/app service breaches, public-system concentration.
- Corpus mapping: applicant/respondent names, titles, public/private status, industry terms, repeated enforcement waves.
- Additional extraction target: sector classifier, enforcement wave detection, repeated industry defects, sector-specific compliance checklist.
- Sources:
  - https://view.asiae.co.kr/article/2026021210573280495
  - https://www.hankyung.com/article/202408293351i
  - https://www.lawtimes.co.kr/news/201006
  - https://www.segye.com/newsView/20250828516111

## Recommended Implementation Changes

1. Add `external_issue_tags` to processed decisions using the issue taxonomy above.
2. Add an `issue_lens` report section to each HTML full report.
3. Extend enforcement extraction with `leak_scale`, `notification_delay`, `security_measure_subtype`, `respondent_sector`, `high_amount_case`.
4. Extend impact review extraction with `reviewed_law_name`, `issue_terms`, `recommendation_type`.
5. Extend data provision extraction with `outcome`, `requesting_agency`, `providing_agency`, `legal_basis`, `video_information_flag`.
6. Add a source-backed issue page for staff that links external debates to decision IDs in the corpus.

## Corpus Match Snapshot

Keyword matching against the 3,990 processed decisions produced `reports/tables/external_issue_match_counts.csv`.

Top broad matches:

- Sector-specific recurring leaks and violations: 1,456 decisions
- Overseas transfer, cloud, and data sovereignty: 1,265 decisions
- Mega-leak enforcement and fine proportionality: 1,158 decisions
- Victim remedies, collective dispute resolution, and use of fines: 1,149 decisions
- Causation and adequacy of safety measures: 791 decisions

Low-count but strategically important matches:

- Automated decisions, AI, and explainability: 117 decisions
- Behavioral advertising, consent, and platform control: 25 decisions

These low-count categories should not be deprioritized solely because of count. They are high-salience issues in recent legal media and academic debate, and likely require forward-looking tagging for newer decisions and prior reviews.

## Recommended Priority Order

1. Enforcement high-salience issues: mega-leaks, safety measures, fine proportionality, victim remedies.
2. Cross-border/platform issues: behavioral advertising, overseas transfer, cloud, controller/processor role allocation.
3. Public-sector preventive issues: pre-inspection, public-system concentration, CCTV/video information.
4. Emerging rights issues: automated decisions, AI explainability, privacy policy evaluation, CPO governance.
5. Vulnerable data subjects and sector waves: children, food/platform services, telecom, medical, mobility, public services.
