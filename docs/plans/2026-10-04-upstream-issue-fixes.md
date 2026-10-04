# Plan: Fix verified upstream issues in the fork

- Branch: `fix/upstream-issues-batch` (from `main` @ `182f48e`)
- Scope: 14 upstream issues (Panniantong/Agent-Reach) that were cross-verified as real for this fork.
- Out of scope (decided): #732 (not reproducible; all calls have timeouts), #642 (fix only in an unmerged third-party PR), #553, #400, #317, #631, #586, #590 (Windows-only), Windows GBK part of #720.
- Status: **plan only — awaiting Boss approval before any code change.**

## Ground rules (apply to every agent)

1. Work only on branch `fix/upstream-issues-batch` in
   `/Users/0xharry/Documents/Codex/2026-10-03/i-have-adhd-plugin-i-have/work/agent-reach-skill-upgrade`.
2. One commit per issue, format `type(scope): message (#<issue>)`, ending with
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
3. Touch only the files listed for that issue. No refactors, no new dependencies
   beyond the `mcp` extra in #608.
4. Never print secrets. Never send Boss's keys anywhere except the provider they belong to.
5. Do not push, open PRs, change GitHub settings, or touch `~/.agent-reach`,
   `~/.agents/skills`, or `~/.agent-reach-venv`. The orchestrator does that after review.
6. Run the full gate before reporting:
   ```bash
   uv run --isolated --with-editable . --with pytest --with 'yt-dlp[default]>=2026.07.04' pytest tests -q
   uv run --isolated --with-editable '.[dev]' --with-requirements constraints.txt ruff check agent_reach tests
   uv run --isolated --with-editable '.[dev]' --with-requirements constraints.txt mypy agent_reach
   ```
   Baseline: 647 passed + 17 subtests, ruff clean, mypy clean.

## Execution order

| Step | Role | Model | Work | Gate |
|---|---|---|---|---|
| 1 | Implementer A | Sonnet | Code fixes C1–C7 | Full gate green |
| 2 | Implementer B | Sonnet | Docs fixes D1–D7 (runs after A; shares `video.md`) | Full gate green |
| 3 | Verifier | Sonnet (fresh) | Re-runs every acceptance check from scratch, incl. live checks | All checks PASS |
| 4 | Reviewer | Opus (fresh) | Reviews `git diff main...HEAD` only | No blocking findings |
| 5 | Orchestrator | — | Push, PR, CI, report to Boss; merge + sync only after Boss OK | CI 7/7 green |

---

## Part 1 — Code fixes (Implementer A)

### C1 · #664 Xueqiu anonymous token (Boss is affected now)
- **Verified cause:** `agent_reach/channels/xueqiu.py:20` `_XUEQIU_HOME = "https://xueqiu.com"`; the homepage only sets `acw_tc`. `https://xueqiu.com/hq` sets `xq_a_token` etc. Fork code → HTTP 400; patched URL → valid quote.
- **Change:**
  - `_XUEQIU_HOME = "https://xueqiu.com/hq"`.
  - Update the docstring/comment in `_ensure_cookies` (lines ~75–92): the fallback now visits `/hq` to obtain the anonymous `xq_a_token`.
  - `backends = ["Xueqiu API (需要登录 Cookie)"]` → `["Xueqiu API（匿名 token；部分功能需登录 Cookie）"]` only if no test or doc pins the old string (grep first; if pinned, leave it).
- **Tests:** update `tests/test_channels.py:768` (`requested == ["https://xueqiu.com"]` → `/hq`). Add a test that the anonymous fallback requests `_XUEQIU_HOME` ending in `/hq` when no cookie is configured.
- **Not in scope:** stale saved cookie blocking the anonymous fallback (Boss has no saved cookie).

