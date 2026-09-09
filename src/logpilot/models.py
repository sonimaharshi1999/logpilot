# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Pydantic models for LogPilot's structured data types."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """Standard log severity levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Supported log format types."""

    JSON = "json"
    SYSLOG = "syslog"
    CUSTOM = "custom"
    AUTO = "auto"


class LogEntry(BaseModel):
    """A single parsed log entry."""

    timestamp: datetime
    level: LogLevel
    message: str
    source: str = "unknown"
    line_number: int = 0
    raw: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)


class AnomalyType(str, Enum):
    """Types of detected anomalies."""

    FREQUENCY_SPIKE = "frequency_spike"
    ERROR_RATE_SURGE = "error_rate_surge"
    NEW_ERROR_PATTERN = "new_error_pattern"
    CLUSTER_OUTLIER = "cluster_outlier"


class Anomaly(BaseModel):
    """A detected anomaly in the log stream."""

    anomaly_type: AnomalyType
    severity: float = Field(ge=0.0, le=1.0, description="Severity score 0-1")
    description: str
    start_time: datetime
    end_time: datetime
    affected_entries: list[int] = Field(
        default_factory=list, description="Line numbers of affected log entries"
    )
    score: float = Field(ge=0.0, description="Statistical score of the anomaly")


class ErrorCluster(BaseModel):
    """A group of similar error messages."""

    cluster_id: int
    representative_message: str
    count: int
    first_seen: datetime
    last_seen: datetime
    sample_messages: list[str] = Field(default_factory=list)
    entry_indices: list[int] = Field(default_factory=list)


class Correlation(BaseModel):
    """A correlation between events across time windows."""

    source_pattern: str
    related_pattern: str
    time_lag_seconds: float
    confidence: float = Field(ge=0.0, le=1.0)
    occurrences: int
    description: str


class IncidentReport(BaseModel):
    """A generated incident report."""

    title: str
    generated_at: datetime
    time_range_start: datetime
    time_range_end: datetime
    total_entries: int
    error_count: int
    warning_count: int
    anomalies: list[Anomaly] = Field(default_factory=list)
    clusters: list[ErrorCluster] = Field(default_factory=list)
    correlations: list[Correlation] = Field(default_factory=list)
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)


class AnalysisConfig(BaseModel):
    """Configuration for log analysis."""

    log_format: LogFormat = LogFormat.AUTO
    custom_pattern: Optional[str] = None
    time_window_minutes: int = Field(default=5, ge=1)
    anomaly_threshold: float = Field(default=2.0, ge=0.5)
    min_cluster_size: int = Field(default=2, ge=1)
    max_clusters: int = Field(default=20, ge=2)
