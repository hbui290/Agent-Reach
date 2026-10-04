# -*- coding: utf-8 -*-
"""Reddit — multi-backend: OpenCLI / rdt-cli. Login is mandatory.

Honest tiering (live-verified 2026-06): there is NO zero-config path.
Anonymous .json endpoints are blocked (403 anti-bot, all variants), and
the official API closed self-service registration in 2025-11 (manual
approval, individual scripts rarely granted — PRAW is only an option for
users who already hold credentials). Every working backend rides a
logged-in session: OpenCLI reuses the browser's, rdt-cli imports cookies.
"""

import base64
import json
import math
import shutil
import time
from pathlib import Path

from agent_reach.utils.paths import (
    PrivatePathError,
    read_small_text_no_follow,
)

from .base import Channel

_CREDENTIAL_FILE = "~/.config/rdt-cli/credential.json"
#: Fallback age limit, used only when the cookie does not state its own expiry.
_CREDENTIAL_TTL_SECONDS = 7 * 86400
#: Below this, warn that a re-export is due soon.
_EXPIRY_WARN_SECONDS = 3 * 86400
_MAX_CREDENTIAL_BYTES = 1024 * 1024
# Pinned to the 0.4.2 state — PyPI still only has 0.4.1 (upstream issue #10).
_RDT_GIT_SOURCE = "git+https://github.com/public-clis/rdt-cli.git@5e4fb3720d5c174e976cd425ccc3b879d52cac66"

def _session_cookie_expiry(token: object) -> float | None:
    """Seconds until ``reddit_session`` expires, or None if it does not say.

    ``reddit_session`` is a JWT whose payload carries ``exp``; ``saved_at`` only
    records when the file was written. The signature is deliberately not
    verified: this phrases a doctor message and must never gate access.
    """
    if not isinstance(token, str):
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, RecursionError):
        return None
    if not isinstance(claims, dict):
        return None
    expiry = claims.get("exp")
    if isinstance(expiry, bool) or not isinstance(expiry, (int, float)):
        return None
    try:
        if not math.isfinite(expiry):
            return None
        return float(expiry) - time.time()
    except OverflowError:  # an int too large for a float is no real expiry
        return None


