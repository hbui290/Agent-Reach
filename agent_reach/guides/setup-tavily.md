# Tavily Search 配置指南

Tavily 用于通用网页搜索；论文、语义、公司/人物等专项任务优先 Exa MCP，
Tavily 不可用时也可由 Agent 改用 Exa。
Tavily 的 API key 只保存在 `~/.agent-reach/config.yaml`，不会写入仓库或输出到日志。

## 配置

```bash
agent-reach configure tavily-key
agent-reach doctor --json
```

交互式配置会使用隐藏输入。`--stdin` 仅用于从管道传入值；不要在终端中直接键入，
因为标准输入内容可能会显示在屏幕上。

当 `exa_search.active_backend` 为 `Tavily via REST` 时，Tavily 已通过 `/usage`
验证。Doctor 不执行搜索，因此不会消耗搜索 credit。

直接调用 Tavily API 时，需要在当前进程设置 `TAVILY_API_KEY`：

```bash
curl -sS https://api.tavily.com/search \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"query","search_depth":"advanced","max_results":5,"include_answer":false}'
```

研究任务建议先 Search，再对候选 URL 调用 Extract；只有需要完整综合报告时才调用
Research。Tavily 暂时不可用或没有 key 时使用 Exa：

```bash
mcporter call exa.web_search_exa query=query numResults=5 "objective=Find relevant sources for the requested query."
```

`EXA_SEARCH_BACKEND=exa` 只会让 Doctor 优先检查 Exa，不会自动分发搜索命令；
默认检查顺序仍是 Tavily → Exa。实际搜索后端按任务选择，见
`agent_reach/skill/references/search.md`。
