# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Multi-format log parser supporting JSON, syslog, and custom regex patterns."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import AnalysisConfig, LogEntry, LogFormat, LogLevel

# -- Syslog pattern --------------------------------------------------------
# Matches: "Sep  9 14:23:01 hostname app[1234]: ERROR message here"
_SYSLOG_RE = re.compile(
    r"(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+"
    r"(?P<source>\S+?)(?:\[\d+\])?:\s+"
    r"(?:(?P<level>DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\s+)?"
    r"(?P<message>.*)"
)

# -- Common timestamp-prefixed log pattern ----------------------------------
# Matches: "2024-01-15 14:23:01,123 ERROR [module] message"
_COMMON_RE = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)\s+"
    r"(?P<level>DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\s+"
    r"(?:\[(?P<source>[^\]]+)\]\s+)?"
    r"(?P<message>.*)"
)

_LEVEL_MAP: dict[str, LogLevel] = {
    "DEBUG": LogLevel.DEBUG,
    "INFO": LogLevel.INFO,
    "WARNING": LogLevel.WARNING,
    "WARN": LogLevel.WARNING,
    "ERROR": LogLevel.ERROR,
    "CRITICAL": LogLevel.CRITICAL,
    "FATAL": LogLevel.CRITICAL,
}


def _normalize_level(raw: str) -> LogLevel:
    """Normalize a raw log level string to a LogLevel enum value."""
    return _LEVEL_MAP.get(raw.upper(), LogLevel.INFO)


def _parse_timestamp(raw: str) -> datetime:
    """Try multiple timestamp formats and return a datetime."""
    formats = [
        "%Y-%m-%d %H:%M:%S,%f",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S,%f",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unable to parse timestamp: {raw!r}")


def _parse_syslog_timestamp(raw: str) -> datetime:
    """Parse a syslog-style timestamp, assuming the current year."""
    now = datetime.now()
    try:
        dt = datetime.strptime(raw, "%b %d %H:%M:%S")
        return dt.replace(year=now.year)
    except ValueError:
        return datetime.strptime(raw, "%b  %d %H:%M:%S").replace(year=now.year)


def _detect_format(line: str) -> LogFormat:
    """Auto-detect the format of a single log line."""
    stripped = line.strip()
    if not stripped:
        return LogFormat.CUSTOM
    if stripped.startswith("{"):
        try:
            json.loads(stripped)
            return LogFormat.JSON
        except json.JSONDecodeError:
            pass
    if _SYSLOG_RE.match(stripped):
        return LogFormat.SYSLOG
    if _COMMON_RE.match(stripped):
        return LogFormat.CUSTOM  # handled by common pattern
    return LogFormat.CUSTOM


def _parse_json_line(line: str, line_number: int) -> Optional[LogEntry]:
    """Parse a JSON-formatted log line."""
    try:
        data = json.loads(line.strip())
    except json.JSONDecodeError:
        return None

    ts_raw = data.get("timestamp") or data.get("time") or data.get("@timestamp", "")
    level_raw = data.get("level") or data.get("severity") or data.get("log_level", "INFO")
    message = data.get("message") or data.get("msg") or data.get("text", "")
    source = data.get("source") or data.get("logger") or data.get("service", "unknown")

    try:
        timestamp = _parse_timestamp(str(ts_raw))
    except ValueError:
        return None

    metadata: dict[str, str] = {}
    skip_keys = {"timestamp", "time", "@timestamp", "level", "severity", "log_level",
                 "message", "msg", "text", "source", "logger", "service"}
    for k, v in data.items():
        if k not in skip_keys:
            metadata[k] = str(v)

    return LogEntry(
        timestamp=timestamp,
        level=_normalize_level(str(level_raw)),
        message=str(message),
        source=str(source),
        line_number=line_number,
        raw=line.strip(),
        metadata=metadata,
    )


def _parse_syslog_line(line: str, line_number: int) -> Optional[LogEntry]:
    """Parse a syslog-formatted log line."""
    match = _SYSLOG_RE.match(line.strip())
    if not match:
        return None

    try:
        timestamp = _parse_syslog_timestamp(match.group("timestamp"))
    except ValueError:
        return None

    level_raw = match.group("level") or "INFO"

    return LogEntry(
        timestamp=timestamp,
        level=_normalize_level(level_raw),
        message=match.group("message"),
        source=match.group("source"),
        line_number=line_number,
        raw=line.strip(),
    )