class RedditChannel(Channel):
    name = "reddit"
    description = "Reddit 帖子和评论"
    backends = ["OpenCLI", "rdt-cli"]
    tier = 1  # no zero-config path exists — see module docstring

    def can_handle(self, url: str) -> bool:
        from agent_reach.utils.url import host_matches

        return host_matches(url, "reddit.com", "redd.it")

    def check(self, config=None):
        """Probe candidates in order; first fully-usable backend wins."""
        self.active_backend = None
        findings = []

        for backend in self.ordered_backends(config):
            if backend == "OpenCLI":
                result = self._check_opencli()
            else:
                result = self._check_rdt()
            if result is None:
                continue
            findings.append((backend, *result))

        for wanted in ("ok", "warn"):
            for backend, status, message in findings:
                if status == wanted:
                    self.active_backend = backend if status == "ok" else None
                    return status, message

        if findings:
            return "error", "\n".join(m for _, _, m in findings)

        return "off", (
            "未安装任何 Reddit 后端。注意：Reddit 没有零配置路径"
            "（匿名 .json 已被封，官方 API 需人工审批），必须用登录态。推荐：\n"
            "  桌面：agent-reach install --system --channels opencli\n"
            "       （复用 Chrome 登录态，登录过 reddit.com 即可用）\n"
            f"  服务器/存量：pipx install '{_RDT_GIT_SOURCE}'\n"
            "       然后 `rdt login` 或手动写入 Cookie（见 doctor 提示）\n"
            "中国大陆访问 Reddit 需要代理"
        )

    def _check_opencli(self):
        """OpenCLI candidate. None = not installed."""
        from agent_reach.backends import opencli_status

        st = opencli_status()
        if not st.installed:
            return None
        if st.broken:
            return "error", st.hint
        if st.ready:
            return "warn", (
                "OpenCLI 桥接已连接，但 Reddit 登录态和实际命令未实时验证；"
                "Doctor 不执行平台命令，因此当前不标记为可用。"
            )
        return "warn", st.hint

    def _check_rdt(self):
        """Inspect rdt's saved credential without invoking its auto-refresh."""
        if not shutil.which("rdt"):
            return None

        credential_path = Path.home() / ".config" / "rdt-cli" / "credential.json"
        try:
            payload = read_small_text_no_follow(
                credential_path,
                max_bytes=_MAX_CREDENTIAL_BYTES,
            )
        except PrivatePathError as exc:
            return "warn", (
                f"rdt-cli 已安装，但 credential.json 无法安全读取：{exc}。"
            )
        except (OSError, UnicodeError):
            return "warn", (
                "rdt-cli 已安装，但 credential.json 无法安全读取；"
                "Doctor 未执行会自动刷新 Cookie 的 `rdt status`。"
            )
        if payload is None:
            return "warn", self._rdt_login_hint()
        try:
            data = json.loads(payload)
        except (UnicodeError, json.JSONDecodeError, ValueError):
            return "warn", (
                "rdt-cli 已安装，但保存的 credential.json 无法安全解析；"
                "Doctor 未执行会自动刷新 Cookie 的 `rdt status`。"
            )
        if not isinstance(data, dict):
            return "warn", self._rdt_login_hint()
        cookies = data.get("cookies")
        if not isinstance(cookies, dict) or not cookies.get("reddit_session"):
            return "warn", self._rdt_login_hint()

        # Prefer the cookie's own expiry; file age is only a fallback.
        remaining = _session_cookie_expiry(cookies.get("reddit_session"))
        if remaining is not None:
            if remaining <= 0:
                return "warn", (
                    f"rdt-cli 已安装，但 reddit_session 已于 {-remaining / 86400:.1f} "
                    "天前过期；请用 Cookie-Editor 重新导出。Doctor 不会自动读取"
                    "浏览器或刷新文件。"
                )
            due = (
                "，建议尽快用 Cookie-Editor 重新导出"
                if remaining < _EXPIRY_WARN_SECONDS
                else ""
            )
            return "warn", (
                f"rdt-cli 已安装，reddit_session 约 {remaining / 86400:.1f} 天后过期"
                f"{due}；Doctor 为避免上游自动刷新浏览器 Cookie，不执行 "
                "`rdt status`，因此未实时验证。"
            )

        saved_at = data.get("saved_at")
        if isinstance(saved_at, (int, float)) and (
            time.time() - saved_at > _CREDENTIAL_TTL_SECONDS
        ):
            return "warn", (
                "rdt-cli 已安装，保存的 Cookie 已超过 7 天；Doctor 不会让"
                "上游自动读取浏览器或刷新文件，请用 Cookie-Editor 明确更新。"
            )
        return "warn", (
            "rdt-cli 已安装并检测到显式保存的 Reddit Cookie；Doctor 为避免"
            "上游自动刷新浏览器 Cookie，不执行 `rdt status`，因此未实时验证。"
        )

    @staticmethod
    def _rdt_login_hint():
        return (
            "rdt-cli 已安装但没有可用的显式 Cookie。请使用 Cookie-Editor：\n"
            "  1. Chrome 应用商店安装 Cookie-Editor 扩展：\n"
            "     https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm\n"
            "  2. 在浏览器打开 reddit.com（确保已登录）\n"
            "  3. 点击 Cookie-Editor 图标，找到 `reddit_session`，复制其 Value\n"
            f"  4. 将以下内容写入 {_CREDENTIAL_FILE}：\n"
            '     {"cookies": {"reddit_session": "<粘贴 Value>"}, '
            '"source": "manual", "username": "<你的用户名>", '
            '"modhash": null, "saved_at": 0, "last_verified_at": null}\n\n'
            "Doctor 不会运行会自动读取浏览器并写文件的 `rdt status`。"
        )
