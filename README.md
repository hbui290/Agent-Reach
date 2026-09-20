<h1 align="center">👁️ Agent Reach</h1>

<p align="center">
  <strong>Install, diagnose, and maintain internet access for your AI agent</strong>
</p>

<p align="center">
  Works with Claude Code, OpenClaw, Cursor, and other agents that can run commands. Content is read through the upstream tools.
</p>

<p align="center">
  <a href="https://trendshift.io/repositories/24387"><img src="https://trendshift.io/api/badge/repositories/24387" alt="Trendshift GitHub Trending #1 Repository of the Day"></a>
  <a href="https://star-history.com/#Panniantong/Agent-Reach&Date"><img src="https://api.star-history.com/badge?repo=Panniantong/Agent-Reach" alt="Star History Rank" width="196" height="55"></a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="MIT License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-green.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://github.com/Panniantong/agent-reach/stargazers"><img src="https://img.shields.io/github/stars/Panniantong/agent-reach?style=for-the-badge" alt="GitHub Stars"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> · <a href="README_zh.md">简体中文</a> · <a href="docs/README_ja.md">日本語</a> · <a href="docs/README_ko.md">한국어</a> · <a href="#platform-capabilities">Platforms</a> · <a href="#search-routing">Search Routing</a>
</p>

> **Security notice:** Agent Reach has no official token, coin, investment product, fee-claim program, wallet connection, or Solana/Pump.fun project. Any crypto project using the Agent Reach name, repository URL, or author identity is unaffiliated. Do not connect a wallet or claim fees based on related messages or links.

---

<details>
<summary>Sponsors</summary>

