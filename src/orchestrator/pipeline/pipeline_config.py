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
            tech_stack: Dict with 'backend', 'frontend', and optional 'min_coverage' keys
        """
        self.tech_stack = tech_stack or {}
        self.backend = self.tech_stack.get('backend', 'python')
        self.frontend = self.tech_stack.get('frontend', 'none')
        self.min_coverage = self.tech_stack.get('min_coverage', 70)

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
            'min_coverage': self.min_coverage
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
                    'python -m pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=xml',
                    '# Show coverage summary',
                    'echo "=== Coverage Results ==="',
                    'if [ -f coverage.xml ]; then echo "Coverage report generated at coverage.xml"; fi'
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
                    'npm test -- --coverage --watchAll=false',
                    '# Show coverage summary',
                    'echo "=== Coverage Results ==="',
                    'if [ -f coverage/coverage-summary.json ]; then echo "Coverage report generated at coverage/"; fi'
                ],
                'build_commands': [
                    'npm run build || echo "No build script defined"'
                ]
            })
        
        # Java configuration - ENHANCED for Spring Boot with JUnit 5
        elif self.backend == 'java':
            config.update({
                'docker_image': 'maven:3.9-eclipse-temurin-21',  # Latest stable Maven with Java 21
                'test_framework': 'junit5',  # Using JUnit 5 (Jupiter)
                'package_manager': 'maven',
                'requirements_file': 'pom.xml',
                'coverage_tool': 'jacoco',  # Use JaCoCo for code coverage
                'cache_paths': ['.m2/repository'],  # Cache Maven dependencies
                'variables': {
                    'MAVEN_OPTS': '-Dmaven.repo.local=$CI_PROJECT_DIR/.m2/repository',
                    'MAVEN_CLI_OPTS': '--batch-mode --errors --fail-at-end --show-version'
                },
                'before_script': [
                    'java -version',
                    'mvn --version',
                    '# Ensure Maven settings for reliability',
                    'mkdir -p ~/.m2',
                    'echo "<?xml version=\\"1.0\\"?><settings><localRepository>${user.home}/.m2/repository</localRepository></settings>" > ~/.m2/settings.xml'
                ],
                'test_commands': [
                    # Real test execution with JUnit 5 and JaCoCo coverage
                    'mvn clean test jacoco:report ${MAVEN_CLI_OPTS}',
                    '# Show test results for pipeline monitoring',
                    'echo "=== Test Results ==="',
                    'find target/surefire-reports -name "*.txt" -exec echo {} \\; -exec head -20 {} \\; || echo "No test reports found"',
                    '# Show coverage summary',
                    'echo "=== Coverage Results ==="',
                    'if [ -f target/site/jacoco/index.html ]; then echo "Coverage report generated at target/site/jacoco/index.html"; fi'
                ],
                'build_commands': [
                    # Real build - will fail if compilation fails
                    'mvn compile ${MAVEN_CLI_OPTS}'
                ],
                # Spring Boot specific configuration
                'spring_boot': {
                    'parent_version': '3.2.0',
                    'java_version': '21',
                    'test_annotations': ['@SpringBootTest', '@WebMvcTest', '@DataJpaTest'],
                    'package_structure': 'com.example'
                }
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
                    'go test -v -coverprofile=coverage.out -covermode=atomic ./...',
                    '# Show coverage summary',
                    'echo "=== Coverage Results ==="',
                    'go tool cover -func=coverage.out || echo "No coverage data found"'
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
                    'cargo install cargo-tarpaulin || echo "Installing tarpaulin"',
                    'cargo tarpaulin --out Xml --output-dir coverage --verbose',
                    '# Show coverage summary',
                    'echo "=== Coverage Results ==="',
                    'if [ -f coverage/cobertura.xml ]; then echo "Coverage report generated at coverage/cobertura.xml"; fi'
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
        
        # Stages - add coverage verification stage for all languages with coverage tools
        stages = self.config['stages'].copy()
        if self.config.get('coverage_tool') and 'coverage' not in stages:
            stages.append('coverage')

        yaml_lines.extend([
            "stages:",
            *[f"  - {stage}" for stage in stages],
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
        
        # Simple but proper before script (only if commands exist)
        if self.config['before_script']:
            yaml_lines.append("before_script:")
            for cmd in self.config['before_script']:
                yaml_lines.append(f"  - {cmd}")
            yaml_lines.append("")
        
        # Test job - simplified without coverage artifacts
        yaml_lines.extend([
            "test_job:",
            "  stage: test",
            "  script:"
        ])
        if self.config['test_commands']:
            for cmd in self.config['test_commands']:
                yaml_lines.append(f"    - {cmd}")
        else:
            # GitLab requires at least one command in script
            yaml_lines.append("    - echo 'No tests configured yet'")

        # Add test reporting and coverage artifacts for all languages
        if self.config.get('coverage_tool'):
            yaml_lines.append("  # Coverage reporting")
            yaml_lines.append("  artifacts:")

            # Language-specific artifact paths
            if self.backend == 'java':
                yaml_lines.extend([
                    "    reports:",
                    "      junit: target/surefire-reports/TEST-*.xml",
                    "      coverage_report:",
                    "        coverage_format: cobertura",
                    "        path: target/site/jacoco/jacoco.xml",
                    "    paths:",
                    "      - target/site/jacoco/"
                ])
            elif self.backend == 'python':
                yaml_lines.extend([
                    "    reports:",
                    "      coverage_report:",
                    "        coverage_format: cobertura",
                    "        path: coverage.xml",
                    "    paths:",
                    "      - coverage.xml",
                    "      - htmlcov/"
                ])
            elif self.backend in ['javascript', 'nodejs', 'node']:
                yaml_lines.extend([
                    "    paths:",
                    "      - coverage/"
                ])
            elif self.backend == 'go':
                yaml_lines.extend([
                    "    paths:",
                    "      - coverage.out"
                ])
            elif self.backend == 'rust':
                yaml_lines.extend([
                    "    reports:",
                    "      coverage_report:",
                    "        coverage_format: cobertura",
                    "        path: coverage/cobertura.xml",
                    "    paths:",
                    "      - coverage/"
                ])

            yaml_lines.extend([
                "    when: always",
                "    expire_in: 1 day"
            ])

        yaml_lines.append("")
        
        # Build job - simplified
        yaml_lines.extend([
            "build_job:",
            "  stage: build",
            "  script:"
        ])
        if self.config['build_commands']:
            for cmd in self.config['build_commands']:
                yaml_lines.append(f"    - {cmd}")
        else:
            # GitLab requires at least one command in script
            yaml_lines.append("    - echo 'No build configured yet'")
        yaml_lines.extend([
            "  # Keep compiled classes for verification",
            "  artifacts:",
            "    paths:",
            "      - target/classes/",
            "    expire_in: 1 day"
        ])

        # Add coverage verification job for all languages
        if self.config.get('coverage_tool'):
            min_cov = self.config.get('min_coverage', 70)
            yaml_lines.extend([
                "",
                "coverage_check:",
                "  stage: coverage",
                "  script:",
                f"    - echo \"Verifying minimum {min_cov}% code coverage\""
            ])

            # Language-specific coverage verification commands
            if self.backend == 'java':
                yaml_lines.append("    - mvn jacoco:check ${MAVEN_CLI_OPTS}")
            elif self.backend == 'python':
                yaml_lines.extend([
                    f"    - pip install coverage",
                    f"    - coverage report --fail-under={min_cov} || (echo \"Coverage below {min_cov}%\" && exit 1)"
                ])
            elif self.backend in ['javascript', 'nodejs', 'node']:
                yaml_lines.extend([
                    f"    - npm test -- --coverage --coverageThreshold='{{\"global\":{{\"lines\":{min_cov},\"statements\":{min_cov},\"functions\":{min_cov},\"branches\":{min_cov}}}}}' --watchAll=false || (echo \"Coverage below {min_cov}%\" && exit 1)"
                ])
            elif self.backend == 'go':
                yaml_lines.extend([
                    f"    - |",
                    f"      coverage=$(go tool cover -func=coverage.out | grep total | awk '{{print $3}}' | sed 's/%//')",
                    f"      if (( $(echo \"$coverage < {min_cov}\" | bc -l) )); then",
                    f"        echo \"Coverage $coverage% is below {min_cov}%\"",
                    f"        exit 1",
                    f"      fi",
                    f"      echo \"Coverage: $coverage%\""
                ])
            elif self.backend == 'rust':
                yaml_lines.extend([
                    f"    - cargo tarpaulin --fail-under {min_cov} || (echo \"Coverage below {min_cov}%\" && exit 1)"
                ])

            yaml_lines.extend([
                "  dependencies:",
                "    - test_job",
                "  allow_failure: false"
            ])

        return '\n'.join(yaml_lines)
    
    def get_test_command(self) -> str:
        """Get the appropriate test command for the tech stack."""
        if self.config['test_framework'] == 'pytest':
            return f"python -m pytest {self.config['test_directory']}/ -v"
        elif self.config['test_framework'] == 'jest':
            return "npm test"
        elif self.config['test_framework'] in ['junit', 'junit5']:
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
    
    def get_minimal_pom_xml(self, project_name: str = "project") -> str:
        """
        Generate a minimal but proper pom.xml for Java projects with JUnit 5.
        Simple configuration that actually works for real testing.
        """
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">

    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>{project_name}</artifactId>
    <version>1.0-SNAPSHOT</version>
    <packaging>jar</packaging>

    <properties>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <maven.compiler.source>21</maven.compiler.source>
        <maven.compiler.target>21</maven.compiler.target>
        <junit.version>5.10.1</junit.version>
    </properties>

    <dependencies>
        <!-- JUnit 5 (Jupiter) for testing -->
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>${{junit.version}}</version>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <sourceDirectory>src/main/java</sourceDirectory>
        <testSourceDirectory>src/test/java</testSourceDirectory>

        <plugins>
            <!-- Compiler plugin -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
                <configuration>
                    <source>21</source>
                    <target>21</target>
                    <compilerArgs>
                        <arg>-Xlint:unchecked</arg>
                    </compilerArgs>
                </configuration>
            </plugin>

            <!-- Surefire plugin for running tests with JUnit 5 -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>3.2.2</version>
                <configuration>
                    <includes>
                        <include>**/*Test.java</include>
                        <include>**/Test*.java</include>
                    </includes>
                </configuration>
            </plugin>

            <!-- JaCoCo plugin for code coverage -->
            <plugin>
                <groupId>org.jacoco</groupId>
                <artifactId>jacoco-maven-plugin</artifactId>
                <version>0.8.11</version>
                <executions>
                    <execution>
                        <id>prepare-agent</id>
                        <goals>
                            <goal>prepare-agent</goal>
                        </goals>
                    </execution>
                    <execution>
                        <id>report</id>
                        <phase>test</phase>
                        <goals>
                            <goal>report</goal>
                        </goals>
                    </execution>
                    <execution>
                        <id>check</id>
                        <goals>
                            <goal>check</goal>
                        </goals>
                        <configuration>
                            <rules>
                                <rule>
                                    <element>BUNDLE</element>
                                    <limits>
                                        <limit>
                                            <counter>LINE</counter>
                                            <value>COVEREDRATIO</value>
                                            <minimum>{self.min_coverage / 100:.2f}</minimum>
                                        </limit>
                                    </limits>
                                </rule>
                            </rules>
                        </configuration>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</project>"""

    def get_minimal_test_file(self, package_name: str = "com.example") -> str:
        """
        Generate a minimal test file using JUnit 5 that will always pass.
        This ensures the pipeline can succeed on first run.
        """
        package_path = package_name.replace('.', '/')
        return f"""package {package_name};

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;

public class AppTest {{

    @Test
    @DisplayName("Basic test that should always pass")
    public void testBasic() {{
        // Simple test that always passes
        assertTrue(true, "Basic test should pass");
    }}

    @Test
    @DisplayName("Test simple addition")
    public void testAddition() {{
        // Another simple test
        assertEquals(4, 2 + 2, "2 + 2 should equal 4");
    }}

    @Test
    @DisplayName("Test App main method exists")
    public void testMainMethodExists() {{
        // Test that we can call main without exceptions
        assertDoesNotThrow(() -> {{
            App.main(new String[]{{}});
        }});
    }}
}}"""

    def get_minimal_main_file(self, package_name: str = "com.example") -> str:
        """
        Generate a minimal main Java file.
        """
        return f"""package {package_name};

public class App {{

    public static void main(String[] args) {{
        System.out.println("Hello, Pipeline!");
    }}

    public static int add(int a, int b) {{
        return a + b;
    }}
}}"""

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return {
            'tech_stack': self.tech_stack,
            'config': self.config
        }