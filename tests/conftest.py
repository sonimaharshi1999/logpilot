# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Shared pytest fixtures for LogPilot tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from logpilot.generator import generate_common_logs, generate_json_logs, generate_syslog_logs
from logpilot.models import AnalysisConfig, LogEntry, LogLevel


@pytest.fixture
def sample_entries() -> list[LogEntry]:
    """A small hand-crafted list of LogEntry objects for unit tests."""
    base = datetime(2024, 6, 15, 10, 0, 0)
    entries: list[LogEntry] = []

    # Normal INFO entries (30)
    for i in range(30):
        entries.append(
            LogEntry(
                timestamp=base + timedelta(seconds=i * 10),
                level=LogLevel.INFO,
                message=f"Request processed in {50 + i}ms",
                source="api-gateway",
                line_number=i + 1,
            )
        )

    # Spike of errors (15 entries in a 1-minute window)
    spike_start = base + timedelta(minutes=6)
    for i in range(15):
        entries.append(
            LogEntry(
                timestamp=spike_start + timedelta(seconds=i * 4),
                level=LogLevel.ERROR,
                message="Connection refused to payment-svc at node-3:5432",
                source="api-gateway",
                line_number=31 + i,
            )
        )

    # More normal entries (20)
    resume = base + timedelta(minutes=10)
    for i in range(20):
        entries.append(
            LogEntry(
                timestamp=resume + timedelta(seconds=i * 15),
                level=LogLevel.INFO,
                message=f"Health check passed for auth-service",
                source="auth-service",
                line_number=46 + i,
            )
        )

    # A few warnings
    for i in range(5):
        entries.append(
            LogEntry(
                timestamp=resume + timedelta(minutes=6, seconds=i * 20),
                level=LogLevel.WARNING,
                message="Slow query detected: 5000ms on users",
                source="user-db",
                line_number=66 + i,
            )
        )

    entries.sort(key=lambda e: e.timestamp)
    return entries


@pytest.fixture
def default_config() -> AnalysisConfig:
    """Default analysis configuration for tests."""
    return AnalysisConfig(
        time_window_minutes=2,
        anomaly_threshold=1.5,
        min_cluster_size=2,
    )


@pytest.fixture
def common_log_lines() -> list[str]:
    """Generate common-format log lines with a seed for reproducibility."""
    return generate_common_logs(num_entries=200, seed=42)


@pytest.fixture
def json_log_lines() -> list[str]:
    """Generate JSON-format log lines."""
    return generate_json_logs(num_entries=200, seed=43)


@pytest.fixture
def syslog_log_lines() -> list[str]:
    """Generate syslog-format log lines."""
    return generate_syslog_logs(num_entries=200, seed=44)


@pytest.fixture
def tmp_common_log(tmp_path: Path, common_log_lines: list[str]) -> Path:
    """Write common-format logs to a temp file and return the path."""
    p = tmp_path / "app.log"
    p.write_text("\n".join(common_log_lines), encoding="utf-8")
    return p


@pytest.fixture
def tmp_json_log(tmp_path: Path, json_log_lines: list[str]) -> Path:
    """Write JSON-format logs to a temp file and return the path."""
    p = tmp_path / "app.json.log"
    p.write_text("\n".join(json_log_lines), encoding="utf-8")
    return p


@pytest.fixture
def tmp_syslog_log(tmp_path: Path, syslog_log_lines: list[str]) -> Path:
    """Write syslog-format logs to a temp file and return the path."""
    p = tmp_path / "syslog.log"
    p.write_text("\n".join(syslog_log_lines), encoding="utf-8")
    return p
