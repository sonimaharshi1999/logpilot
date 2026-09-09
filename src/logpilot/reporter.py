# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Incident report generation in Markdown format."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import (
    Anomaly,
    AnomalyType,
    Correlation,
    ErrorCluster,
    IncidentReport,
    LogEntry,
    LogLevel,
)


def _severity_label(score: float) -> str:
    """Convert a 0-1 severity score to a human-readable label."""
    if score >= 0.8:
        return "CRITICAL"
    if score >= 0.5:
        return "HIGH"
    if score >= 0.3:
        return "MEDIUM"
    return "LOW"


def _generate_summary(report: IncidentReport) -> str:
    """Generate a textual executive summary from the incident report data."""
    lines: list[str] = []

    total = report.total_entries
    lines.append(
        f"Analyzed {total:,} log entries spanning "
        f"{report.time_range_start:%Y-%m-%d %H:%M} to "
        f"{report.time_range_end:%Y-%m-%d %H:%M}."
    )

    if report.error_count:
        pct = report.error_count / total * 100 if total else 0
        lines.append(
            f"Found {report.error_count:,} errors and "
            f"{report.warning_count:,} warnings ({pct:.1f}% error rate)."
        )

    if report.anomalies:
        critical = sum(1 for a in report.anomalies if a.severity >= 0.8)
        lines.append(
            f"Detected {len(report.anomalies)} anomalies "
            f"({critical} critical)."
        )

    if report.clusters:
        lines.append(
            f"Grouped errors into {len(report.clusters)} distinct clusters."
        )

    if report.correlations:
        lines.append(
            f"Identified {len(report.correlations)} correlated event patterns."
        )

    return " ".join(lines)


def _generate_recommendations(report: IncidentReport) -> list[str]:
    """Generate actionable recommendations based on findings."""
    recs: list[str] = []

    for anomaly in report.anomalies:
        if anomaly.anomaly_type == AnomalyType.FREQUENCY_SPIKE:
            recs.append(
                f"Investigate log frequency spike at {anomaly.start_time:%H:%M} "
                f"-- possible cascading failure or retry storm."
            )
        elif anomaly.anomaly_type == AnomalyType.ERROR_RATE_SURGE:
            recs.append(
                f"Review error rate surge at {anomaly.start_time:%H:%M} "
                f"-- check recent deployments or infrastructure changes."
            )

    for cluster in report.clusters[:3]:
        recs.append(
            f"Address recurring error pattern ({cluster.count} occurrences): "
            f'"{cluster.representative_message[:100]}"'
        )

    for corr in report.correlations[:3]:
        recs.append(
            f"Examine correlated patterns (confidence={corr.confidence:.0%}, "
            f"avg lag={corr.time_lag_seconds:.1f}s): {corr.description[:120]}"
        )

    if not recs:
        recs.append("No significant issues detected. Continue monitoring.")

    return recs


def build_report(
    entries: list[LogEntry],
    anomalies: list[Anomaly],
    clusters: list[ErrorCluster],
    correlations: list[Correlation],
) -> IncidentReport:
    """Assemble a complete incident report from analysis results.

    Args:
        entries: All parsed log entries.
        anomalies: Detected anomalies.
        clusters: Error clusters.
        correlations: Correlated patterns.

    Returns:
        A fully populated IncidentReport.
    """
    error_levels = {LogLevel.ERROR, LogLevel.CRITICAL}

    report = IncidentReport(
        title="LogPilot Incident Report",
        generated_at=datetime.now(),
        time_range_start=entries[0].timestamp if entries else datetime.now(),
        time_range_end=entries[-1].timestamp if entries else datetime.now(),
        total_entries=len(entries),
        error_count=sum(1 for e in entries if e.level in error_levels),
        warning_count=sum(1 for e in entries if e.level == LogLevel.WARNING),
        anomalies=anomalies,
        clusters=clusters,
        correlations=correlations,
    )

    report.summary = _generate_summary(report)
    report.recommendations = _generate_recommendations(report)
    return report


def render_markdown(report: IncidentReport) -> str:
    """Render an IncidentReport as a Markdown document.

    Args:
        report: The incident report to render.

    Returns:
        A Markdown string suitable for writing to a file.
    """
    lines: list[str] = []
    lines.append(f"# {report.title}")
    lines.append("")
    lines.append(f"**Generated:** {report.generated_at:%Y-%m-%d %H:%M:%S}")
    lines.append(
        f"**Time Range:** {report.time_range_start:%Y-%m-%d %H:%M} -- "
        f"{report.time_range_end:%Y-%m-%d %H:%M}"
    )
    lines.append("")

    # --- Executive summary ---
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(report.summary)
    lines.append("")

    # --- Statistics ---
    lines.append("## Statistics")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total entries | {report.total_entries:,} |")
    lines.append(f"| Errors | {report.error_count:,} |")
    lines.append(f"| Warnings | {report.warning_count:,} |")
    lines.append(f"| Anomalies | {len(report.anomalies)} |")
    lines.append(f"| Error clusters | {len(report.clusters)} |")
    lines.append(f"| Correlations | {len(report.correlations)} |")
    lines.append("")

    # --- Anomalies ---
    if report.anomalies:
        lines.append("## Anomalies Detected")
        lines.append("")
        for i, anomaly in enumerate(report.anomalies, 1):
            label = _severity_label(anomaly.severity)
            lines.append(f"### {i}. [{label}] {anomaly.anomaly_type.value}")
            lines.append("")
            lines.append(f"- **Time:** {anomaly.start_time:%H:%M} -- {anomaly.end_time:%H:%M}")
            lines.append(f"- **Severity:** {anomaly.severity:.2f}")
            lines.append(f"- **Score:** {anomaly.score:.2f}")
            lines.append(f"- **Detail:** {anomaly.description}")
            lines.append(f"- **Affected lines:** {len(anomaly.affected_entries)}")
            lines.append("")

    # --- Error clusters ---
    if report.clusters:
        lines.append("## Error Clusters")
        lines.append("")
        for cluster in report.clusters:
            lines.append(f"### Cluster #{cluster.cluster_id} ({cluster.count} occurrences)")
            lines.append("")
            lines.append(f"- **Representative:** `{cluster.representative_message[:120]}`")
            lines.append(
                f"- **Window:** {cluster.first_seen:%H:%M:%S} -- "
                f"{cluster.last_seen:%H:%M:%S}"
            )
            if cluster.sample_messages:
                lines.append("- **Samples:**")
                for msg in cluster.sample_messages[:3]:
                    lines.append(f"  - `{msg[:100]}`")
            lines.append("")

    # --- Correlations ---
    if report.correlations:
        lines.append("## Correlated Patterns")
        lines.append("")
        for corr in report.correlations:
            lines.append(
                f"- **Confidence {corr.confidence:.0%}** | "
                f"Lag {corr.time_lag_seconds:.1f}s | "
                f"{corr.occurrences} co-occurrences"
            )
            lines.append(f"  {corr.description}")
            lines.append("")

    # --- Recommendations ---
    lines.append("## Recommendations")
    lines.append("")
    for rec in report.recommendations:
        lines.append(f"- {rec}")
    lines.append("")

    lines.append("---")
    lines.append("*Report generated by [LogPilot](https://github.com/maharshisoni/logpilot)*")
    lines.append("")

    return "\n".join(lines)


def save_report(report: IncidentReport, path: Path) -> Path:
    """Render and save an incident report as Markdown.

    Args:
        report: The incident report.
        path: Destination file path.

    Returns:
        The path the report was written to.
    """
    content = render_markdown(report)
    path.write_text(content, encoding="utf-8")
    return path
