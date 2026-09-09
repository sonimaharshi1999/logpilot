# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Click-based CLI for LogPilot -- AI-powered log analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from . import __version__
from .correlator import find_correlations
from .detector import cluster_errors, detect_all_anomalies
from .display import (
    print_analysis_summary,
    print_anomalies,
    print_clusters,
    print_correlations,
    print_report_summary,
)
from .generator import write_sample_logs
from .models import AnalysisConfig, LogFormat, LogLevel
from .parser import parse_log_file
from .reporter import build_report, render_markdown, save_report

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="logpilot")
def main() -> None:
    """LogPilot -- AI-Powered Log Analysis CLI for SRE and DevOps."""


@main.command()
@click.argument("log_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "log_format",
    type=click.Choice(["auto", "json", "syslog", "custom"]),
    default="auto",
    help="Log format (auto-detected by default).",
)
@click.option(
    "--pattern",
    type=str,
    default=None,
    help="Custom regex pattern with named groups: timestamp, level, message, source.",
)
@click.option(
    "--window",
    type=int,
    default=5,
    help="Time window in minutes for bucketing (default: 5).",
)
@click.option(
    "--threshold",
    type=float,
    default=2.0,
    help="Z-score threshold for anomaly detection (default: 2.0).",
)
def analyze(
    log_file: Path,
    log_format: str,
    pattern: Optional[str],
    window: int,
    threshold: float,
) -> None:
    """Analyze a log file: parse, detect anomalies, cluster errors, and correlate patterns."""
    config = AnalysisConfig(
        log_format=LogFormat(log_format),
        custom_pattern=pattern,
        time_window_minutes=window,
        anomaly_threshold=threshold,
    )

    console.print(f"\n[bold blue]LogPilot[/bold blue] analyzing [cyan]{log_file}[/cyan]...\n")

    entries = parse_log_file(log_file, config)
    if not entries:
        console.print("[red]No parseable log entries found.[/red]")
        raise SystemExit(1)

    anomalies = detect_all_anomalies(entries, config)
    clusters = cluster_errors(entries, config)
    correlations = find_correlations(entries, config)

    error_count = sum(1 for e in entries if e.level in {LogLevel.ERROR, LogLevel.CRITICAL})
    warning_count = sum(1 for e in entries if e.level == LogLevel.WARNING)

    print_analysis_summary(
        total=len(entries),
        errors=error_count,
        warnings=warning_count,
        anomaly_count=len(anomalies),
        cluster_count=len(clusters),
        correlation_count=len(correlations),
        console=console,
    )

    print_anomalies(anomalies, console)
    print_clusters(clusters, console)
    print_correlations(correlations, console)


@main.command()
@click.argument("log_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "log_format",
    type=click.Choice(["auto", "json", "syslog", "custom"]),
    default="auto",
    help="Log format.",
)
@click.option("--window", type=int, default=5, help="Time window in minutes.")
@click.option("--threshold", type=float, default=2.0, help="Z-score threshold.")
def detect(
    log_file: Path,
    log_format: str,
    window: int,
    threshold: float,
) -> None:
    """Detect anomalies in a log file (frequency spikes and error-rate surges)."""
    config = AnalysisConfig(
        log_format=LogFormat(log_format),
        time_window_minutes=window,
        anomaly_threshold=threshold,
    )

    console.print(f"\n[bold blue]LogPilot[/bold blue] scanning [cyan]{log_file}[/cyan] for anomalies...\n")

    entries = parse_log_file(log_file, config)
    if not entries:
        console.print("[red]No parseable log entries found.[/red]")
        raise SystemExit(1)

    anomalies = detect_all_anomalies(entries, config)
    print_anomalies(anomalies, console)

    if not anomalies:
        console.print("[green]All clear -- no anomalies detected.[/green]")


@main.command()
@click.argument("log_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path for the Markdown report (default: <logfile>_report.md).",
)
@click.option(
    "--format",
    "log_format",
    type=click.Choice(["auto", "json", "syslog", "custom"]),
    default="auto",
    help="Log format.",
)
@click.option("--window", type=int, default=5, help="Time window in minutes.")
@click.option("--threshold", type=float, default=2.0, help="Z-score threshold.")
def report(
    log_file: Path,
    output: Optional[Path],
    log_format: str,
    window: int,
    threshold: float,
) -> None:
    """Generate a full Markdown incident report from a log file."""
    config = AnalysisConfig(
        log_format=LogFormat(log_format),
        time_window_minutes=window,
        anomaly_threshold=threshold,
    )

    console.print(f"\n[bold blue]LogPilot[/bold blue] generating report for [cyan]{log_file}[/cyan]...\n")

    entries = parse_log_file(log_file, config)
    if not entries:
        console.print("[red]No parseable log entries found.[/red]")
        raise SystemExit(1)

    anomalies = detect_all_anomalies(entries, config)
    clusters = cluster_errors(entries, config)
    correlations = find_correlations(entries, config)

    incident_report = build_report(entries, anomalies, clusters, correlations)

    if output is None:
        output = log_file.with_name(log_file.stem + "_report.md")

    save_report(incident_report, output)
    print_report_summary(incident_report, console)
    console.print(f"\n[bold green]Report saved to:[/bold green] {output}")


@main.command(name="generate-sample")
@click.option(
    "--output-dir", "-o",
    type=click.Path(path_type=Path),
    default=Path("sample_logs"),
    help="Directory to write sample log files into.",
)
@click.option("--seed", type=int, default=42, help="Random seed for reproducibility.")
def generate_sample(output_dir: Path, seed: int) -> None:
    """Generate synthetic sample log files for testing."""
    files = write_sample_logs(output_dir, seed=seed)
    console.print("[bold green]Sample logs generated:[/bold green]")
    for fmt, path in files.items():
        console.print(f"  [cyan]{fmt}[/cyan]: {path}")


if __name__ == "__main__":
    main()
