<h1 align="center">👁️ Agent Reach</h1>

<p align="center">
  <strong>Give your AI agent safe, diagnosable access to the web and 13+ platforms.</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-green.svg?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://github.com/hbui290/Agent-Reach/actions/workflows/pytest.yml"><img src="https://github.com/hbui290/Agent-Reach/actions/workflows/pytest.yml/badge.svg" alt="CI"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="#what-this-fork-changes">Fork Changes</a> ·
  <a href="#search-routing">Search Routing</a> ·
  <a href="#platforms">Platforms</a> ·
  <a href="#cli-reference">CLI</a> ·
  <a href="#security">Security</a>
</p>

This is a maintained fork of [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) with Tavily-first search, stricter Doctor checks, and reliability fixes.

> **Scam warning:** Agent Reach has no token, coin, wallet connection, fee-claim program, or Solana/Pump.fun project. Anything crypto-related using this name is unaffiliated.

---

## What It Is

Agent Reach is an **installer, doctor, and config tool** for AI agents such as Claude Code, Codex, Cursor, and OpenClaw. It:

1. Installs and registers the upstream CLI, MCP, and Skill tools an agent needs to read the internet.
2. Checks which channels actually work (`agent-reach doctor`) and explains how to fix the ones that don't.
3. Stores credentials locally and ships an agent skill that tells the agent which tool to use for each task.

It is **not** a proxy or wrapper. After setup, the agent calls the upstream tools (Tavily, Exa, yt-dlp, gh, OpenCLI, …) directly.

## Quick Start

Paste this into your AI agent:

~~~text
Install the hbui290 fork of Agent Reach with
`pipx install https://github.com/hbui290/Agent-Reach/archive/refs/heads/main.zip`.
If `agent-reach` is already installed, check where it came from before replacing it.
Then run `agent-reach install --env=auto` (read-only check) and `agent-reach doctor`.
Use `--system` only after I approve the proposed system changes.
~~~

Or do it yourself:

~~~bash
pipx install https://github.com/hbui290/Agent-Reach/archive/refs/heads/main.zip
agent-reach install --env=auto     # check only, changes nothing
agent-reach configure tavily-key   # hidden prompt; recommended for web search
agent-reach doctor                 # show what works and what to fix
~~~

To update, rerun the install command with `pipx install --force …`. See the [Update Guide](docs/update.md).

<details>
<summary>OpenClaw users</summary>

Agent Reach needs shell access. If OpenClaw uses the default `messaging` profile, enable exec first:

~~~bash
openclaw config set tools.profile "coding"
openclaw gateway restart
~~~

</details>

## What This Fork Changes

Compared with upstream [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) v1.5.0:

**Search**
- Tavily is the default for general web search, news, URL extraction, site crawling, and deep research.
- Exa remains available for papers, companies, people, semantic/RAG search, and similar-page discovery, and as a fallback when Tavily is unavailable.

**Doctor**
- Verifies the Tavily key through the usage endpoint without spending a search credit, and reports remaining or exhausted quota.
- Reports Exa status alongside Tavily.
- Probes Jina Reader with a real request instead of always reporting OK.

**CLI**
- `agent-reach configure tavily-key` reads the key through a hidden prompt or `--stdin` and refuses keys passed as arguments.
- `install --env` now handles XiaoHongShu and Reddit correctly.
- Install, update, and MCP hints point to this fork.

**Reliability**
- The MCP server no longer blocks while Doctor runs.
- Restricted filesystems produce a warning instead of a crash.
- `transcribe` uses your configured YouTube browser cookies.

**Agent skill**
- Read-only tasks run directly; installs, logins, cookies, and browser actions require approval.
- Finds the CLI via PATH → venv → `~/.local/bin` → conda.
- Treats search results as untrusted data (prompt-injection defense).
- Asks before sending private URLs or audio to remote services, and reports whether video text came from captions or ASR.

No new dependencies or platform backends are added. Regression tests cover routing, quota states, malformed API responses, and secret handling.

## Search Routing

| Task | Backend |
|---|---|
| General web, news, recent events | Tavily `/search` |
| Read a URL, map or crawl a site, deep research | Tavily `/extract`, `/map`, `/crawl`, `/research` |
| Papers, academic, technical research | Exa MCP |
| Companies, people, financial reports | Exa MCP |
| Semantic search, RAG, similar pages | Exa MCP |
| Repositories, code, issues, PRs | GitHub (`gh`) |

The agent picks a backend per task. If the chosen backend fails, it switches to another configured one and reports coverage limits. A supplied URL is read directly instead of searched. Doctor checks configuration and quota only; it does not prove a search returned the right content.

