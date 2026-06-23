from __future__ import annotations

from pulsepoint_alerts.monitor import active_section_text, active_unit_incident_signatures, build_unit_regex


def test_missing_active_cycle_should_preserve_existing_signature_baseline():
    unit_re = build_unit_regex(["M231", "M31", "PT30"])

    initial_page = """
ACTIVE
Medical Emergency
5:41 PM
VIA RANCHO SAN DIEGO #LIVING R, SAN MIGUEL, CA
M231
RECENT
Closed call
4:00 PM
M231
"""
    initial_active = active_section_text(initial_page)
    assert initial_active is not None
    initial_signatures, initial_units = active_unit_incident_signatures(initial_active, unit_re)

    previously_present_signatures = set(initial_signatures)
    previously_present_units = set(initial_units)

    missing_active_page = """
RECENT
Closed call
4:00 PM
M231
"""
    assert active_section_text(missing_active_page) is None

    # Missing Active must skip scan without clearing baseline state.
    assert previously_present_units == {"M231"}
    assert previously_present_signatures == set(initial_signatures)

    returned_page = """
ACTIVE
Medical Emergency
6:40 PM
TECATE RD, POTRERO, CA
E3348
M31
PT30

Medical Emergency
5:41 PM
VIA RANCHO SAN DIEGO #LIVING R, SAN MIGUEL, CA
M231
RECENT
Closed call
4:00 PM
M231
"""
    returned_active = active_section_text(returned_page)
    assert returned_active is not None
    returned_signatures, _returned_units = active_unit_incident_signatures(returned_active, unit_re)

    new_signatures = set(returned_signatures) - previously_present_signatures
    new_blocks = [returned_signatures[signature] for signature in new_signatures]

    assert len(new_signatures) == 1
    assert any("TECATE RD" in block for block in new_blocks)
    assert all("VIA RANCHO SAN DIEGO" not in block for block in new_blocks)
