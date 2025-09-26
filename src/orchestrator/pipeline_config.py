"""
Centralized pipeline configuration management.
Eliminates hardcoded CI/CD references and provides dynamic configuration.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import json


class PipelineConfig:
    """Centralized configuration for CI/CD pipelines."""
    
    def __init__(self, tech_stack: Optional[Dict[str, str]] = None):
        """
        Initialize pipeline configuration based on tech stack.
        
        Args:
            tech_stack: Dict with 'backend' and 'frontend' keys
        """
        self.tech_stack = tech_stack or {}
        self.backend = self.tech_stack.get('backend', 'python')
        self.frontend = self.tech_stack.get('frontend', 'none')
        
        # Load configuration based on tech stack
        self.config = self._load_stack_config()
    
    def _load_stack_config(self) -> Dict[str, Any]:
        """Load configuration based on detected tech stack."""
        config = {
            'pipeline_file': '.gitlab-ci.yml',
            'stages': ['test', 'build'],
            'cache_paths': [],
            'artifacts': {},
            'variables': {},
            'before_script': [],
            'test_commands': [],
            'build_commands': [],
            'docker_image': None,
            'test_framework': None,
            'package_manager': None,
            'requirements_file': None,
            'test_directory': 'tests',
            'source_directory': 'src',
            'coverage_tool': None,
            'min_coverage': 70
        }
        
        # Python configuration
        if self.backend == 'python':
            config.update({
                'docker_image': 'python:3.11-slim',
                'test_framework': 'pytest',
                'package_manager': 'pip',
                'requirements_file': 'requirements.txt',
                'coverage_tool': 'pytest-cov',
                'cache_paths': ['.cache/pip/', 'venv/'],
                'variables': {
                    'PIP_CACHE_DIR': "$CI_PROJECT_DIR/.cache/pip"
                },
                'before_script': [
                    'python --version',
                    'python -m pip install --upgrade pip',
                    'pip install virtualenv',
                    'virtualenv venv',
                    'source venv/bin/activate'
                ],
                'test_commands': [
                    'pip install pytest pytest-cov',
                    'if [ -f requirements.txt ]; then pip install -r requirements.txt; fi',
                    'python -m pytest tests/ -v --cov=src --cov-report=term-missing'
                ],
                'build_commands': [
                    'python -m py_compile src/**/*.py || true',
                    'python -m compileall src/ -q || true'
                ]
            })
        
        # JavaScript/Node configuration
        elif self.backend in ['javascript', 'nodejs', 'node']:
            config.update({
                'docker_image': 'node:18-alpine',
                'test_framework': 'jest',
                'package_manager': 'npm',
                'requirements_file': 'package.json',
                'coverage_tool': 'jest',
                'cache_paths': ['node_modules/', '.npm/'],
                'variables': {
                    'NPM_CONFIG_CACHE': "$CI_PROJECT_DIR/.npm"
                },
                'before_script': [
                    'node --version',
                    'npm --version',
                    'npm ci || npm install'
                ],
                'test_commands': [
                    'npm test -- --coverage --watchAll=false'
                ],
                'build_commands': [
                    'npm run build || echo "No build script defined"'
                ]
            })
        
        # Java configuration
        elif self.backend == 'java':
            config.update({
                'docker_image': 'maven:3.8-openjdk-17',
                'test_framework': 'junit',
                'package_manager': 'maven',
                'requirements_file': 'pom.xml',
                'coverage_tool': 'jacoco',
                'cache_paths': ['.m2/'],
                'variables': {
                    'MAVEN_OPTS': "-Dmaven.repo.local=$CI_PROJECT_DIR/.m2 -Djava.net.preferIPv4Stack=true"
                },
                'before_script': [
                    'java -version',
                    'mvn --version'
                ],
                'test_commands': [
                    'mvn clean test jacoco:report -Dmaven.wagon.http.retryHandler.count=5 -Dmaven.wagon.httpconnectionManager.ttlSeconds=120 -Dmaven.wagon.http.ssl.insecure=true -Dmaven.wagon.http.ssl.allowall=true',
                    'echo "=== TEST SUMMARY ===" && find target -name "*.xml" -o -name "*.html" | head -10',
                    'if [ -f target/site/jacoco/index.html ]; then echo "✅ Coverage report generated"; else echo "❌ Coverage report missing" && exit 1; fi',
                    'if [ -d target/surefire-reports ]; then echo "✅ Test reports generated"; else echo "❌ Test reports missing" && exit 1; fi'
                ],
                'build_commands': [
                    'mvn clean compile -Dmaven.wagon.http.retryHandler.count=5 -Dmaven.wagon.httpconnectionManager.ttlSeconds=120 -Dmaven.wagon.http.ssl.insecure=true -Dmaven.wagon.http.ssl.allowall=true',
                    'echo "=== BUILD SUMMARY ===" && find target -name "*.class" | wc -l && echo "classes compiled"'
                ]
            })
        
        # Go configuration
        elif self.backend == 'go':
            config.update({
                'docker_image': 'golang:1.20-alpine',
                'test_framework': 'go test',
                'package_manager': 'go mod',
                'requirements_file': 'go.mod',
                'coverage_tool': 'go test',
                'cache_paths': ['vendor/', '.go/'],
                'variables': {
                    'GOPATH': "$CI_PROJECT_DIR/.go"
                },
                'before_script': [
                    'go version',
                    'go mod download || true'
                ],
                'test_commands': [
                    'go test -v -cover ./...'
                ],
                'build_commands': [
                    'go build -v ./...'
                ]
            })
        
        # Rust configuration
        elif self.backend == 'rust':
            config.update({
                'docker_image': 'rust:latest',
                'test_framework': 'cargo test',
                'package_manager': 'cargo',
                'requirements_file': 'Cargo.toml',
                'coverage_tool': 'tarpaulin',
                'cache_paths': ['target/', '.cargo/'],
                'variables': {
                    'CARGO_HOME': "$CI_PROJECT_DIR/.cargo"
                },
                'before_script': [
                    'rustc --version',
                    'cargo --version'
                ],
                'test_commands': [
                    'cargo test --verbose'
                ],
                'build_commands': [
                    'cargo build --release'
                ]
            })
        
        return config
    
    def generate_pipeline_yaml(self) -> str:
        """
        Generate CI/CD pipeline YAML based on configuration.

        Returns:
            YAML string for pipeline configuration
        """
        yaml_lines = [
            f"# Auto-generated CI/CD Pipeline for {self.backend}",
            f"# Generated by PipelineConfig",
            f"# Supports both Docker and Shell executors",
            ""
        ]

        # Docker image commented out for shell executor compatibility
        yaml_lines.extend([
            "# Uncomment for Docker executor:",
            f"# image: {self.config['docker_image']}",
            ""
        ])
        
        # Stages
        yaml_lines.extend([
            "stages:",
            *[f"  - {stage}" for stage in self.config['stages']],
            ""
        ])
        
        # Variables
        if self.config['variables']:
            yaml_lines.append("variables:")
            for key, value in self.config['variables'].items():
                yaml_lines.append(f"  {key}: \"{value}\"")
            yaml_lines.append("")
        
        # Cache
        if self.config['cache_paths']:
            yaml_lines.extend([
                "cache:",
                "  paths:",
                *[f"    - {path}" for path in self.config['cache_paths']],
                ""
            ])
        
        # Before script with DNS fix for shell executors
        yaml_lines.append("before_script:")
        # Add DNS fix for shell executors
        if self.backend == 'java':
            yaml_lines.extend([
                "  - echo 'Configuring Maven settings for dependency resolution...'",
                "  - mkdir -p ~/.m2",
                "  - echo '<settings xmlns=\"http://maven.apache.org/SETTINGS/1.0.0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://maven.apache.org/SETTINGS/1.0.0 https://maven.apache.org/xsd/settings-1.0.0.xsd\">' > ~/.m2/settings.xml",
                "  - echo '  <mirrors>' >> ~/.m2/settings.xml",
                "  - echo '    <mirror><id>maven-central</id><url>https://repo1.maven.org/maven2</url><mirrorOf>central</mirrorOf></mirror>' >> ~/.m2/settings.xml",
                "  - echo '  </mirrors>' >> ~/.m2/settings.xml",
                "  - echo '  <profiles>' >> ~/.m2/settings.xml",
                "  - echo '    <profile>' >> ~/.m2/settings.xml",
                "  - echo '      <id>default</id>' >> ~/.m2/settings.xml",
                "  - echo '      <activation><activeByDefault>true</activeByDefault></activation>' >> ~/.m2/settings.xml",
                "  - echo '      <properties>' >> ~/.m2/settings.xml",
                "  - echo '        <maven.wagon.http.retryHandler.count>5</maven.wagon.http.retryHandler.count>' >> ~/.m2/settings.xml",
                "  - echo '        <maven.wagon.httpconnectionManager.ttlSeconds>120</maven.wagon.httpconnectionManager.ttlSeconds>' >> ~/.m2/settings.xml",
                "  - echo '        <maven.wagon.http.ssl.insecure>true</maven.wagon.http.ssl.insecure>' >> ~/.m2/settings.xml",
                "  - echo '        <maven.wagon.http.ssl.allowall>true</maven.wagon.http.ssl.allowall>' >> ~/.m2/settings.xml",
                "  - echo '      </properties>' >> ~/.m2/settings.xml",
                "  - echo '    </profile>' >> ~/.m2/settings.xml",
                "  - echo '  </profiles>' >> ~/.m2/settings.xml",
                "  - echo '</settings>' >> ~/.m2/settings.xml",
                "  - echo 'Maven settings configured for dependency resolution'",
                "  - mvn help:effective-settings -q | head -20 || echo 'Settings validation failed'"
            ])

        # Add original before_script commands
        if self.config['before_script']:
            for cmd in self.config['before_script']:
                yaml_lines.append(f"  - {cmd}")
        yaml_lines.append("")
        
        # Test job
        yaml_lines.extend([
            "test_job:",
            "  stage: test",
            "  script:"
        ])
        for cmd in self.config['test_commands']:
            yaml_lines.append(f"    - {cmd}")
        # Coverage configuration based on tech stack
        if self.backend == 'java':
            yaml_lines.extend([
                "  coverage: '/Total.*?([0-9]{1,3})%/'",
                "  artifacts:",
                "    reports:",
                "      junit:",
                "        - target/surefire-reports/TEST-*.xml",
                "      coverage_report:",
                "        coverage_format: cobertura",
                "        path: target/site/jacoco/jacoco.xml",
                "    paths:",
                "      - target/site/jacoco/",
                "    when: always",
                "    expire_in: 1 week",
                ""
            ])
        else:
            yaml_lines.extend([
                "  coverage: '/TOTAL.*\\s+(\\d+%)$/'",
                "  artifacts:",
                "    reports:",
                "      coverage_report:",
                "        coverage_format: cobertura",
                "        path: coverage.xml",
                "    when: always",
                "    expire_in: 1 week",
                ""
            ])
        
        # Build job
        yaml_lines.extend([
            "build_job:",
            "  stage: build",
            "  script:"
        ])
        for cmd in self.config['build_commands']:
            yaml_lines.append(f"    - {cmd}")
        yaml_lines.extend([
            "  artifacts:",
            "    paths:",
            f"      - {self.config['source_directory']}/",
            "    expire_in: 1 week"
        ])
        
        return '\n'.join(yaml_lines)
    
    def get_test_command(self) -> str:
        """Get the appropriate test command for the tech stack."""
        if self.config['test_framework'] == 'pytest':
            return f"python -m pytest {self.config['test_directory']}/ -v"
        elif self.config['test_framework'] == 'jest':
            return "npm test"
        elif self.config['test_framework'] == 'junit':
            return "mvn test"
        elif self.config['test_framework'] == 'go test':
            return "go test ./..."
        elif self.config['test_framework'] == 'cargo test':
            return "cargo test"
        else:
            return "echo 'No test framework configured'"
    
    def get_coverage_command(self) -> str:
        """Get the appropriate coverage command for the tech stack."""
        if self.config['coverage_tool'] == 'pytest-cov':
            return f"python -m pytest {self.config['test_directory']}/ --cov={self.config['source_directory']} --cov-report=term-missing --cov-report=xml"
        elif self.config['coverage_tool'] == 'jest':
            return "npm test -- --coverage"
        elif self.config['coverage_tool'] == 'jacoco':
            return "mvn clean test jacoco:report"
        elif self.config['coverage_tool'] == 'go test':
            return "go test -cover ./..."
        elif self.config['coverage_tool'] == 'tarpaulin':
            return "cargo tarpaulin --out Xml"
        else:
            return "echo 'No coverage tool configured'"
    
    def get_dependencies_file(self) -> str:
        """Get the appropriate dependencies file name."""
        return self.config['requirements_file'] or 'requirements.txt'
    
    def detect_tech_stack(self, project_path: Path) -> Dict[str, str]:
        """
        Auto-detect tech stack from project files.
        
        Args:
            project_path: Path to project root
            
        Returns:
            Dict with detected backend and frontend
        """
        detected = {'backend': 'unknown', 'frontend': 'none'}
        
        # Backend detection
        if (project_path / 'requirements.txt').exists() or \
           (project_path / 'setup.py').exists() or \
           (project_path / 'pyproject.toml').exists():
            detected['backend'] = 'python'
        elif (project_path / 'package.json').exists():
            detected['backend'] = 'nodejs'
        elif (project_path / 'pom.xml').exists():
            detected['backend'] = 'java'
        elif (project_path / 'go.mod').exists():
            detected['backend'] = 'go'
        elif (project_path / 'Cargo.toml').exists():
            detected['backend'] = 'rust'
        elif (project_path / 'composer.json').exists():
            detected['backend'] = 'php'
        elif (project_path / 'Gemfile').exists():
            detected['backend'] = 'ruby'
        
        # Frontend detection
        if (project_path / 'index.html').exists():
            detected['frontend'] = 'html-css-js'
        elif (project_path / 'package.json').exists():
            # Check for frontend frameworks
            try:
                with open(project_path / 'package.json', 'r') as f:
                    package_json = json.load(f)
                    deps = {**package_json.get('dependencies', {}), 
                           **package_json.get('devDependencies', {})}
                    
                    if 'react' in deps:
                        detected['frontend'] = 'react'
                    elif 'vue' in deps:
                        detected['frontend'] = 'vue'
                    elif 'angular' in deps or '@angular/core' in deps:
                        detected['frontend'] = 'angular'
            except:
                pass
        
        return detected
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return {
            'tech_stack': self.tech_stack,
            'config': self.config
        }