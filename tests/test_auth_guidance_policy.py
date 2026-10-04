"""Documentation must preserve the project's explicit auth boundaries."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _policy_documents() -> list[Path]:
    documents = list(ROOT.glob("README*.md"))
    for directory in (
        ROOT / "docs",
        ROOT / "agent_reach" / "guides",
        ROOT / "agent_reach" / "skill",
    ):
        documents.extend(directory.rglob("*.md"))
    return sorted(set(documents))


def test_xiaohongshu_guidance_never_starts_implicit_login():
    """Do not reintroduce QR or automatic browser-cookie login guidance."""
    xhs_markers = ("xiaohongshu", "小红书", "小紅書", "xhs")
    legacy_auth_markers = (
        "扫码",
        "二维码",
        "qr login",
        "qr scan",
        "qrcode",
        "ブラウザからcookieを自動抽出",
        "브라우저에서 cookie 자동 추출",
    )
    forbidden_commands = (
        "xhs " + "login",
        "get_login_" + "qrcode",
    )

    violations = []
    for path in _policy_documents():
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for command in forbidden_commands:
            if command in lowered:
                violations.append(f"{path.relative_to(ROOT)}: {command}")
        for line_number, line in enumerate(lowered.splitlines(), 1):
            if not any(marker in line for marker in xhs_markers):
                continue
            if any(marker in line for marker in legacy_auth_markers):
                violations.append(
                    f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}"
                )

    assert not violations, "\n".join(violations)


def test_xiaohongshu_opencli_and_export_boundaries_are_truthful():
    """Cookie import is for MCP/legacy tools, never OpenCLI or Chrome."""
    boundary_docs = (
        ROOT / "docs" / "install.md",
        ROOT / "agent_reach" / "guides" / "setup-xiaohongshu.md",
        ROOT / "agent_reach" / "skill" / "references" / "social.md",
    )
    for path in boundary_docs:
        text = path.read_text(encoding="utf-8")
        assert "已经存在且明确控制" in text, path.relative_to(ROOT)
        assert "不会把 Cookie 注入 OpenCLI" in text, path.relative_to(ROOT)

    xhs_guide = boundary_docs[1].read_text(encoding="utf-8")
    assert "xiaohongshu.com 同域 Cookie 集" in xhs_guide
    assert "非 xiaohongshu.com 域 Cookie" in xhs_guide


def test_twitter_operational_docs_explain_the_environment_boundary():
    """Saved cookies help doctor only; direct twitter commands need env vars."""
    # Landing pages may stay concise; operational documents must preserve the
    # environment boundary wherever users actually configure or invoke Twitter.
    operational_docs = (
        ROOT / "docs" / "cookie-export.md",
        ROOT / "docs" / "install.md",
        ROOT / "docs" / "troubleshooting.md",
        ROOT / "agent_reach" / "guides" / "setup-twitter.md",
        ROOT / "agent_reach" / "skill" / "SKILL.md",
        ROOT / "agent_reach" / "skill" / "SKILL_en.md",
        ROOT / "agent_reach" / "skill" / "references" / "social.md",
    )

    for path in operational_docs:
        text = path.read_text(encoding="utf-8")
        assert "TWITTER_AUTH_TOKEN" in text, path.relative_to(ROOT)
        assert "TWITTER_CT0" in text, path.relative_to(ROOT)

    twitter_guide = (
        ROOT / "agent_reach" / "guides" / "setup-twitter.md"
    ).read_text(encoding="utf-8")
    assert "不会执行 `twitter status`" in twitter_guide
    assert "不会修改当前 Shell" in twitter_guide
    assert "Export → Header String" in twitter_guide
    assert "cookie JSON" not in twitter_guide
    assert "复制全部" not in twitter_guide

    for expected in (
        "--sync-legacy-twitter",
        "~/.agent-reach/config.yaml",
        "~/.config/xfetch/session.json",
        "~/.config/bird/credentials.env",
    ):
        assert expected in twitter_guide
    assert "默认只写" in twitter_guide
    assert "不会自动删除" in twitter_guide

    rendered_as_verified = (
        "✅ Twitter/X tweets",
        "✅ Twitter/Xツイート",
        "✅ Twitter/X 트윗",
    )
    all_text = "\n".join(
        path.read_text(encoding="utf-8") for path in _policy_documents()
    )
    assert not any(claim in all_text for claim in rendered_as_verified)


def test_readmes_keep_current_bilibili_and_xhs_routes():
    """READMEs must not revive retired yt-dlp/Bilibili or XHS defaults."""
    overview_docs = (
        ROOT / "README.md",
        ROOT / "docs" / "README_en.md",
    )

    for path in overview_docs:
        text = path.read_text(encoding="utf-8")
        assert "bilibili.py     → yt-dlp" not in text, path.relative_to(ROOT)
        assert "YouTube + Bilibili" not in text, path.relative_to(ROOT)


def test_readmes_do_not_advertise_retired_channels():
    """READMEs must match the channels shipped by the CLI."""
    for path in (ROOT / "README.md", ROOT / "docs" / "README_en.md"):
        text = path.read_text(encoding="utf-8").lower()
        assert "douyin" not in text, path.relative_to(ROOT)
        assert "weibo" not in text, path.relative_to(ROOT)


def test_public_guidance_never_installs_the_unrelated_pypi_package():
    """The PyPI name is owned by another project; GitHub URLs are required."""
    candidates = _policy_documents() + [
        ROOT / "agent_reach" / "integrations" / "mcp_server.py",
    ]
    bare_install = re.compile(
        r"\bpip\s+install(?:\s+--upgrade)?\s+['\"]?agent-reach(?:\[[^\]]+\])?\b",
        re.IGNORECASE,
    )
    violations = []
    for path in candidates:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if bare_install.search(line) and (
                "github.com/Panniantong/agent-reach" not in line
            ):
                violations.append(
                    f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}"
                )

    assert not violations, "\n".join(violations)


def test_public_guidance_never_puts_secrets_in_process_arguments():
    """Operational docs should use hidden prompts or stdin for credentials."""
    forbidden = (
        'agent-reach configure twitter-cookies "',
        "agent-reach configure twitter-cookies '",
        'agent-reach configure xhs-cookies "',
        "agent-reach configure xhs-cookies '",
        "agent-reach configure groq-key gsk_",
        "agent-reach configure openai-key sk-",
        "agent-reach configure github-token gh",
        "agent-reach configure proxy http",
    )
    violations = []
    for path in _policy_documents():
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in text:
                violations.append(f"{path.relative_to(ROOT)}: {marker}")

    assert not violations, "\n".join(violations)


def test_skill_explains_unverified_backend_state():
    """A null backend is an explicit safety state, not a routing instruction."""
    skills = (
        ROOT / "agent_reach" / "skill" / "SKILL.md",
        ROOT / "agent_reach" / "skill" / "SKILL_en.md",
    )
    for path in skills:
        text = path.read_text(encoding="utf-8")
        assert "active_backend: null" in text, path.relative_to(ROOT)
        assert "Doctor" in text, path.relative_to(ROOT)


def test_video_reference_has_content_level_youtube_fallbacks():
    """Version-only health must not be presented as proof subtitles work."""
    text = (
        ROOT / "agent_reach" / "skill" / "references" / "video.md"
    ).read_text(encoding="utf-8")
    assert "opencli youtube transcript" in text
    assert "最多重试 3 次" in text
    assert "agent-reach transcribe" in text


def test_youtube_subtitle_commands_prefer_original_language_tracks():
    """Plain --write-auto-sub returns machine translations; -orig is the original."""
    skill_dir = ROOT / "agent_reach" / "skill"
    for path in (
        skill_dir / "references" / "video.md",
        skill_dir / "SKILL.md",
        skill_dir / "SKILL_en.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert '--sub-langs ".*-orig' in text, path.relative_to(ROOT)


def test_update_guide_says_doctor_does_not_install_skills():
    """Doctor is read-only; only `skill --install` writes skill files."""
    text = (ROOT / "docs" / "update.md").read_text(encoding="utf-8")
    assert "makes sure an Agent Reach skill" not in text
    assert "`agent-reach doctor` is read-only" in text
    assert "agent-reach skill --install" in text


def test_install_guide_directory_table_matches_real_layout():
    """Config is YAML and skill install writes SKILL.md plus references/."""
    text = (ROOT / "docs" / "install.md").read_text(encoding="utf-8")
    assert "~/.agent-reach/config.json" not in text
    assert "~/.agent-reach/config.yaml" in text
    assert "~/.agents/skills/agent-reach/" in text
    assert "`references/*.md`" in text


def test_security_policy_routes_reports_to_the_fork():
    """The fork must not send reporters only to the upstream advisory form."""
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "https://github.com/hbui290/Agent-Reach/security/advisories/new" in text
    assert "Panniantong/Agent-Reach/security/advisories" not in text
    primary = text.split("## Reporting a Vulnerability", 1)[1].split("##", 1)[0]
    assert primary.index("hbui290/Agent-Reach") < primary.index(
        "Panniantong/Agent-Reach"
    )


def test_cli_lookup_guidance_has_no_author_specific_conda_step():
    """`conda run -n dl` is the upstream author's private environment."""
    skill_dir = ROOT / "agent_reach" / "skill"
    for path in (skill_dir / "SKILL.md", skill_dir / "SKILL_en.md", ROOT / "README.md"):
        text = path.read_text(encoding="utf-8")
        assert "conda run -n dl" not in text, path.relative_to(ROOT)
    assert "→ conda" not in (ROOT / "README.md").read_text(encoding="utf-8")