### C2 · #720 `--polish` uses a removed Groq model
- **Verified cause:** `agent_reach/scripts/transcribe_xiaoyuzhou.sh:293` `MODEL = "llama-3.3-70b-versatile"`. Groq returns `model_not_found` for Boss's key. `qwen/qwen3.8-27b` is listed for Boss's key and correctly punctuated a test sentence with `reasoning_effort: "none"`. The HTTPError path (lines ~331–334) returns raw text, and the loop still prints `✅`.
- **Change (script only):**
  - `MODEL = os.environ.get("POLISH_MODEL") or "qwen/qwen3.8-27b"`; pass `POLISH_MODEL` through the env block alongside `GROQ_API_KEY`.
  - Add `"reasoning_effort": "none"` to the request body.
  - Treat empty `content` as a failure (fall back to raw, no recursion).
  - Track fallback: if any `polish()` call fell back, print `⚠️ 润色失败，已保留原文 (...)` instead of `✅`. Keep the exit code 0 (the transcript itself succeeded).
  - Update the user-facing labels at lines 6, 277, 280, 373 from "Llama 3.3 70B" to the active model (for example `润色: Groq ${POLISH_MODEL:-qwen/qwen3.8-27b}`).
- **Tests:** in `tests/test_xiaoyuzhou_install.py` (or a new `tests/test_xiaoyuzhou_polish.py`): the script does not contain `llama-3.3`, contains `POLISH_MODEL` and `reasoning_effort`. Static assertions only; no network.
- **Docs part** (`video.md:127,131`) is handled by D7.

### C3 · #608 `agent-reach[mcp]` extra does not exist
- **Verified cause:** `integrations/mcp_server.py:43` recommends `agent-reach[mcp]`; `pyproject.toml` extras are only `browser`, `cookies`, `all`, `dev`. uv only warns and skips `mcp`.
- **Change:** in `pyproject.toml` `[project.optional-dependencies]`, add `mcp = ["mcp[cli]>=1.0"]` (same spec as `all`). Leave `mcp_server.py` unchanged. Check that `constraints.txt` and the CI `wheel-gate` job need no change.
- **Tests:** parse `pyproject.toml` with `tomllib`/`tomli` and assert that `mcp` exists and that the extra named in the `mcp_server.py` hint exists.

### C4 · #611 check-update retries after the GitHub quota is exhausted
- **Verified cause:** `cli.py:2238–2265` `_github_get_with_retry` sleeps and retries on `rate_limit` even when `X-RateLimit-Remaining: 0` (3 calls, about 3 s). `github_token` is never sent.
- **Change:**
  - When the response is 403/429 with `X-RateLimit-Remaining == "0"`, return `(None, "rate_limit", attempt)` immediately, with no sleep. Keep the current retry for 429 + `Retry-After` and for 5xx.
  - Add an optional `headers=None` parameter. In `_cmd_check_update` and `_cmd_watch`, pass `{"Authorization": f"Bearer {token}"}` when `Config(read_only=True).get("github_token")` is set. Only ever send it to `https://api.github.com/`; assert the URL prefix before attaching it.
- **Tests (`tests/test_cli.py`):**
  - 403 with Remaining=0 → `attempts == 1`, `sleeps == []`.
  - Existing 429 + Retry-After test still passes.
  - Token header is sent when configured and is absent when not.
  - Existing mocks that patch `requests.get` must keep working (accept `**kwargs`).

### C5 · #729 YouTube doctor message overclaims
- **Verified cause:** `channels/youtube.py:97` returns `"可提取视频信息和字幕"`, but `check()` makes no request to YouTube.
- **Change:** message → `"yt-dlp 可用（仅本地检查，未验证 YouTube 实际访问与字幕）"`. Keep status `ok`. No network probe (Doctor stays read-only and local).
- **Tests:** update `tests/test_youtube_channel.py:191` and any other test that pins the old string.

### C6 · #740 OpenCLI multi-profile shows "not connected"
- **Verified cause:** `backends/opencli.py:~154` reads only the top-level `extensionConnected`. In OpenCLI `src/daemon.ts`, with more than one connected profile and no selected route, the top level is `false` while `profiles[]` lists entries with `extensionConnected: true`.
- **Change:**
  ```python
  profiles = daemon_status.get("profiles")
  st.extension_connected = bool(daemon_status.get("extensionConnected")) or (
      isinstance(profiles, list)
      and any(isinstance(p, dict) and p.get("extensionConnected") is True for p in profiles)
  )
  ```
- **Tests (`tests/test_opencli_backend.py`):** top-level false + a profile with true → connected; empty `profiles` → not connected; `profiles` of the wrong type → not connected.

