"""
CSV Exporter - Outputs metrics as CSV files for Excel analysis
"""

import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class CSVExporter:
    """
    Exports all metrics to CSV files for easy Excel analysis.
    Creates separate CSV files for different metric types.
    """

    def __init__(self, logs_dir: Path):
        """
        Initialize CSV exporter.

        Args:
            logs_dir: Base directory for CSV files
        """
        self.logs_dir = logs_dir
        self.csv_dir = logs_dir / 'csv'
        self.csv_dir.mkdir(parents=True, exist_ok=True)

        # Initialize CSV files with headers
        self._init_csv_files()

    def _init_csv_files(self):
        """Initialize all CSV files with headers"""

        # 1. Runs CSV
        runs_file = self.csv_dir / 'runs.csv'
        if not runs_file.exists():
            with open(runs_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'project_id', 'start_time', 'end_time', 'duration_seconds',
                    'llm_provider', 'llm_model', 'llm_temperature',
                    'execution_mode', 'specific_issue',
                    'status', 'total_issues', 'successful_issues', 'failed_issues',
                    'success_rate', 'total_errors'
                ])

        # 2. Issues CSV
        issues_file = self.csv_dir / 'issues.csv'
        if not issues_file.exists():
            with open(issues_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'issue_iid', 'start_time', 'end_time', 'duration_seconds',
                    'status', 'complexity_score',
                    'total_errors', 'total_pipeline_attempts', 'succeeded_pipelines', 'failed_pipelines',
                    'pipeline_success_rate', 'debugging_cycles', 'resolved_cycles',
                    'debugging_success_rate', 'first_time_right',
                    'total_agent_retries', 'total_tool_calls',
                    'total_tokens', 'input_tokens', 'output_tokens', 'estimated_cost_usd',
                    'files_created', 'files_modified', 'lines_added', 'lines_deleted',
                    'commits', 'test_coverage'
                ])

        # 3. Agents CSV
        agents_file = self.csv_dir / 'agents.csv'
        if not agents_file.exists():
            with open(agents_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'issue_iid', 'agent_name', 'attempt_number',
                    'start_time', 'end_time', 'duration_seconds',
                    'success', 'retries', 'tool_calls', 'tokens_used',
                    'error_message'
                ])

        # 4. Pipelines CSV
        pipelines_file = self.csv_dir / 'pipelines.csv'
        if not pipelines_file.exists():
            with open(pipelines_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'issue_iid', 'pipeline_id', 'commit_sha',
                    'triggered_by', 'retry_attempt',
                    'start_time', 'end_time', 'duration_seconds',
                    'status', 'failed_jobs', 'error_type',
                    'queue_time', 'execution_time'
                ])

        # 5. Debugging Cycles CSV
        debugging_file = self.csv_dir / 'debugging_cycles.csv'
        if not debugging_file.exists():
            with open(debugging_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'issue_iid', 'agent', 'error_type', 'error_message',
                    'start_time', 'end_time', 'duration_seconds',
                    'attempts', 'resolved', 'resolution_method'
                ])

        # 6. Errors CSV
        errors_file = self.csv_dir / 'errors.csv'
        if not errors_file.exists():
            with open(errors_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'issue_iid', 'agent', 'error_type', 'error_message',
                    'timestamp', 'severity', 'resolved'
                ])

        # 7. Tool Usage CSV
        tools_file = self.csv_dir / 'tool_usage.csv'
        if not tools_file.exists():
            with open(tools_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'run_id', 'issue_iid', 'agent', 'tool_name',
                    'call_count', 'success_count', 'failure_count',
                    'avg_duration_ms', 'total_duration_ms'
                ])

    def export_run(self, run_data: Dict[str, Any]):
        """
        Export run-level data to runs.csv

        Args:
            run_data: Dictionary containing run metadata
        """
        runs_file = self.csv_dir / 'runs.csv'
        with open(runs_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                run_data.get('run_id'),
                run_data.get('project_id'),
                run_data.get('start_time'),
                run_data.get('end_time'),
                run_data.get('duration_seconds', 0),
                run_data.get('llm_configuration', {}).get('provider', ''),
                run_data.get('llm_configuration', {}).get('model', ''),
                run_data.get('llm_configuration', {}).get('temperature', 0.0),
                run_data.get('execution_mode', ''),
                run_data.get('specific_issue', ''),
                run_data.get('status', ''),
                run_data.get('total_issues', 0),
                run_data.get('total_successes', 0),
                run_data.get('total_errors', 0),
                run_data.get('success_rate', 0.0),
                run_data.get('total_errors', 0)
            ])

    def export_issue(self, run_id: str, issue_data: Dict[str, Any]):
        """
        Export issue-level data to issues.csv

        Args:
            run_id: Parent run ID
            issue_data: Dictionary containing issue metrics
        """
        issues_file = self.csv_dir / 'issues.csv'
        with open(issues_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                run_id,
                issue_data.get('issue_iid'),
                issue_data.get('start_time'),
                issue_data.get('end_time'),
                issue_data.get('duration_seconds', 0),
                issue_data.get('status'),
                issue_data.get('complexity_score', 0),
                issue_data.get('total_errors', 0),
                issue_data.get('pipeline_attempts', 0),
                issue_data.get('succeeded_pipelines', 0),
                issue_data.get('failed_pipelines', 0),
                issue_data.get('pipeline_success_rate', 0.0),
                issue_data.get('debugging_cycles', 0),
                issue_data.get('resolved_cycles', 0),
                issue_data.get('debugging_success_rate', 0.0),
                issue_data.get('first_time_right', False),
                issue_data.get('total_agent_retries', 0),
                issue_data.get('total_tool_calls', 0),
                issue_data.get('cost_metrics', {}).get('total_tokens', 0),
                issue_data.get('cost_metrics', {}).get('input_tokens', 0),
                issue_data.get('cost_metrics', {}).get('output_tokens', 0),
                issue_data.get('cost_metrics', {}).get('estimated_cost_usd', 0.0),
                issue_data.get('code_metrics', {}).get('files_created', 0),
                issue_data.get('code_metrics', {}).get('files_modified', 0),
                issue_data.get('code_metrics', {}).get('lines_added', 0),
                issue_data.get('code_metrics', {}).get('lines_deleted', 0),
                issue_data.get('code_metrics', {}).get('commits', 0),
                issue_data.get('code_metrics', {}).get('test_coverage', 0.0)
            ])

    def export_agent_execution(self, run_id: str, issue_iid: int, agent_data: Dict[str, Any]):
        """
        Export agent execution data to agents.csv

        Args:
            run_id: Parent run ID
            issue_iid: Issue IID (project-specific internal ID)
            agent_data: Dictionary containing agent metrics
        """
        agents_file = self.csv_dir / 'agents.csv'
        with open(agents_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                run_id,
                issue_iid,
                agent_data.get('agent_name'),
                agent_data.get('attempt_number', 1),
                agent_data.get('start_time'),
                agent_data.get('end_time'),
                agent_data.get('duration_seconds', 0),
                agent_data.get('success', False),
                agent_data.get('retries', 0),
                agent_data.get('tool_calls', 0),
                agent_data.get('tokens_used', 0),
                agent_data.get('error_message', '')
            ])

    def export_pipeline(self, run_id: str, issue_iid: int, pipeline_data: Dict[str, Any]):
        """
        Export pipeline data to pipelines.csv

        Args:
            run_id: Parent run ID
            issue_iid: Issue IID (project-specific internal ID)
            pipeline_data: Dictionary containing pipeline metrics
        """
        pipelines_file = self.csv_dir / 'pipelines.csv'
        with open(pipelines_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                run_id,
                issue_iid,
                pipeline_data.get('pipeline_id'),
                pipeline_data.get('commit_sha', ''),
                pipeline_data.get('triggered_by', ''),
                pipeline_data.get('retry_attempt', 0),
                pipeline_data.get('start_time'),
                pipeline_data.get('end_time'),
                pipeline_data.get('duration_seconds', 0),
                pipeline_data.get('status'),
                ','.join(pipeline_data.get('failed_jobs', [])),
                pipeline_data.get('error_type', ''),
                pipeline_data.get('queue_time', 0),
                pipeline_data.get('execution_time', 0)
            ])

    def export_debugging_cycle(self, run_id: str, issue_iid: int, cycle_data: Dict[str, Any]):
        """
        Export debugging cycle data to debugging_cycles.csv

        Args:
            run_id: Parent run ID
            issue_iid: Issue IID (project-specific internal ID)
            cycle_data: Dictionary containing cycle metrics
        """
        debugging_file = self.csv_dir / 'debugging_cycles.csv'
        with open(debugging_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                run_id,
                issue_iid,
                cycle_data.get('agent'),
                cycle_data.get('error_type'),
                cycle_data.get('error_message', ''),
                cycle_data.get('start_time'),
                cycle_data.get('end_time'),
                cycle_data.get('duration_seconds', 0),
                cycle_data.get('attempts', 0),
                cycle_data.get('resolved', False),
                cycle_data.get('resolution_method', '')
            ])

    def export_error(self, run_id: str, issue_iid: int, error_data: Dict[str, Any]):
        """
        Export error data to errors.csv

        Args:
            run_id: Parent run ID
            issue_iid: Issue IID (project-specific internal ID)
            error_data: Dictionary containing error info
        """
        errors_file = self.csv_dir / 'errors.csv'
        with open(errors_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                run_id,
                issue_iid,
                error_data.get('agent', ''),
                error_data.get('type', ''),
                error_data.get('message', ''),
                error_data.get('timestamp'),
                error_data.get('severity', 'error'),
                error_data.get('resolved', False)
            ])

    def export_tool_usage(self, run_id: str, issue_iid: int, tool_stats: Dict[str, Any]):
        """
        Export tool usage statistics to tool_usage.csv

        Args:
            run_id: Parent run ID
            issue_iid: Issue IID (project-specific internal ID)
            tool_stats: Dictionary containing tool usage metrics
        """
        tools_file = self.csv_dir / 'tool_usage.csv'
        with open(tools_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write one row per tool
            agent = tool_stats.get('agent', '')
            for tool_name, stats in tool_stats.get('tools', {}).items():
                writer.writerow([
                    run_id,
                    issue_iid,
                    agent,
                    tool_name,
                    stats.get('call_count', 0),
                    stats.get('success_count', 0),
                    stats.get('failure_count', 0),
                    stats.get('avg_duration_ms', 0),
                    stats.get('total_duration_ms', 0)
                ])

    def get_summary_report(self) -> str:
        """
        Generate a summary of all CSV files for user reference.

        Returns:
            Formatted string with CSV file locations and descriptions
        """
        summary = f"""
=== CSV Export Summary ===

All metrics exported to: {self.csv_dir}

Files created:
1. runs.csv           - Overall run configuration and results
2. issues.csv         - Detailed metrics per issue
3. agents.csv         - Agent execution data (one row per execution)
4. pipelines.csv      - Pipeline attempts and results
5. debugging_cycles.csv - Debugging cycle tracking
6. errors.csv         - All errors encountered
7. tool_usage.csv     - Tool usage statistics

Excel Analysis Tips:
- Use Pivot Tables for aggregations
- Filter by run_id to analyze specific runs
- Compare LLM models using runs.csv
- Track agent performance in agents.csv
- Analyze pipeline reliability in pipelines.csv

Example Excel Analyses:
1. Success rate by LLM model (Pivot: llm_model vs success_rate)
2. Average retries by agent (Pivot: agent_name vs avg(retries))
3. Pipeline success rate over time (Chart: date vs pipeline_success_rate)
4. Most common errors (Pivot: error_type vs count)
5. Cost efficiency (Chart: estimated_cost_usd vs successful_issues)
"""
        return summary
