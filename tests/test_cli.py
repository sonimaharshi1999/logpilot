# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Tests for the CLI entry point."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from logpilot.cli import main
from logpilot.generator import generate_common_logs


class TestCLI:
    """Tests for Click CLI commands."""

    def test_version(self) -> None:
        """--version should print the package version."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "logpilot" in result.output

    def test_analyze_command(self, tmp_path: Path) -> None:
        """analyze command should run without error on valid input."""
        log_file = tmp_path / "test.log"
        lines = generate_common_logs(num_entries=100, seed=10)
        log_file.write_text("\n".join(lines), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(main, ["analyze", str(log_file)])
        assert result.exit_code == 0

    def test_detect_command(self, tmp_path: Path) -> None:
        """detect command should run without error."""
        log_file = tmp_path / "test.log"
        lines = generate_common_logs(num_entries=100, seed=11)
        log_file.write_text("\n".join(lines), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(main, ["detect", str(log_file)])
        assert result.exit_code == 0

    def test_report_command(self, tmp_path: Path) -> None:
        """report command should create a Markdown file."""
        log_file = tmp_path / "test.log"
        lines = generate_common_logs(num_entries=100, seed=12)
        log_file.write_text("\n".join(lines), encoding="utf-8")

        report_path = tmp_path / "out_report.md"
        runner = CliRunner()
        result = runner.invoke(main, ["report", str(log_file), "-o", str(report_path)])
        assert result.exit_code == 0
        assert report_path.exists()

    def test_generate_sample_command(self, tmp_path: Path) -> None:
        """generate-sample command should create sample files."""
        runner = CliRunner()
        out_dir = tmp_path / "samples"
        result = runner.invoke(main, ["generate-sample", "-o", str(out_dir)])
        assert result.exit_code == 0
        assert out_dir.exists()
        assert any(out_dir.iterdir())

    def test_analyze_missing_file(self) -> None:
        """analyze on a nonexistent file should fail cleanly."""
        runner = CliRunner()
        result = runner.invoke(main, ["analyze", "/nonexistent/path.log"])
        assert result.exit_code != 0
