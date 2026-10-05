"""Failure-boundary regressions for the PR 18 follow-up review."""

import errno
import os
from argparse import Namespace
from pathlib import Path

import pytest

import agent_reach.cli as cli
from agent_reach.config import Config
from agent_reach.core import AgentReach


def test_library_doctor_report_uses_active_config(tmp_path, monkeypatch):
    import agent_reach.doctor as doctor

    cfg = Config(config_path=tmp_path / "custom.yaml")
    results = {}
    monkeypatch.setattr(doctor, "check_all", lambda config: results)
    calls = []

    def report(received_results, config=None):
        calls.append((received_results, config))
        return "report"

    monkeypatch.setattr(doctor, "format_report", report)
    assert AgentReach(config=cfg).doctor_report() == "report"
    assert calls == [(results, cfg)]


def test_system_install_saves_proxy_pair_once(isolated_home, monkeypatch):
    import agent_reach.doctor as doctor

    writes = []
    original_save = Config.save

    def save(config):
        writes.append(dict(config.data))
        return original_save(config)

    monkeypatch.setattr(Config, "save", save)
    monkeypatch.setattr(cli, "_install_system_deps", lambda: True)
    monkeypatch.setattr(cli, "_install_mcporter", lambda: True)
    monkeypatch.setattr(cli, "_install_skill", lambda: True)
    monkeypatch.setattr(doctor, "check_all", lambda _config: {})
    monkeypatch.setattr(doctor, "format_report", lambda _results, _config: "report")

    cli._cmd_install(
        Namespace(
            env="server", proxy="http://proxy.invalid:8080", system=True,
            safe=False, dry_run=False, channels="",
        )
    )

    assert len(writes) == 1
    assert writes[0]["proxy"] == "http://proxy.invalid:8080"
    assert writes[0]["bilibili_proxy"] == "http://proxy.invalid:8080"
    assert Config().get("proxy") == Config().get("bilibili_proxy")


def _old_skill(home):
    target = home / ".claude" / "skills" / "agent-reach"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("OLD", encoding="utf-8")
    (target / "custom.md").write_text("CUSTOM", encoding="utf-8")
    return target


def test_skill_backup_stays_on_target_filesystem(isolated_home, monkeypatch):
    target = _old_skill(isolated_home)
    original = os.rename

    def rename(src, dst):
        if Path(src) == target and not Path(dst).is_relative_to(target.parent):
            raise OSError(errno.EXDEV, "cross-device rename")
        return original(src, dst)

    monkeypatch.setattr(os, "rename", rename)
    assert cli._install_skill() is True
    assert (target / "SKILL.md").read_text(encoding="utf-8") != "OLD"


def test_skill_failed_restore_retains_recoverable_backup(isolated_home, monkeypatch, capsys):
    target = _old_skill(isolated_home)
    original = os.rename
    backups = []

    def rename(src, dst):
        if Path(src) == target:
            backups.append(Path(dst))
            return original(src, dst)
        if Path(dst) == target:
            raise OSError("synthetic publication or restore failure")
        return original(src, dst)

    original_makedirs = os.makedirs

    def makedirs(path, *args, **kwargs):
        if Path(path) == target / "references":
            raise OSError("synthetic write failure")
        return original_makedirs(path, *args, **kwargs)

    monkeypatch.setattr(os, "rename", rename)
    monkeypatch.setattr(os, "makedirs", makedirs)
    assert cli._install_skill() is False
    assert len(backups) == 1
    assert (backups[0] / "SKILL.md").read_text(encoding="utf-8") == "OLD"
    assert (backups[0] / "custom.md").read_text(encoding="utf-8") == "CUSTOM"
    assert str(backups[0]) in capsys.readouterr().out


def test_skill_write_failure_does_not_move_old_install(isolated_home, monkeypatch):
    target = _old_skill(isolated_home)
    original = os.makedirs
    moved = []
    original_rename = os.rename

    def makedirs(path, *args, **kwargs):
        if Path(path).name == "references":
            raise OSError("synthetic staging failure")
        return original(path, *args, **kwargs)

    def rename(src, dst):
        moved.append((src, dst))
        return original_rename(src, dst)

    monkeypatch.setattr(os, "makedirs", makedirs)
    monkeypatch.setattr(os, "rename", rename)
    assert cli._install_skill() is False
    assert moved == []
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "OLD"
    assert (target / "custom.md").read_text(encoding="utf-8") == "CUSTOM"


def test_skill_preserved_install_does_not_read_resources(isolated_home, monkeypatch):
    target = _old_skill(isolated_home)
    original = Path.read_text

    def read(path, *args, **kwargs):
        if "agent_reach/skill" in str(path):
            raise OSError("synthetic resource failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    assert cli._install_skill(force=False) is True
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "OLD"


def test_skill_publication_failure_restores_symlink(isolated_home, tmp_path, monkeypatch):
    referent = tmp_path / "external-skill"
    referent.mkdir()
    (referent / "SKILL.md").write_text("EXTERNAL", encoding="utf-8")
    target = isolated_home / ".claude" / "skills" / "agent-reach"
    target.parent.mkdir(parents=True)
    try:
        target.symlink_to(referent, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    original = os.rename
    failed = False

    def rename(src, dst):
        nonlocal failed
        if Path(dst) == target and not failed:
            failed = True
            raise OSError("synthetic publication failure")
        return original(src, dst)

    monkeypatch.setattr(os, "rename", rename)
    assert cli._install_skill() is False
    assert failed
    assert target.is_symlink()
    assert (referent / "SKILL.md").read_text(encoding="utf-8") == "EXTERNAL"
