"""
Modern 5-stage pipeline configuration based on CI/CD best practices.
Implements consistent structure across tech stacks for research comparability.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import json


class PipelineConfig:
    """Modern 5-stage pipeline configuration for research comparability."""

    # Standard stages for all pipelines (consistency for research)
    STANDARD_STAGES = ['validate', 'build', 'test', 'analyze', 'deploy']

    # Minimal stages for agent workflow (fast feedback)
    MINIMAL_STAGES = ['test', 'build']

    # Pipeline modes
    MODES = ['minimal', 'standard', 'full']

    def __init__(self, tech_stack: Optional[Dict[str, str]] = None, mode: str = 'minimal'):
        """
        Initialize pipeline configuration.

        Args:
            tech_stack: Dict with 'backend', 'frontend', 'min_coverage', etc.
            mode: 'minimal' (2 stages), 'standard' (3 stages), or 'full' (5 stages)
        """
        self.tech_stack = tech_stack or {}
        self.backend = self.tech_stack.get('backend', 'python')
        self.frontend = self.tech_stack.get('frontend', 'none')
        self.min_coverage = self.tech_stack.get('min_coverage', 70)
        self.enable_security = self.tech_stack.get('enable_security', True)
        self.enable_quality = self.tech_stack.get('enable_quality', True)

        # Pipeline mode (minimal by default for agent workflow)
        self.mode = mode if mode in self.MODES else 'minimal'

        # Load configuration based on tech stack
        self.config = self._load_stack_config()

    def _load_stack_config(self) -> Dict[str, Any]:
        """Load modern pipeline configuration based on tech stack."""

        # Base configuration (same for all tech stacks for research consistency)
        config = {
            'pipeline_file': '.gitlab-ci.yml',
            'stages': self.STANDARD_STAGES,
            'cache_strategy': 'pull-push',
            'interruptible': True,  # Allow canceling outdated pipelines
            'default_retry': {
                'max': 2,
                'when': ['network_failure', 'runner_system_failure']
            },
            # Include tech_stack in config for agents
            'tech_stack': self.tech_stack
        }

        # Tech-stack specific configuration
        if self.backend == 'python':
            config.update(self._python_config())
        elif self.backend == 'java':
            config.update(self._java_config())
        elif self.backend in ['javascript', 'node', 'nodejs']:
            config.update(self._nodejs_config())
        elif self.backend == 'go':
            config.update(self._go_config())
        elif self.backend == 'rust':
            config.update(self._rust_config())
        else:
            config.update(self._default_config())

        return config

    def _python_config(self) -> Dict[str, Any]:
        """Python-specific pipeline configuration."""
        return {
            'docker_image': 'python:3.11-slim',
            'variables': {
                'PIP_CACHE_DIR': '$CI_PROJECT_DIR/.cache/pip',
                'PYTHONPATH': '$CI_PROJECT_DIR'
            },
            'cache': {
                'key': '${CI_JOB_NAME}-${CI_COMMIT_REF_SLUG}',
                'paths': ['.cache/pip', 'venv/']
            },
            'jobs': {
                'validate:lint': {
                    'stage': 'validate',
                    'script': [
                        'pip install --quiet flake8 black mypy',
                        'flake8 src/ --count --show-source --statistics',
                        'black --check src/',
                        'mypy src/ --ignore-missing-imports'
                    ],
                    'allow_failure': False
                },
                'validate:dependencies': {
                    'stage': 'validate',
                    'script': [
                        'pip install --quiet pip-audit',
                        'pip-audit --desc'
                    ],
                    'allow_failure': True
                },
                'build:package': {
                    'stage': 'build',
                    'script': [
                        'pip install --quiet build wheel setuptools',
                        'python -m build'
                    ],
                    'artifacts': {
                        'paths': ['dist/'],
                        'expire_in': '1 week'
                    }
                },
                'test:unit': {
                    'stage': 'test',
                    'script': [
                        'pip install --quiet pytest pytest-cov pytest-html',
                        f'pytest --cov=src --cov-report=xml --cov-report=html --cov-report=term --cov-fail-under={self.min_coverage}'
                    ],
                    'coverage': '/TOTAL.*\\s+(\\d+)%/',
                    'artifacts': {
                        'reports': {
                            'junit': 'report.xml',
                            'coverage_report': {
                                'coverage_format': 'cobertura',
                                'path': 'coverage.xml'
                            }
                        },
                        'paths': ['htmlcov/'],
                        'expire_in': '30 days'
                    }
                },
                'analyze:security': {
                    'stage': 'analyze',
                    'script': [
                        'pip install --quiet bandit safety',
                        'bandit -r src/ -f json -o bandit-report.json',
                        'safety check --json > safety-report.json || true'
                    ],
                    'artifacts': {
                        'paths': ['*-report.json'],
                        'expire_in': '30 days'
                    },
                    'allow_failure': True
                },
                'analyze:quality': {
                    'stage': 'analyze',
                    'script': [
                        'pip install --quiet radon',
                        'radon cc src/ -s -j > complexity-report.json',
                        'radon mi src/ -s -j > maintainability-report.json'
                    ],
                    'artifacts': {
                        'paths': ['*-report.json'],
                        'expire_in': '30 days'
                    }
                }
            }
        }

    def _java_config(self) -> Dict[str, Any]:
        """Java-specific pipeline configuration."""
        return {
            'docker_image': 'maven:3.9-eclipse-temurin-21',
            'variables': {
                'MAVEN_OPTS': '-Dmaven.repo.local=$CI_PROJECT_DIR/.m2/repository',
                'MAVEN_CLI_OPTS': '--batch-mode --errors --fail-at-end --show-version'
            },
            'cache': {
                'key': '${CI_JOB_NAME}-${CI_COMMIT_REF_SLUG}',
                'paths': ['.m2/repository/', 'target/']
            },
            'jobs': {
                'validate:lint': {
                    'stage': 'validate',
                    'script': [
                        'mvn $MAVEN_CLI_OPTS checkstyle:check',
                        'mvn $MAVEN_CLI_OPTS spotbugs:check'
                    ],
                    'allow_failure': False
                },
                'build:compile': {
                    'stage': 'build',
                    'script': [
                        'mvn $MAVEN_CLI_OPTS clean compile'
                    ],
                    'artifacts': {
                        'paths': ['target/classes/'],
                        'expire_in': '1 week'
                    }
                },
                'test:unit': {
                    'stage': 'test',
                    'needs': ['build:compile'],
                    'script': [
                        f'mvn $MAVEN_CLI_OPTS test jacoco:report -Djacoco.minimum.coverage={self.min_coverage/100}'
                    ],
                    'coverage': '/Total.*?([0-9]{1,3})%/',
                    'artifacts': {
                        'reports': {
                            'junit': 'target/surefire-reports/TEST-*.xml',
                            'coverage_report': {
                                'coverage_format': 'cobertura',
                                'path': 'target/site/jacoco/jacoco.xml'
                            }
                        },
                        'paths': ['target/site/jacoco/'],
                        'expire_in': '30 days'
                    }
                },
                'test:integration': {
                    'stage': 'test',
                    'needs': ['build:compile'],
                    'script': [
                        'mvn $MAVEN_CLI_OPTS verify -DskipUnitTests'
                    ],
                    'allow_failure': True
                },
                'analyze:security': {
                    'stage': 'analyze',
                    'script': [
                        'mvn $MAVEN_CLI_OPTS dependency-check:check'
                    ],
                    'artifacts': {
                        'paths': ['target/dependency-check-report.html'],
                        'expire_in': '30 days'
                    },
                    'allow_failure': True
                },
                'analyze:quality': {
                    'stage': 'analyze',
                    'script': [
                        'mvn $MAVEN_CLI_OPTS sonar:sonar -Dsonar.projectKey=$CI_PROJECT_PATH_SLUG || true'
                    ],
                    'allow_failure': True
                }
            }
        }

    def _nodejs_config(self) -> Dict[str, Any]:
        """Node.js-specific pipeline configuration."""
        return {
            'docker_image': 'node:20-alpine',
            'variables': {
                'NPM_CONFIG_CACHE': '$CI_PROJECT_DIR/.npm'
            },
            'cache': {
                'key': '${CI_JOB_NAME}-${CI_COMMIT_REF_SLUG}',
                'paths': ['.npm/', 'node_modules/']
            },
            'jobs': {
                'validate:lint': {
                    'stage': 'validate',
                    'script': [
                        'npm ci --silent',
                        'npm run lint || npx eslint src/',
                        'npm run prettier:check || npx prettier --check "src/**/*.{js,jsx,ts,tsx}"'
                    ],
                    'allow_failure': False
                },
                'validate:audit': {
                    'stage': 'validate',
                    'script': [
                        'npm audit --audit-level=moderate'
                    ],
                    'allow_failure': True
                },
                'build:compile': {
                    'stage': 'build',
                    'script': [
                        'npm ci --silent',
                        'npm run build || npm run compile || echo "No build step defined"'
                    ],
                    'artifacts': {
                        'paths': ['dist/', 'build/'],
                        'expire_in': '1 week'
                    }
                },
                'test:unit': {
                    'stage': 'test',
                    'script': [
                        'npm ci --silent',
                        f'npm run test:coverage || npx jest --coverage --coverageThreshold=\'{{"global":{{"lines":{self.min_coverage}}}}}\''
                    ],
                    'coverage': '/Lines\\s*:\\s*(\\d+\\.\\d+)%/',
                    'artifacts': {
                        'reports': {
                            'junit': 'junit.xml',
                            'coverage_report': {
                                'coverage_format': 'cobertura',
                                'path': 'coverage/cobertura-coverage.xml'
                            }
                        },
                        'paths': ['coverage/'],
                        'expire_in': '30 days'
                    }
                },
                'analyze:quality': {
                    'stage': 'analyze',
                    'script': [
                        'npm ci --silent',
                        'npx jscpd src/ --min-tokens 50 --reporters "json" --output jscpd-report.json'
                    ],
                    'artifacts': {
                        'paths': ['*-report.json'],
                        'expire_in': '30 days'
                    },
                    'allow_failure': True
                }
            }
        }

    def _go_config(self) -> Dict[str, Any]:
        """Go-specific pipeline configuration."""
        return {
            'docker_image': 'golang:1.21-alpine',
            'variables': {
                'GOPATH': '$CI_PROJECT_DIR/.go',
                'GO111MODULE': 'on'
            },
            'cache': {
                'key': '${CI_JOB_NAME}-${CI_COMMIT_REF_SLUG}',
                'paths': ['.go/', 'vendor/']
            },
            'before_script': [
                'apk add --no-cache git gcc musl-dev'
            ],
            'jobs': {
                'validate:lint': {
                    'stage': 'validate',
                    'script': [
                        'go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest',
                        'golangci-lint run --timeout 5m'
                    ],
                    'allow_failure': False
                },
                'validate:vet': {
                    'stage': 'validate',
                    'script': [
                        'go vet ./...'
                    ],
                    'allow_failure': False
                },
                'build:compile': {
                    'stage': 'build',
                    'script': [
                        'go build -v ./...'
                    ],
                    'artifacts': {
                        'paths': ['bin/'],
                        'expire_in': '1 week'
                    }
                },
                'test:unit': {
                    'stage': 'test',
                    'script': [
                        f'go test -v -coverprofile=coverage.out -covermode=atomic ./...',
                        'go tool cover -func=coverage.out',
                        f'coverage=$(go tool cover -func=coverage.out | grep total | awk \'{{print $3}}\' | sed \'s/%//\')',
                        f'echo "Coverage: $coverage%"',
                        f'if [ $(echo "$coverage < {self.min_coverage}" | bc) -eq 1 ]; then exit 1; fi'
                    ],
                    'coverage': '/Coverage: (\\d+\\.\\d+)%/',
                    'artifacts': {
                        'paths': ['coverage.out'],
                        'expire_in': '30 days'
                    }
                },
                'analyze:security': {
                    'stage': 'analyze',
                    'script': [
                        'go install github.com/securego/gosec/v2/cmd/gosec@latest',
                        'gosec -fmt json -out gosec-report.json ./...'
                    ],
                    'artifacts': {
                        'paths': ['*-report.json'],
                        'expire_in': '30 days'
                    },
                    'allow_failure': True
                }
            }
        }

    def _rust_config(self) -> Dict[str, Any]:
        """Rust-specific pipeline configuration."""
        return {
            'docker_image': 'rust:1.75',
            'variables': {
                'CARGO_HOME': '$CI_PROJECT_DIR/.cargo'
            },
            'cache': {
                'key': '${CI_JOB_NAME}-${CI_COMMIT_REF_SLUG}',
                'paths': ['.cargo/', 'target/']
            },
            'jobs': {
                'validate:lint': {
                    'stage': 'validate',
                    'script': [
                        'rustup component add clippy rustfmt',
                        'cargo fmt -- --check',
                        'cargo clippy -- -D warnings'
                    ],
                    'allow_failure': False
                },
                'build:compile': {
                    'stage': 'build',
                    'script': [
                        'cargo build --release'
                    ],
                    'artifacts': {
                        'paths': ['target/release/'],
                        'expire_in': '1 week'
                    }
                },
                'test:unit': {
                    'stage': 'test',
                    'script': [
                        'cargo install cargo-tarpaulin',
                        f'cargo tarpaulin --out Xml --fail-under {self.min_coverage}'
                    ],
                    'coverage': '/(\\d+\\.\\d+)% coverage/',
                    'artifacts': {
                        'reports': {
                            'coverage_report': {
                                'coverage_format': 'cobertura',
                                'path': 'cobertura.xml'
                            }
                        },
                        'expire_in': '30 days'
                    }
                },
                'analyze:security': {
                    'stage': 'analyze',
                    'script': [
                        'cargo install cargo-audit',
                        'cargo audit'
                    ],
                    'allow_failure': True
                }
            }
        }

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for unknown tech stacks."""
        return {
            'docker_image': 'alpine:latest',
            'jobs': {
                'validate:check': {
                    'stage': 'validate',
                    'script': ['echo "No validation configured for unknown tech stack"']
                },
                'build:compile': {
                    'stage': 'build',
                    'script': ['echo "No build configured for unknown tech stack"']
                },
                'test:unit': {
                    'stage': 'test',
                    'script': ['echo "No tests configured for unknown tech stack"']
                },
                'analyze:check': {
                    'stage': 'analyze',
                    'script': ['echo "No analysis configured for unknown tech stack"']
                },
                'deploy:skip': {
                    'stage': 'deploy',
                    'script': ['echo "No deployment configured"']
                }
            }
        }

    def generate_pipeline_yaml(self) -> str:
        """
        Generate GitLab CI YAML configuration based on pipeline mode.

        Returns:
            YAML string for .gitlab-ci.yml
        """
        # Route to appropriate generator based on mode
        if self.mode == 'minimal':
            return self.generate_minimal_pipeline_yaml()
        elif self.mode == 'full':
            return self._generate_full_pipeline_yaml()
        else:  # standard mode (future implementation)
            return self._generate_full_pipeline_yaml()

    def _generate_full_pipeline_yaml(self) -> str:
        """Generate full 5-stage GitLab CI YAML configuration."""
        yaml_lines = []

        # Header
        yaml_lines.extend([
            f"# Modern 5-Stage CI/CD Pipeline for {self.backend}",
            "# Auto-generated by PipelineConfig",
            "# Following CI/CD best practices for research comparability",
            "",
            f"image: {self.config.get('docker_image', 'alpine:latest')}",
            ""
        ])

        # Stages
        yaml_lines.extend([
            "stages:",
            *[f"  - {stage}" for stage in self.config['stages']],
            ""
        ])

        # Variables
        if 'variables' in self.config:
            yaml_lines.append("variables:")
            for key, value in self.config['variables'].items():
                yaml_lines.append(f'  {key}: "{value}"')
            yaml_lines.append("")

        # Cache
        if 'cache' in self.config:
            yaml_lines.extend([
                "cache:",
                f"  key: {self.config['cache']['key']}",
                "  paths:",
                *[f"    - {path}" for path in self.config['cache']['paths']],
                ""
            ])

        # Default configuration
        yaml_lines.extend([
            "default:",
            "  interruptible: true",
            "  retry:",
            "    max: 2",
            "    when:",
            "      - runner_system_failure",
            "      - stuck_or_timeout_failure",
            ""
        ])

        # Global before_script if exists
        if 'before_script' in self.config and self.config['before_script']:
            yaml_lines.append("before_script:")
            for cmd in self.config['before_script']:
                yaml_lines.append(f"  - {cmd}")
            yaml_lines.append("")

        # Jobs
        if 'jobs' in self.config:
            for job_name, job_config in self.config['jobs'].items():
                yaml_lines.append(f"{job_name}:")
                yaml_lines.append(f"  stage: {job_config['stage']}")

                # Add needs if specified
                if 'needs' in job_config:
                    yaml_lines.append("  needs:")
                    for need in job_config['needs']:
                        yaml_lines.append(f"    - {need}")

                # Script
                yaml_lines.append("  script:")
                for cmd in job_config['script']:
                    yaml_lines.append(f"    - {cmd}")

                # Coverage regex
                if 'coverage' in job_config:
                    yaml_lines.append(f"  coverage: '{job_config['coverage']}'")

                # Artifacts
                if 'artifacts' in job_config:
                    yaml_lines.append("  artifacts:")
                    if 'reports' in job_config['artifacts']:
                        yaml_lines.append("    reports:")
                        for report_type, report_path in job_config['artifacts']['reports'].items():
                            if isinstance(report_path, dict):
                                yaml_lines.append(f"      {report_type}:")
                                for key, value in report_path.items():
                                    yaml_lines.append(f"        {key}: {value}")
                            else:
                                yaml_lines.append(f"      {report_type}: {report_path}")
                    if 'paths' in job_config['artifacts']:
                        yaml_lines.append("    paths:")
                        for path in job_config['artifacts']['paths']:
                            yaml_lines.append(f"      - {path}")
                    if 'expire_in' in job_config['artifacts']:
                        yaml_lines.append(f"    expire_in: {job_config['artifacts']['expire_in']}")

                # Allow failure
                if job_config.get('allow_failure', False):
                    yaml_lines.append("  allow_failure: true")

                yaml_lines.append("")

        # Add metrics collection job
        yaml_lines.extend([
            "# Metrics collection for research",
            "collect:metrics:",
            "  stage: deploy",
            "  script:",
            "    - echo 'Collecting pipeline metrics for research'",
            "    - |",
            "      cat > metrics.json << EOF",
            "      {",
            '        "pipeline_id": "$CI_PIPELINE_ID",',
            f'        "tech_stack": "{self.backend}",',
            '        "timestamp": "$(date -Iseconds)",',
            f'        "coverage_threshold": {self.min_coverage},',
            '        "pipeline_status": "$CI_PIPELINE_STATUS"',
            "      }",
            "      EOF",
            "  artifacts:",
            "    paths:",
            "      - metrics.json",
            "    expire_in: 90 days",
            "  when: always",
            ""
        ])

        return '\n'.join(yaml_lines)

    def generate_minimal_pipeline_yaml(self) -> str:
        """
        Generate minimal 2-stage pipeline for fast agent workflow.
        Only includes test and build stages - perfect for baseline verification.
        """
        yaml_lines = []

        # Header
        yaml_lines.extend([
            f"# Minimal 2-Stage Pipeline for {self.backend}",
            "# Optimized for agent workflow - test + build only",
            "# Auto-generated by PipelineConfig",
            "",
            f"image: {self.config.get('docker_image', 'alpine:latest')}",
            ""
        ])

        # Minimal stages
        yaml_lines.extend([
            "stages:",
            "  - test",
            "  - build",
            ""
        ])

        # Variables (only essential ones)
        if 'variables' in self.config:
            yaml_lines.append("variables:")
            for key, value in self.config['variables'].items():
                yaml_lines.append(f'  {key}: "{value}"')
            yaml_lines.append("")

        # Cache (essential for speed)
        if 'cache' in self.config:
            yaml_lines.extend([
                "cache:",
                f"  key: {self.config['cache']['key']}",
                "  paths:",
                *[f"    - {path}" for path in self.config['cache']['paths']],
                ""
            ])

        # Default settings
        yaml_lines.extend([
            "default:",
            "  interruptible: true",
            "  retry:",
            "    max: 2",
            "    when:",
            "      - runner_system_failure",
            "      - stuck_or_timeout_failure",
            ""
        ])

        # Get only test and build jobs
        jobs = self.config.get('jobs', {})

        # Test job (essential)
        test_job_key = None
        for key in ['test:unit', 'test', 'test:run']:
            if key in jobs:
                test_job_key = key
                break

        if test_job_key:
            job_config = jobs[test_job_key]
            yaml_lines.extend([
                "test_job:",
                "  stage: test",
                "  script:"
            ])
            for cmd in job_config.get('script', []):
                yaml_lines.append(f"    - {cmd}")

            # Add artifacts if defined
            if 'artifacts' in job_config:
                yaml_lines.append("  artifacts:")
                if 'reports' in job_config['artifacts']:
                    yaml_lines.append("    reports:")
                    for report_type, report_path in job_config['artifacts']['reports'].items():
                        yaml_lines.append(f"      {report_type}: {report_path}")
                if 'paths' in job_config['artifacts']:
                    yaml_lines.append("    paths:")
                    for path in job_config['artifacts']['paths']:
                        yaml_lines.append(f"      - {path}")
                if 'expire_in' in job_config['artifacts']:
                    yaml_lines.append(f"    expire_in: {job_config['artifacts']['expire_in']}")

            yaml_lines.extend(["  allow_failure: false", ""])

        # Build job (essential)
        build_job_key = None
        for key in ['build:compile', 'build', 'build:package']:
            if key in jobs:
                build_job_key = key
                break

        if build_job_key:
            job_config = jobs[build_job_key]
            yaml_lines.extend([
                "build_job:",
                "  stage: build",
                "  needs: [\"test_job\"]" if test_job_key else "  stage: build",
                "  script:"
            ])
            for cmd in job_config.get('script', []):
                yaml_lines.append(f"    - {cmd}")

            # Add artifacts if defined
            if 'artifacts' in job_config:
                yaml_lines.append("  artifacts:")
                if 'paths' in job_config['artifacts']:
                    yaml_lines.append("    paths:")
                    for path in job_config['artifacts']['paths']:
                        yaml_lines.append(f"      - {path}")
                if 'expire_in' in job_config['artifacts']:
                    yaml_lines.append(f"    expire_in: {job_config['artifacts']['expire_in']}")

            yaml_lines.extend(["  allow_failure: false", ""])

        return '\n'.join(yaml_lines)


# Example usage and testing
if __name__ == "__main__":
    # Test different tech stacks
    tech_stacks = [
        {'backend': 'python', 'min_coverage': 80},
        {'backend': 'java', 'min_coverage': 75},
        {'backend': 'javascript', 'min_coverage': 70},
        {'backend': 'go', 'min_coverage': 65},
        {'backend': 'rust', 'min_coverage': 60},
        {'backend': 'unknown'},
    ]

    for tech in tech_stacks:
        config = PipelineConfig(tech)
        print(f"\n{'='*60}")
        print(f"Tech Stack: {tech}")
        print(f"Stages: {config.config['stages']}")
        print(f"Jobs: {list(config.config.get('jobs', {}).keys())}")
        print('='*60)