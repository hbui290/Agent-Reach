<h1 align="center">👁️ Agent Reach</h1>

<p align="center">
  <strong>统一安装、诊断和维护 AI Agent 的互联网数据渠道</strong>
</p>

<p align="center">
  适用于 Claude Code、OpenClaw、Cursor 等可运行命令的 Agent；内容由对应的上游工具读取。
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
  <a href="#快速开始">快速开始</a> · <a href="README.md">English</a> · <a href="docs/README_ja.md">日本語</a> · <a href="docs/README_ko.md">한국어</a> · <a href="#平台能力">平台能力</a> · <a href="#搜索路由">搜索路由</a>
</p>

---

<details>
<summary>赞助商</summary>

| | |
|---|---|
| <img src="docs/assets/sponsors/browseract.png" width="100" alt="BrowserAct"> [BrowserAct](https://www.browseract.ai/Agent) | 用真实浏览器采集网站数据；新用户赠 1000 积分。 |
| <img src="docs/assets/sponsors/tencent-cloud.svg" width="100" alt="腾讯云"> [腾讯云 Lighthouse](https://www.tencentcloud.com/act/pro/intl-openclaw?referral_code=G76Y819A&lang=zh&pg=) | 快速部署 OpenClaw，并接入 Agent Reach。 |
| <img src="docs/assets/sponsors/coreclaw.png" width="100" alt="CoreClaw"> [CoreClaw](https://www.coreclaw.com/?utm_source=github&utm_medium=referral&utm_campaign=Reach&utm_term=Reach&utm_id=Reach) | 提供 100+ 数据采集工具，支持 JSON/CSV；可免费试用 $3。 |
| <img src="docs/assets/sponsors/astraflow.png" width="100" alt="AstraFlow"> [星图 AstraFlow](https://www.ucloud.cn/site/active/astraflow?ytag=geo_waituo_Agent) | 一个入口调用 200+ 模型。 |

</details>

## Agent Reach 是什么？

Agent Reach 是 AI Agent 的安装与诊断工具：帮助准备 CLI、MCP 和 Skill，检查各平台的可用后端，并给出修复建议。它不代理搜索或网页内容；Agent 按说明直接调用对应的上游工具。

## 快速开始

把这句话发给你的 AI Agent：

~~~text
帮我安装 Agent Reach：https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md
~~~

安装后运行 **agent-reach doctor** 查看渠道状态。已经安装？按[升级指南](docs/update.md)更新。

> **默认安全：** **agent-reach install** 只检查环境；只有在你明确授权修改系统后，Agent 才应运行 **agent-reach install --system**。先预览操作可用 **--dry-run**。

<details>
<summary>OpenClaw 用户注意</summary>

Agent Reach 需要 shell 执行权限。若 OpenClaw 使用默认的 **messaging** 工具配置，请先启用 exec：

~~~bash
openclaw config set tools.profile "coding"
openclaw gateway restart
~~~

然后开启新对话再安装。其他支持命令执行的 Agent 不受此限制。

</details>

## 平台能力

| 平台 | 能力与配置 |
|---|---|
| 网页、RSS、YouTube | 阅读网页和 RSS/Atom，提取 YouTube 字幕；无需 API Key。 |
| GitHub | 可读公开仓库；登录 gh 后可访问私有仓库及 Issue、PR 等。 |
| B站、V2EX | B站可搜索和查看视频；V2EX 可读帖子与用户。B站字幕可通过 OpenCLI 解锁。 |
| 网页搜索 | Tavily 需 API Key，处理通用搜索；Exa MCP 用于语义、论文、公司/人物等专项搜索，也可作为备选。Exa 的认证、额度和费用取决于 endpoint。 |
| Twitter/X、Reddit | 可免配置阅读单条公开推文；Twitter 搜索和时间线需要登录。Reddit 搜索与阅读都需要登录，没有免登录路径。 |
| Facebook、Instagram | 桌面端通过 OpenCLI 使用你已有的 Chrome 登录会话。 |
| 小红书 | OpenCLI 使用已有 Chrome 会话；MCP/旧版工具需用户手动导出 Cookie。 |
| LinkedIn、雪球 | 公开资料、职位、股票及帖子等；部分能力需要登录或额外配置。 |
| Boss直聘、小宇宙 | Boss直聘需要本地 Chrome 登录；小宇宙转录需要 Groq API Key。 |

需要配置某个平台时，直接告诉 Agent「帮我配 Twitter」等；它会按指南说明所需权限和步骤。

Agent Reach 本身免费开源；Tavily、Exa MCP endpoint、代理等第三方服务的额度和费用按服务商方案计算。完整平台说明见 [Agent Skill](agent_reach/skill/SKILL.md)。

## 搜索路由

| 任务 | 优先使用 |
|---|---|
| 普通网页、新闻、时效信息、URL 抽取、站点爬取、深度研究 | Tavily |
| 论文/学术、公司/人物/财报、语义搜索、RAG、相似页面发现 | Exa MCP |

Agent 根据任务选择后端；首选服务不可用时，可尝试另一个已配置的服务。**agent-reach doctor** 会检查 Tavily 用量接口和本地 Exa MCP 配置，但不会执行搜索，也不会验证远端 Exa endpoint。

详细说明：[搜索指南](agent_reach/skill/references/search.md) · [Tavily 配置](agent_reach/guides/setup-tavily.md) · [Exa 配置](agent_reach/guides/setup-exa.md)

## 安全与卸载

- 配置和凭据保存在本机 **~/.agent-reach/config.yaml**；Unix 系统会限制为仅文件所有者可读写。
- Agent Reach 不会自动读取浏览器 Cookie 或替你登录。Cookie 等同登录凭据；使用相关平台时建议使用专用账号。
- 小红书 OpenCLI 只使用你已有且明确控制的 Chrome 会话；没有现成会话时，需由你手动导出 Cookie 并配置其他后端。
- 卸载前先运行 **agent-reach uninstall --dry-run**。正式卸载会删除本地配置（含 Token/Cookie）和 Skill 文件；**--keep-config** 可保留配置。第三方工具不会自动卸载。

## 文档

- 安装与升级：[安装指南](docs/install.md) · [升级指南](docs/update.md) · [故障排查](docs/troubleshooting.md)
- 搜索：[路由说明](agent_reach/skill/references/search.md) · [Tavily](agent_reach/guides/setup-tavily.md) · [Exa](agent_reach/guides/setup-exa.md)
- 平台与凭据：[Agent Skill](agent_reach/skill/SKILL.md) · [社交平台指南](agent_reach/skill/references/social.md) · [Cookie 导出](docs/cookie-export.md)

## 联系与贡献

Bug 反馈和功能请求请提交 [GitHub Issues](https://github.com/Panniantong/Agent-Reach/issues)。

- Email: [pnt01@foxmail.com](mailto:pnt01@foxmail.com)
- X: [@Neo_Reidlab](https://x.com/Neo_Reidlab)

商务合作或交流群：

<details>
<summary>查看微信二维码与备注方式</summary>

商务合作请备注「业务 + 需求」；Agent Builder 可备注「Builder + 你在做什么」；加入交流群请备注「加群」。

<p align="center">
  <img src="docs/wechat-group-qr.jpg" width="240" alt="WeChat QR">
</p>

</details>

<details>
<summary>致谢</summary>

感谢 [OpenCLI](https://github.com/jackwener/opencli)、[twitter-cli](https://github.com/public-clis/twitter-cli)、[rdt-cli](https://github.com/public-clis/rdt-cli)、[bili-cli](https://github.com/public-clis/bilibili-cli)、[xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp)、[yt-dlp](https://github.com/yt-dlp/yt-dlp)、[Jina Reader](https://github.com/jina-ai/reader)、[Exa](https://exa.ai)、[mcporter](https://github.com/nicobailon/mcporter)、[feedparser](https://github.com/kurtmckee/feedparser) 和 [mcp-server-linkedin](https://github.com/stickerdaniel/linkedin-mcp-server)。

</details>

## 许可证与链接

[MIT](LICENSE) · [Star History](https://star-history.com/#Panniantong/Agent-Reach&Date) · [AtomGit 镜像](https://atomgit.com/qq_51337814/Agent-Reach) · [Agent Skills Hub](https://agentskillshub.top/)
