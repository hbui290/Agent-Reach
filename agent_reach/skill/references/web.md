# 网页阅读

通用网页、RSS。公开网页主动使用可用 Jina Reader/已连接 reader；结构化抽取可用 Tavily Extract。
host 原生读取用于补充核验或替代不可用后端；用户指定与适用专用 skill 优先。
已知 URL 不需要先搜索。登录页、错误页、元数据或摘要不能充当完整正文。
私有地址、带凭据/签名的 URL、内网地址：发送给任何远程读取服务（Jina、Tavily Extract、
云端 MCP、host reader）前，先警告接收方会拿到 URL（token/签名可能授予访问，正文可能含
私人内容），说明接收方、内容与目的并请求许可；不输出真实 token。能去掉不必要凭据先去掉；
有确实留在本机的读取路径时优先用它。获准不代表第三方能访问本机/内网或通过认证。

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
# 值含空格或特殊字符时给整个 token 加引号："key=value with spaces"。不要在已加引号的
# token 里再给值加引号（如 'key="v"'）：这时引号会原样传给 mcporter，不会被剥离。
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
