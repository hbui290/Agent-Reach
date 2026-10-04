import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "test.sh"


def test_integration_script_has_valid_shell_syntax(bash_executable):
    subprocess.run([bash_executable, "-n", SCRIPT.name], check=True, cwd=ROOT)


def test_integration_script_exercises_the_current_cli_contract():
    text = SCRIPT.read_text(encoding="utf-8")

    # Installs from inside the checkout so Windows pip never sees a /c/... path.
    assert '( cd "$REPO_ROOT" && python -m pip install --quiet -c constraints.txt -e ".[dev]" )' in text
    assert '"$REPO_ROOT[dev]"' not in text
    assert 'TEST_DIR=$(cd "$TEST_DIR" && pwd -P)' in text
    assert 'export HOME="$TEST_DIR/home"' in text
    assert "sys.version_info >= (3, 10)" in text
    assert 'PYTHON_CMD=("$REPO_ROOT/.venv/bin/python")' in text
    assert 'venv/Scripts/activate' in text
    assert "agent-reach install --env=auto --safe" in text
    assert "agent-reach install --env=auto --system --dry-run" in text
    assert "agent-reach doctor --json" in text
    assert 'pytest "$REPO_ROOT/tests" -q' in text

    nonexistent_commands = (
        "agent-reach read ",
        "agent-reach search ",
        "agent-reach search-github ",
        "agent-reach search-twitter ",
        "agent-reach search-reddit ",
        "agent-reach search-youtube ",
        "agent-reach search-bilibili ",
        "agent-reach search-xhs ",
    )
    assert not any(command in text for command in nonexistent_commands)
