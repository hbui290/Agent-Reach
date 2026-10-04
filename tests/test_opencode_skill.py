"""OpenCode discovery and metadata compatibility for the packaged skill."""

from __future__ import annotations

import importlib.resources
import os
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from agent_reach.cli import _cmd_uninstall, _install_skill, _uninstall_skill


def _frontmatter(resource_name: str) -> dict[str, object]:
    text = (
        importlib.resources.files("agent_reach")
        .joinpath("skill", resource_name)
        .read_text(encoding="utf-8")
    )
    match = re.match(r"\A---\n(.*?)\n---\n", text, flags=re.DOTALL)
    assert match is not None, f"{resource_name} must start with YAML frontmatter"
    return yaml.safe_load(match.group(1))


def test_skill_frontmatter_uses_opencode_supported_fields():
    """Both locale variants must follow OpenCode's documented schema."""
    allowed_fields = {
        "name",
        "description",
        "license",
        "compatibility",
        "metadata",
    }

    for resource_name in ("SKILL.md", "SKILL_en.md"):
        frontmatter = _frontmatter(resource_name)
        assert set(frontmatter) <= allowed_fields, resource_name
        assert frontmatter["name"] == "agent-reach", resource_name

        description = frontmatter["description"]
        assert isinstance(description, str), resource_name
        assert 1 <= len(description) <= 1024, resource_name

        metadata = frontmatter.get("metadata", {})
        assert isinstance(metadata, dict), resource_name
        assert all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in metadata.items()
        ), resource_name


def test_install_skill_discovers_opencode_global_directory(tmp_path: Path):
    skill_parent = tmp_path / ".config" / "opencode" / "skills"
    skill_parent.mkdir(parents=True)

    with patch(
        "agent_reach.cli.os.path.expanduser",
        side_effect=lambda value: value.replace("~", os.fspath(tmp_path)),
    ), patch.dict(os.environ, {}, clear=True):
        _install_skill()

    installed = skill_parent / "agent-reach" / "SKILL.md"
    assert installed.is_file()
    assert "Agent Reach" in installed.read_text(encoding="utf-8")


def test_uninstall_skill_removes_opencode_global_directory(tmp_path: Path):
    installed = tmp_path / ".config" / "opencode" / "skills" / "agent-reach"
    installed.mkdir(parents=True)
    (installed / "SKILL.md").write_text("test", encoding="utf-8")

    with patch(
        "agent_reach.cli.os.path.expanduser",
        side_effect=lambda value: value.replace("~", os.fspath(tmp_path)),
    ), patch.dict(os.environ, {}, clear=True):
        _uninstall_skill()

    assert not installed.exists()


def test_full_uninstall_includes_opencode_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    installed = tmp_path / ".config" / "opencode" / "skills" / "agent-reach"
    installed.mkdir(parents=True)

    with patch(
        "agent_reach.cli.os.path.expanduser",
        side_effect=lambda value: os.fspath(
            tmp_path / value.removeprefix("~/")
        )
        if value.startswith("~/")
        else value,
    ), patch("agent_reach.utils.paths.home_dir", return_value=tmp_path), patch(
        "shutil.which", return_value=None
    ):
        _cmd_uninstall(SimpleNamespace(dry_run=True, keep_config=True))

    output = capsys.readouterr().out
    assert f"Would remove OpenCode skill: {installed}" in output
    assert installed.is_dir()


def _home_patches(tmp_path: Path, extra_env: dict[str, str] | None = None):
    return (
        patch(
            "agent_reach.cli.os.path.expanduser",
            side_effect=lambda value: os.fspath(tmp_path / value.removeprefix("~/"))
            if value.startswith("~/")
            else value,
        ),
        patch("agent_reach.utils.paths.home_dir", return_value=tmp_path),
        patch("shutil.which", return_value=None),
        patch.dict(os.environ, extra_env or {}, clear=True),
    )


def test_full_uninstall_removes_openclaw_home_and_dangling_symlink(tmp_path: Path):
    openclaw_home = tmp_path / "oc"
    oc_skill = openclaw_home / ".openclaw" / "skills" / "agent-reach"
    oc_skill.mkdir(parents=True)
    dangling = tmp_path / ".claude" / "skills" / "agent-reach"
    dangling.parent.mkdir(parents=True)
    try:
        dangling.symlink_to(tmp_path / "missing-target")
    except OSError:
        pytest.skip("symlinks unavailable")

    p1, p2, p3, p4 = _home_patches(tmp_path, {"OPENCLAW_HOME": os.fspath(openclaw_home)})
    with p1, p2, p3, p4:
        _cmd_uninstall(SimpleNamespace(dry_run=False, keep_config=True))

    assert not oc_skill.exists()
    assert not os.path.lexists(dangling)


def test_full_uninstall_exits_nonzero_when_removal_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    (tmp_path / ".agent-reach").mkdir()

    p1, p2, p3, p4 = _home_patches(tmp_path)
    with p1, p2, p3, p4, patch(
        "shutil.rmtree", side_effect=PermissionError("denied")
    ), pytest.raises(SystemExit) as exc:
        _cmd_uninstall(SimpleNamespace(dry_run=False, keep_config=False))

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Cleanup incomplete" in out
    assert "already clean" not in out


def test_skill_uninstall_reports_failure(tmp_path: Path):
    installed = tmp_path / ".agents" / "skills" / "agent-reach"
    installed.mkdir(parents=True)

    p1, p2, p3, p4 = _home_patches(tmp_path)
    with p1, p2, p3, p4, patch("shutil.rmtree", side_effect=PermissionError("denied")):
        assert _uninstall_skill() is False
