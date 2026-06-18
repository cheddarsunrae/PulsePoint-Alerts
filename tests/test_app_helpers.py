from pulsepoint_alerts.app import agency_display


def test_agency_display_shows_saved_name_for_matching_agency_ids():
    cfg = {
        "agency_ids": "37047",
        "agency_presets": [
            {"name": "AMR San Diego", "agency_ids": "37047"},
        ],
    }

    assert agency_display(cfg) == "37047 (AMR San Diego)"


def test_agency_display_falls_back_to_ids_when_no_saved_name_matches():
    cfg = {
        "agency_ids": "37047",
        "agency_presets": [
            {"name": "Other Agency", "agency_ids": "12345"},
        ],
    }

    assert agency_display(cfg) == "37047"


def test_agency_display_handles_empty_agency_ids():
    cfg = {
        "agency_ids": "",
        "agency_presets": [],
    }

    assert agency_display(cfg) == "(none)"


from pulsepoint_alerts.app import unit_set_display


def test_unit_set_display_shows_saved_name_for_matching_units():
    cfg = {
        "units": ["E36", "M231"],
        "unit_presets": [
            {"name": "Station 36 / Jamul set", "units": ["E36", "M231"]},
        ],
    }

    assert unit_set_display(cfg) == "E36, M231 (Station 36 / Jamul set)"


def test_unit_set_display_falls_back_to_units_when_no_saved_name_matches():
    cfg = {
        "units": ["M231"],
        "unit_presets": [
            {"name": "Other Unit Set", "units": ["E36"]},
        ],
    }

    assert unit_set_display(cfg) == "M231"


def test_unit_set_display_handles_empty_units():
    cfg = {
        "units": [],
        "unit_presets": [],
    }

    assert unit_set_display(cfg) == "(none)"
