# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Tests for the report generation module."""

from __future__ import annotations

from pathlib import Path

from logpilot.correlator import find_correlations
from logpilot.detector import cluster_errors, detect_all_anomalies
from logpilot.models import AnalysisConfig, LogEntry
from logpilot.reporter import build_report, render_markdown, save_report


class TestReportGeneration:
    """Tests for incident report building and rendering."""

    def test_build_report_fields(
        self, sample_entries: list[LogEntry], default_config: AnalysisConfig
    ) -> None:
        """Built report should populate all top-level fields."""
        anomalies = detect_all_anomalies(sample_entries, default_config)
        clusters = cluster_errors(sample_entries, default_config)
        correlations = find_correlations(sample_entries, default_config)

        report = build_report(sample_entries, anomalies, clusters, correlations)

        assert report.total_entries == len(sample_entries)
        assert report.error_count > 0
        assert report.summary != ""
        assert len(report.recommendations) > 0

    def test_render_markdown_structure(
        self, sample_entries: list[LogEntry], default_config: AnalysisConfig
    ) -> None:
        """Rendered Markdown should contain expected headings."""
        anomalies = detect_all_anomalies(sample_entries, default_config)
        clusters = cluster_errors(sample_entries, default_config)
        correlations = find_correlations(sample_entries, default_config)
        report = build_report(sample_entries, anomalies, clusters, correlations)

        md = render_markdown(report)

        assert "# LogPilot Incident Report" in md
        assert "## Executive Summary" in md
        assert "## Statistics" in md
        assert "## Recommendations" in md

    def test_save_report_writes_file(
        self,
        tmp_path: Path,
        sample_entries: list[LogEntry],
        default_config: AnalysisConfig,
    ) -> None:
        """save_report should write a .md file to disk."""
        anomalies = detect_all_anomalies(sample_entries, default_config)
        clusters = cluster_errors(sample_entries, default_config)
        correlations = find_correlations(sample_entries, default_config)
        report = build_report(sample_entries, anomalies, clusters, correlations)

        out = tmp_path / "report.md"
        result = save_report(report, out)

        assert result == out
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "LogPilot" in content