### C7 · #635 mcporter XDG config is ignored
- **Verified cause:** `channels/mcporter.py:~97` only checks `~/.mcporter`. mcporter (`openclaw/mcporter`, `src/paths.ts`) uses `$XDG_CONFIG_HOME/mcporter` when `XDG_CONFIG_HOME` is non-empty and absolute, then falls back to legacy `~/.mcporter`.
- **Change in `_select_config_layers`:** build the candidate list as follows:
  1. If `XDG_CONFIG_HOME` is non-empty and absolute: `<xdg>/mcporter/mcporter.json`, then `<xdg>/mcporter/mcporter.jsonc`.
  2. Then `~/.mcporter/mcporter.json` and `~/.mcporter/mcporter.jsonc`.

  The first existing file wins and is labelled `"home"`. Keep `MCPORTER_CONFIG` precedence and the `read_small_text_no_follow` symlink hardening unchanged.
- **Tests:** XDG file is preferred over legacy; XDG set but empty dir → legacy is used; relative XDG → ignored; XDG unset → unchanged behavior.

### Implementer A — prompt

```text
You are IMPLEMENTER A. Repo: /Users/0xharry/Documents/Codex/2026-10-03/i-have-adhd-plugin-i-have/work/agent-reach-skill-upgrade
Branch: fix/upstream-issues-batch (already checked out; verify with `git branch --show-current`).
Read CLAUDE.md in the repo and docs/plans/2026-10-04-upstream-issue-fixes.md, Part 1 and the ground rules.
Implement C1..C7 exactly as specified, in that order, with one commit per item:
  fix(xueqiu): fetch anonymous token from /hq (#664)
  fix(xiaoyuzhou): replace removed Groq polish model and surface fallback (#720)
  fix(packaging): add mcp extra referenced by MCP server hint (#608)
  fix(check-update): stop retrying exhausted GitHub quota and use github_token (#611)
  fix(youtube): doctor message no longer claims unverified subtitle access (#729)
  fix(opencli): treat any connected profile as connected (#740)
  fix(mcporter): honor XDG_CONFIG_HOME config location (#635)
Each commit message ends with: Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Rules: read the code before editing; match the surrounding style; touch only the listed files and tests;
no new deps except the mcp extra; never print secrets; no network calls in tests; do not push or edit anything outside the repo.
If a spec conflicts with what you find in the code, stop and report instead of improvising.
Before finishing, run the full gate (pytest, ruff, mypy commands in the plan) and paste the summary lines.

Return exactly:
1. Table: item | issue | files changed | commit SHA | tests added/updated
2. Gate results: pytest summary line, ruff result, mypy result
3. Any deviation from the plan, with the reason (or "none")
```

---

## Part 2 — Docs/skill fixes (Implementer B)

### D1 · #742 YouTube subtitles return machine translations
- **Verified:** on a Korean video, the `video.md:19` flags select `zh-Hans` and `en` (machine translations); adding `.*-orig` selects `ko-orig` (original). `SKILL.md:123` and `SKILL_en.md:148` have no `--sub-langs`, so they always get `en`.
- **Change in `agent_reach/skill/references/video.md` (download subtitles section):**
  ```bash
  # Check available tracks first: manual subs are best; among auto subs "<lang>-orig" is the original language, other languages are usually machine translations
  yt-dlp --list-subs --skip-download "URL"
  # Download manual subs + original-language auto subs (+ zh/en as a fallback)
  yt-dlp --write-sub --write-auto-sub --sub-langs ".*-orig,zh-Hans,zh,en" --skip-download -o "/tmp/%(id)s" "URL"
  ```
  Add the rule: when summarizing, say whether the text came from manual subs, original auto subs (`-orig`), or machine translation. If there is no `-orig` track, a plain `<lang>` track matching the video `language` (from `--dump-json`) is the original. Keep the existing Chinese wording style.
- **Change in `SKILL.md:123` and `SKILL_en.md:148`:** add `--sub-langs ".*-orig,en"` to the quick command.
- **Test:** add an assertion (in `tests/test_auth_guidance_policy.py` or the existing skill tests) that `.*-orig` appears in `video.md`, `SKILL.md`, and `SKILL_en.md`.

