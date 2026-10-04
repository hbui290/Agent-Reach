# -*- coding: utf-8 -*-
"""Regressions for edge cases found while auditing the fork."""

import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import agent_reach.cli as cli
from agent_reach.config import Config, ConfigError
from agent_reach.utils.text import scrub_url_credentials
from agent_reach.utils.url import normalize_public_http_url


def _write_config(home, text):
    path = home / ".agent-reach" / "config.yaml"
    path.parent.mkdir(mode=0o700, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return path


def test_broken_yaml_is_a_clean_error_without_the_secret_line(isolated_home, capsys):
    _write_config(isolated_home, 'proxy: "http://u:SECRETPW@h\n')

    with pytest.raises(ConfigError) as exc:
        Config()
    assert "SECRETPW" not in str(exc.value)

    with patch("sys.argv", ["agent-reach", "doctor"]), pytest.raises(SystemExit) as code:
        cli.main()
    captured = capsys.readouterr()
    assert code.value.code == 1
    assert "SECRETPW" not in captured.out + captured.err
    assert "Traceback" not in captured.err


def test_blank_config_value_falls_back_to_env(isolated_home, monkeypatch):
    _write_config(isolated_home, "tavily_api_key:\ngithub_token: ''\n")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-env")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-env")

    config = Config()
    assert config.get("tavily_api_key") == "tvly-env"
    assert config.get("github_token") == "ghp-env"


@pytest.mark.parametrize(
    "text, secret",
    [
        ("http://user:p@ss@1.2.3.4/x", "ss@1.2.3.4"),
        ("https://a/b?refresh_token=ABC", "ABC"),
        ("https://a/b?x=1&client_secret=DEF", "DEF"),
        ("https://s3/o?X-Amz-Signature=SIG123", "SIG123"),
    ],
)
def test_scrub_hides_common_credentials(text, secret):
    assert secret not in scrub_url_credentials(text)


def test_scrub_keeps_plain_urls():
    url = "https://github.com/Panniantong/Agent-Reach?tab=readme"
    assert scrub_url_credentials(url) == url


def test_unicode_url_is_sent_as_ascii():
    url = normalize_public_http_url("https://zh.wikipedia.org/wiki/北京")
    assert url == "https://zh.wikipedia.org/wiki/%E5%8C%97%E4%BA%AC"
    assert normalize_public_http_url("https://例子.测试/a%20b?q=1") == (
        "https://xn--fsqu00a.xn--0zwm56d/a%20b?q=1"
    )


def test_fullwidth_lookalike_host_is_still_blocked():
    with pytest.raises(ValueError):
        normalize_public_http_url("http://metadata.google.ｉｎｔｅｒｎａｌ/")


def _fake_xhs_run(login_output):
    def run(cmd, *args, **kwargs):
        if "ps" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "xiaohongshu-mcp\n", "")
        if "printenv" in cmd:
            return subprocess.CompletedProcess(cmd, 1, "", "")
        if any("check_login_status" in str(part) for part in cmd):
            return subprocess.CompletedProcess(cmd, 0, login_output, "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    return run


@pytest.mark.parametrize(
    "login_output, verified",
    [("Not logged in. Please scan QR code.", False), ("未登录", False), ("已登录", True)],
)
def test_xhs_login_check_does_not_trust_not_logged_in(login_output, verified, capsys):
    with patch("shutil.which", return_value="/usr/bin/tool"), patch(
        "subprocess.run", side_effect=_fake_xhs_run(login_output)
    ), patch("time.sleep"):
        cli._configure_xhs_cookies("a1=x; web_session=y")
    assert ("Login verified" in capsys.readouterr().out) is verified


@pytest.mark.parametrize(
    "body", [ValueError("not json"), {"tag_name": None}, ["not", "a", "dict"]]
)
def test_check_update_survives_odd_github_bodies(body, capsys):
    resp = SimpleNamespace(status_code=200)
    if isinstance(body, Exception):
        resp.json = lambda: (_ for _ in ()).throw(body)
    else:
        resp.json = lambda: body
    with patch.object(cli, "_github_get_with_retry", return_value=(resp, None, 1)):
        result = cli._cmd_check_update()
    assert result in {"error", "up_to_date"}


def test_check_update_failure_exits_nonzero():
    with patch.object(cli, "_cmd_check_update", return_value="error"), patch(
        "sys.argv", ["agent-reach", "check-update"]
    ), pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1


def test_skill_language_follows_first_set_locale(isolated_home, monkeypatch):
    (isolated_home / ".agents" / "skills").mkdir(parents=True)
    monkeypatch.setenv("AGENT_REACH_LANG", "zh_CN")
    monkeypatch.setenv("LANG", "en_US.UTF-8")

    cli._install_skill()

    installed = isolated_home / ".agents" / "skills" / "agent-reach" / "SKILL.md"
    source = cli.Path(cli.__file__).parent / "skill" / "SKILL.md"
    assert installed.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_skill_install_reports_unusable_agents_dir(isolated_home, capsys):
    (isolated_home / ".agents").mkdir()
    (isolated_home / ".agents" / "skills").write_text("", encoding="utf-8")

    assert cli._install_skill() is False
    assert "Could not create" in capsys.readouterr().out