def test_social_reference_documents_xhs_download_and_instagram_limits():
    """XHS media download is routed; Instagram limits describe current failures."""
    text = (
        ROOT / "agent_reach" / "skill" / "references" / "social.md"
    ).read_text(encoding="utf-8")
    assert 'opencli xiaohongshu download "NOTE_URL" --output' in text

    instagram = text.split("## Instagram", 1)[1]
    assert "Unexpected token '<'" in instagram
    assert "不要循环重试" in instagram
    assert "HTTP 400" not in instagram


def test_video_reference_describes_current_polish_model():
    """The polish docs must match the script's model, not the removed Llama."""
    reference = (
        ROOT / "agent_reach" / "skill" / "references" / "video.md"
    ).read_text(encoding="utf-8")
    script = (
        ROOT / "agent_reach" / "scripts" / "transcribe_xiaoyuzhou.sh"
    ).read_text(encoding="utf-8")
    assert "Llama" not in reference
    assert "Groq 上免费" not in reference
    assert "POLISH_MODEL" in reference
    assert "qwen/qwen3.8-27b" in reference
    assert "qwen/qwen3.8-27b" in script


def test_skill_routes_finance_and_documents_opencli_discovery():
    skills = (
        ROOT / "agent_reach" / "skill" / "SKILL.md",
        ROOT / "agent_reach" / "skill" / "SKILL_en.md",
    )
    for path in skills:
        text = path.read_text(encoding="utf-8")
        assert "references/finance.md" in text, path.relative_to(ROOT)
        assert "opencli list" in text, path.relative_to(ROOT)
        assert "--help" in text, path.relative_to(ROOT)

    finance = ROOT / "agent_reach" / "skill" / "references" / "finance.md"
    text = finance.read_text(encoding="utf-8")
    assert "opencli xueqiu stock" in text
    assert "agent-reach configure --from-browser chrome --platform xueqiu" in text
