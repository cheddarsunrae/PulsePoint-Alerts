from pathlib import Path
import ast


CORE_MODULES = [
    Path("src/pulsepoint_alerts/alerting.py"),
    Path("src/pulsepoint_alerts/monitor.py"),
    Path("src/pulsepoint_alerts/runtime.py"),
    Path("src/pulsepoint_alerts/config.py"),
]


# Only require docstrings for safety-critical functions that exist in the
# current repo layout. Do not list future/planned helper names here unless the
# function actually exists in src/pulsepoint_alerts.
SAFETY_CRITICAL_FUNCTIONS = {
    "trigger_alert",
    "silence_alert",
    "record_alert",
    "acknowledge_latest_alert",
}


def existing_core_modules():
    """Return only core modules that actually exist in this repo layout."""
    return [path for path in CORE_MODULES if path.exists()]


def collect_function_docstrings():
    """Collect docstrings for safety-critical function definitions."""
    found = {name: [] for name in SAFETY_CRITICAL_FUNCTIONS}

    for path in existing_core_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in found:
                found[node.name].append(ast.get_docstring(node))

    return found


def test_core_modules_have_module_docstrings():
    for path in existing_core_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert ast.get_docstring(tree), f"{path} is missing a module docstring"


def test_safety_critical_functions_have_docstrings():
    found = collect_function_docstrings()

    missing = sorted(
        name
        for name, docstrings in found.items()
        if not any(docstrings)
    )

    assert not missing, f"Missing docstrings for: {missing}"
