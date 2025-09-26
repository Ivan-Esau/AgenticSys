"""
Dynamic prompt templates that adapt to tech stack and pipeline configuration.
Replaces hardcoded pipeline references with configurable templates.
"""

from typing import Dict, Any, Optional


class PromptTemplates:
    """Generate dynamic prompts based on pipeline configuration."""
    
    @staticmethod
    def get_pipeline_template(pipeline_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate pipeline template based on configuration.
        
        Args:
            pipeline_config: Configuration from PipelineConfig.to_dict()
            
        Returns:
            Dynamic pipeline template string
        """
        if not pipeline_config:
            # Fallback to generic template
            return PromptTemplates._get_generic_pipeline_template()
        
        config = pipeline_config.get('config', {})
        tech_stack = pipeline_config.get('tech_stack', {})
        backend = tech_stack.get('backend', 'python')
        
        template = []
        template.append(f"PIPELINE INFORMATION FOR {backend.upper()} PROJECT:")
        template.append("(Basic pipeline already exists - DO NOT CREATE OR MODIFY)")
        template.append("")
        template.append("Expected pipeline structure:")
        template.append(f"# CI/CD Pipeline for {backend} project")
        
        # Docker image
        if config.get('docker_image'):
            template.append(f"image: {config['docker_image']}")
            template.append("")
        
        # Stages
        template.append("stages:")
        for stage in config.get('stages', ['test', 'build']):
            template.append(f"  - {stage}")
        template.append("")
        
        # Variables
        if config.get('variables'):
            template.append("variables:")
            for key, value in config['variables'].items():
                template.append(f'  {key}: "{value}"')
            template.append("")
        
        # Cache
        if config.get('cache_paths'):
            template.append("cache:")
            template.append("  paths:")
            for path in config['cache_paths']:
                template.append(f"    - {path}")
            template.append("")
        
        # Before script
        if config.get('before_script'):
            template.append("before_script:")
            for cmd in config['before_script']:
                template.append(f"  - {cmd}")
            template.append("")
        
        # Test job
        template.append("test_job:")
        template.append("  stage: test")
        template.append("  script:")
        for cmd in config.get('test_commands', ['echo "No tests configured"']):
            template.append(f"    - {cmd}")
        template.append("  allow_failure: false  # Tests should pass")
        template.append("")
        
        # Build job
        template.append("build_job:")
        template.append("  stage: build")
        template.append("  script:")
        for cmd in config.get('build_commands', ['echo "No build configured"']):
            template.append(f"    - {cmd}")
        template.append("```")
        
        return '\n'.join(template)
    
    @staticmethod
    def _get_generic_pipeline_template() -> str:
        """Fallback generic pipeline template."""
        return """PIPELINE INFORMATION:
Basic pipeline already exists - DO NOT CREATE OR MODIFY .gitlab-ci.yml

Expected pipeline features:
1. Detects the project's tech stack automatically
2. Uses appropriate Docker image
3. Installs necessary dependencies
4. Runs tests if they exist
5. Builds the project if applicable

For reference only:
- Programming language detection (requirements.txt, package.json, etc.)
- Test framework integration (pytest, jest, junit, etc.)
- Build tools configuration"""
    
    @staticmethod
    def get_testing_instructions(pipeline_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate testing instructions based on configuration.
        
        Args:
            pipeline_config: Configuration from PipelineConfig.to_dict()
            
        Returns:
            Dynamic testing instructions
        """
        if not pipeline_config:
            return PromptTemplates._get_generic_testing_instructions()
        
        config = pipeline_config.get('config', {})
        tech_stack = pipeline_config.get('tech_stack', {})
        backend = tech_stack.get('backend', 'python')
        
        instructions = []
        instructions.append(f"TESTING INSTRUCTIONS FOR {backend.upper()}:")
        instructions.append("")
        
        # Test framework
        test_framework = config.get('test_framework', 'unknown')
        instructions.append(f"1. USE {test_framework.upper()} FRAMEWORK:")
        
        if test_framework == 'pytest':
            instructions.append("   - Write tests in tests/ directory")
            instructions.append("   - Use pytest fixtures for setup/teardown")
            instructions.append("   - Follow test_*.py naming convention")
            instructions.append("   - Run with: python -m pytest tests/")
        elif test_framework == 'jest':
            instructions.append("   - Write tests in __tests__/ or *.test.js files")
            instructions.append("   - Use describe/it blocks for organization")
            instructions.append("   - Mock modules with jest.mock()")
            instructions.append("   - Run with: npm test")
        elif test_framework == 'junit':
            instructions.append("   - Write tests in src/test/java/")
            instructions.append("   - Use @Test annotations")
            instructions.append("   - Follow *Test.java naming convention")
            instructions.append("   - Run with: mvn test")
            instructions.append("   - CRITICAL: Add JaCoCo plugin to pom.xml for coverage")
            instructions.append("   - Ensure pom.xml has jacoco-maven-plugin configured")
        elif test_framework == 'go test':
            instructions.append("   - Write tests in *_test.go files")
            instructions.append("   - Use testing.T for test functions")
            instructions.append("   - Follow Test* naming convention")
            instructions.append("   - Run with: go test ./...")
        
        instructions.append("")
        
        # Dependencies file
        deps_file = config.get('requirements_file', 'requirements.txt')
        instructions.append(f"2. MANAGE DEPENDENCIES IN {deps_file}:")
        instructions.append(f"   - Add test dependencies to {deps_file}")
        instructions.append(f"   - Keep dependencies minimal and specific")
        instructions.append("")
        
        # Coverage
        coverage_tool = config.get('coverage_tool', 'default')
        instructions.append(f"3. ENSURE MINIMUM {config.get('min_coverage', 70)}% COVERAGE:")
        instructions.append(f"   - Use coverage tool: {coverage_tool}")
        if coverage_tool == 'jacoco':
            instructions.append("   - MANDATORY: Update pom.xml with JaCoCo plugin configuration")
            instructions.append("   - Plugin must include prepare-agent and report executions")
            instructions.append("   - Generates target/site/jacoco/jacoco.xml for GitLab")
        instructions.append(f"   - Test all core functionalities")
        instructions.append(f"   - Include edge cases and error handling")
        instructions.append("")
        
        # Test directory structure
        instructions.append(f"4. USE PROPER DIRECTORY STRUCTURE:")
        instructions.append(f"   - Tests in: {config.get('test_directory', 'tests')}/")
        instructions.append(f"   - Source in: {config.get('source_directory', 'src')}/")
        instructions.append("")
        
        # Commands
        instructions.append("5. KEY COMMANDS:")
        instructions.append(f"   - Install deps: {PromptTemplates._get_install_command(backend, config)}")
        instructions.append(f"   - Run tests: {PromptTemplates._get_test_command(backend, config)}")
        instructions.append(f"   - Coverage: {PromptTemplates._get_coverage_command(backend, config)}")
        
        return '\n'.join(instructions)
    
    @staticmethod
    def _get_generic_testing_instructions() -> str:
        """Fallback generic testing instructions."""
        return """GENERIC TESTING INSTRUCTIONS:
1. Detect the project's test framework
2. Write comprehensive tests for all functionality
3. Ensure tests are runnable in CI/CD
4. Maintain good test coverage
5. Use appropriate mocking and fixtures"""
    
    @staticmethod
    def _get_install_command(backend: str, config: Dict) -> str:
        """Get dependency installation command."""
        if backend == 'python':
            return f"pip install -r {config.get('requirements_file', 'requirements.txt')}"
        elif backend == 'nodejs':
            return "npm install"
        elif backend == 'java':
            return "mvn install"
        elif backend == 'go':
            return "go mod download"
        elif backend == 'rust':
            return "cargo build"
        else:
            return "install dependencies"
    
    @staticmethod
    def _get_test_command(backend: str, config: Dict) -> str:
        """Get test execution command."""
        if backend == 'python':
            return f"python -m pytest {config.get('test_directory', 'tests')}/"
        elif backend == 'nodejs':
            return "npm test"
        elif backend == 'java':
            return "mvn test"
        elif backend == 'go':
            return "go test ./..."
        elif backend == 'rust':
            return "cargo test"
        else:
            return "run tests"
    
    @staticmethod
    def _get_coverage_command(backend: str, config: Dict) -> str:
        """Get coverage command."""
        if backend == 'python':
            return f"pytest --cov={config.get('source_directory', 'src')} --cov-report=term"
        elif backend == 'nodejs':
            return "npm test -- --coverage"
        elif backend == 'java':
            return "mvn test jacoco:report"
        elif backend == 'go':
            return "go test -cover ./..."
        elif backend == 'rust':
            return "cargo tarpaulin"
        else:
            return "run coverage"
    
    @staticmethod
    def get_coding_instructions(pipeline_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate coding instructions based on tech stack.
        
        Args:
            pipeline_config: Configuration from PipelineConfig.to_dict()
            
        Returns:
            Dynamic coding instructions
        """
        if not pipeline_config:
            return "Follow project conventions and best practices"
        
        tech_stack = pipeline_config.get('tech_stack', {})
        backend = tech_stack.get('backend', 'python')
        config = pipeline_config.get('config', {})
        
        instructions = []
        instructions.append(f"CODING STANDARDS FOR {backend.upper()}:")
        instructions.append("")
        
        if backend == 'python':
            instructions.append("- Follow PEP 8 style guide")
            instructions.append("- Use type hints for function signatures")
            instructions.append("- Place code in src/ directory")
            instructions.append("- Create __init__.py files for packages")
        elif backend == 'nodejs':
            instructions.append("- Follow JavaScript Standard Style or ESLint rules")
            instructions.append("- Use ES6+ features (const/let, arrow functions)")
            instructions.append("- Export modules properly")
            instructions.append("- Handle async operations with async/await")
        elif backend == 'java':
            instructions.append("- Follow Java naming conventions")
            instructions.append("- Use proper package structure")
            instructions.append("- Implement interfaces where appropriate")
            instructions.append("- Add JavaDoc comments")
        elif backend == 'go':
            instructions.append("- Follow Go conventions (gofmt)")
            instructions.append("- Use proper error handling")
            instructions.append("- Keep functions small and focused")
            instructions.append("- Add godoc comments")
        
        instructions.append("")
        instructions.append(f"Dependencies: Add to {config.get('requirements_file', 'requirements.txt')}")
        instructions.append(f"Source directory: {config.get('source_directory', 'src')}/")
        instructions.append(f"Test directory: {config.get('test_directory', 'tests')}/")
        
        return '\n'.join(instructions)