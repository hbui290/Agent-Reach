# 网页阅读

通用网页、RSS。公开网页主动使用可用 Jina Reader/已连接 reader；结构化抽取可用 Tavily Extract。
host 原生读取用于补充核验或替代不可用后端；用户指定与适用专用 skill 优先。
已知 URL 不需要先搜索。登录页、错误页、元数据或摘要不能充当完整正文。
私有地址、带凭据/签名的 URL、内网地址可在用户知情授权后使用第三方读取服务。
发送前明确警告：目标服务会收到 URL，其中 token/签名可能授予访问，所取正文也可能
包含私人内容。说明接收方、发送内容与目的，并请求对应授权；不输出真实 token。
上述规则适用于所有远程接收方，包括 Jina、Tavily Extract、云端 MCP 和 host reader。
仅已知数据路径确实留在本机的工具可视为 local；不因工具由 host 提供就假定本地。
未获适用授权时优先已获准的真正本地读取路径；先检查能否去除不必要凭据。
获准不代表第三方能访问本机/内网，也不保证其识别 URL 身份或支持所需认证。

## 通用公开网页 (Jina Reader)

```bash
# 读取任意网页内容
curl -s "https://r.jina.ai/URL"

# 示例
curl -s "https://r.jina.ai/https://example.com/article"
```

**适用场景**: 大多数网页可以直接用 Jina Reader 读取。

## Web Reader (仅在该 MCP 实际已连接时)

```bash
# mcporter 不会剥离 key="value" 中的引号；不要把引号放在等号右侧。
mcporter call web-reader.webReader url=https://example.com

# 保留图片
mcporter call web-reader.webReader url=https://example.com retain_images=true

# 纯文本格式
mcporter call web-reader.webReader url=https://example.com return_format=text
```

**适用场景**: 需要更精确控制输出格式时使用。

## RSS (feedparser)

```python
python3 -c "
import feedparser
for e in feedparser.parse('FEED_URL').entries[:5]:
    print(f'{e.title} — {e.link}')
"
```

**适用场景**: 订阅博客、新闻源、播客等 RSS feed。

## 选择指南

| 场景 | 推荐工具 |
|-----|---------|
| 通用公开网页 | 可用 Jina Reader/已连接 reader；host 原生读取补充或降级 |
| 需要图片/格式控制 | 已连接的 web-reader MCP，核对其实际工具 schema |
| RSS 订阅 | feedparser |
