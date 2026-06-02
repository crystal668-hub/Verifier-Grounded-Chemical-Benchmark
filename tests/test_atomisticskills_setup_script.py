from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_setup_script_uses_resolved_python_for_mcp_configuration() -> None:
    script = (ROOT / "scripts" / "setup_atomisticskills_first_batch.sh").read_text()

    assert "\npython configure_mcp.py" not in script
    assert "conda info --base" in script
    assert '"$CONFIGURE_PYTHON" configure_mcp.py --agent codex --scope project || true' in script
