# -*- coding: utf-8 -*-

import os
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import agent_reach.cli as cli

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIBE_SCRIPT = ROOT / "agent_reach" / "scripts" / "transcribe_xiaoyuzhou.sh"


class _DummyConfig:
    def get(self, _key):
        return None


def test_install_xiaoyuzhou_deps_does_not_raise_when_no_groq_key(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(
        cli.os.path,
        "expanduser",
        lambda value: value.replace("~", str(tmp_path)),
    )
    with patch("agent_reach.config.Config", return_value=_DummyConfig()), patch(
        "shutil.which", return_value=None
    ):
        cli._install_xiaoyuzhou_deps()

    out = capsys.readouterr().out
    assert "Xiaoyuzhou" in out
    assert "Groq API key not set" in out


def test_install_xiaoyuzhou_deps_replaces_stale_managed_script(
    monkeypatch, tmp_path, capsys
):
    import stat

    installed = tmp_path / ".agent-reach" / "tools" / "xiaoyuzhou" / "transcribe.sh"
    installed.parent.mkdir(parents=True)
    installed.write_text("#!/bin/sh\necho stale\n", encoding="utf-8")

    monkeypatch.setattr(
        cli.os.path,
        "expanduser",
        lambda value: value.replace("~", str(tmp_path)),
    )
    monkeypatch.setattr("agent_reach.config.Config", lambda: _DummyConfig())
    monkeypatch.setattr("shutil.which", lambda _name: None)

    cli._install_xiaoyuzhou_deps()

    assert installed.read_text(encoding="utf-8") == TRANSCRIBE_SCRIPT.read_text(
        encoding="utf-8"
    )
    if os.name != "nt":
        assert installed.stat().st_mode & stat.S_IXUSR
    assert "script updated" in capsys.readouterr().out


def test_transcribe_script_is_cross_platform_shell_syntax(bash_executable):
    subprocess.run(
        [bash_executable, "-n", TRANSCRIBE_SCRIPT.relative_to(ROOT).as_posix()],
        check=True,
        cwd=ROOT,
    )


def test_transcribe_script_handles_git_bash_python_and_size_math():
    text = TRANSCRIBE_SCRIPT.read_text(encoding="utf-8")
    assert "command -v python3" in text
    assert "command -v python" in text
    assert "command -v py" in text
    assert "cygpath -w" in text
    assert "| bc" not in text


def _bash_path(path: Path) -> str:
    """Render a native path for a Bash process, including Git Bash on Windows."""
    rendered = path.resolve().as_posix()
    if os.name == "nt" and len(rendered) >= 3 and rendered[1:3] == ":/":
        return f"/{rendered[0].lower()}{rendered[2:]}"
    return rendered


def _append_bash_function(path: Path, name: str, script: str) -> None:
    lines = script.splitlines()
    if lines and lines[0].startswith("#!"):
        lines = lines[1:]
    body = "\n".join(lines)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{name}() {{\n{body}\n}}\n")


def _script_env(
    tmp_path: Path, curl_script: str
) -> tuple[dict[str, str], Path, Path, Path]:
    curl_log = tmp_path / "curl.log"
    temp_root = tmp_path / "tmp"
    temp_root.mkdir()
    bash_env = tmp_path / "bash-env.sh"
    _append_bash_function(bash_env, "curl", curl_script)

    env = os.environ.copy()
    env.update({
        "BASH_ENV": _bash_path(bash_env),
        "CURL_LOG": _bash_path(curl_log),
        "GROQ_API_KEY": "test-key",
        "TMPDIR": _bash_path(temp_root),
    })
    return env, curl_log, temp_root, bash_env


def _assert_work_dir_cleaned(temp_root: Path) -> None:
    assert list(temp_root.glob("agent-reach-xiaoyuzhou.*")) == []


@pytest.mark.parametrize(
    "url",
    [
        "ftp://xiaoyuzhoufm.com/episode/123",
        "https://notxiaoyuzhoufm.com/episode/123",
        "https://xiaoyuzhoufm.com.evil.example/episode/123",
        "https://evil.example/episode/123?next=xiaoyuzhoufm.com",
    ],
)
def test_transcribe_script_rejects_non_xiaoyuzhou_urls_before_curl(
    tmp_path, url, bash_executable
):
    env, curl_log, temp_root, _ = _script_env(
        tmp_path,
        "#!/bin/sh\nprintf 'called\\n' >> \"$CURL_LOG\"\nexit 42\n",
    )

    result = subprocess.run(
        [
            bash_executable,
            TRANSCRIBE_SCRIPT.relative_to(ROOT).as_posix(),
            url,
            _bash_path(tmp_path / "out.txt"),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=ROOT,
    )

    assert result.returncode != 0
    assert "仅支持 xiaoyuzhoufm.com" in result.stderr
    assert not curl_log.exists()
    _assert_work_dir_cleaned(temp_root)


@pytest.mark.parametrize(
    "url",
    [
        "http://xiaoyuzhoufm.com/episode/123",
        "https://www.xiaoyuzhoufm.com/episode/123",
    ],
)
def test_transcribe_script_accepts_http_xiaoyuzhou_hosts(
    tmp_path, url, bash_executable
):
    env, curl_log, temp_root, _ = _script_env(
        tmp_path,
        "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$CURL_LOG\"\nexit 42\n",
    )

    result = subprocess.run(
        [
            bash_executable,
            TRANSCRIBE_SCRIPT.relative_to(ROOT).as_posix(),
            url,
            _bash_path(tmp_path / "out.txt"),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=ROOT,
    )

    assert result.returncode != 0
    assert curl_log.exists()
    _assert_work_dir_cleaned(temp_root)


def test_transcribe_script_uses_secure_temp_and_bounded_curl_calls():
    text = TRANSCRIBE_SCRIPT.read_text(encoding="utf-8")

    assert "mktemp -d" in text
    assert "xiaoyuzhou_$$" not in text
    assert "/tmp/podcast_transcript.txt" not in text
    assert 'mktemp "${TEMP_ROOT%/}/agent-reach-transcript.XXXXXX"' in text
    assert "trap cleanup EXIT" in text
    assert text.count('--connect-timeout "$CURL_CONNECT_TIMEOUT"') == 4
    assert text.count('--max-time "$GROQ_TIMEOUT"') == 2
    assert text.count("--fail --show-error --location") == 2
    assert text.count("--max-filesize") == 4
    assert text.count('--max-filesize "$MAX_API_RESPONSE_BYTES"') == 2
    assert "MAX_DURATION_SECONDS=10800" in text
    assert '-t "$MAX_DURATION_SECONDS"' in text
    assert 'if [ "$WAIT_SEC" -gt 900 ]' in text
    assert "r.read(32 * 1024 * 1024 + 1)" in text

    page_limit = int(re.search(r"^MAX_PAGE_BYTES=(\d+)$", text, re.MULTILINE).group(1))
    audio_limit = int(re.search(r"^MAX_AUDIO_BYTES=(\d+)$", text, re.MULTILINE).group(1))
    api_response_limit = int(
        re.search(r"^MAX_API_RESPONSE_BYTES=(\d+)$", text, re.MULTILINE).group(1)
    )
    assert page_limit <= 10 * 1024 * 1024
    assert 25 * 1024 * 1024 <= audio_limit <= 2 * 1024 * 1024 * 1024
    assert api_response_limit <= 32 * 1024 * 1024


def test_transcribe_script_skips_store_python_stub(tmp_path, bash_executable):
    """A python3 that exists but cannot run (Windows Store stub) is skipped."""
    env, curl_log, temp_root, bash_env = _script_env(
        tmp_path,
        "#!/bin/sh\nprintf 'called\\n' >> \"$CURL_LOG\"\nexit 42\n",
    )
    real_python = sys.executable.replace("\\", "/")
    _append_bash_function(bash_env, "python3", "#!/bin/sh\nreturn 9009\n")
    _append_bash_function(bash_env, "python", f'#!/bin/sh\n"{real_python}" "$@"\n')

    result = subprocess.run(
        [
            bash_executable,
            TRANSCRIBE_SCRIPT.relative_to(ROOT).as_posix(),
            "https://www.xiaoyuzhoufm.com/episode/123",
            _bash_path(tmp_path / "out.txt"),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=ROOT,
    )

    assert "未找到 Python" not in result.stderr
    assert "仅支持 xiaoyuzhoufm.com" not in result.stderr
    assert curl_log.exists()
    _assert_work_dir_cleaned(temp_root)


@pytest.mark.parametrize("stored", ["gsk_plain", "'gsk_quoted'"])
def test_transcribe_script_reads_config_key_without_pyyaml(
    tmp_path, stored, bash_executable
):
    env, curl_log, temp_root, _ = _script_env(
        tmp_path,
        "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$CURL_LOG\"\nexit 42\n",
    )
    del env["GROQ_API_KEY"]
    home = tmp_path / "home"
    (home / ".agent-reach").mkdir(parents=True)
    (home / ".agent-reach" / "config.yaml").write_text(
        f"groq_api_key: {stored}\n", encoding="utf-8"
    )
    # Make `import yaml` fail, like a system Python without PyYAML.
    no_yaml = tmp_path / "no-yaml"
    no_yaml.mkdir()
    (no_yaml / "yaml.py").write_text("raise ImportError('no yaml')\n", encoding="utf-8")
    env["HOME"] = _bash_path(home)
    env["PYTHONPATH"] = str(no_yaml)

    result = subprocess.run(
        [
            bash_executable,
            TRANSCRIBE_SCRIPT.relative_to(ROOT).as_posix(),
            "https://www.xiaoyuzhoufm.com/episode/123",
            _bash_path(tmp_path / "out.txt"),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=ROOT,
    )

    assert "GROQ_API_KEY" not in result.stderr
    assert curl_log.exists()
    _assert_work_dir_cleaned(temp_root)


def _script_snippet(start, end):
    text = TRANSCRIBE_SCRIPT.read_text(encoding="utf-8")
    begin = text.index(start)
    return text[begin : text.index(end, begin) + len(end)]


def test_transcribe_script_key_fallback_drops_trailing_comment(tmp_path):
    reader = _script_snippet("import os\nimport re\n", "                break\n")
    config = tmp_path / "config.yaml"
    config.write_text(
        "groq_api_key: gsk_abc  # personal key\n", encoding="utf-8"
    )
    no_yaml = tmp_path / "no-yaml"
    no_yaml.mkdir()
    (no_yaml / "yaml.py").write_text("raise ImportError('no yaml')\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-c", reader],
        capture_output=True,
        encoding="utf-8",
        env={
            **os.environ,
            "AGENT_REACH_CONFIG_FILE": str(config),
            "PYTHONPATH": str(no_yaml),
        },
    )

    assert result.stdout.strip() == "gsk_abc"


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_transcribe_script_output_swap_keeps_private_mode(tmp_path, bash_executable):
    block = _script_snippet('PARTIAL="$OUTPUT.partial.$$"', "    exit 1\nfi\n")
    output = tmp_path / "agent-reach-transcript.abc"
    output.write_text("", encoding="utf-8")
    output.chmod(0o600)
    final = tmp_path / "final.txt"
    final.write_text("transcript\n", encoding="utf-8")

    subprocess.run(
        [bash_executable, "-c", f"umask 022\nOUTPUT='{output}'\nFINAL='{final}'\n{block}"],
        check=True,
    )

    assert output.read_text(encoding="utf-8") == "transcript\n"
    assert output.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("ffprobe_output", ["", "not-a-number"])
def test_transcribe_script_fails_clearly_for_invalid_duration(
    tmp_path, ffprobe_output, bash_executable
):
    env, _, temp_root, bash_env = _script_env(
        tmp_path,
        """#!/bin/bash
output=""
while [ "$#" -gt 0 ]; do
    if [ "$1" = "-o" ]; then
        output="$2"
        shift 2
    else
        shift
    fi
done
if [ -n "$output" ]; then
    printf 'fake audio' > "$output"
else
    printf '%s' '<html><script>"title":"Test"</script>https://media.xyzcdn.net/test.mp3</html>'
fi
""",
    )
    _append_bash_function(
        bash_env,
        "ffprobe",
        "#!/bin/sh\nprintf '%s' \"$FFPROBE_OUTPUT\"\n",
    )
    env["FFPROBE_OUTPUT"] = ffprobe_output

    result = subprocess.run(
        [
            bash_executable,
            TRANSCRIBE_SCRIPT.relative_to(ROOT).as_posix(),
            "https://www.xiaoyuzhoufm.com/episode/123",
            _bash_path(tmp_path / "out.txt"),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=ROOT,
    )

    assert result.returncode != 0
    assert "ffprobe 返回无效音频时长" in result.stderr
    _assert_work_dir_cleaned(temp_root)


@pytest.mark.parametrize("ffprobe_output", ["10801", "9" * 500])
def test_transcribe_script_rejects_overlong_audio_before_ffmpeg_or_groq(
    tmp_path, ffprobe_output, bash_executable
):
    env, curl_log, temp_root, bash_env = _script_env(
        tmp_path,
        """#!/bin/bash
printf '%s\n' "$*" >> "$CURL_LOG"
output=""
while [ "$#" -gt 0 ]; do
    if [ "$1" = "-o" ]; then
        output="$2"
        shift 2
    else
        shift
    fi
done
if [ -n "$output" ]; then
    printf 'fake audio' > "$output"
else
    printf '%s' '<html><script>"title":"Test"</script>https://media.xyzcdn.net/test.mp3</html>'
fi
""",
    )
    ffmpeg_marker = tmp_path / "ffmpeg-called"
    _append_bash_function(
        bash_env,
        "ffprobe",
        "#!/bin/sh\nprintf '%s' \"$FFPROBE_OUTPUT\"\n",
    )
    _append_bash_function(
        bash_env,
        "ffmpeg",
        "#!/bin/sh\nprintf 'called' > \"$FFMPEG_MARKER\"\n",
    )
    env["FFMPEG_MARKER"] = _bash_path(ffmpeg_marker)
    env["FFPROBE_OUTPUT"] = ffprobe_output

    result = subprocess.run(
        [
            bash_executable,
            TRANSCRIBE_SCRIPT.relative_to(ROOT).as_posix(),
            "https://www.xiaoyuzhoufm.com/episode/123",
            _bash_path(tmp_path / "out.txt"),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=ROOT,
    )

    assert result.returncode != 0
    assert "音频时长超过 3 小时限制" in result.stderr
    assert not ffmpeg_marker.exists()
    curl_calls = curl_log.read_text(encoding="utf-8").splitlines()
    assert len(curl_calls) == 2
    assert all("api.groq.com" not in call for call in curl_calls)
    _assert_work_dir_cleaned(temp_root)


def test_transcribe_script_polish_uses_configurable_current_model():
    text = TRANSCRIBE_SCRIPT.read_text(encoding="utf-8")

    assert "llama-3.3" not in text
    assert "Llama 3.3" not in text
    assert "POLISH_MODEL" in text
    assert "qwen/qwen3.8-27b" in text
    assert "reasoning_effort" in text


def _polish_python_source() -> str:
    text = TRANSCRIBE_SCRIPT.read_text(encoding="utf-8")
    marker = 'POLISH_MODEL="${POLISH_MODEL:-}"'
    start = text.index("<<'PY'", text.index(marker)) + len("<<'PY'\n")
    return text[start : text.index("\nPY\n", start) + 1]


def _run_polish_python(tmp_path, monkeypatch, capsys, urlopen, polish_model=None):
    import io
    import json
    import urllib.request

    in_file = tmp_path / "in.txt"
    out_file = tmp_path / "out.txt"
    in_file.write_text("今天天气不错我们出去玩", encoding="utf-8")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("IN_FILE", str(in_file))
    monkeypatch.setenv("OUT_FILE", str(out_file))
    if polish_model is None:
        monkeypatch.delenv("POLISH_MODEL", raising=False)
    else:
        monkeypatch.setenv("POLISH_MODEL", polish_model)
    requests = []

    def fake_urlopen(req, timeout=None):
        requests.append(json.loads(req.data))
        return urlopen(req)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("sys.stderr", io.StringIO())
    source = _polish_python_source()
    compile(source, "polish.py", "exec")
    exec(source, {"__name__": "__main__"})
    return requests, out_file.read_text(encoding="utf-8"), capsys.readouterr().out


class _FakeResponse:
    def __init__(self, content, finish_reason="stop"):
        import json

        self._payload = json.dumps(
            {"choices": [{"message": {"content": content}, "finish_reason": finish_reason}]}
        ).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _limit=None):
        return self._payload


def test_polish_python_success_uses_default_model_and_no_reasoning(
    tmp_path, monkeypatch, capsys
):
    requests, result, out = _run_polish_python(
        tmp_path,
        monkeypatch,
        capsys,
        lambda _req: _FakeResponse("今天天气不错，我们出去玩。"),
    )

    assert requests[0]["model"] == "qwen/qwen3.8-27b"
    assert requests[0]["reasoning_effort"] == "none"
    assert result == "今天天气不错，我们出去玩。\n"
    assert "✅" in out
    assert "⚠️" not in out


def test_polish_python_honors_polish_model_env(tmp_path, monkeypatch, capsys):
    requests, _result, _out = _run_polish_python(
        tmp_path,
        monkeypatch,
        capsys,
        lambda _req: _FakeResponse("今天天气不错，我们出去玩。"),
        polish_model="custom/model",
    )

    assert requests[0]["model"] == "custom/model"
    assert "reasoning_effort" not in requests[0]


def test_polish_python_sends_reasoning_effort_only_for_qwen_models(
    tmp_path, monkeypatch, capsys
):
    requests, _result, _out = _run_polish_python(
        tmp_path,
        monkeypatch,
        capsys,
        lambda _req: _FakeResponse("今天天气不错，我们出去玩。"),
        polish_model="qwen/qwen3-32b",
    )

    assert requests[0]["reasoning_effort"] == "none"


def test_polish_python_partial_failure_reports_partial(tmp_path, monkeypatch, capsys):
    import io
    import urllib.error

    calls = []

    def urlopen(req):
        calls.append(req)
        if len(calls) == 1:
            return _FakeResponse("被截断", finish_reason="length")
        if len(calls) == 2:
            return _FakeResponse("今天天气不，")
        raise urllib.error.HTTPError(req.full_url, 500, "boom", {}, io.BytesIO(b"{}"))

    requests, result, out = _run_polish_python(tmp_path, monkeypatch, capsys, urlopen)

    assert len(requests) == 3
    assert result == "今天天气不，错我们出去玩\n"  # 左半润色，右半保留原文
    assert "⚠️ 部分润色失败" in out
    assert "HTTP 500" in out
    assert "润色失败，已保留原文" not in out
    assert "✅" not in out


def test_polish_python_http_error_keeps_raw_text_and_warns(tmp_path, monkeypatch, capsys):
    import io
    import urllib.error

    def raise_http_error(req):
        raise urllib.error.HTTPError(
            req.full_url, 404, "Not Found", {}, io.BytesIO(b'{"error":"model_not_found"}')
        )

    requests, result, out = _run_polish_python(
        tmp_path, monkeypatch, capsys, raise_http_error
    )

    assert len(requests) == 1
    assert result == "今天天气不错我们出去玩\n"
    assert "⚠️ 润色失败，已保留原文" in out
    assert "HTTP 404" in out
    assert "✅" not in out


def test_polish_python_empty_content_falls_back_without_recursion(
    tmp_path, monkeypatch, capsys
):
    requests, result, out = _run_polish_python(
        tmp_path,
        monkeypatch,
        capsys,
        lambda _req: _FakeResponse("   ", finish_reason="length"),
    )

    assert len(requests) == 1
    assert result == "今天天气不错我们出去玩\n"
    assert "⚠️ 润色失败，已保留原文" in out
    assert "✅" not in out
