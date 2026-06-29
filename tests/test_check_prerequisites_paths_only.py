"""Tests for check-prerequisites --paths-only flag (#3025)."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def prereq_repo(tmp_path: Path, repo_root: Path) -> Path:
    """Create a temporary repository with the .specify/scripts directory."""
    # Copy the entire .specify directory from the repo root
    src_specify = repo_root / ".specify"
    dst_specify = tmp_path / ".specify"
    shutil.copytree(src_specify, dst_specify, symlinks=False, ignore_dangling_symlinks=True)

    # Initialize a git repo so Bash script can detect branch
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp_path), check=True)

    # Create a dummy feature.json to test persistence (if needed)
    feature_json = tmp_path / ".specify" / "feature.json"
    if feature_json.exists():
        feature_json.unlink()

    return tmp_path


def test_bash_paths_only_does_not_persist_json(prereq_repo: Path) -> None:
    """With -PathsOnly, check-prerequisites.sh must NOT write .specify/feature.json."""
    script = prereq_repo / ".specify" / "scripts" / "bash" / "check-prerequisites.sh"
    if not script.exists():
        pytest.skip("Bash script not found")

    env = os.environ.copy()
    env["SPECIFY_FEATURE_DIRECTORY"] = "features/test-feature"
    env["SPECIFY_FEATURE"] = "test-feature"  # for the Bash script

    result = subprocess.run(
        ["bash", str(script), "--paths-only"],
        env=env,
        cwd=str(prereq_repo),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    feature_json = prereq_repo / ".specify" / "feature.json"
    assert not feature_json.exists(), "feature.json was created but should not have been"


def test_bash_normal_mode_persists_json(prereq_repo: Path) -> None:
    """Without -PathsOnly, check-prerequisites.sh MUST persist SPECIFY_FEATURE_DIRECTORY into feature.json."""
    script = prereq_repo / ".specify" / "scripts" / "bash" / "check-prerequisites.sh"
    if not script.exists():
        pytest.skip("Bash script not found")

    feature_dir = "features/bash-persist-test"
    env = os.environ.copy()
    env["SPECIFY_FEATURE_DIRECTORY"] = feature_dir
    env["SPECIFY_FEATURE"] = "bash-persist-test"

    result = subprocess.run(
        ["bash", str(script)],
        env=env,
        cwd=str(prereq_repo),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    feature_json = prereq_repo / ".specify" / "feature.json"
    assert feature_json.exists(), "feature.json was not created"

    data = json.loads(feature_json.read_text())
    assert data.get("feature_directory") == feature_dir, (
        f"Expected '{feature_dir}', got '{data.get('feature_directory')}'"
    )


def test_ps_paths_only_does_not_persist_json(prereq_repo: Path) -> None:
    """With -PathsOnly, check-prerequisites.ps1 must NOT write .specify/feature.json."""
    script = prereq_repo / ".specify" / "scripts" / "powershell" / "check-prerequisites.ps1"
    if not script.exists():
        pytest.skip("PowerShell script not found")

    # Check if pwsh is available
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("pwsh not available")

    feature_dir = "features/ps-test"
    env = os.environ.copy()
    env["SPECIFY_FEATURE_DIRECTORY"] = feature_dir

    result = subprocess.run(
        [pwsh, "-File", str(script), "-PathsOnly"],
        env=env,
        cwd=str(prereq_repo),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    feature_json = prereq_repo / ".specify" / "feature.json"
    assert not feature_json.exists(), "feature.json was created but should not have been"


def test_ps_normal_mode_persists_feature_json(prereq_repo: Path) -> None:
    """
    Without -PathsOnly, check-prerequisites.ps1 persists SPECIFY_FEATURE_DIRECTORY into feature.json.

    This is the symmetric PowerShell test for the Bash guard added in #3025.
    """
    script = prereq_repo / ".specify" / "scripts" / "powershell" / "check-prerequisites.ps1"
    if not script.exists():
        pytest.skip("PowerShell script not found")

    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("pwsh not available")

    feature_dir = "features/ps-persist-test"
    env = os.environ.copy()
    env["SPECIFY_FEATURE_DIRECTORY"] = feature_dir

    # Run the script WITHOUT -PathsOnly
    result = subprocess.run(
        [pwsh, "-File", str(script)],
        env=env,
        cwd=str(prereq_repo),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    feature_json = prereq_repo / ".specify" / "feature.json"
    assert feature_json.exists(), "feature.json was not created"

    data = json.loads(feature_json.read_text())
    assert data.get("feature_directory") == feature_dir, (
        f"Expected '{feature_dir}', got '{data.get('feature_directory')}'"
    )
