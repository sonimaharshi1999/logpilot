# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Tests for the correlation engine."""

from __future__ import annotations

from datetime import datetime, timedelta

from logpilot.correlator import find_correlations
from logpilot.models import AnalysisConfig, LogEntry, LogLevel


class TestCorrelation:
    """Tests for time-window correlation detection."""

    def test_finds_correlated_patterns(self) -> None:
        """Two error patterns that consistently co-occur should be correlated."""
        config = AnalysisConfig(time_window_minutes=5)
        entries: list[LogEntry] = []

        base = datetime(2024, 6, 15, 10, 0, 0)

        # Pattern A always followed by Pattern B ~30s later, repeated 5 times
        for i in range(5):
            offset = timedelta(minutes=i * 10)
            entries.append(
                LogEntry(
                    timestamp=base + offset,
                    level=LogLevel.ERROR,
                    message="Connection refused to payment-svc at node-3:5432",
                    source="api-gateway",
                    line_number=i * 2 + 1,
                )
            )
            entries.append(
                LogEntry(
                    timestamp=base + offset + timedelta(seconds=30),
                    level=LogLevel.ERROR,
                    message="Timeout after 5000ms waiting for payment-svc",
                    source="api-gateway",
                    line_number=i * 2 + 2,
                )
            )

        entries.sort(key=lambda e: e.timestamp)
        correlations = find_correlations(entries, config)
        assert len(correlations) >= 1
        assert correlations[0].confidence > 0.3

    def test_no_correlation_on_single_pattern(self) -> None:
        """A single repeated pattern has nothing to correlate with."""
        config = AnalysisConfig(time_window_minutes=5)
        base = datetime(2024, 6, 15, 10, 0, 0)
        entries = [
            LogEntry(
                timestamp=base + timedelta(minutes=i),
                level=LogLevel.ERROR,
                message="Same error over and over",
                source="svc",
                line_number=i,
            )
            for i in range(10)
        ]
        correlations = find_correlations(entries, config)
        assert correlations == []

    def test_no_correlation_on_distant_events(self) -> None:
        """Events far apart in time should not correlate."""
        config = AnalysisConfig(time_window_minutes=1)
        base = datetime(2024, 6, 15, 10, 0, 0)
        entries = [
            LogEntry(
                timestamp=base,
                level=LogLevel.ERROR,
                message="Error A happened",
                source="svc",
                line_number=1,
            ),
            LogEntry(
                timestamp=base + timedelta(hours=1),
                level=LogLevel.ERROR,
                message="Error A happened",
                source="svc",
                line_number=2,
            ),
            LogEntry(
                timestamp=base + timedelta(minutes=30),
                level=LogLevel.ERROR,
                message="Error B happened",
                source="svc",
                line_number=3,
            ),
            LogEntry(
                timestamp=base + timedelta(hours=1, minutes=30),
                level=LogLevel.ERROR,
                message="Error B happened",
                source="svc",
                line_number=4,
            ),
        ]
        correlations = find_correlations(entries, config)
        # With a 1-minute window and events 30+ min apart, nothing should correlate
        assert correlations == []
