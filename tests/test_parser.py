# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Tests for the log parser module."""

from __future__ import annotations

from pathlib import Path

from logpilot.models import AnalysisConfig, LogFormat, LogLevel
from logpilot.parser import parse_log_file, parse_log_lines


class TestCommonFormatParsing:
    """Tests for common timestamp+level log format."""

    def test_parse_common_format_entries(
        self, tmp_common_log: Path, default_config: AnalysisConfig
    ) -> None:
        """Parsing common-format logs should produce entries with correct fields."""
        entries = parse_log_file(tmp_common_log, default_config)
        assert len(entries) > 0
        for entry in entries:
            assert entry.timestamp is not None
            assert entry.level in LogLevel
            assert entry.message != ""

    def test_parse_common_format_sorted(self, tmp_common_log: Path) -> None:
        """Parsed entries should be sorted by timestamp."""
        entries = parse_log_file(tmp_common_log)
        for i in range(1, len(entries)):
            assert entries[i].timestamp >= entries[i - 1].timestamp


class TestJsonFormatParsing:
    """Tests for JSON log format."""

    def test_parse_json_format(
        self, tmp_json_log: Path, default_config: AnalysisConfig
    ) -> None:
        """Parsing JSON logs should extract all fields correctly."""
        config = AnalysisConfig(log_format=LogFormat.JSON)
        entries = parse_log_file(tmp_json_log, config)
        assert len(entries) > 0
        for entry in entries:
            assert entry.timestamp is not None
            assert entry.level in LogLevel
            assert entry.message != ""

    def test_json_metadata_extraction(self, json_log_lines: list[str]) -> None:
        """JSON parser should capture extra fields as metadata."""
        config = AnalysisConfig(log_format=LogFormat.JSON)
        entries = parse_log_lines(json_log_lines[:10], config)
        assert len(entries) > 0
        # Our generator includes request_id and host as extra fields
        for entry in entries:
            assert "request_id" in entry.metadata or "host" in entry.metadata


class TestSyslogFormatParsing:
    """Tests for syslog format."""

    def test_parse_syslog_format(
        self, tmp_syslog_log: Path, default_config: AnalysisConfig
    ) -> None:
        """Parsing syslog-format logs should produce valid entries."""
        config = AnalysisConfig(log_format=LogFormat.SYSLOG)
        entries = parse_log_file(tmp_syslog_log, config)
        assert len(entries) > 0
        for entry in entries:
            assert entry.source != "unknown"


class TestAutoDetection:
    """Tests for automatic format detection."""

    def test_auto_detect_json(self, tmp_json_log: Path) -> None:
        """Auto-detection should correctly parse JSON logs without explicit format."""
        entries = parse_log_file(tmp_json_log)
        assert len(entries) > 0

    def test_auto_detect_common(self, tmp_common_log: Path) -> None:
        """Auto-detection should correctly parse common-format logs."""
        entries = parse_log_file(tmp_common_log)
        assert len(entries) > 0


class TestEdgeCases:
    """Tests for parser edge cases."""

    def test_empty_file(self, tmp_path: Path) -> None:
        """Parsing an empty file should return an empty list."""
        empty = tmp_path / "empty.log"
        empty.write_text("", encoding="utf-8")
        entries = parse_log_file(empty)
        assert entries == []

    def test_blank_lines_skipped(self, tmp_path: Path) -> None:
        """Blank lines should be silently skipped."""
        content = (
            "2024-06-15 10:00:00,000 INFO [test] First entry\n"
            "\n"
            "\n"
            "2024-06-15 10:00:01,000 ERROR [test] Second entry\n"
        )
        p = tmp_path / "blanks.log"
        p.write_text(content, encoding="utf-8")
        entries = parse_log_file(p)
        assert len(entries) == 2

    def test_malformed_lines_skipped(self, tmp_path: Path) -> None:
        """Lines that match no format should be skipped without error."""
        content = (
            "2024-06-15 10:00:00,000 INFO [test] Valid entry\n"
            "this is just random garbage text\n"
            "another broken line 12345\n"
            "2024-06-15 10:00:05,000 ERROR [test] Also valid\n"
        )
        p = tmp_path / "mixed.log"
        p.write_text(content, encoding="utf-8")
        entries = parse_log_file(p)
        assert len(entries) == 2
