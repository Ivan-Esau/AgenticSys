"""
Issue Tracker - Detailed metrics for each issue
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class IssueTracker:
    """
    Tracks comprehensive metrics for a single issue including:
    - Pipeline attempts (failed/succeeded)
    - Agent execution metrics
    - Debugging cycles
    - Error tracking
    """

    def __init__(self, run_id: str, issue_id: int):
        """
        Initialize issue tracker.

        Args:
            run_id: Parent run ID
            issue_id: GitLab issue number
        """
        self.run_id = run_id
        self.issue_id = issue_id
        self.start_time = datetime.now()
        self.end_time = None

        # Agent-specific metrics
        self.agent_metrics = {
            'planning': {'attempts': 0, 'successes': 0, 'failures': 0, 'duration': 0},
            'coding': {'attempts': 0, 'successes': 0, 'failures': 0, 'duration': 0, 'retries': 0},
            'testing': {'attempts': 0, 'successes': 0, 'failures': 0, 'duration': 0, 'retries': 0},
            'review': {'attempts': 0, 'successes': 0, 'failures': 0, 'duration': 0, 'retries': 0}
        }

        # Pipeline tracking
        self.pipeline_attempts = []  # List of all pipeline runs
        self.failed_pipelines = 0
        self.succeeded_pipelines = 0

        # Debugging cycles tracking
        self.debugging_cycles = []  # Each cycle = {agent, error_type, attempts, resolution}

        # Error tracking
        self.errors = []  # List of all errors encountered

        # Current debugging context
        self.current_cycle = None

        # Logs directory
        self.logs_dir = Path(f'logs/runs/{run_id}/issues')
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        print(f"[ISSUE TRACKER] Started tracking issue #{issue_id} (run: {run_id})")

    def start_agent(self, agent_name: str):
        """Record agent execution start"""
        self.agent_metrics[agent_name]['attempts'] += 1
        self.agent_metrics[agent_name]['start_time'] = datetime.now()
        print(f"[ISSUE #{self.issue_id}] Agent {agent_name} attempt #{self.agent_metrics[agent_name]['attempts']}")

    def end_agent(self, agent_name: str, success: bool):
        """Record agent execution end"""
        if 'start_time' in self.agent_metrics[agent_name]:
            duration = (datetime.now() - self.agent_metrics[agent_name]['start_time']).total_seconds()
            self.agent_metrics[agent_name]['duration'] += duration
            del self.agent_metrics[agent_name]['start_time']

        if success:
            self.agent_metrics[agent_name]['successes'] += 1
        else:
            self.agent_metrics[agent_name]['failures'] += 1

        self._save_metrics()

    def record_pipeline_attempt(self, pipeline_id: str, status: str, commit_sha: Optional[str] = None):
        """
        Record a pipeline execution attempt.

        Args:
            pipeline_id: GitLab pipeline ID
            status: 'success', 'failed', 'running', etc.
            commit_sha: Git commit that triggered pipeline
        """
        attempt = {
            'pipeline_id': pipeline_id,
            'status': status,
            'commit_sha': commit_sha,
            'timestamp': datetime.now().isoformat()
        }

        self.pipeline_attempts.append(attempt)

        if status == 'success':
            self.succeeded_pipelines += 1
        elif status == 'failed':
            self.failed_pipelines += 1

        print(f"[ISSUE #{self.issue_id}] Pipeline {pipeline_id}: {status} (total: {len(self.pipeline_attempts)})")
        self._save_metrics()

    def start_debugging_cycle(self, agent: str, error_type: str, error_message: str):
        """
        Start tracking a debugging cycle when pipeline/agent fails.

        Args:
            agent: Which agent is debugging
            error_type: Type of error (e.g., 'test_failure', 'build_error', 'lint_error')
            error_message: Error details
        """
        self.current_cycle = {
            'agent': agent,
            'error_type': error_type,
            'error_message': error_message,
            'start_time': datetime.now().isoformat(),
            'attempts': 0,
            'resolved': False
        }

        # Track error
        self.errors.append({
            'type': error_type,
            'message': error_message,
            'agent': agent,
            'timestamp': datetime.now().isoformat()
        })

        print(f"[ISSUE #{self.issue_id}] Debugging cycle started: {agent} fixing {error_type}")

    def record_debug_attempt(self):
        """Record a debugging attempt within current cycle"""
        if self.current_cycle:
            self.current_cycle['attempts'] += 1
            self.agent_metrics[self.current_cycle['agent']]['retries'] += 1
            print(f"[ISSUE #{self.issue_id}] Debug attempt #{self.current_cycle['attempts']}")

    def end_debugging_cycle(self, resolved: bool):
        """
        End current debugging cycle.

        Args:
            resolved: Whether the issue was successfully resolved
        """
        if self.current_cycle:
            self.current_cycle['end_time'] = datetime.now().isoformat()
            self.current_cycle['resolved'] = resolved

            # Calculate cycle duration
            start = datetime.fromisoformat(self.current_cycle['start_time'])
            end = datetime.fromisoformat(self.current_cycle['end_time'])
            self.current_cycle['duration_seconds'] = (end - start).total_seconds()

            # Store completed cycle
            self.debugging_cycles.append(self.current_cycle)

            status = "RESOLVED" if resolved else "FAILED"
            print(f"[ISSUE #{self.issue_id}] Debugging cycle {status} after {self.current_cycle['attempts']} attempts")

            self.current_cycle = None
            self._save_metrics()

    def finalize_issue(self, status: str):
        """
        Finalize issue tracking and write final report.

        Args:
            status: 'completed', 'failed', or 'skipped'
        """
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        # Calculate statistics
        total_errors = len(self.errors)
        total_debugging_cycles = len(self.debugging_cycles)
        resolved_cycles = sum(1 for cycle in self.debugging_cycles if cycle['resolved'])
        total_pipeline_attempts = len(self.pipeline_attempts)

        # Total retries across all agents
        total_retries = sum(metrics['retries'] for metrics in self.agent_metrics.values())

        final_report = {
            'run_id': self.run_id,
            'issue_id': self.issue_id,
            'status': status,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': duration,

            # Agent metrics
            'agent_metrics': self.agent_metrics,
            'total_agent_retries': total_retries,

            # Pipeline metrics
            'pipeline_attempts': total_pipeline_attempts,
            'succeeded_pipelines': self.succeeded_pipelines,
            'failed_pipelines': self.failed_pipelines,
            'pipeline_success_rate': (self.succeeded_pipelines / total_pipeline_attempts * 100) if total_pipeline_attempts > 0 else 0,
            'pipeline_details': self.pipeline_attempts,

            # Debugging metrics
            'total_errors': total_errors,
            'debugging_cycles': total_debugging_cycles,
            'resolved_cycles': resolved_cycles,
            'debugging_success_rate': (resolved_cycles / total_debugging_cycles * 100) if total_debugging_cycles > 0 else 0,
            'debugging_details': self.debugging_cycles,

            # Error log
            'errors': self.errors
        }

        # Write final report
        report_file = self.logs_dir / f"issue_{self.issue_id}_report.json"
        with open(report_file, 'w') as f:
            json.dump(final_report, f, indent=2)

        print(f"[ISSUE #{self.issue_id}] Final report written:")
        print(f"  - Status: {status}")
        print(f"  - Duration: {duration:.2f}s")
        print(f"  - Pipelines: {total_pipeline_attempts} ({self.succeeded_pipelines} success, {self.failed_pipelines} failed)")
        print(f"  - Debugging cycles: {total_debugging_cycles} ({resolved_cycles} resolved)")
        print(f"  - Errors: {total_errors}")
        print(f"  - Agent retries: {total_retries}")

        return final_report

    def _save_metrics(self):
        """Save current metrics to file (incremental updates)"""
        current_data = {
            'run_id': self.run_id,
            'issue_id': self.issue_id,
            'start_time': self.start_time.isoformat(),
            'agent_metrics': self.agent_metrics,
            'pipeline_attempts': len(self.pipeline_attempts),
            'succeeded_pipelines': self.succeeded_pipelines,
            'failed_pipelines': self.failed_pipelines,
            'debugging_cycles': len(self.debugging_cycles),
            'errors': len(self.errors),
            'status': 'in_progress'
        }

        metrics_file = self.logs_dir / f"issue_{self.issue_id}_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(current_data, f, indent=2)