| | |
|---|---|
| <img src="docs/assets/sponsors/browseract.png" width="100" alt="BrowserAct"> [BrowserAct](https://www.browseract.ai/Agent) | Collect website data in a real browser without writing scrapers; new users receive 1,000 credits. |
| <img src="docs/assets/sponsors/tencent-cloud.svg" width="100" alt="Tencent Cloud"> [Tencent Cloud Lighthouse](https://www.tencentcloud.com/act/pro/intl-openclaw?referral_code=G76Y819A&lang=en&pg=) | Deploy OpenClaw and connect it to Agent Reach. |
| <img src="docs/assets/sponsors/coreclaw.png" width="100" alt="CoreClaw"> [CoreClaw](https://www.coreclaw.com/?utm_source=github&utm_medium=referral&utm_campaign=Reach&utm_term=Reach&utm_id=Reach) | 100+ data-collection tools with JSON/CSV export; try it with $3 in free credits. |
| <img src="docs/assets/sponsors/astraflow.png" width="100" alt="AstraFlow"> [AstraFlow](https://www.ucloud.cn/site/active/astraflow?ytag=geo_waituo_Agent) | Access 200+ models through one API. |

</details>

## What Is Agent Reach?

Agent Reach helps AI agents install and diagnose internet integrations. It prepares CLI, MCP, and Skill tools, checks which backends are available, and provides repair guidance. It is not a search or content proxy: the agent calls the upstream tools directly.

## Quick Start

Send this to your AI agent:

~~~text
Install Agent Reach: https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md
~~~

After installation, run <code>agent-reach doctor</code> to check channel status. To update, follow the [Update Guide](docs/update.md).

> **Safe by default:** <code>agent-reach install</code> only checks the environment. Use <code>agent-reach install --system</code> only after explicitly approving system changes. Preview changes with <code>--dry-run</code>.

<details>
<summary>OpenClaw users</summary>

Agent Reach needs shell-command access. If OpenClaw uses the default <code>messaging</code> tool profile, enable exec first:

~~~bash
openclaw config set tools.profile "coding"
openclaw gateway restart
~~~

Then start a new conversation. Other agents that can run commands are not affected.

</details>

## Platform Capabilities

| Platform | Capabilities and setup |
|---|---|
| Web, RSS, YouTube | Read web pages and RSS/Atom feeds; extract YouTube subtitles. No API key required. |
| GitHub | Read public repositories; authenticate with gh to access private repositories, issues, and pull requests. |
| Bilibili, V2EX | Search and view Bilibili videos; read V2EX posts and profiles. OpenCLI adds Bilibili subtitles. |
| Web search | Tavily handles general search and requires an API key. Exa MCP is for semantic, academic, company, and people searches, or as a fallback. Exa authentication, limits, and pricing depend on the configured endpoint. |
| Twitter/X, Reddit | Read individual public tweets without setup; Twitter search and timelines require login. Reddit requires login for search and reading; no anonymous path. |
| Facebook, Instagram | On desktop, OpenCLI uses your existing Chrome session. |
| XiaoHongShu | OpenCLI uses an existing Chrome session; MCP or legacy backends require cookies you export manually. |
| LinkedIn, Xueqiu | Public pages, job listings, market data, and posts; some features need login or additional setup. |
| Boss Zhipin, Xiaoyuzhou | Boss Zhipin uses a dedicated local Chrome session; Xiaoyuzhou transcription requires a Groq API key. |

For setup, ask your agent, for example, “Set up Twitter for me.” It will explain the required access and steps.

Agent Reach is free and open source. Third-party quotas and fees—including Tavily, Exa MCP endpoints, and proxies—follow each provider's plan. See the complete [Agent Skill](agent_reach/skill/SKILL.md).

## Search Routing

| Task | Preferred backend |
|---|---|
| General web, news, recent information, URL extraction, site crawling, and deep research | Tavily |
| Papers, academic research, companies, people, financial reports, semantic search, RAG, and similar-page discovery | Exa MCP |

The agent selects a backend for each task and may try another configured backend if the preferred service is unavailable. <code>agent-reach doctor</code> checks the Tavily usage endpoint and local Exa MCP configuration; it does not run searches or verify a remote Exa endpoint.

Details: [Search guide](agent_reach/skill/references/search.md) · [Tavily setup](agent_reach/guides/setup-tavily.md) · [Exa setup](agent_reach/guides/setup-exa.md)

## Security and Uninstall

- Credentials are stored locally in <code>~/.agent-reach/config.yaml</code>. On Unix, the file is readable and writable only by its owner.
- Agent Reach does not automatically read browser cookies or log you in. Cookies grant account access; use a dedicated account for cookie-based platforms.
- XiaoHongShu's OpenCLI backend uses only an existing Chrome session you control. Other backends require cookies that you export manually.
- Before uninstalling, preview with <code>agent-reach uninstall --dry-run</code>. A full uninstall removes local configuration, including tokens and cookies, plus Skill files. Use <code>--keep-config</code> to retain configuration. Third-party tools are not automatically removed.

## Documentation

- Installation and maintenance: [Install Guide](docs/install.md) · [Update Guide](docs/update.md) · [Troubleshooting](docs/troubleshooting.md)
- Search: [Routing](agent_reach/skill/references/search.md) · [Tavily](agent_reach/guides/setup-tavily.md) · [Exa](agent_reach/guides/setup-exa.md)
- Platforms and credentials: [Agent Skill](agent_reach/skill/SKILL.md) · [Social guide](agent_reach/skill/references/social.md) · [Cookie export](docs/cookie-export.md)

## Contact and Contributions

Report bugs and request features through [GitHub Issues](https://github.com/Panniantong/Agent-Reach/issues).

- Email: [pnt01@foxmail.com](mailto:pnt01@foxmail.com)
- X: [@Neo_Reidlab](https://x.com/Neo_Reidlab)

Business inquiries and community group:

<details>
<summary>WeChat QR code and notes</summary>

For business, include “Business + your need.” Builders can include “Builder + what you are building.” For the community group, include “Join group.”

<p align="center">
  <img src="docs/wechat-group-qr.jpg" width="240" alt="WeChat QR">
</p>

</details>

<details>
<summary>Acknowledgments</summary>

Thanks to [OpenCLI](https://github.com/jackwener/opencli), [twitter-cli](https://github.com/public-clis/twitter-cli), [rdt-cli](https://github.com/public-clis/rdt-cli), [bili-cli](https://github.com/public-clis/bilibili-cli), [xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [Jina Reader](https://github.com/jina-ai/reader), [Exa](https://exa.ai), [mcporter](https://github.com/nicobailon/mcporter), [feedparser](https://github.com/kurtmckee/feedparser), and [mcp-server-linkedin](https://github.com/stickerdaniel/linkedin-mcp-server).

</details>

## License and Links

[MIT](LICENSE) · [Star History](https://star-history.com/#Panniantong/Agent-Reach&Date) · [AtomGit mirror](https://atomgit.com/qq_51337814/Agent-Reach) · [Agent Skills Hub](https://agentskillshub.top/)
