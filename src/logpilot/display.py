# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Rich terminal output for LogPilot analysis results."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .models import Anomaly, AnomalyType, Correlation, ErrorCluster, IncidentReport, LogLevel


def _level_style(level: LogLevel) -> str:
    """Return a Rich style string for a given log level."""
    styles: dict[LogLevel, str] = {
        LogLevel.DEBUG: "dim",
        LogLevel.INFO: "green",
        LogLevel.WARNING: "yellow bold",
        LogLevel.ERROR: "red bold",
        LogLevel.CRITICAL: "red bold reverse",
    }
    return styles.get(level, "")


def _severity_color(severity: float) -> str:
    """Map a 0-1 severity score to a colour name."""
    if severity >= 0.8:
        return "red"
    if severity >= 0.5:
        return "yellow"
    if severity >= 0.3:
        return "cyan"
    return "green"


def print_analysis_summary(
    total: int,
    errors: int,
    warnings: int,
    anomaly_count: int,
    cluster_count: int,
    correlation_count: int,
    console: Console | None = None,
) -> None:
    """Print a high-level analysis summary panel.

    Args:
        total: Total log entries parsed.
        errors: Number of error-level entries.
        warnings: Number of warning-level entries.
        anomaly_count: Detected anomalies.
        cluster_count: Error clusters found.
        correlation_count: Correlated patterns.
        console: Optional Rich console (creates one if not provided).
    """
    if console is None:
        console = Console()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total entries", f"{total:,}")
    table.add_row("Errors", Text(f"{errors:,}", style="red bold"))
    table.add_row("Warnings", Text(f"{warnings:,}", style="yellow bold"))
    table.add_row("Anomalies", f"{anomaly_count}")
    table.add_row("Error clusters", f"{cluster_count}")
    table.add_row("Correlations", f"{correlation_count}")

    panel = Panel(table, title="LogPilot Analysis Summary", border_style="blue")
    console.print(panel)


def print_anomalies(anomalies: list[Anomaly], console: Console | None = None) -> None:
    """Print detected anomalies in a formatted table.

    Args:
        anomalies: List of Anomaly objects to display.
        console: Optional Rich console.
    """
    if console is None:
        console = Console()

    if not anomalies:
        console.print("[green]No anomalies detected.[/green]")
        return

    table = Table(title="Detected Anomalies", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Type", style="bold")
    table.add_column("Severity", justify="center")
    table.add_column("Time Window")
    table.add_column("Description")
    table.add_column("Lines", justify="right")

    for i, anomaly in enumerate(anomalies, 1):
        color = _severity_color(anomaly.severity)
        sev_text = Text(f"{anomaly.severity:.2f}", style=f"{color} bold")

        type_label = anomaly.anomaly_type.value.replace("_", " ").title()

        table.add_row(
            str(i),
            type_label,
            sev_text,
            f"{anomaly.start_time:%H:%M} - {anomaly.end_time:%H:%M}",
            anomaly.description[:80],
            str(len(anomaly.affected_entries)),
        )

    console.print(table)


def print_clusters(clusters: list[ErrorCluster], console: Console | None = None) -> None:
    """Print error clusters as a tree.

    Args:
        clusters: List of ErrorCluster objects.
        console: Optional Rich console.
    """
    if console is None:
        console = Console()

    if not clusters:
        console.print("[green]No error clusters identified.[/green]")
        return

    tree = Tree("[bold]Error Clusters[/bold]")

    for cluster in clusters:
        branch = tree.add(
            f"[bold red]Cluster #{cluster.cluster_id}[/bold red] "
            f"({cluster.count} occurrences)"
        )
        branch.add(f"[dim]Representative:[/dim] {cluster.representative_message[:100]}")
        branch.add(
            f"[dim]Time range:[/dim] "
            f"{cluster.first_seen:%H:%M:%S} - {cluster.last_seen:%H:%M:%S}"
        )
        if cluster.sample_messages:
            samples = branch.add("[dim]Samples:[/dim]")
            for msg in cluster.sample_messages[:3]:
                samples.add(f"[yellow]{msg[:80]}[/yellow]")

    console.print(tree)


def print_correlations(
    correlations: list[Correlation], console: Console | None = None
) -> None:
    """Print correlated patterns in a table.

    Args:
        correlations: List of Correlation objects.
        console: Optional Rich console.
    """
    if console is None:
        console = Console()

    if not correlations:
        console.print("[green]No correlated patterns found.[/green]")
        return

    table = Table(title="Correlated Patterns", show_lines=True)
    table.add_column("Confidence", justify="center", style="bold")
    table.add_column("Avg Lag", justify="right")
    table.add_column("Co-occurrences", justify="right")
    table.add_column("Description")

    for corr in correlations:
        conf_color = _severity_color(corr.confidence)
        table.add_row(
            Text(f"{corr.confidence:.0%}", style=f"{conf_color} bold"),
            f"{corr.time_lag_seconds:.1f}s",
            str(corr.occurrences),
            corr.description[:100],
        )

    console.print(table)


def print_report_summary(report: IncidentReport, console: Console | None = None) -> None:
    """Print the incident report's executive summary and recommendations.

    Args:
        report: An IncidentReport.
        console: Optional Rich console.
    """
    if console is None:
        console = Console()

    console.print()
    console.print(Panel(report.summary, title="Executive Summary", border_style="blue"))

    if report.recommendations:
        console.print()
        rec_tree = Tree("[bold]Recommendations[/bold]")
        for rec in report.recommendations:
            rec_tree.add(f"[yellow]{rec}[/yellow]")
        console.print(rec_tree)
