from pathlib import Path

from pipc.labels import derive_labels, extract_max_money
from pipc.parse import parse_decision_file, parse_list_file


def test_parse_list_file_maps_standard_fields(tmp_path: Path) -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Ppc>
      <totalCnt>1</totalCnt>
      <ppc id="1">
        <결정문일련번호>123</결정문일련번호>
        <사건명>개인정보 유출 사건</사건명>
        <의안번호>2024-1</의안번호>
        <회의종류>전체회의</회의종류>
        <의결구분>시정명령</의결구분>
        <의결일>2024.1.31.</의결일>
        <결정문상세링크>https://example.test/123</결정문상세링크>
      </ppc>
    </Ppc>
    """
    path = tmp_path / "page_1.xml"
    path.write_text(xml, encoding="utf-8")

    parsed = parse_list_file(path)

    assert parsed.total_count == 1
    assert parsed.rows[0]["decision_id"] == "123"
    assert parsed.rows[0]["decision_date"] == "2024-01-31"
    assert parsed.rows[0]["detail_url"] == "https://example.test/123"


def test_parse_decision_file_collects_nested_section_text(tmp_path: Path) -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Decision>
      <ID>abc</ID>
      <사건명>안전조치 위반</사건명>
      <주문><p>피심인에게 과징금 1억원을 부과한다.</p></주문>
      <이유><p>개인정보 보호법 제29조 위반이다.</p></이유>
    </Decision>
    """
    path = tmp_path / "abc.xml"
    path.write_text(xml, encoding="utf-8")

    row = parse_decision_file(path)

    assert row["order_text"] == "피심인에게 과징금 1억원을 부과한다."
    assert row["reason_text"] == "개인정보 보호법 제29조 위반이다."


def test_derive_labels_extracts_sanction_amount_and_articles() -> None:
    labels = derive_labels("개인정보 보호법 제29조 위반으로 과징금 1억원과 시정명령을 부과한다.")

    assert labels.document_category == "enforcement"
    assert labels.sanction_strength == 4
    assert "과징금" in labels.sanction_types
    assert labels.monetary_amount == 100_000_000
    assert labels.violated_articles == "제29조"


def test_extract_max_money_handles_manwon() -> None:
    assert extract_max_money("과태료 1,500만원을 부과한다.") == 15_000_000


def test_impact_review_does_not_become_breach_case_type() -> None:
    labels = derive_labels("「자동차관리법 시행규칙」 일부개정안에 대한 개인정보 침해요인 평가에 관한 건")

    assert labels.document_category == "privacy_impact_review"
    assert labels.case_type == ""


def test_data_provision_request_does_not_treat_purpose_fine_as_sanction() -> None:
    labels = derive_labels(
        "양구군의 쓰레기 불법투기 과태료 부과를 위한 렌터카업체 보유 개인정보 제공에 관한 건\n"
        "양구군은 과태료 부과를 위해 개인정보를 제공받을 수 없다.",
        amount_text="양구군은 과태료 부과를 위해 개인정보를 제공받을 수 없다.",
        title_text="양구군의 쓰레기 불법투기 과태료 부과를 위한 렌터카업체 보유 개인정보 제공에 관한 건",
    )

    assert labels.document_category == "data_provision_request"
    assert labels.sanction_types == ""
    assert labels.sanction_strength == 0