### D2 · #580 update.md says Doctor installs the skill
- **Verified:** `docs/update.md:95–99` claims this; `_cmd_doctor` uses `Config(read_only=True)` and never calls `_install_skill`. Running Doctor in a temp HOME creates no skill dir.
- **Change:** replace the paragraph with: Doctor is read-only and never installs or overwrites skills; run `agent-reach skill --install` to refresh the bundled skill (it copies `SKILL.md` and `references/`).
- **Test:** assert that `docs/update.md` does not contain `makes sure an Agent Reach skill`.

### D3 · #622 install.md directory table is stale
- **Verified:** `docs/install.md:41–45` shows `config.json` and skills = `SKILL.md` only. Real behavior: config is `~/.agent-reach/config.yaml`; `skill --install` writes `SKILL.md` + 7 `references/*.md` into detected skill roots (`~/.agents/skills`, `~/.config/opencode/skills`, `~/.openclaw/skills`, `~/.claude/skills`, `$OPENCLAW_HOME`), defaulting to `~/.agents/skills`.
- **Change:** fix both rows (Config: `~/.agent-reach/config.yaml`; Skills: `~/.agents/skills/agent-reach/` (+ other detected agent skill dirs) | `SKILL.md` + `references/*.md`). Confirm the root list against `cli.py:549–575` before writing.

### D4 · #703 security reports go to upstream
- **Verified:** `SECURITY.md:14` links to `Panniantong/Agent-Reach/security/advisories/new`; on the fork, private vulnerability reporting is `enabled:false` and Issues are disabled.
- **Change:** link → `https://github.com/hbui290/Agent-Reach/security/advisories/new`, plus one line: vulnerabilities in upstream-only code may also be reported to Panniantong/Agent-Reach.
- **Needs Boss (GitHub setting, outside effect):** enable private vulnerability reporting on the fork, either in Settings → Code security or with `gh api -X PUT repos/hbui290/Agent-Reach/private-vulnerability-reporting`. The orchestrator asks Boss; implementers must not do it.

### D5 · #728 leftover `conda run -n dl`
- **Change:** delete step 4 from the CLI lookup list in `SKILL.md:189` and `SKILL_en.md:195`; change `README.md:98` "PATH → venv → `~/.local/bin` → conda" to "PATH → venv → `~/.local/bin`". No test depends on it (verified).

### D6 · #369(b) XHS media download missing from the skill · #550 Instagram note is stale
- **#369b:** under "后端 A：OpenCLI" in `agent_reach/skill/references/social.md` (lines ~11–27), add:
  ```bash
  # 下载笔记图片/视频到本地（需完整 NOTE_URL 含 xsec_token 或 xhslink；会写入磁盘，先确认输出目录）
  opencli xiaohongshu download "NOTE_URL" --output /tmp/xhs-downloads
  ```
  Verified locally with `opencli xiaohongshu download --help` (OpenCLI 1.8.8).
- **#550:** in the Instagram note (`social.md:~319`), add: on OpenCLI 1.8.8, `instagram user` (and sometimes `search`) may return an HTML page, 429, or `Unexpected token '<'` (open OpenCLI issues #2456, #2553). Do not retry in a loop; report the limitation; suggest upgrading OpenCLI. The old HTTP 400 bug is already fixed (#2147, #2234). Do not mention the 400 as current.

