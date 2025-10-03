"""
Run Logger - Tracks overall system run configuration and metadata
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class RunLogger:
    """
    Logs configuration and metadata for each system run.
    Creates a unique run ID and stores all run-level information.
    """

    def __init__(self, project_id: str, config: Dict[str, Any]):
        """
        Initialize run logger with configuration.

        Args:
            project_id: GitLab project ID
            config: System configuration including LLM settings
        """
        self.project_id = project_id
        self.run_id = self._generate_run_id()
        self.start_time = datetime.now()
        self.end_time = None

        # Extract LLM configuration
        self.llm_config = {
            'provider': config.get('llm_provider', 'unknown'),
            'model': config.get('llm_model', 'unknown'),
            'temperature': config.get('llm_temperature', 0.0)
        }

        # Execution mode
        self.mode = config.get('mode', 'implement_all')
        self.specific_issue = config.get('specific_issue')

        # Metrics storage
        self.issues_processed = []
        self.total_errors = 0
        self.total_successes = 0

        # Create logs directory
        self.logs_dir = Path('logs/runs')
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Write initial run metadata
        self._write_run_metadata()

    def _generate_run_id(self) -> str:
        """Generate unique run ID based on timestamp"""
        return f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_project_{self.project_id}"

    def _write_run_metadata(self):
        """Write run metadata to file"""
        metadata = {
            'run_id': self.run_id,
            'project_id': self.project_id,
            'start_time': self.start_time.isoformat(),
            'llm_configuration': self.llm_config,
            'execution_mode': self.mode,
            'specific_issue': self.specific_issue,
            'status': 'running'
        }

        run_file = self.logs_dir / f"{self.run_id}_metadata.json"
        with open(run_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"[RUN LOGGER] Created run: {self.run_id}")
        print(f"[RUN LOGGER] LLM: {self.llm_config['provider']}/{self.llm_config['model']} (temp={self.llm_config['temperature']})")

    def add_issue(self, issue_id: int):
        """Track that an issue is being processed"""
        self.issues_processed.append(issue_id)
        self._update_metadata()

    def record_error(self):
        """Increment error counter"""
        self.total_errors += 1
        self._update_metadata()

    def record_success(self):
        """Increment success counter"""
        self.total_successes += 1
        self._update_metadata()

    def finalize_run(self, status: str = 'completed'):
        """
        Finalize the run and write final statistics.

        Args:
            status: 'completed', 'failed', or 'stopped'
        """
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        final_data = {
            'run_id': self.run_id,
            'project_id': self.project_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': duration,
            'llm_configuration': self.llm_config,
            'execution_mode': self.mode,
            'specific_issue': self.specific_issue,
            'status': status,
            'issues_processed': self.issues_processed,
            'total_issues': len(self.issues_processed),
            'total_successes': self.total_successes,
            'total_errors': self.total_errors,
            'success_rate': (self.total_successes / len(self.issues_processed) * 100) if self.issues_processed else 0
        }

        run_file = self.logs_dir / f"{self.run_id}_final.json"
        with open(run_file, 'w') as f:
            json.dump(final_data, f, indent=2)

        print(f"[RUN LOGGER] Run finalized: {status}")
        print(f"[RUN LOGGER] Duration: {duration:.2f}s")
        print(f"[RUN LOGGER] Issues: {len(self.issues_processed)}, Successes: {self.total_successes}, Errors: {self.total_errors}")

    def _update_metadata(self):
        """Update metadata file with current stats"""
        metadata = {
            'run_id': self.run_id,
            'project_id': self.project_id,
            'start_time': self.start_time.isoformat(),
            'llm_configuration': self.llm_config,
            'execution_mode': self.mode,
            'specific_issue': self.specific_issue,
            'status': 'running',
            'issues_processed': self.issues_processed,
            'total_errors': self.total_errors,
            'total_successes': self.total_successes
        }

        run_file = self.logs_dir / f"{self.run_id}_metadata.json"
        with open(run_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def get_run_summary(self) -> Dict[str, Any]:
        """Get current run summary"""
        return {
            'run_id': self.run_id,
            'llm_config': self.llm_config,
            'issues_processed': len(self.issues_processed),
            'successes': self.total_successes,
            'errors': self.total_errors
        }
