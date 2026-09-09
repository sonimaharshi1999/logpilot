# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Tests for the anomaly detection module."""

from __future__ import annotations

from logpilot.detector import (
    cluster_errors,
    detect_all_anomalies,
    detect_error_rate_anomalies,
    detect_frequency_anomalies,
)
from logpilot.models import AnalysisConfig, AnomalyType, LogEntry


class TestFrequencyAnomalies:
    """Tests for frequency-based anomaly detection."""

    def test_detects_spike(
        self, sample_entries: list[LogEntry], default_config: AnalysisConfig
    ) -> None:
        """A concentrated burst of entries should be flagged as a frequency spike."""
        anomalies = detect_frequency_anomalies(sample_entries, default_config)
        # The sample_entries fixture has a 15-entry burst in 1 minute
        spike_types = [a for a in anomalies if a.anomaly_type == AnomalyType.FREQUENCY_SPIKE]
        assert len(spike_types) >= 1

    def test_no_anomaly_on_uniform(self, default_config: AnalysisConfig) -> None:
        """Uniformly spaced entries should produce no frequency anomalies."""
        from datetime import datetime, timedelta

        entries = [
            LogEntry(
                timestamp=datetime(2024, 1, 1, 10) + timedelta(minutes=i),
                level="INFO",
                message="ok",
                line_number=i,
            )
            for i in range(60)
        ]
        anomalies = detect_frequency_anomalies(entries, default_config)
        assert anomalies == []

    def test_too_few_entries(self, default_config: AnalysisConfig) -> None:
        """Fewer than 3 entries should return no anomalies."""
        from datetime import datetime

        entries = [
            LogEntry(timestamp=datetime(2024, 1, 1, 10), level="INFO", message="a", line_number=1)
        ]
        assert detect_frequency_anomalies(entries, default_config) == []


class TestErrorRateAnomalies:
    """Tests for error-rate anomaly detection."""

    def test_detects_error_surge(
        self, sample_entries: list[LogEntry], default_config: AnalysisConfig
    ) -> None:
        """A window with disproportionately many errors should be flagged."""
        anomalies = detect_error_rate_anomalies(sample_entries, default_config)
        surge_types = [a for a in anomalies if a.anomaly_type == AnomalyType.ERROR_RATE_SURGE]
        assert len(surge_types) >= 1


class TestClustering:
    """Tests for error message clustering."""

    def test_clusters_similar_errors(
        self, sample_entries: list[LogEntry], default_config: AnalysisConfig
    ) -> None:
        """Repeated identical error messages should form a cluster."""
        clusters = cluster_errors(sample_entries, default_config)
        # The fixture has 15 identical error messages
        assert len(clusters) >= 1
        assert clusters[0].count >= 2

    def test_empty_on_no_errors(self, default_config: AnalysisConfig) -> None:
        """No error entries should produce no clusters."""
        from datetime import datetime

        entries = [
            LogEntry(
                timestamp=datetime(2024, 1, 1, 10),
                level="INFO",
                message="all good",
                line_number=1,
            )
        ]
        clusters = cluster_errors(entries, default_config)
        assert clusters == []


class TestCombinedDetection:
    """Tests for the combined detect_all_anomalies function."""

    def test_combined_returns_sorted(
        self, sample_entries: list[LogEntry], default_config: AnalysisConfig
    ) -> None:
        """Combined anomalies should be sorted by severity descending."""
        anomalies = detect_all_anomalies(sample_entries, default_config)
        for i in range(1, len(anomalies)):
            assert anomalies[i].severity <= anomalies[i - 1].severity
