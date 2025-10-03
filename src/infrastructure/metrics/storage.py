"""
MetricsStorage - Atomic persistence with crash recovery
Handles JSON and CSV export with guaranteed data safety
"""

import json
import csv
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from .models import RunMetrics, IssueMetrics


class MetricsStorage:
    """
    Handles persistent storage of metrics with atomic writes.
    Ensures no data loss even on crashes.
    """

    def __init__(self, base_dir: Path = Path("logs")):
        """
        Initialize storage.

        Args:
            base_dir: Base directory for logs
        """
        self.base_dir = base_dir
        self.runs_dir = base_dir / "runs"
        self.csv_dir = base_dir / "csv"

        # Create directories
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.csv_dir.mkdir(parents=True, exist_ok=True)

        # Initialize CSV files
        self._init_csv_files()

    # ==================== JSON Storage ====================

    def save_run_metadata(self, run_metrics: RunMetrics):
        """
        Save run metadata incrementally (called during execution).

        Args:
            run_metrics: Run metrics to save
        """
        run_dir = self.runs_dir / run_metrics.run_id
        run_dir.mkdir(exist_ok=True)

        metadata_file = run_dir / "metadata.json"

        # Atomic write using temp file
        self._atomic_json_write(metadata_file, run_metrics.to_dict())

    def save_run_final(self, run_metrics: RunMetrics):
        """
        Save final run report (called on completion).

        Args:
            run_metrics: Finalized run metrics
        """
        run_dir = self.runs_dir / run_metrics.run_id
        run_dir.mkdir(exist_ok=True)

        final_file = run_dir / "final_report.json"

        # Atomic write
        self._atomic_json_write(final_file, run_metrics.to_dict())

    def save_issue_metrics(self, run_id: str, issue_metrics: IssueMetrics):
        """
        Save issue metrics incrementally.

        Args:
            run_id: Run ID
            issue_metrics: Issue metrics to save
        """
        issue_dir = self.runs_dir / run_id / "issues"
        issue_dir.mkdir(parents=True, exist_ok=True)

        metrics_file = issue_dir / f"issue_{issue_metrics.issue_id}_metrics.json"

        # Atomic write
        self._atomic_json_write(metrics_file, issue_metrics.to_dict())

    def save_issue_final(self, run_id: str, issue_metrics: IssueMetrics):
        """
        Save final issue report.

        Args:
            run_id: Run ID
            issue_metrics: Finalized issue metrics
        """
        issue_dir = self.runs_dir / run_id / "issues"
        issue_dir.mkdir(parents=True, exist_ok=True)

        report_file = issue_dir / f"issue_{issue_metrics.issue_id}_report.json"

        # Atomic write
        self._atomic_json_write(report_file, issue_metrics.to_dict())

    def _atomic_json_write(self, filepath: Path, data: Dict[str, Any]):
        """
        Atomic JSON write using temp file + rename.
        Guarantees no partial writes even on crashes.

        Args:
            filepath: Target file path
            data: Data to write
        """
        temp_file = filepath.with_suffix('.tmp')

        try:
            # Write to temp file
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

            # Atomic rename (overwrites existing file)
            temp_file.replace(filepath)

        except Exception as e:
            # Clean up temp file on error
            if temp_file.exists():
                temp_file.unlink()
            raise Exception(f"Failed to write {filepath}: {e}")

    def load_run_metrics(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Load run metrics from disk.

        Args:
            run_id: Run ID to load

        Returns:
            Run metrics dict or None if not found
        """
        metadata_file = self.runs_dir / run_id / "metadata.json"

        if not metadata_file.exists():
            return None

        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ==================== CSV Export ====================

    def _init_csv_files(self):
        """Initialize CSV files with headers"""

        # 1. Runs CSV
        runs_csv = self.csv_dir / 'runs.csv'
        if not runs_csv.exists():
            with open(runs_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'project_id', 'start_time', 'end_time', 'duration_seconds',
                    'status', 'llm_provider', 'llm_model', 'llm_temperature',
                    'execution_mode', 'specific_issue', 'max_retries', 'min_coverage_percent',
                    'total_issues', 'successful_issues', 'failed_issues', 'skipped_issues',
                    'success_rate_percent', 'total_tokens', 'total_cost_usd',
                    'total_agent_duration_seconds', 'total_pipeline_duration_seconds',
                    'total_errors', 'total_debugging_cycles'
                ])

        # 2. Issues CSV
        issues_csv = self.csv_dir / 'issues.csv'
        if not issues_csv.exists():
            with open(issues_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'issue_id', 'start_time', 'end_time', 'duration_seconds',
                    'status', 'total_agent_attempts', 'successful_agents', 'failed_agents',
                    'pipeline_success_count', 'pipeline_failure_count',
                    'total_debugging_cycles', 'resolved_debugging_cycles',
                    'total_tokens', 'total_cost_usd', 'first_time_right', 'complexity_score',
                    'files_created', 'files_modified', 'files_deleted',
                    'lines_added', 'lines_deleted', 'commits', 'test_coverage_percent',
                    'total_errors'
                ])

        # 3. Agents CSV
        agents_csv = self.csv_dir / 'agents.csv'
        if not agents_csv.exists():
            with open(agents_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'issue_id', 'agent_type', 'attempt_number',
                    'start_time', 'end_time', 'duration_seconds', 'status',
                    'success', 'retry_count', 'tool_calls_count',
                    'input_tokens', 'output_tokens', 'total_tokens', 'cost_usd',
                    'error_message'
                ])

        # 4. Pipelines CSV
        pipelines_csv = self.csv_dir / 'pipelines.csv'
        if not pipelines_csv.exists():
            with open(pipelines_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'issue_id', 'pipeline_id', 'commit_sha',
                    'triggered_by', 'retry_attempt', 'status',
                    'start_time', 'end_time', 'duration_seconds',
                    'queue_time_seconds', 'execution_time_seconds',
                    'failed_jobs', 'error_type', 'error_message'
                ])

        # 5. Tool Usage CSV
        tools_csv = self.csv_dir / 'tool_usage.csv'
        if not tools_csv.exists():
            with open(tools_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'issue_id', 'agent_type', 'tool_name',
                    'call_count', 'success_count', 'failure_count',
                    'avg_duration_ms', 'total_duration_ms'
                ])

        # 6. Debugging Cycles CSV
        debugging_csv = self.csv_dir / 'debugging_cycles.csv'
        if not debugging_csv.exists():
            with open(debugging_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'issue_id', 'agent', 'error_type', 'error_message',
                    'start_time', 'end_time', 'duration_seconds',
                    'attempts', 'resolved', 'resolution_method'
                ])

        # 7. Errors CSV
        errors_csv = self.csv_dir / 'errors.csv'
        if not errors_csv.exists():
            with open(errors_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'issue_id', 'agent', 'error_type', 'error_message',
                    'severity', 'timestamp'
                ])

    def export_run_to_csv(self, run_metrics: RunMetrics):
        """
        Export run metrics to CSV.

        Args:
            run_metrics: Run metrics to export
        """
        runs_csv = self.csv_dir / 'runs.csv'

        with open(runs_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            config = run_metrics.config
            llm = config.llm if config else None

            writer.writerow([
                run_metrics.run_id,
                run_metrics.project_id,
                run_metrics.start_time.isoformat(),
                run_metrics.end_time.isoformat() if run_metrics.end_time else '',
                run_metrics.duration_seconds,
                run_metrics.status.value,
                llm.provider if llm else '',
                llm.model if llm else '',
                llm.temperature if llm else 0.0,
                config.execution_mode if config else '',
                config.specific_issue if config else '',
                config.max_retries if config else 0,
                config.min_coverage_percent if config else 0.0,
                run_metrics.total_issues,
                run_metrics.successful_issues,
                run_metrics.failed_issues,
                run_metrics.skipped_issues,
                run_metrics.success_rate_percent,
                run_metrics.total_tokens,
                run_metrics.total_cost_usd,
                run_metrics.total_agent_duration_seconds,
                run_metrics.total_pipeline_duration_seconds,
                run_metrics.total_errors,
                run_metrics.total_debugging_cycles
            ])

    def export_issue_to_csv(self, run_id: str, issue_metrics: IssueMetrics):
        """
        Export issue metrics to CSV.

        Args:
            run_id: Run ID
            issue_metrics: Issue metrics to export
        """
        issues_csv = self.csv_dir / 'issues.csv'

        with open(issues_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                run_id,
                issue_metrics.issue_id,
                issue_metrics.start_time.isoformat(),
                issue_metrics.end_time.isoformat() if issue_metrics.end_time else '',
                issue_metrics.duration_seconds,
                issue_metrics.status.value,
                issue_metrics.total_agent_attempts,
                issue_metrics.successful_agents,
                issue_metrics.failed_agents,
                issue_metrics.pipeline_success_count,
                issue_metrics.pipeline_failure_count,
                issue_metrics.total_debugging_cycles,
                issue_metrics.resolved_debugging_cycles,
                issue_metrics.total_tokens,
                issue_metrics.total_cost_usd,
                issue_metrics.first_time_right,
                issue_metrics.complexity_score,
                issue_metrics.code_metrics.files_created,
                issue_metrics.code_metrics.files_modified,
                issue_metrics.code_metrics.files_deleted,
                issue_metrics.code_metrics.lines_added,
                issue_metrics.code_metrics.lines_deleted,
                issue_metrics.code_metrics.commits,
                issue_metrics.code_metrics.test_coverage_percent,
                len(issue_metrics.errors)
            ])

        # Export agent executions
        self._export_agents_to_csv(run_id, issue_metrics)

        # Export pipelines
        self._export_pipelines_to_csv(run_id, issue_metrics)

        # Export tool usage
        self._export_tools_to_csv(run_id, issue_metrics)

        # Export debugging cycles
        self._export_debugging_to_csv(run_id, issue_metrics)

        # Export errors
        self._export_errors_to_csv(run_id, issue_metrics)

    def _export_agents_to_csv(self, run_id: str, issue_metrics: IssueMetrics):
        """Export agent executions to CSV"""
        agents_csv = self.csv_dir / 'agents.csv'

        with open(agents_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            for agent in issue_metrics.agent_executions:
                writer.writerow([
                    run_id,
                    issue_metrics.issue_id,
                    agent.agent_type.value,
                    agent.attempt_number,
                    agent.start_time.isoformat(),
                    agent.end_time.isoformat() if agent.end_time else '',
                    agent.duration_seconds,
                    agent.status.value,
                    agent.success,
                    agent.retry_count,
                    len(agent.tool_calls),
                    agent.token_usage.input_tokens,
                    agent.token_usage.output_tokens,
                    agent.token_usage.total_tokens,
                    agent.token_usage.estimated_cost_usd,
                    agent.error_message or ''
                ])

    def _export_pipelines_to_csv(self, run_id: str, issue_metrics: IssueMetrics):
        """Export pipelines to CSV"""
        pipelines_csv = self.csv_dir / 'pipelines.csv'

        with open(pipelines_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            for pipeline in issue_metrics.pipelines:
                writer.writerow([
                    run_id,
                    issue_metrics.issue_id,
                    pipeline.pipeline_id,
                    pipeline.commit_sha,
                    pipeline.triggered_by,
                    pipeline.retry_attempt,
                    pipeline.status,
                    pipeline.start_time.isoformat() if pipeline.start_time else '',
                    pipeline.end_time.isoformat() if pipeline.end_time else '',
                    pipeline.duration_seconds,
                    pipeline.queue_time_seconds,
                    pipeline.execution_time_seconds,
                    ','.join(pipeline.failed_jobs),
                    pipeline.error_type or '',
                    pipeline.error_message or ''
                ])

    def _export_tools_to_csv(self, run_id: str, issue_metrics: IssueMetrics):
        """Export tool usage to CSV"""
        tools_csv = self.csv_dir / 'tool_usage.csv'

        with open(tools_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            for agent in issue_metrics.agent_executions:
                for tool_name, stats in agent.tool_stats.items():
                    writer.writerow([
                        run_id,
                        issue_metrics.issue_id,
                        agent.agent_type.value,
                        tool_name,
                        stats.call_count,
                        stats.success_count,
                        stats.failure_count,
                        stats.avg_duration_ms,
                        stats.total_duration_ms
                    ])

    def _export_debugging_to_csv(self, run_id: str, issue_metrics: IssueMetrics):
        """Export debugging cycles to CSV"""
        debugging_csv = self.csv_dir / 'debugging_cycles.csv'

        with open(debugging_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            for cycle in issue_metrics.debugging_cycles:
                writer.writerow([
                    run_id,
                    issue_metrics.issue_id,
                    cycle.agent,
                    cycle.error_type,
                    cycle.error_message,
                    cycle.start_time.isoformat(),
                    cycle.end_time.isoformat() if cycle.end_time else '',
                    cycle.duration_seconds,
                    cycle.attempts,
                    cycle.resolved,
                    cycle.resolution_method or ''
                ])

    def _export_errors_to_csv(self, run_id: str, issue_metrics: IssueMetrics):
        """Export errors to CSV"""
        errors_csv = self.csv_dir / 'errors.csv'

        with open(errors_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            for error in issue_metrics.errors:
                writer.writerow([
                    run_id,
                    issue_metrics.issue_id,
                    error.get('agent', ''),
                    error.get('type', ''),
                    error.get('message', ''),
                    error.get('severity', 'error'),
                    error.get('timestamp', '')
                ])

    # ==================== Cleanup ====================

    def cleanup_old_runs(self, max_runs: int = 100, max_age_days: int = 30):
        """
        Clean up old run data.

        Args:
            max_runs: Maximum number of runs to keep
            max_age_days: Maximum age in days
        """
        from datetime import timedelta

        all_runs = sorted(self.runs_dir.glob('run_*'))

        # Keep only last max_runs
        if len(all_runs) > max_runs:
            for old_run in all_runs[:-max_runs]:
                shutil.rmtree(old_run, ignore_errors=True)

        # Delete runs older than max_age_days
        cutoff = datetime.now() - timedelta(days=max_age_days)
        for run_dir in self.runs_dir.glob('run_*'):
            try:
                # Extract timestamp from run_YYYYMMDD_HHMMSS_*
                timestamp_str = run_dir.name.split('_')[1] + '_' + run_dir.name.split('_')[2]
                run_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')

                if run_time < cutoff:
                    shutil.rmtree(run_dir, ignore_errors=True)
            except (IndexError, ValueError):
                # Skip if can't parse timestamp
                continue
