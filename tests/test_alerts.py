"""Validation tests for Prometheus alerting rules, promtool unit tests, and runbook completeness."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from src.core import metrics

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_ALERTS = {
    "GetnetHighErrorRate",
    "GetnetHighChatLatencyP95",
    "GetnetLLMErrorsOrFallbacks",
    "GetnetGuardrailClassifierDegraded",
    "GetnetRateLimitBackendErrors",
    "GetnetOperatorNotificationFailures",
    "GetnetMerchantNotificationFailures",
    "GetnetOldestOpenTicketAge",
    "GetnetHighAbstentionRate",
    "GetnetEstimatedCostPerHour",
    "GetnetReplicaDown",
}

EXPECTED_NEW_METRICS = {
    "getnet_llm_calls_total",
    "getnet_guardrail_classifier_total",
    "getnet_estimated_cost_usd_total",
    "getnet_merchant_notifications_total",
    "getnet_sse_connections",
    "getnet_open_ticket_oldest_age_seconds",
}

RUNBOOK_SECTIONS = (
    "O que significa",
    "Primeiras verificações",
    "Mitigação",
    "Escalonamento",
)


def test_alerts_yml_and_runbook_cover_all_alerts() -> None:
    alerts_doc = yaml.safe_load((ROOT / "deploy" / "alerts.yml").read_text(encoding="utf-8"))
    rules = [r for grp in alerts_doc["groups"] for r in grp["rules"]]
    by_name = {r["alert"]: r for r in rules}
    assert set(by_name) == EXPECTED_ALERTS

    runbook_text = (ROOT / "docs" / "RUNBOOK.md").read_text(encoding="utf-8")
    sections = re.split(r"(?m)^##\s+", runbook_text)
    by_anchor: dict[str, str] = {}
    for sec in sections[1:]:
        heading = sec.splitlines()[0].strip()
        anchor = re.sub(r"[^a-z0-9]+", "", heading.lower())
        by_anchor[anchor] = sec

    for name, rule in by_name.items():
        severity = rule["labels"]["severity"]
        assert severity in {"warning", "critical"}
        url = rule["annotations"]["runbook_url"]
        assert "#" in url
        anchor = url.split("#", 1)[1].lower()
        assert anchor == name.lower()
        assert anchor in by_anchor, f"Missing runbook section for {name}"
        for part in RUNBOOK_SECTIONS:
            assert part in by_anchor[anchor], f"{name} missing '{part}'"


def test_promtool_unit_tests_cover_firing_and_silent_for_every_alert() -> None:
    test_doc = yaml.safe_load((ROOT / "deploy" / "alerts_test.yml").read_text(encoding="utf-8"))
    prom_doc = yaml.safe_load((ROOT / "deploy" / "prometheus.yml").read_text(encoding="utf-8"))
    assert "alerts.yml" in " ".join(prom_doc.get("rule_files") or [])

    firing: set[str] = set()
    silent: set[str] = set()
    for tc in test_doc["tests"]:
        for art in tc.get("alert_rule_test") or []:
            alertname = art["alertname"]
            if art.get("exp_alerts"):
                firing.add(alertname)
            else:
                silent.add(alertname)

    assert EXPECTED_ALERTS <= firing
    assert EXPECTED_ALERTS <= silent


def test_alert_metrics_and_new_metrics_exported_from_startup() -> None:
    rendered = metrics.render()
    typed = set(re.findall(r"(?m)^# TYPE (\S+) ", rendered))
    assert EXPECTED_NEW_METRICS <= typed

    alerts_doc = yaml.safe_load((ROOT / "deploy" / "alerts.yml").read_text(encoding="utf-8"))
    for grp in alerts_doc["groups"]:
        for rule in grp["rules"]:
            for m in re.findall(r"\b(getnet_[a-z0-9_]+)", str(rule["expr"])):
                base = re.sub(r"_(bucket|sum|count)$", "", m)
                assert base in typed, f"Metric {base} referenced in alert {rule['alert']} not exported at startup"
