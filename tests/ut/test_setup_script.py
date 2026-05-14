"""Sanity checks for ``scripts/setup.sh`` and local Docker Compose tooling."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SETUP_SH = REPO_ROOT / "scripts" / "setup.sh"


def test_setup_script_exists() -> None:
    assert SETUP_SH.is_file(), f"expected {SETUP_SH}"


def test_setup_script_shell_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SETUP_SH)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_setup_script_checks_docker_and_compose() -> None:
    text = SETUP_SH.read_text(encoding="utf-8")
    assert "docker version" in text or "docker compose" in text
    assert "docker compose version" in text
    assert "require_docker_cli" in text
    assert "require_docker_compose" in text


def test_setup_script_installs_ollama_when_missing() -> None:
    text = SETUP_SH.read_text(encoding="utf-8")
    assert "ensure_ollama_cli" in text
    assert "ollama.com/install.sh" in text
    assert "SKIP_OLLAMA_INSTALL" in text


def test_starter_script_exists_and_shell_syntax() -> None:
    starter = REPO_ROOT / "scripts" / "starter.sh"
    assert starter.is_file(), f"expected {starter}"
    text = starter.read_text(encoding="utf-8")
    assert "agent-db" in text
    assert "docker compose" in text
    result = subprocess.run(
        ["bash", "-n", str(starter)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_setup_script_default_raw_uses_refs_heads() -> None:
    """Default compose download matches GitHub raw URLs with refs/heads/BRANCH."""
    text = SETUP_SH.read_text(encoding="utf-8")
    assert "refs/heads/main" in text
    assert "jbcodeforce/km-agent/refs/heads/main" in text


def test_compose_yaml_does_not_run_ollama_in_docker() -> None:
    """Ollama is native on the host; Compose should not define an ollama image service."""
    compose = (REPO_ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "ollama/ollama" not in compose
    assert "host.docker.internal" in compose


def test_docker_cli_and_compose_available() -> None:
    """Mirrors what ``scripts/setup.sh`` requires on the host."""
    if shutil.which("docker") is None:
        pytest.skip("Docker CLI not installed")
    r = subprocess.run(
        ["docker", "version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if r.returncode != 0:
        pytest.skip(f"Docker daemon not reachable: {r.stderr.strip() or r.stdout.strip()}")
    c = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert c.returncode == 0, c.stderr or c.stdout


@pytest.mark.skipif(
    os.environ.get("KMA_TEST_SETUP_FETCH") != "1",
    reason="set KMA_TEST_SETUP_FETCH=1 to run network fetch test",
)
def test_setup_download_compose_to_tmp(tmp_path: Path) -> None:
    """Optional: verifies curl + raw URL (uses same default raw base as the script)."""
    env = os.environ.copy()
    env["KMA_TARGET_DIR"] = str(tmp_path)
    env["SKIP_OLLAMA_INSTALL"] = "1"
    env["KMA_RAW_BASE"] = (
        "https://raw.githubusercontent.com/jbcodeforce/km-agent/refs/heads/main"
    )
    # Exercise only download path: replace main() body behavior by sourcing is heavy;
    # run script but it also requires docker — so we skip unless docker exists.
    if shutil.which("docker") is None:
        pytest.skip("Docker not installed")
    r = subprocess.run(
        ["bash", str(SETUP_SH)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert (tmp_path / "compose.yaml").is_file()
    assert "services:" in (tmp_path / "compose.yaml").read_text(encoding="utf-8")
