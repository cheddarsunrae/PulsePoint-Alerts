from __future__ import annotations

from pulsepoint_alerts.monitor import (
    active_section_text,
    active_unit_incident_signatures,
    build_unit_regex,
    reset_unit_baseline_if_units_changed,
    unit_baseline_key,
)


def test_unit_baseline_key_ignores_order_case_and_spacing():
    assert unit_baseline_key([" m231 ", "PT30", "m31"]) == unit_baseline_key(["M31", "M231", "pt30"])


def test_unit_list_change_resets_baseline_before_alerting_current_active_calls():
    previous_units = set()
    previous_signatures = set()
    baseline_captured = True
    last_key = unit_baseline_key(["E36"])

    current_units = ["E3363", "E3383", "E36", "M231", "M31", "PT30"]

    (
        last_key,
        baseline_captured,
        previous_units,
        previous_signatures,
        changed,
    ) = reset_unit_baseline_if_units_changed(
        current_units,
        last_key,
        baseline_captured,
        previous_units,
        previous_signatures,
    )

    assert changed is True
    assert baseline_captured is False
    assert previous_units == set()
    assert previous_signatures == set()
    assert last_key == unit_baseline_key(current_units)

    page = """
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
Medical Emergency
4:00 PM
M231
"""
    active_text = active_section_text(page)
    assert active_text is not None

    unit_re = build_unit_regex(current_units)
    active_signatures, found_units = active_unit_incident_signatures(active_text, unit_re)
    current_signatures = set(active_signatures)

    if not baseline_captured:
        previous_units = found_units
        previous_signatures = current_signatures
        baseline_captured = True
        new_signatures = set()
    else:
        new_signatures = current_signatures - previous_signatures

    assert baseline_captured is True
    assert previous_units == {"M231", "M31", "PT30"}
    assert previous_signatures == current_signatures
    assert new_signatures == set()


def test_same_unit_list_does_not_reset_baseline():
    previous_units = {"M231"}
    previous_signatures = {"abc123"}
    baseline_captured = True
    last_key = unit_baseline_key(["M231", "PT30"])

    (
        new_key,
        new_baseline_captured,
        new_previous_units,
        new_previous_signatures,
        changed,
    ) = reset_unit_baseline_if_units_changed(
        ["PT30", "M231"],
        last_key,
        baseline_captured,
        previous_units,
        previous_signatures,
    )

    assert changed is False
    assert new_key == last_key
    assert new_baseline_captured is True
    assert new_previous_units == previous_units
    assert new_previous_signatures == previous_signatures