Details: [Agent guide (English)](agent_reach/skill/SKILL_en.md) · [Search reference](agent_reach/skill/references/search.md) · [Tavily setup](agent_reach/guides/setup-tavily.md) · [Exa setup](agent_reach/guides/setup-exa.md)

## Platforms

| Platform | What works | Setup |
|---|---|---|
| Web, RSS | Read pages and RSS/Atom feeds | None |
| YouTube | Subtitles and metadata; ASR transcription | None; ASR needs a Groq or OpenAI key |
| Web search | Tavily search/extract/crawl/research; Exa semantic search | Tavily API key; Exa MCP via mcporter |
| GitHub | Public repos; private repos, issues, PRs | `gh auth login` for private access |
| Twitter/X | Single public tweets; search and timelines | Login cookies for search |
| Reddit | Search and read | Login required |
| Bilibili, V2EX | Bilibili videos and subtitles; V2EX posts and profiles | OpenCLI for Bilibili subtitles |
| XiaoHongShu | Notes and search | OpenCLI with your Chrome session, or manually exported cookies |
| Facebook, Instagram | Posts and profiles | OpenCLI with your Chrome session |
| LinkedIn | Profiles, jobs, posts | LinkedIn MCP login |
| Xueqiu | Quotes, market data, posts | Some features need cookies |
| Boss Zhipin | Job search | Dedicated local Chrome session |
| Xiaoyuzhou | Podcast transcription | Groq API key |

Ask your agent, for example, "Set up Twitter for me." It will explain the access required before changing anything.

Agent Reach is free. Third-party services (Tavily, Exa endpoints, Groq/OpenAI, proxies) bill according to their own plans.

## CLI Reference

| Command | Purpose |
|---|---|
| `agent-reach install [--env auto\|local\|server] [--channels …] [--system] [--dry-run]` | Check the environment; install tools only with `--system` |
| `agent-reach doctor [--json]` | Show channel status and fixes |
| `agent-reach configure <name> [--stdin]` | Save `tavily-key`, `groq-key`, `openai-key`, `github-token`, `proxy`, or cookies |
| `agent-reach configure --from-browser chrome --platform <p>` | Import cookies for one explicitly chosen platform |
| `agent-reach transcribe <url-or-file>` | Transcribe audio/video via Groq or OpenAI Whisper |
| `agent-reach skill --install` | Register the agent skill |
| `agent-reach watch` / `check-update` | Health check and upstream release check |
| `agent-reach uninstall [--dry-run] [--keep-config]` | Remove config and skill files |

`check-update` compares against upstream releases; new upstream versions reach this fork only after they are merged.

## Security

- Credentials live in `~/.agent-reach/config.yaml`, readable only by you on Unix. Secrets are entered through hidden prompts or `--stdin`, never as command arguments.
- Agent Reach never reads browser cookies or logs in on its own. Cookies grant account access, so use a dedicated account for cookie-based platforms.
- `install` is check-only by default. System changes need `--system`; preview them with `--dry-run`.
- `uninstall` removes config (tokens, cookies) and skill files. Use `--keep-config` to keep config. Third-party tools are not removed.

## Development

~~~bash
git clone https://github.com/hbui290/Agent-Reach.git && cd Agent-Reach
pip install -e '.[dev]'
pytest tests -q
ruff check agent_reach tests && mypy agent_reach
~~~

CI runs lint, type checks, tests on Python 3.10–3.13 and Windows, and a wheel build. Branch from `main`, open a PR, and keep the version identical in `pyproject.toml`, `agent_reach/__init__.py`, and `tests/test_cli.py`.

## Documentation

- [Install Guide](docs/install.md) · [Update Guide](docs/update.md) · [Troubleshooting](docs/troubleshooting.md) · [Cookie export](docs/cookie-export.md)
- [Agent Skill](agent_reach/skill/SKILL.md) · [Agent guide (English)](agent_reach/skill/SKILL_en.md) · [Social platforms](agent_reach/skill/references/social.md)

Most guides and skill references are in Chinese to stay mergeable with upstream.

## Credits

Built on the work of [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) ([Star History](https://star-history.com/#Panniantong/Agent-Reach&Date)) and the tools it installs: [OpenCLI](https://github.com/jackwener/opencli), [twitter-cli](https://github.com/public-clis/twitter-cli), [rdt-cli](https://github.com/public-clis/rdt-cli), [bili-cli](https://github.com/public-clis/bilibili-cli), [xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [Jina Reader](https://github.com/jina-ai/reader), [Tavily](https://tavily.com), [Exa](https://exa.ai), [mcporter](https://github.com/nicobailon/mcporter), [feedparser](https://github.com/kurtmckee/feedparser), and [linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server).

Upstream bugs and feature requests: [Panniantong/Agent-Reach issues](https://github.com/Panniantong/Agent-Reach/issues).

## License

[MIT](LICENSE)
