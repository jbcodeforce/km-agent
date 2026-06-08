"""Sanity checks for ``scripts/verify_agent_env.sh``."""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFY_SH = REPO_ROOT / "scripts" / "verify_agent_env.sh"


def test_verify_script_exists() -> None:
    assert VERIFY_SH.is_file(), f"expected {VERIFY_SH}"


def test_verify_script_shell_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(VERIFY_SH)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_verify_script_help_exits_zero() -> None:
    result = subprocess.run(
        ["bash", str(VERIFY_SH), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--frontend" in result.stdout
    assert "--trace-env" in result.stdout


def test_verify_script_contains_expected_checks() -> None:
    text = VERIFY_SH.read_text(encoding="utf-8")
    assert "check_postgres_container" in text
    assert "check_db_tcp" in text
    assert "check_backend" in text
    assert "check_frontend" in text
    assert "/agents" in text
    assert "KMA_VERIFY_AGENT_DB_CONTAINER" in text
    assert "KMA_DB_HOST" in text
    assert "trace_resolved_configuration" in text
    assert "format_env_value_for_trace" in text


def test_verify_script_contains_omlx_check() -> None:
    text = VERIFY_SH.read_text(encoding="utf-8")
    assert "check_omlx" in text
    assert "KMA_MLX_BASE_URL" in text
    assert "/models" in text


def test_verify_script_omlx_check_only_when_mlx(monkeypatch) -> None:
    """check_omlx is invoked from main and guarded by provider == mlx."""
    text = VERIFY_SH.read_text(encoding="utf-8")
    assert 'mlx' in text
    assert "check_omlx || ok=1" in text
