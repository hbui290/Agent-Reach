# -*- coding: utf-8 -*-
"""Tests for the Tavily-first web search backend routing."""

from pathlib import Path
from types import SimpleNamespace

import agent_reach.channels.exa_search as search_module
from agent_reach.channels.exa_search import ExaSearchChannel

ROOT = Path(__file__).resolve().parents[1]


class _Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_tavily_is_primary_and_usage_check_does_not_search(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _Response(200, {"key": {"usage": 12, "limit": 1000}})

    monkeypatch.setattr(search_module.requests, "get", fake_get)
    channel = ExaSearchChannel()

    status, message = channel.check({"tavily_api_key": "tvly-test"})

    assert status == "ok"
    assert channel.active_backend == channel.TAVILY_BACKEND
    assert calls == [
        (
            channel._TAVILY_USAGE_URL,
            {
                "headers": {"Authorization": "Bearer tvly-test"},
                "timeout": 10,
            },
        )
    ]
    assert "12/1000" in message


def test_invalid_tavily_key_reports_configured_but_unverified_exa(monkeypatch):
    monkeypatch.setattr(search_module.requests, "get", lambda *_a, **_k: _Response(401))
    monkeypatch.setattr(search_module.shutil, "which", lambda name: "/usr/bin/mcporter")
    monkeypatch.setattr(
        search_module,
        "inspect_mcporter_config",
        lambda: SimpleNamespace(
            server_names=frozenset({"exa"}),
            imports_unchecked=False,
        ),
    )
    channel = ExaSearchChannel()

    status, message = channel.check({"tavily_api_key": "tvly-invalid"})

    assert status == "warn"
    assert channel.active_backend is None
    assert "Tavily API key 无效" in message
    assert "Exa 已写入 mcporter 配置" in message


def test_search_backend_override_moves_exa_to_the_front():
    channel = ExaSearchChannel()

    ordered = channel.ordered_backends({"exa_search_backend": "exa"})

    assert ordered == [channel.EXA_BACKEND, channel.TAVILY_BACKEND]


def test_whitespace_backend_override_does_not_suppress_task_routing():
    channel = ExaSearchChannel()

    assert channel.backend_for_task("paper", {"search_backend": "   "}) == channel.EXA_BACKEND
    assert channel.ordered_backends({"search_backend": "   "}, task="paper") == [
        channel.EXA_BACKEND,
        channel.TAVILY_BACKEND,
    ]
    assert (
        channel.backend_for_task("general", {"search_backend": "  ", "web_search_backend": "exa"})
        == channel.EXA_BACKEND
    )


def test_unknown_override_does_not_hide_a_valid_lower_priority_override():
    channel = ExaSearchChannel()

    config = {"search_backend": "retired-provider", "exa_search_backend": "exa"}

    assert channel.backend_for_task("general", config) == channel.EXA_BACKEND


def test_tavily_usage_rejects_non_object_response(monkeypatch):
    monkeypatch.setattr(
        search_module.requests,
        "get",
        lambda *_a, **_k: _Response(200, ["not-an-object"]),
    )
    channel = ExaSearchChannel()

    status, message = channel._check_tavily({"tavily_api_key": "tvly-test"})

    assert status == "warn"
    assert "格式" in message


def test_tavily_usage_requires_key_object(monkeypatch):
    channel = ExaSearchChannel()

    for payload in ({}, {"key": None}, {"key": []}):
        monkeypatch.setattr(
            search_module.requests,
            "get",
            lambda *_a, payload=payload, **_k: _Response(200, payload),
        )

        status, message = channel._check_tavily({"tavily_api_key": "tvly-test"})

        assert status == "warn"
        assert "格式" in message


def test_tavily_ignores_non_numeric_usage_counters(monkeypatch):
    payload = {
        "key": {"usage": None, "limit": "1000"},
        "account": {
            "plan_usage": True,
            "plan_limit": 100,
            "paygo_usage": [],
            "paygo_limit": {},
        },
    }
    monkeypatch.setattr(search_module.requests, "get", lambda *_a, **_k: _Response(200, payload))
    channel = ExaSearchChannel()

    status, message = channel._check_tavily({"tavily_api_key": "tvly-test"})

    assert status == "ok"
    assert "credits" not in message


def test_tavily_warns_when_plan_and_paygo_credits_are_exhausted(monkeypatch):
    payload = {
        "key": {"usage": 900, "limit": 1000},
        "account": {
            "plan_usage": 15000,
            "plan_limit": 15000,
            "paygo_usage": 100,
            "paygo_limit": 100,
        },
    }
    monkeypatch.setattr(search_module.requests, "get", lambda *_a, **_k: _Response(200, payload))
    channel = ExaSearchChannel()

    status, message = channel._check_tavily({"tavily_api_key": "tvly-test"})

    assert status == "warn"
    assert "额度已用完" in message


def test_tavily_accepts_remaining_paygo_credits_after_plan_limit(monkeypatch):
    payload = {
        "key": {"usage": 900, "limit": 1000},
        "account": {
            "plan_usage": 15000,
            "plan_limit": 15000,
            "paygo_usage": 30,
            "paygo_limit": 100,
        },
    }
    monkeypatch.setattr(search_module.requests, "get", lambda *_a, **_k: _Response(200, payload))
    channel = ExaSearchChannel()

    status, message = channel._check_tavily({"tavily_api_key": "tvly-test"})

    assert status == "ok"
    assert "30/100" in message


def test_tavily_warns_when_key_limit_is_exhausted_with_paygo_remaining(monkeypatch):
    payload = {
        "key": {"usage": 1000, "limit": 1000},
        "account": {
            "plan_usage": 15000,
            "plan_limit": 15000,
            "paygo_usage": 30,
            "paygo_limit": 100,
        },
    }
    monkeypatch.setattr(search_module.requests, "get", lambda *_a, **_k: _Response(200, payload))
    channel = ExaSearchChannel()

    status, message = channel._check_tavily({"tavily_api_key": "tvly-test"})

    assert status == "warn"
    assert "API key 用量上限已用完" in message
    assert "30/100" in message


def test_specialized_tasks_route_to_exa_and_general_tasks_to_tavily():
    channel = ExaSearchChannel()

    for task in (
        "paper",
        "论文",
        "company",
        "公司",
        "people",
        "人物",
        "semantic",
        "语义",
        "rag",
        "similar",
        "research paper",
        "technical research",
        "financial report",
        "similar page",
        "rag retrieval",
    ):
        assert channel.backend_for_task(task) == channel.EXA_BACKEND
    for task in ("general", "news", "extract", "crawl", "research"):
        assert channel.backend_for_task(task) == channel.TAVILY_BACKEND


def test_explicit_backend_override_wins_over_task_route():
    channel = ExaSearchChannel()

    assert channel.backend_for_task("paper", {"search_backend": "tavily"}) == channel.TAVILY_BACKEND


def test_task_route_orders_health_checks_without_claiming_unverified_exa(monkeypatch):
    channel = ExaSearchChannel()
    assert channel.ordered_backends(task="paper") == [
        channel.EXA_BACKEND,
        channel.TAVILY_BACKEND,
    ]

    calls = []
    monkeypatch.setattr(
        channel,
        "_check_exa",
        lambda: calls.append(channel.EXA_BACKEND) or ("warn", "Exa configured but unverified"),
    )
    monkeypatch.setattr(
        channel,
        "_check_tavily",
        lambda _config: calls.append(channel.TAVILY_BACKEND) or ("ok", "Tavily verified"),
    )
    status, _ = channel.check(task="paper")

    assert status == "ok"
    assert channel.active_backend == channel.TAVILY_BACKEND
    assert calls == [channel.EXA_BACKEND, channel.TAVILY_BACKEND]


def test_root_readme_summarizes_the_fork_search_changes():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "What This Fork Changes" in readme
    assert "Panniantong/Agent-Reach" in readme
    assert "Tavily is the default" in readme
    assert "Exa remains available" in readme
    assert "without spending a search credit" in readme
