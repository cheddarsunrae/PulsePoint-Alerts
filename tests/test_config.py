from pulsepoint_alerts.config import normalize_units


def test_normalize_units():
    assert normalize_units("m231, M36, m231") == ["M231", "M36"]
