# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Synthetic log generator for testing and demonstration."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


_SERVICES = ["api-gateway", "auth-service", "payment-svc", "user-db", "cache-layer"]

_INFO_TEMPLATES = [
    "Request processed successfully in {ms}ms",
    "Health check passed for {service}",
    "Connection pool size: {pool_size}",
    "Cache hit ratio: {ratio:.2f}",
    "Scheduled job {job_id} completed",
    "User {user_id} authenticated via OAuth",
    "Rate limit bucket refilled for {service}",
]

_WARNING_TEMPLATES = [
    "Slow query detected: {ms}ms on {table}",
    "Connection pool nearing capacity: {pool_size}/{max_pool}",
    "Retry attempt {attempt}/3 for {service}",
    "Disk usage at {usage}% on {host}",
    "Certificate expires in {days} days",
    "Memory usage elevated: {mem_pct}% of allocated",
]

_ERROR_TEMPLATES = [
    "Connection refused to {service} at {host}:{port}",
    "Timeout after {ms}ms waiting for {service}",
    "NullPointerException in {module}.{method}",
    "Database connection pool exhausted: {pool_size}/{max_pool}",
    "Failed to parse request body: invalid JSON at position {pos}",
    "Authentication failed for user {user_id}: invalid token",
    "OutOfMemoryError in {service}: heap space exceeded",
    "Disk write failed on {host}: no space left on device",
]

_CRITICAL_TEMPLATES = [
    "Service {service} is DOWN -- health check failed {count} times",
    "Data corruption detected in {table} -- checksum mismatch",
    "Cascading failure: {service} triggering circuit breaker",
    "Security alert: unauthorized access attempt from {ip}",
]


def _random_ip() -> str:
    """Generate a random private IP address."""
    return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def _fill_template(template: str) -> str:
    """Fill a log message template with plausible random values."""
    replacements: dict[str, str] = {
        "{ms}": str(random.randint(1, 30000)),
        "{service}": random.choice(_SERVICES),
        "{pool_size}": str(random.randint(5, 95)),
        "{max_pool}": str(100),
        "{ratio}": f"{random.random():.2f}",
        "{job_id}": f"job-{random.randint(1000, 9999)}",
        "{user_id}": f"usr-{random.randint(10000, 99999)}",
        "{table}": random.choice(["users", "orders", "sessions", "events"]),
        "{host}": f"node-{random.randint(1, 12)}",
        "{port}": str(random.choice([5432, 6379, 8080, 3306, 9200])),
        "{module}": random.choice(["RequestHandler", "AuthManager", "PaymentProcessor"]),
        "{method}": random.choice(["process", "validate", "execute", "handle"]),
        "{pos}": str(random.randint(0, 500)),
        "{attempt}": str(random.randint(1, 3)),
        "{usage}": str(random.randint(80, 99)),
        "{days}": str(random.randint(1, 14)),
        "{mem_pct}": str(random.randint(85, 99)),
        "{count}": str(random.randint(3, 10)),
        "{ip}": _random_ip(),
    }
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


