# Reddit 配置指南

## 功能说明

Reddit 封锁了几乎所有非浏览器的直接访问（包括数据中心和 ISP 代理 IP），JSON API 返回 403。

桌面环境优先使用 **OpenCLI**（复用浏览器里已登录的 reddit.com 会话）；
服务器或存量用户使用 **rdt-cli**：
- **搜索**：`rdt search "关键词"`
- **阅读完整帖子+评论**：`rdt read POST_ID`

免费，无需代理，无需 API Key。需要登录认证（`rdt login`，自动从浏览器提取 Cookie）。

## Agent 可自动完成的步骤

1. 检查 rdt-cli 是否可用：
```bash
which rdt && echo "installed" || echo "not installed"
```

2. 如果未安装，从 GitHub 安装与 Agent Reach 校验过的版本（PyPI 版本落后）：
```bash
pipx install 'git+https://github.com/public-clis/rdt-cli.git@5e4fb3720d5c174e976cd425ccc3b879d52cac66'
```

或一键安装（桌面环境装 OpenCLI，服务器环境装 rdt-cli）：
```bash
agent-reach install --env=auto --system --channels=reddit
```

## 使用示例

搜索 Reddit 内容：
```bash
rdt search "python best practices" --limit 5
```

阅读完整帖子和评论：
```bash
rdt read POST_ID
```

## 需要用户手动做的步骤

登录是必须的（Reddit 没有零配置路径）：
- OpenCLI：在浏览器里登录 reddit.com，并启用 OpenCLI 扩展
- rdt-cli：先在浏览器登录 reddit.com，再运行 `rdt login`

安装命令需用户明确授权后再执行。

## Fallback：Exa 搜索

如果你已经配置了 Exa（通过 mcporter），也可以通过 Exa 搜索 Reddit 内容：

```bash
mcporter call exa.web_search_exa "query=site:reddit.com python best practices" numResults=5
```

OpenCLI / rdt-cli 是当前推荐方案，两者都需要上面的登录步骤。
