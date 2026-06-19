from pulsepoint_alerts.monitor import (
    active_section_text,
    active_unit_incident_signatures,
    build_unit_regex,
    normalize_incident_text,
    summarize_incident_block,
    incident_signature_text,
    split_active_incident_blocks,
)


def test_active_section_excludes_recent_section():
    page_text = """
HEADER

ACTIVE

Medical Emergency
123 Main St
M231
E201

RECENT

Medical Emergency
456 Closed St
M231
"""

    active = active_section_text(page_text)

    assert active is not None
    assert "123 Main St" in active
    assert "M231" in active
    assert "RECENT" not in active
    assert "456 Closed St" not in active


def test_recent_only_unit_does_not_match():
    page_text = """
ACTIVE

No monitored units here

RECENT

Traffic Collision
M231
Closed incident
"""

    active = active_section_text(page_text)
    unit_re = build_unit_regex(["M231"])
    signatures, units = active_unit_incident_signatures(active or "", unit_re)

    assert signatures == {}
    assert units == set()


def test_active_unit_signature_detects_monitored_unit():
    active = """
Medical Emergency
5:42 PM
123 Main St
Patient contact
?M231
E201
"""

    unit_re = build_unit_regex(["M231"])
    signatures, units = active_unit_incident_signatures(active, unit_re)

    assert "M231" in units
    assert len(signatures) >= 1
    assert any("123 Main St" in block for block in signatures.values())


def test_active_unit_signature_detects_multiple_units_in_same_incident():
    active = """
Structure Fire
5:42 PM
789 Broadway
^E201
?M231
B1
"""

    unit_re = build_unit_regex(["M231", "E201"])
    signatures, units = active_unit_incident_signatures(active, unit_re)

    assert units == {"M231", "E201"}
    assert len(signatures) >= 1


def test_normalize_incident_text_removes_time_and_age_noise():
    original = "Medical Emergency 12:31 PM 4 MINS M231"
    normalized = normalize_incident_text(original)

    assert "12:31" not in normalized
    assert "4 MINS" not in normalized
    assert "MEDICAL EMERGENCY" in normalized
    assert "M231" in normalized


def test_summarize_incident_block_deduplicates_lines():
    block = """
Medical Emergency
Medical Emergency
123 Main St
M231
M231
"""

    summary = summarize_incident_block(block)

    assert summary.count("Medical Emergency") == 1
    assert summary.count("M231") == 1
    assert "123 Main St" in summary

def test_split_active_incident_blocks_keeps_neighboring_incidents_separate():
    active = """
(3)
Medical Emergency
5:42 PM
ROCKY MOUNTAIN RD, JAMUL, CA
E36
M231
Traffic Collision
5:26 PM
CHAMPAGNE BL & LAWRENCE WELK DR, DEER SPRINGS, CA
E12
E82
M11
Vegetation Fire
1:18 PM
NB 15 SO MISSION RD, PALA MESA, CA
9CU
AA310
"""

    blocks = split_active_incident_blocks(active)

    assert len(blocks) == 3
    assert "M231" in blocks[0]
    assert "M11" in blocks[1]
    assert "AA310" in blocks[2]

def test_new_neighbor_incident_does_not_create_new_monitored_unit_signature():
    before = """
Medical Emergency
5:42 PM
ROCKY MOUNTAIN RD, JAMUL, CA
E36
M231
Traffic Collision
5:26 PM
CHAMPAGNE BL & LAWRENCE WELK DR, DEER SPRINGS, CA
E12
E82
M11
"""

    after = """
Medical Emergency
5:55 PM
PARADISE MOUNTAIN RD #SPC 117, VALLEY CENTER, CA
M71
Medical Emergency
5:42 PM
ROCKY MOUNTAIN RD, JAMUL, CA
E36
M231
Traffic Collision
5:26 PM
CHAMPAGNE BL & LAWRENCE WELK DR, DEER SPRINGS, CA
E12
E82
M11
Vegetation Fire
1:18 PM
NB 15 SO MISSION RD, PALA MESA, CA
9CU
AA310
"""

    unit_re = build_unit_regex(["M231"])
    before_signatures, before_units = active_unit_incident_signatures(before, unit_re)
    after_signatures, after_units = active_unit_incident_signatures(after, unit_re)

    assert before_units == {"M231"}
    assert after_units == {"M231"}
    assert set(after_signatures) == set(before_signatures)

def test_unit_status_prefix_change_does_not_create_new_signature():
    with_prefix = """
Medical Emergency
5:42 PM
ROCKY MOUNTAIN RD, JAMUL, CA
?E36
?M231
"""

    without_prefix = """
Medical Emergency
5:42 PM
ROCKY MOUNTAIN RD, JAMUL, CA
E36
M231
"""

    unit_re = build_unit_regex(["M231"])
    before_signatures, _ = active_unit_incident_signatures(with_prefix, unit_re)
    after_signatures, _ = active_unit_incident_signatures(without_prefix, unit_re)

    assert set(after_signatures) == set(before_signatures)

def test_unit_roster_change_does_not_create_new_signature_for_same_incident():
    with_extra_unit = """
Medical Emergency
5:42 PM
ROCKY MOUNTAIN RD, JAMUL, CA
E36
M231
B1
"""

    without_extra_unit = """
Medical Emergency
5:42 PM
ROCKY MOUNTAIN RD, JAMUL, CA
M231
"""

    unit_re = build_unit_regex(["M231"])
    before_signatures, _ = active_unit_incident_signatures(with_extra_unit, unit_re)
    after_signatures, _ = active_unit_incident_signatures(without_extra_unit, unit_re)

    assert set(after_signatures) == set(before_signatures)

def test_incident_signature_text_ignores_unit_only_lines():
    block = """
Medical Emergency
5:42 PM
ROCKY MOUNTAIN RD, JAMUL, CA
?E36
M231
B1
"""

    signature = incident_signature_text(block)

    assert "MEDICAL EMERGENCY" in signature
    assert "ROCKY MOUNTAIN RD" in signature
    assert "M231" not in signature
    assert "E36" not in signature
    assert "B1" not in signature

def test_unparseable_active_layout_fails_safe_without_bundling():
    active = """
Medical Emergency
ROCKY MOUNTAIN RD, JAMUL, CA
M231
Traffic Collision
CHAMPAGNE BL & LAWRENCE WELK DR, DEER SPRINGS, CA
M11
"""

    unit_re = build_unit_regex(["M231"])
    signatures, units = active_unit_incident_signatures(active, unit_re)

    assert signatures == {}
    assert units == set()
