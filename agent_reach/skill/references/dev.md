# 开发工具

GitHub 检索优先可用的专用 skill/连接；需要仓库、代码、Issue、PR 等查询时，
也可使用已安装的 gh CLI。私有仓库必须有对应授权，不把内容发送到公开搜索。

## GitHub：只读查询

```bash
# 认证状态（不登录）
gh auth status

# 搜索
gh search repos KEYWORD1 KEYWORD2 --sort stars --limit 10   # 关键词不要整体加引号：引号=精确短语匹配，常返回 0 条
gh search code "query" --language python

# 仓库（只为读代码时克隆到临时目录）
gh repo view owner/repo
gh repo clone owner/repo /tmp/repo

# Issues / Pull Requests
gh issue list -R owner/repo --state open
gh issue view 123 -R owner/repo
gh pr list -R owner/repo --state open
gh pr view 123 -R owner/repo
gh pr checks 123 --repo owner/repo

# Actions / CI
gh run list --repo owner/repo --limit 10
gh run view <run-id> --repo owner/repo --log-failed
gh workflow list --repo owner/repo

# Releases / GET API
gh release list -R owner/repo
gh api --method GET repos/owner/repo

# JSON 输出
gh issue list --repo owner/repo --json number,title --jq '.[] | "\(.number): \(.title)"'
```

## 用户另行要求的登录与变更

以下为设置/变更示例，查资料不授权执行它们。需要用户对对应登录、创建、
同步或发布动作的明确要求；有专用 skill 时交由该 skill。Skill 本身不增加权限。

```bash
gh auth login
gh repo create my-repo --private
gh repo fork owner/repo
gh repo fork owner/repo --clone
gh repo sync owner/repo
gh issue create -R owner/repo --title "Title" --body "Body"
gh pr create -R owner/repo --title "Title" --body "Body"
gh release create v1.0.0
```

## 选择指南

| 工具 | 用途与条件 |
|---|---|
| host GitHub 连接 / gh CLI | 返回目标仓库、代码、Issue、PR 的真实内容；权限需覆盖目标 |
| zread | 仅在已连接且能读取目标仓库时使用，不假设此名称存在 |
| context7 | 仅在已连接时查询相应技术文档，不代替指定仓库代码 |
