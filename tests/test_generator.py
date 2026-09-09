# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Tests for the synthetic log generator."""

from __future__ import annotations

import json
from pathlib import Path

from logpilot.generator import (
    generate_common_logs,
    generate_json_logs,
    generate_syslog_logs,
    write_sample_logs,
)


class TestLogGeneration:
    """Tests for synthetic log generation."""

    def test_common_log_count(self) -> None:
        """Generator should produce the requested number of lines."""
        lines = generate_common_logs(num_entries=100, seed=1)
        assert len(lines) == 100

    def test_json_logs_are_valid_json(self) -> None:
        """Every JSON log line should parse as valid JSON."""
        lines = generate_json_logs(num_entries=50, seed=2)
        for line in lines:
            data = json.loads(line)
            assert "timestamp" in data
            assert "level" in data
            assert "message" in data

    def test_syslog_format(self) -> None:
        """Syslog lines should contain expected structural elements."""
        lines = generate_syslog_logs(num_entries=50, seed=3)
        for line in lines:
            # Should have a bracket-enclosed PID
            assert "[" in line and "]" in line

    def test_reproducibility(self) -> None:
        """Same seed should produce identical output."""
        a = generate_common_logs(num_entries=50, seed=99)
        b = generate_common_logs(num_entries=50, seed=99)
        assert a == b

    def test_write_sample_logs(self, tmp_path: Path) -> None:
        """write_sample_logs should create files in all formats."""
        files = write_sample_logs(tmp_path, seed=42)
        assert "common" in files
        assert "json" in files
        assert "syslog" in files
        for path in files.values():
            assert path.exists()
            assert path.stat().st_size > 0
