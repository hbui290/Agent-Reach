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


# ── round 3: transcribe, remaining CLI, OpenCLI, MCP ──


def test_watch_flags_unparseable_update_response(capsys):
    from agent_reach.config import Config as _Config

    resp = SimpleNamespace(status_code=200)
    resp.json = lambda: (_ for _ in ()).throw(ValueError("html"))
    ok = {"web": {"status": "ok", "name": "Web", "message": "", "tier": 0}}
    with patch("agent_reach.doctor.check_all", return_value=ok), patch.object(
        cli, "_github_get_with_retry", return_value=(resp, None, 1)
    ), patch.object(_Config, "get", return_value=None):
        cli._cmd_watch()
    out = capsys.readouterr().out
    assert "无法检查更新" in out
    assert "已是最新" not in out


@pytest.mark.parametrize(
    "remote, local, newer",
    [
        ("1.5.0-rc1", "1.5.0", False),
        ("1.4.0-hotfix", "1.5.0", False),
        ("1.10.0", "1.9.0", True),
        ("1.6.0-rc1", "1.5.0", True),
        ("1.5", "1.5.0", False),
    ],
)
def test_version_compare_handles_suffixes(remote, local, newer):
    assert cli._is_newer_version(remote, local) is newer


def test_non_ascii_github_token_falls_back_to_anonymous():
    config = SimpleNamespace(get=lambda key: "ghp_tök\u200b")
    assert cli._github_auth_headers(config) is None


def test_setup_prompt_treats_eof_as_skip():
    getpass = SimpleNamespace(getpass=lambda _label: (_ for _ in ()).throw(EOFError()))
    assert cli._setup_prompt(getpass, "KEY: ") == ""


@pytest.mark.parametrize("item", [{"note_card": "x"}, {"note": ["a"]}])
def test_format_xhs_tolerates_odd_nesting(item):
    from agent_reach.channels.xiaohongshu import _clean_note

    assert isinstance(_clean_note(item), dict)


def test_transcribe_invalid_key_is_not_echoed(tmp_path, monkeypatch):
    from agent_reach import transcribe as tr

    cfg = Config(config_path=tmp_path / "c.yaml")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_SUPER\nSECRET")
    chunk = tmp_path / "chunk.m4a"
    chunk.write_bytes(b"x")
    with pytest.raises(tr.TranscribeError) as exc:
        tr.transcribe_chunk(chunk, "groq", config=cfg)
    assert "SECRET" not in str(exc.value)


def test_transcribe_key_whitespace_is_stripped(tmp_path, monkeypatch):
    from agent_reach import transcribe as tr

    monkeypatch.setenv("GROQ_API_KEY", "gsk_abc\r\n")
    assert tr._provider_key("groq", Config(config_path=tmp_path / "c.yaml")) == "gsk_abc"


def test_transcribe_decodes_utf8_without_charset(tmp_path, monkeypatch):
    from agent_reach import transcribe as tr

    monkeypatch.setenv("GROQ_API_KEY", "gsk_abc")
    body = "Xin chào thế giới 你好"
    resp = SimpleNamespace(
        ok=True, status_code=200, content=body.encode("utf-8"),
        text=body.encode("utf-8").decode("latin-1"),
    )
    monkeypatch.setattr(tr.requests, "post", lambda *a, **k: resp)
    chunk = tmp_path / "chunk.m4a"
    chunk.write_bytes(b"x")
    assert tr.transcribe_chunk(chunk, "groq", config=Config(config_path=tmp_path / "c.yaml")) == body


def test_chunk_audio_ignores_chunks_from_an_earlier_run(tmp_path, monkeypatch):
    from agent_reach import transcribe as tr

    (tmp_path / "chunk_002.m4a").write_bytes(b"stale")

    def fake_run(cmd, *args, **kwargs):
        for i in range(2):
            (tmp_path / f"chunk_{i:03d}.m4a").write_bytes(b"new")

    monkeypatch.setattr(tr, "_require", lambda _name: None)
    monkeypatch.setattr(tr, "_run", fake_run)
    chunks = tr.chunk_audio(tmp_path / "src.m4a", tmp_path)
    assert [c.name for c in chunks] == ["chunk_000.m4a", "chunk_001.m4a"]


@pytest.mark.parametrize(
    "source", ["/Users/me/podcast.mp3", "C:\\Users\\me\\a.mp3", "./a.wav", "episode.mp3"]
)
def test_missing_local_file_is_reported_as_such(tmp_path, source):
    from agent_reach import transcribe as tr

    with pytest.raises(tr.TranscribeError, match="local file not found"):
        tr._transcribe_in_dir(source, ["groq"], Config(config_path=tmp_path / "c.yaml"), tmp_path)


@pytest.mark.parametrize("source", ["youtu.be/abc", "https://example.com/a.mp3"])
def test_scheme_less_urls_are_not_mistaken_for_paths(source):
    from agent_reach import transcribe as tr

    assert tr._looks_like_local_path(source) is False


def _opencli_probe(status, output="", hint=""):
    from agent_reach.probe import ProbeResult

    return ProbeResult(status=status, output=output, hint=hint)


def test_opencli_version_ignores_node_warnings():
    from agent_reach.backends import opencli

    probe = _opencli_probe("ok", "1.8.8\n(node:42) ExperimentalWarning: x")
    with patch.object(opencli, "probe_command", return_value=probe), patch.object(
        opencli, "_fetch_daemon_status", return_value=None
    ):
        assert opencli.opencli_status().version == "1.8.8"


def test_opencli_timeout_is_not_called_a_broken_node():
    from agent_reach.backends import opencli

    probe = _opencli_probe("timeout", hint="timed out after 10s")
    with patch.object(opencli, "probe_command", return_value=probe):
        st = opencli.opencli_status()
    assert "node 环境损坏" not in st.hint
    assert "timeout" in st.hint