### D7 · #720 docs part
- **Change:** `video.md:127,131`: replace "Llama 3.3 70B" with "Groq LLM（默认 `qwen/qwen3.8-27b`，可用 `POLISH_MODEL` 覆盖）". Remove the "免费" claim unless it is verified (do not verify by spending Boss's quota).

### Implementer B — prompt

```text
You are IMPLEMENTER B. Repo: /Users/0xharry/Documents/Codex/2026-10-03/i-have-adhd-plugin-i-have/work/agent-reach-skill-upgrade
Branch: fix/upstream-issues-batch (Implementer A's commits are already on it; do not rewrite them).
Read CLAUDE.md and docs/plans/2026-10-04-upstream-issue-fixes.md, Part 2 and the ground rules.
Implement D1..D7 in order, with one commit per item:
  docs(skill): prefer original-language YouTube subtitles (#742)
  docs(update): doctor is read-only and does not install skills (#580)
  docs(install): correct config and skill directory table (#622)
  docs(security): route vulnerability reports to the fork (#703)
  docs(skill): drop author-specific conda lookup step (#728)
  docs(social): add XHS media download and current Instagram limits (#369, #550)
  docs(video): describe the current polish model (#720)
Each commit message ends with: Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Rules: keep each file's language (Chinese references stay Chinese, English stays English); match the existing tone and format;
touch only the listed files and tests; never use the bare PyPI name `agent-reach` in install commands;
do not change GitHub settings; never print secrets.
Before finishing, run the full gate and paste the summary lines.

Return exactly:
1. Table: item | issue | files changed | commit SHA | tests added/updated
2. Gate results: pytest summary line, ruff result, mypy result
3. Any deviation from the plan, with the reason (or "none")
```

---

## Part 3 — Verifier (fresh agent, does not trust the implementers)

```text
You are the VERIFIER. Do NOT edit files or commit. Repo as above, branch fix/upstream-issues-batch.
Read docs/plans/2026-10-04-upstream-issue-fixes.md. For EVERY item C1..C7 and D1..D7, check the acceptance
criteria yourself from scratch: read the diff (`git diff main...HEAD -- <file>`), run the gate, and do these live checks:
- C1: with HOME pointed at an empty temp dir, run the branch's xueqiu code with
  `uv run --isolated --with-editable . python -c ...` to fetch quote SH600519 → expect valid data (print only symbol + price).
- C2: run only the embedded polish Python block against Groq with Boss's key loaded from Config (never print it)
  on one short Chinese sentence (<=200 completion tokens) → expect punctuated text and no `✅` on forced failure
  (simulate failure with POLISH_MODEL=invalid-model → expect the ⚠️ line).
- C3: `uv pip install --dry-run "agent-reach[mcp] @ file://$PWD"` in a temp venv → no "does not have an extra" warning.
- C4/C5/C6/C7: run the new tests and also one manual mock run each.
- D1: `yt-dlp -j --skip-download --write-auto-sub --write-sub --sub-langs ".*-orig,zh-Hans,zh,en" https://www.youtube.com/watch?v=9bZkp7q19f0`
  → requested_subtitles includes ko-orig.
- D2: HOME=temp `agent-reach doctor` creates no skill dir (statement in docs is true).
- D3: HOME=temp `uv run ... agent-reach skill --install` → files match the new table.
- Everything: grep that `llama-3.3`, `conda run -n dl`, and `Panniantong/Agent-Reach/security` are gone from the fork-owned paths.
Return: table item | criterion | PASS/FAIL | evidence (command + key output line). Then a list of FAILs with the exact reason.
```

## Part 4 — Reviewer (fresh agent, review only)

```text
You are the REVIEWER. Review only; no edits. Run `git diff main...HEAD` on branch fix/upstream-issues-batch.
Check: correctness vs. the plan, regressions, secret handling (token only sent to api.github.com), thread/env
side effects, tests that really assert the behavior (not just strings where behavior is testable),
docs accuracy and language consistency, commit hygiene (one issue per commit, message format).
Return findings ranked blocking / should-fix / nit, each with file:line and a one-line fix. If none: "No blocking findings".
```

## Part 5 — Orchestrator closeout and expected output

1. After the verifier and reviewer pass: push the branch and open a PR to `hbui290/Agent-Reach:main`, with the body listing each issue → commit → evidence.
2. Wait for CI 7/7 green.
3. **Ask Boss** before: merging; enabling private vulnerability reporting (D4); syncing the runtime.
4. After merge (with Boss OK), sync and verify:
   - venv: the `uv pip install ... --reinstall` command from the main zip, then `diff -rq -x __pycache__`.
   - skill: `agent-reach skill --install`, then diff against `agent_reach/skill`.
   - xiaoyuzhou script: copy `agent_reach/scripts/transcribe_xiaoyuzhou.sh` → `~/.agent-reach/tools/xiaoyuzhou/transcribe.sh` (show the diff first).
   - `agent-reach doctor`: xueqiu `ok`, youtube shows the new message.

**Final report to Boss (Vietnamese, short):**

| Issue | Change | Evidence it works | Commit |
|---|---|---|---|

followed by: test count (expected 647 + new tests, all passing), CI status, what was NOT verified, and what Boss needs to do (D4 setting).