def _parse_common_line(line: str, line_number: int) -> Optional[LogEntry]:
    """Parse a common timestamp+level log line."""
    match = _COMMON_RE.match(line.strip())
    if not match:
        return None

    try:
        timestamp = _parse_timestamp(match.group("timestamp"))
    except ValueError:
        return None

    return LogEntry(
        timestamp=timestamp,
        level=_normalize_level(match.group("level")),
        message=match.group("message"),
        source=match.group("source") or "unknown",
        line_number=line_number,
        raw=line.strip(),
    )


def _parse_custom_line(
    line: str, line_number: int, pattern: Optional[str] = None
) -> Optional[LogEntry]:
    """Parse a line using a custom regex or fall back to the common pattern."""
    if pattern:
        match = re.match(pattern, line.strip())
        if match:
            groups = match.groupdict()
            try:
                timestamp = _parse_timestamp(groups.get("timestamp", ""))
            except (ValueError, KeyError):
                return None
            return LogEntry(
                timestamp=timestamp,
                level=_normalize_level(groups.get("level", "INFO")),
                message=groups.get("message", line.strip()),
                source=groups.get("source", "unknown"),
                line_number=line_number,
                raw=line.strip(),
            )
    # Fall back to common pattern
    return _parse_common_line(line, line_number)


def parse_log_file(
    path: Path,
    config: Optional[AnalysisConfig] = None,
) -> list[LogEntry]:
    """Parse a log file and return structured log entries.

    Args:
        path: Path to the log file.
        config: Optional analysis configuration for format and pattern hints.

    Returns:
        A list of parsed LogEntry objects, sorted by timestamp.
    """
    if config is None:
        config = AnalysisConfig()

    entries: list[LogEntry] = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    detected_format = config.log_format
    if detected_format == LogFormat.AUTO and lines:
        # Sample first non-empty line for detection
        for sample in lines:
            if sample.strip():
                detected_format = _detect_format(sample)
                break

    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        entry: Optional[LogEntry] = None

        if detected_format == LogFormat.JSON:
            entry = _parse_json_line(line, idx)
        elif detected_format == LogFormat.SYSLOG:
            entry = _parse_syslog_line(line, idx)
        elif detected_format == LogFormat.CUSTOM:
            entry = _parse_custom_line(line, idx, config.custom_pattern)
        else:
            # AUTO fallback: try each parser
            entry = _parse_json_line(line, idx)
            if entry is None:
                entry = _parse_syslog_line(line, idx)
            if entry is None:
                entry = _parse_common_line(line, idx)

        if entry is not None:
            entries.append(entry)

    entries.sort(key=lambda e: e.timestamp)
    return entries


def parse_log_lines(
    lines: list[str],
    config: Optional[AnalysisConfig] = None,
) -> list[LogEntry]:
    """Parse log lines directly (for testing or piped input).

    Args:
        lines: Raw log lines.
        config: Optional analysis configuration.

    Returns:
        A list of parsed LogEntry objects, sorted by timestamp.
    """
    if config is None:
        config = AnalysisConfig()

    detected_format = config.log_format
    if detected_format == LogFormat.AUTO and lines:
        for sample in lines:
            if sample.strip():
                detected_format = _detect_format(sample)
                break

    entries: list[LogEntry] = []
    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        entry: Optional[LogEntry] = None
        if detected_format == LogFormat.JSON:
            entry = _parse_json_line(line, idx)
        elif detected_format == LogFormat.SYSLOG:
            entry = _parse_syslog_line(line, idx)
        elif detected_format == LogFormat.CUSTOM:
            entry = _parse_custom_line(line, idx, config.custom_pattern)
        else:
            entry = _parse_json_line(line, idx)
            if entry is None:
                entry = _parse_syslog_line(line, idx)
            if entry is None:
                entry = _parse_common_line(line, idx)
        if entry is not None:
            entries.append(entry)

    entries.sort(key=lambda e: e.timestamp)
    return entries
