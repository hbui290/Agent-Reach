# Groq Whisper 配置指南

## 功能说明
当 YouTube/Bilibili 视频没有字幕时，用 Groq 的 Whisper API 进行语音转文字。Groq 提供免费额度。

## Agent 可自动完成的步骤

1. 检查是否已配置：
```bash
agent-reach doctor | grep -i "groq\|whisper"
```

2. 让用户在自己的终端里写入 key（隐藏输入，key 不进入聊天记录、命令参数或 Shell 历史）：
```bash
agent-reach configure groq-key
```

3. 再次运行第 1 步的 `doctor` 确认已配置。

## 需要用户手动做的步骤

请告诉用户：

> 视频语音转文字需要一个 Groq API Key（免费）。
>
> 步骤：
> 1. 打开 https://console.groq.com
> 2. 用 Google 账号或邮箱注册
> 3. 点击左侧 "API Keys"
> 4. 点击 "Create API Key"
> 5. 复制生成的 Key，在终端运行 `agent-reach configure groq-key` 并粘贴（不要发到聊天里）
>
> Groq 提供免费额度，日常使用完全够用。

## 用户配置完成后的操作

1. 运行 `agent-reach doctor` 确认已配置
2. 反馈："✅ 语音转文字已开启！现在遇到没有字幕的视频，我也能帮你提取内容了。"
