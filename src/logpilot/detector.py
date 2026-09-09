# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Statistical anomaly detection on log frequency, error rates, and patterns."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer

from .models import (
    AnalysisConfig,
    Anomaly,
    AnomalyType,
    ErrorCluster,
    LogEntry,
    LogLevel,
)


def _bucket_entries(
    entries: list[LogEntry], window_minutes: int
) -> dict[datetime, list[LogEntry]]:
    """Group log entries into fixed-width time buckets."""
    if not entries:
        return {}

    buckets: dict[datetime, list[LogEntry]] = {}
    origin = entries[0].timestamp.replace(second=0, microsecond=0)
    delta = timedelta(minutes=window_minutes)

    for entry in entries:
        offset = (entry.timestamp - origin).total_seconds()
        bucket_idx = int(offset // delta.total_seconds())
        bucket_start = origin + delta * bucket_idx
        buckets.setdefault(bucket_start, []).append(entry)

    return buckets


def detect_frequency_anomalies(
    entries: list[LogEntry],
    config: AnalysisConfig,
) -> list[Anomaly]:
    """Detect anomalies in log frequency using z-score analysis.

    A time bucket whose entry count exceeds the mean by more than
    ``config.anomaly_threshold`` standard deviations is flagged.

    Args:
        entries: Parsed log entries sorted by timestamp.
        config: Analysis configuration with threshold and window settings.

    Returns:
        A list of Anomaly objects for frequency spikes.
    """
    if len(entries) < 3:
        return []

    buckets = _bucket_entries(entries, config.time_window_minutes)
    if len(buckets) < 3:
        return []

    counts = np.array([len(v) for v in buckets.values()], dtype=np.float64)
    mean = float(np.mean(counts))
    std = float(np.std(counts))

    if std < 1e-9:
        return []

    anomalies: list[Anomaly] = []
    window = timedelta(minutes=config.time_window_minutes)

    for bucket_start, bucket_entries in buckets.items():
        z_score = (len(bucket_entries) - mean) / std
        if z_score > config.anomaly_threshold:
            severity = min(1.0, z_score / (config.anomaly_threshold * 3))
            anomalies.append(
                Anomaly(
                    anomaly_type=AnomalyType.FREQUENCY_SPIKE,
                    severity=severity,
                    description=(
                        f"Log frequency spike: {len(bucket_entries)} entries "
                        f"in {config.time_window_minutes}-min window "
                        f"(z-score={z_score:.2f}, mean={mean:.1f})"
                    ),
                    start_time=bucket_start,
                    end_time=bucket_start + window,
                    affected_entries=[e.line_number for e in bucket_entries],
                    score=z_score,
                )
            )

    return anomalies


def detect_error_rate_anomalies(
    entries: list[LogEntry],
    config: AnalysisConfig,
) -> list[Anomaly]:
    """Detect sudden surges in error rate across time windows.

    Compares each bucket's error ratio to the global average.

    Args:
        entries: Parsed log entries sorted by timestamp.
        config: Analysis configuration.

    Returns:
        A list of Anomaly objects for error-rate surges.
    """
    if len(entries) < 3:
        return []

    buckets = _bucket_entries(entries, config.time_window_minutes)
    if len(buckets) < 3:
        return []

    error_levels = {LogLevel.ERROR, LogLevel.CRITICAL}

    global_errors = sum(1 for e in entries if e.level in error_levels)
    global_rate = global_errors / len(entries) if entries else 0.0

    rates: list[float] = []
    for bucket_entries in buckets.values():
        errs = sum(1 for e in bucket_entries if e.level in error_levels)
        rates.append(errs / len(bucket_entries) if bucket_entries else 0.0)

    rates_arr = np.array(rates, dtype=np.float64)
    mean_rate = float(np.mean(rates_arr))
    std_rate = float(np.std(rates_arr))

    if std_rate < 1e-9:
        return []

    anomalies: list[Anomaly] = []
    window = timedelta(minutes=config.time_window_minutes)

    for bucket_start, bucket_entries in buckets.items():
        errs = sum(1 for e in bucket_entries if e.level in error_levels)
        rate = errs / len(bucket_entries) if bucket_entries else 0.0
        z_score = (rate - mean_rate) / std_rate

        if z_score > config.anomaly_threshold:
            severity = min(1.0, z_score / (config.anomaly_threshold * 3))
            anomalies.append(
                Anomaly(
                    anomaly_type=AnomalyType.ERROR_RATE_SURGE,
                    severity=severity,
                    description=(
                        f"Error rate surge: {rate:.1%} errors in window "
                        f"(global avg={global_rate:.1%}, z-score={z_score:.2f})"
                    ),
                    start_time=bucket_start,
                    end_time=bucket_start + window,
                    affected_entries=[
                        e.line_number for e in bucket_entries if e.level in error_levels
                    ],
                    score=z_score,
                )
            )

    return anomalies


def _fallback_exact_clusters(
    error_entries: list[LogEntry],
    config: AnalysisConfig,
) -> list[ErrorCluster]:
    """Group errors by exact message match when TF-IDF yields no features."""
    groups: dict[str, list[LogEntry]] = {}
    for entry in error_entries:
        groups.setdefault(entry.message, []).append(entry)

    clusters: list[ErrorCluster] = []
    for cid, (msg, group) in enumerate(
        sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
    ):
        if len(group) < config.min_cluster_size:
            continue
        clusters.append(
            ErrorCluster(
                cluster_id=cid,
                representative_message=msg,
                count=len(group),
                first_seen=min(e.timestamp for e in group),
                last_seen=max(e.timestamp for e in group),
                sample_messages=[msg],
                entry_indices=[e.line_number for e in group],
            )
        )
    return clusters[: config.max_clusters]


def cluster_errors(
    entries: list[LogEntry],
    config: AnalysisConfig,
) -> list[ErrorCluster]:
    """Cluster similar error messages using TF-IDF and DBSCAN.

    Args:
        entries: Parsed log entries.
        config: Analysis configuration with cluster size settings.

    Returns:
        A list of ErrorCluster objects grouping similar errors.
    """
    error_entries = [
        e for e in entries if e.level in {LogLevel.ERROR, LogLevel.CRITICAL}
    ]

    if len(error_entries) < config.min_cluster_size:
        return []

    messages = [e.message for e in error_entries]

    # Use max_df=1.0 so terms appearing in all documents are kept
    # (important when many errors share the same message).
    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words="english",
        max_df=1.0,
        min_df=1,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(messages)
    except ValueError:
        return []

    # If the vocabulary is empty (e.g. all stop words), fall back to a
    # simple exact-match grouping.
    if tfidf_matrix.shape[1] == 0:
        return _fallback_exact_clusters(error_entries, config)

    # Use DBSCAN for density-based clustering
    clustering = DBSCAN(eps=0.7, min_samples=config.min_cluster_size, metric="cosine")
    labels = clustering.fit_predict(tfidf_matrix)

    clusters: list[ErrorCluster] = []
    label_set = set(labels)
    label_set.discard(-1)  # Remove noise label

    for label in sorted(label_set):
        indices = [i for i, lbl in enumerate(labels) if lbl == label]
        cluster_entries = [error_entries[i] for i in indices]

        # Pick the most central message as representative
        representative = Counter(e.message for e in cluster_entries).most_common(1)[0][0]

        clusters.append(
            ErrorCluster(
                cluster_id=int(label),
                representative_message=representative,
                count=len(cluster_entries),
                first_seen=min(e.timestamp for e in cluster_entries),
                last_seen=max(e.timestamp for e in cluster_entries),
                sample_messages=list({e.message for e in cluster_entries})[:5],
                entry_indices=[e.line_number for e in cluster_entries],
            )
        )

    clusters.sort(key=lambda c: c.count, reverse=True)
    return clusters[: config.max_clusters]


def detect_all_anomalies(
    entries: list[LogEntry],
    config: AnalysisConfig,
) -> list[Anomaly]:
    """Run all anomaly detection methods and return combined results.

    Args:
        entries: Parsed log entries.
        config: Analysis configuration.

    Returns:
        A combined, severity-sorted list of all detected anomalies.
    """
    anomalies: list[Anomaly] = []
    anomalies.extend(detect_frequency_anomalies(entries, config))
    anomalies.extend(detect_error_rate_anomalies(entries, config))

    anomalies.sort(key=lambda a: a.severity, reverse=True)
    return anomalies
