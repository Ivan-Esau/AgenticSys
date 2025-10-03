"""
Metrics Analyzer - Comparative analysis tools
Helps identify which configurations and parameters perform better
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import statistics


@dataclass
class RunComparison:
    """Comparison result between runs"""
    metric_name: str
    values: Dict[str, float]  # run_id -> value
    best_run_id: str
    best_value: float
    worst_run_id: str
    worst_value: float
    avg_value: float
    std_dev: float
    improvement_percent: float  # Best vs worst


class MetricsAnalyzer:
    """
    Analyze and compare metrics across multiple runs.
    Helps identify which parameters influence performance.
    """

    def __init__(self, logs_dir: Path = Path("logs")):
        """
        Initialize analyzer.

        Args:
            logs_dir: Base logs directory
        """
        self.logs_dir = logs_dir
        self.runs_dir = logs_dir / "runs"
        self.csv_dir = logs_dir / "csv"

    # ==================== Data Loading ====================

    def load_all_runs(self) -> List[Dict[str, Any]]:
        """
        Load metadata for all runs.

        Returns:
            List of run metadata dictionaries
        """
        runs = []

        for run_dir in self.runs_dir.glob("run_*"):
            metadata_file = run_dir / "metadata.json"
            final_file = run_dir / "final_report.json"

            # Prefer final report if available
            if final_file.exists():
                with open(final_file, 'r', encoding='utf-8') as f:
                    runs.append(json.load(f))
            elif metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    runs.append(json.load(f))

        return runs

    def load_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Load specific run data.

        Args:
            run_id: Run ID to load

        Returns:
            Run data or None
        """
        run_dir = self.runs_dir / run_id
        final_file = run_dir / "final_report.json"
        metadata_file = run_dir / "metadata.json"

        if final_file.exists():
            with open(final_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        return None

    def load_runs_csv(self) -> List[Dict[str, Any]]:
        """
        Load runs from CSV.

        Returns:
            List of run data from CSV
        """
        runs_csv = self.csv_dir / "runs.csv"

        if not runs_csv.exists():
            return []

        runs = []
        with open(runs_csv, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                runs.append(row)

        return runs

    # ==================== Comparative Analysis ====================

    def compare_llm_models(self) -> Dict[str, Any]:
        """
        Compare performance across different LLM models.

        Returns:
            Comparison results by model
        """
        runs = self.load_runs_csv()

        # Group by model
        by_model = defaultdict(list)

        for run in runs:
            model = run.get('llm_model', 'unknown')
            if model:
                by_model[model].append(run)

        # Calculate statistics for each model
        results = {}

        for model, model_runs in by_model.items():
            results[model] = self._calculate_model_stats(model_runs)

        return results

    def compare_temperatures(self) -> Dict[str, Any]:
        """
        Compare performance across different temperature settings.

        Returns:
            Comparison results by temperature
        """
        runs = self.load_runs_csv()

        # Group by temperature
        by_temp = defaultdict(list)

        for run in runs:
            temp = run.get('llm_temperature', '0.0')
            temp_key = f"temp_{temp}"
            by_temp[temp_key].append(run)

        # Calculate statistics
        results = {}

        for temp, temp_runs in by_temp.items():
            results[temp] = self._calculate_model_stats(temp_runs)

        return results

    def compare_configurations(self, group_by: str = 'llm_model') -> Dict[str, RunComparison]:
        """
        Compare runs grouped by specific configuration parameter.

        Args:
            group_by: Parameter to group by (llm_model, llm_temperature, max_retries, etc.)

        Returns:
            Dictionary of comparisons
        """
        runs = self.load_runs_csv()

        # Metrics to compare
        metrics = [
            'success_rate_percent',
            'total_cost_usd',
            'total_agent_duration_seconds',
            'total_errors',
            'total_debugging_cycles'
        ]

        comparisons = {}

        for metric in metrics:
            comparisons[metric] = self._compare_metric_across_groups(
                runs, group_by, metric
            )

        return comparisons

    def _compare_metric_across_groups(self, runs: List[Dict], group_by: str,
                                       metric: str) -> Dict[str, Any]:
        """
        Compare a specific metric across groups.

        Args:
            runs: List of runs
            group_by: Grouping parameter
            metric: Metric to compare

        Returns:
            Comparison results
        """
        # Group runs
        grouped = defaultdict(list)

        for run in runs:
            group_value = run.get(group_by, 'unknown')
            metric_value = self._parse_numeric(run.get(metric, 0))
            if metric_value is not None:
                grouped[group_value].append(metric_value)

        # Calculate statistics for each group
        results = {}

        for group, values in grouped.items():
            if values:
                results[group] = {
                    'count': len(values),
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
                    'min': min(values),
                    'max': max(values)
                }

        return results

    def _calculate_model_stats(self, runs: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics for a set of runs"""
        if not runs:
            return {}

        stats = {
            'run_count': len(runs),
            'avg_success_rate': self._avg_metric(runs, 'success_rate_percent'),
            'avg_cost': self._avg_metric(runs, 'total_cost_usd'),
            'avg_duration': self._avg_metric(runs, 'total_agent_duration_seconds'),
            'avg_errors': self._avg_metric(runs, 'total_errors'),
            'total_issues_processed': sum(
                int(r.get('total_issues', 0) or 0) for r in runs
            ),
            'total_successful_issues': sum(
                int(r.get('successful_issues', 0) or 0) for r in runs
            )
        }

        return stats

    def _avg_metric(self, runs: List[Dict], metric: str) -> float:
        """Calculate average of a metric across runs"""
        values = [self._parse_numeric(r.get(metric, 0)) for r in runs]
        values = [v for v in values if v is not None]

        if not values:
            return 0.0

        return statistics.mean(values)

    def _parse_numeric(self, value: Any) -> Optional[float]:
        """Parse numeric value from string or number"""
        if value is None or value == '':
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    # ==================== Cost Analysis ====================

    def analyze_cost_efficiency(self) -> Dict[str, Any]:
        """
        Analyze cost efficiency across runs.

        Returns:
            Cost efficiency analysis
        """
        runs = self.load_runs_csv()

        # Calculate cost per successful issue
        efficiency_data = []

        for run in runs:
            cost = self._parse_numeric(run.get('total_cost_usd', 0))
            successful = self._parse_numeric(run.get('successful_issues', 0))

            if cost and successful and successful > 0:
                cost_per_issue = cost / successful

                efficiency_data.append({
                    'run_id': run.get('run_id'),
                    'model': run.get('llm_model'),
                    'cost_per_issue': cost_per_issue,
                    'total_cost': cost,
                    'successful_issues': successful
                })

        # Sort by cost efficiency (cheapest per issue first)
        efficiency_data.sort(key=lambda x: x['cost_per_issue'])

        return {
            'most_efficient': efficiency_data[:5] if efficiency_data else [],
            'least_efficient': efficiency_data[-5:] if efficiency_data else [],
            'avg_cost_per_issue': statistics.mean(
                [d['cost_per_issue'] for d in efficiency_data]
            ) if efficiency_data else 0.0
        }

    # ==================== Performance Analysis ====================

    def analyze_performance_trends(self) -> Dict[str, Any]:
        """
        Analyze performance trends over time.

        Returns:
            Performance trend analysis
        """
        runs = self.load_runs_csv()

        # Sort by time
        runs_with_time = [
            r for r in runs
            if r.get('start_time')
        ]
        runs_with_time.sort(key=lambda x: x['start_time'])

        # Calculate moving average of success rate
        window_size = 5
        moving_avg = []

        for i in range(len(runs_with_time) - window_size + 1):
            window = runs_with_time[i:i + window_size]
            avg_success = self._avg_metric(window, 'success_rate_percent')
            moving_avg.append({
                'run_index': i + window_size,
                'avg_success_rate': avg_success
            })

        # Detect improvement or degradation
        if len(moving_avg) >= 2:
            first_avg = moving_avg[0]['avg_success_rate']
            last_avg = moving_avg[-1]['avg_success_rate']
            trend = "improving" if last_avg > first_avg else "degrading"
            change_percent = ((last_avg - first_avg) / first_avg * 100
                              if first_avg > 0 else 0)
        else:
            trend = "insufficient_data"
            change_percent = 0.0

        return {
            'total_runs': len(runs_with_time),
            'moving_average': moving_avg,
            'trend': trend,
            'change_percent': change_percent
        }

    # ==================== Best Configuration ====================

    def find_best_configuration(self) -> Dict[str, Any]:
        """
        Find the best performing configuration.

        Returns:
            Best configuration analysis
        """
        runs = self.load_runs_csv()

        if not runs:
            return {'error': 'No runs available'}

        # Score each run (higher is better)
        scored_runs = []

        for run in runs:
            score = self._calculate_run_score(run)
            if score is not None:
                scored_runs.append({
                    'run_id': run.get('run_id'),
                    'score': score,
                    'config': {
                        'llm_provider': run.get('llm_provider'),
                        'llm_model': run.get('llm_model'),
                        'llm_temperature': run.get('llm_temperature'),
                        'max_retries': run.get('max_retries')
                    },
                    'metrics': {
                        'success_rate': run.get('success_rate_percent'),
                        'cost': run.get('total_cost_usd'),
                        'duration': run.get('total_agent_duration_seconds')
                    }
                })

        # Sort by score
        scored_runs.sort(key=lambda x: x['score'], reverse=True)

        return {
            'best_run': scored_runs[0] if scored_runs else None,
            'worst_run': scored_runs[-1] if scored_runs else None,
            'top_5': scored_runs[:5],
            'avg_score': statistics.mean([r['score'] for r in scored_runs])
                         if scored_runs else 0.0
        }

    def _calculate_run_score(self, run: Dict[str, Any]) -> Optional[float]:
        """
        Calculate overall score for a run.
        Considers success rate, cost, and duration.

        Args:
            run: Run data

        Returns:
            Score (0-100) or None
        """
        success_rate = self._parse_numeric(run.get('success_rate_percent', 0))
        cost = self._parse_numeric(run.get('total_cost_usd', 0))
        duration = self._parse_numeric(run.get('total_agent_duration_seconds', 0))
        total_issues = self._parse_numeric(run.get('total_issues', 0))

        if success_rate is None or total_issues == 0:
            return None

        # Scoring formula (weights can be adjusted)
        # 60% success rate, 20% cost efficiency, 20% time efficiency

        score = success_rate * 0.6

        # Cost efficiency (lower is better)
        # Normalize: $0.01 per issue = 100 points, $1.00 per issue = 0 points
        if cost and total_issues and total_issues > 0:
            cost_per_issue = cost / total_issues
            cost_score = max(0, 100 - (cost_per_issue * 100))
            score += cost_score * 0.2

        # Time efficiency (lower is better)
        # Normalize: 60s per issue = 100 points, 600s per issue = 0 points
        if duration and total_issues and total_issues > 0:
            time_per_issue = duration / total_issues
            time_score = max(0, 100 - (time_per_issue / 6))
            score += time_score * 0.2

        return score

    # ==================== Report Generation ====================

    def generate_comparison_report(self, output_file: Optional[Path] = None) -> str:
        """
        Generate comprehensive comparison report.

        Args:
            output_file: Optional file to write report to

        Returns:
            Report text
        """
        report_lines = []

        report_lines.append("=" * 80)
        report_lines.append("METRICS COMPARISON REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")

        # Best configuration
        report_lines.append("## Best Configuration")
        report_lines.append("")
        best_config = self.find_best_configuration()
        if best_config.get('best_run'):
            best = best_config['best_run']
            report_lines.append(f"Run ID: {best['run_id']}")
            report_lines.append(f"Score: {best['score']:.2f}/100")
            report_lines.append(f"Model: {best['config']['llm_model']}")
            report_lines.append(f"Temperature: {best['config']['llm_temperature']}")
            report_lines.append(f"Success Rate: {best['metrics']['success_rate']}%")
            report_lines.append(f"Total Cost: ${best['metrics']['cost']}")
        report_lines.append("")

        # LLM comparison
        report_lines.append("## LLM Model Comparison")
        report_lines.append("")
        llm_comparison = self.compare_llm_models()
        for model, stats in llm_comparison.items():
            report_lines.append(f"### {model}")
            report_lines.append(f"  Runs: {stats.get('run_count', 0)}")
            report_lines.append(f"  Avg Success Rate: {stats.get('avg_success_rate', 0):.2f}%")
            report_lines.append(f"  Avg Cost: ${stats.get('avg_cost', 0):.4f}")
            report_lines.append(f"  Avg Duration: {stats.get('avg_duration', 0):.2f}s")
            report_lines.append("")

        # Cost efficiency
        report_lines.append("## Cost Efficiency")
        report_lines.append("")
        cost_analysis = self.analyze_cost_efficiency()
        if cost_analysis.get('most_efficient'):
            report_lines.append("Most Efficient (Cost per Issue):")
            for item in cost_analysis['most_efficient']:
                report_lines.append(
                    f"  {item['model']}: ${item['cost_per_issue']:.4f} "
                    f"({item['successful_issues']} issues)"
                )
        report_lines.append("")

        # Performance trends
        report_lines.append("## Performance Trends")
        report_lines.append("")
        trends = self.analyze_performance_trends()
        report_lines.append(f"Total Runs: {trends.get('total_runs', 0)}")
        report_lines.append(f"Trend: {trends.get('trend', 'unknown')}")
        report_lines.append(f"Change: {trends.get('change_percent', 0):.2f}%")
        report_lines.append("")

        report_lines.append("=" * 80)

        report = "\n".join(report_lines)

        # Write to file if specified
        if output_file:
            output_file.write_text(report, encoding='utf-8')

        return report


# Utility function for quick analysis
def quick_analysis(logs_dir: Path = Path("logs")) -> str:
    """
    Perform quick analysis and return report.

    Args:
        logs_dir: Logs directory

    Returns:
        Analysis report
    """
    analyzer = MetricsAnalyzer(logs_dir)
    return analyzer.generate_comparison_report()
