# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Time-window correlation engine for root cause analysis."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from itertools import combinations

from .models import AnalysisConfig, Correlation, LogEntry, LogLevel


def _extract_pattern(message: str) -> str:
    """Extract a simplified pattern key from a log message.

    Normalises numbers, IDs, and paths to produce a canonical form
    suitable for grouping.
    """
    import re

    pattern = message.strip()
    # Replace hex IDs
    pattern = re.sub(r"0x[0-9a-fA-F]+", "<HEX>", pattern)
    # Replace UUIDs
    pattern = re.sub(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        "<UUID>",
        pattern,
    )
    # Replace IP addresses
    pattern = re.sub(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "<IP>", pattern)
    # Replace numbers
    pattern = re.sub(r"\b\d+\b", "<N>", pattern)
    # Replace file paths
    pattern = re.sub(r"/[\w./\-]+", "<PATH>", pattern)
    return pattern


def find_correlations(
    entries: list[LogEntry],
    config: AnalysisConfig,
) -> list[Correlation]:
    """Find temporal correlations between recurring error patterns.

    For each pair of distinct error patterns that co-occur within the
    configured time window, compute the average time lag and a confidence
    score based on how consistently the co-occurrence repeats.

    Args:
        entries: Parsed log entries sorted by timestamp.
        config: Analysis configuration (time window, thresholds).

    Returns:
        A list of Correlation objects sorted by confidence descending.
    """
    error_levels = {LogLevel.ERROR, LogLevel.CRITICAL, LogLevel.WARNING}
    error_entries = [e for e in entries if e.level in error_levels]

    if len(error_entries) < 2:
        return []

    # Group entries by normalised pattern
    pattern_groups: dict[str, list[LogEntry]] = defaultdict(list)
    for entry in error_entries:
        pattern = _extract_pattern(entry.message)
        pattern_groups[pattern].append(entry)

    # Only keep patterns that occur more than once
    frequent_patterns = {
        p: evts for p, evts in pattern_groups.items() if len(evts) >= 2
    }

    if len(frequent_patterns) < 2:
        return []

    window = timedelta(minutes=config.time_window_minutes)
    correlations: list[Correlation] = []

    for (pat_a, events_a), (pat_b, events_b) in combinations(
        frequent_patterns.items(), 2
    ):
        lags: list[float] = []

        for ea in events_a:
            for eb in events_b:
                lag = abs((eb.timestamp - ea.timestamp).total_seconds())
                if lag <= window.total_seconds() and lag > 0:
                    lags.append(lag)

        if not lags:
            continue

        avg_lag = sum(lags) / len(lags)
        # Confidence: how many co-occurrences vs. expected maximum
        max_possible = min(len(events_a), len(events_b))
        confidence = min(1.0, len(lags) / max(max_possible, 1))

        if confidence >= 0.3:
            # Build a human-readable summary of the first occurrence in each pattern
            src_sample = events_a[0].message[:80]
            rel_sample = events_b[0].message[:80]

            correlations.append(
                Correlation(
                    source_pattern=pat_a,
                    related_pattern=pat_b,
                    time_lag_seconds=avg_lag,
                    confidence=confidence,
                    occurrences=len(lags),
                    description=(
                        f"Pattern '{src_sample}' correlates with "
                        f"'{rel_sample}' (avg lag {avg_lag:.1f}s, "
                        f"{len(lags)} co-occurrences)"
                    ),
                )
            )

    correlations.sort(key=lambda c: c.confidence, reverse=True)
    return correlations[:20]