def generate_common_logs(
    num_entries: int = 500,
    start_time: Optional[datetime] = None,
    error_spike: bool = True,
    seed: Optional[int] = None,
) -> list[str]:
    """Generate synthetic log lines in common timestamp+level format.

    Produces realistic application logs with an optional error spike in
    the middle of the time range to test anomaly detection.

    Args:
        num_entries: Total number of log lines to produce.
        start_time: Starting timestamp (defaults to now minus 2 hours).
        error_spike: Whether to inject an error spike for anomaly testing.
        seed: Optional random seed for reproducibility.

    Returns:
        A list of formatted log strings.
    """
    if seed is not None:
        random.seed(seed)

    if start_time is None:
        # Use a fixed start time when seed is set, for reproducibility
        if seed is not None:
            start_time = datetime(2024, 6, 15, 8, 0, 0)
        else:
            start_time = datetime.now() - timedelta(hours=2)

    lines: list[str] = []
    current = start_time
    interval = timedelta(seconds=max(1, 7200 // num_entries))

    spike_start = num_entries // 3
    spike_end = spike_start + num_entries // 6

    for i in range(num_entries):
        # Determine log level probabilities
        if error_spike and spike_start <= i < spike_end:
            # Error spike zone: much higher error/critical rate
            level_weights = {"INFO": 20, "WARNING": 20, "ERROR": 50, "CRITICAL": 10}
        else:
            level_weights = {"INFO": 70, "WARNING": 15, "ERROR": 12, "CRITICAL": 3}

        level = random.choices(
            list(level_weights.keys()),
            weights=list(level_weights.values()),
            k=1,
        )[0]

        if level == "INFO":
            message = _fill_template(random.choice(_INFO_TEMPLATES))
        elif level == "WARNING":
            message = _fill_template(random.choice(_WARNING_TEMPLATES))
        elif level == "ERROR":
            message = _fill_template(random.choice(_ERROR_TEMPLATES))
        else:
            message = _fill_template(random.choice(_CRITICAL_TEMPLATES))

        source = random.choice(_SERVICES)
        ts = current.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        lines.append(f"{ts} {level} [{source}] {message}")

        # Add small jitter to the interval
        jitter = timedelta(milliseconds=random.randint(-500, 500))
        current += interval + jitter

    return lines


def generate_json_logs(
    num_entries: int = 500,
    start_time: Optional[datetime] = None,
    error_spike: bool = True,
    seed: Optional[int] = None,
) -> list[str]:
    """Generate synthetic log lines in JSON format.

    Args:
        num_entries: Total number of log lines.
        start_time: Starting timestamp.
        error_spike: Inject an error spike for testing.
        seed: Random seed.

    Returns:
        A list of JSON-encoded log strings.
    """
    if seed is not None:
        random.seed(seed)

    if start_time is None:
        if seed is not None:
            start_time = datetime(2024, 6, 15, 8, 0, 0)
        else:
            start_time = datetime.now() - timedelta(hours=2)

    lines: list[str] = []
    current = start_time
    interval = timedelta(seconds=max(1, 7200 // num_entries))

    spike_start = num_entries // 3
    spike_end = spike_start + num_entries // 6

    for i in range(num_entries):
        if error_spike and spike_start <= i < spike_end:
            level_weights = {"INFO": 20, "WARNING": 20, "ERROR": 50, "CRITICAL": 10}
        else:
            level_weights = {"INFO": 70, "WARNING": 15, "ERROR": 12, "CRITICAL": 3}

        level = random.choices(
            list(level_weights.keys()),
            weights=list(level_weights.values()),
            k=1,
        )[0]

        if level == "INFO":
            message = _fill_template(random.choice(_INFO_TEMPLATES))
        elif level == "WARNING":
            message = _fill_template(random.choice(_WARNING_TEMPLATES))
        elif level == "ERROR":
            message = _fill_template(random.choice(_ERROR_TEMPLATES))
        else:
            message = _fill_template(random.choice(_CRITICAL_TEMPLATES))

        service = random.choice(_SERVICES)
        record = {
            "timestamp": current.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
            "level": level,
            "service": service,
            "message": message,
            "request_id": f"req-{random.randint(100000, 999999)}",
            "host": f"node-{random.randint(1, 12)}",
        }
        lines.append(json.dumps(record))

        jitter = timedelta(milliseconds=random.randint(-500, 500))
        current += interval + jitter

    return lines


def generate_syslog_logs(
    num_entries: int = 500,
    start_time: Optional[datetime] = None,
    error_spike: bool = True,
    seed: Optional[int] = None,
) -> list[str]:
    """Generate synthetic log lines in syslog format.

    Args:
        num_entries: Total number of log lines.
        start_time: Starting timestamp.
        error_spike: Inject an error spike for testing.
        seed: Random seed.

    Returns:
        A list of syslog-formatted log strings.
    """
    if seed is not None:
        random.seed(seed)

    if start_time is None:
        if seed is not None:
            start_time = datetime(2024, 6, 15, 8, 0, 0)
        else:
            start_time = datetime.now() - timedelta(hours=2)

    lines: list[str] = []
    current = start_time
    interval = timedelta(seconds=max(1, 7200 // num_entries))

    spike_start = num_entries // 3
    spike_end = spike_start + num_entries // 6

    hostnames = ["web-01", "web-02", "db-master", "cache-01", "worker-03"]

    for i in range(num_entries):
        if error_spike and spike_start <= i < spike_end:
            level_weights = {"INFO": 20, "WARNING": 20, "ERROR": 50, "CRITICAL": 10}
        else:
            level_weights = {"INFO": 70, "WARNING": 15, "ERROR": 12, "CRITICAL": 3}

        level = random.choices(
            list(level_weights.keys()),
            weights=list(level_weights.values()),
            k=1,
        )[0]

        if level == "INFO":
            message = _fill_template(random.choice(_INFO_TEMPLATES))
        elif level == "WARNING":
            message = _fill_template(random.choice(_WARNING_TEMPLATES))
        elif level == "ERROR":
            message = _fill_template(random.choice(_ERROR_TEMPLATES))
        else:
            message = _fill_template(random.choice(_CRITICAL_TEMPLATES))

        hostname = random.choice(hostnames)
        service = random.choice(_SERVICES)
        pid = random.randint(1000, 65535)
        ts = current.strftime("%b %d %H:%M:%S")
        # Syslog: "Sep  9 14:23:01 hostname app[pid]: LEVEL message"
        lines.append(f"{ts} {hostname} {service}[{pid}]: {level} {message}")

        jitter = timedelta(milliseconds=random.randint(-500, 500))
        current += interval + jitter

    return lines


def write_sample_logs(output_dir: Path, seed: int = 42) -> dict[str, Path]:
    """Write sample log files in all supported formats to a directory.

    Args:
        output_dir: Directory to write files into.
        seed: Random seed for reproducibility.

    Returns:
        A dict mapping format name to file path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, Path] = {}

    common_path = output_dir / "sample_app.log"
    common_path.write_text(
        "\n".join(generate_common_logs(num_entries=500, seed=seed)),
        encoding="utf-8",
    )
    files["common"] = common_path

    json_path = output_dir / "sample_app.json.log"
    json_path.write_text(
        "\n".join(generate_json_logs(num_entries=500, seed=seed + 1)),
        encoding="utf-8",
    )
    files["json"] = json_path

    syslog_path = output_dir / "sample_syslog.log"
    syslog_path.write_text(
        "\n".join(generate_syslog_logs(num_entries=500, seed=seed + 2)),
        encoding="utf-8",
    )
    files["syslog"] = syslog_path

    return files
