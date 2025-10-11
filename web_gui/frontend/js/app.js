/**
 * Main Application Controller
 * Coordinates WebSocket, API, and UI components
 */

class App {
    constructor() {
        this.ws = new WebSocketClient();
        this.api = new APIClient();
        this.ui = new UIManager();

        this.systemRunning = false;
        this.uptimeInterval = null;
        this.startTime = null;

        this.init();
    }

    async init() {
        console.log('Initializing AgenticSys Control Center...');

        // Load saved theme
        this.ui.loadTheme();

        // Setup WebSocket listeners
        this.setupWebSocketListeners();

        // Setup UI event listeners
        this.setupUIListeners();

        // Connect to WebSocket
        this.ws.connect();

        // Load initial data
        await this.loadInitialData();

        console.log('Initialization complete');
    }

    setupWebSocketListeners() {
        // Connection events
        this.ws.on('connected', (connected) => {
            this.ui.updateConnectionStatus(connected);
            if (connected) {
                // Request current status when connected
                this.ws.send('get_status');
            }
        });

        this.ws.on('error', (error) => {
            console.error('WebSocket error:', error);
            const errorMsg = error && error.message ? error.message : 'WebSocket connection error';
            this.ui.showError(`WebSocket error: ${errorMsg}`);
        });

        // System events
        this.ws.on('system_status', (data) => {
            this.handleSystemStatus(data);
        });

        // Agent events
        this.ws.on('agent_output', (data) => {
            // Filter out tool outputs (JSON, file contents, etc.) - only show agent messages
            const content = data.content;

            // ALWAYS show messages containing important keywords (agent status updates)
            const importantKeywords = [
                'COMPLETE:', 'PIPELINE', 'MONITORING', 'WAITING', 'WAIT]',
                'DEBUG', 'FIX', 'SUCCESS', 'FAILED', 'ERROR', 'RETRY',
                'Issue #', 'Branch:', 'Merge', 'Tests', 'Coverage'
            ];

            const containsImportantKeyword = importantKeywords.some(keyword =>
                content.includes(keyword)
            );

            if (containsImportantKeyword) {
                // Always show important status messages
                this.ui.updateCurrentAgent(data.agent);
                this.ui.addAgentOutput(data.agent, data.content, data.level);
                return;
            }

            // Skip if content looks like tool output:
            // - Starts with { or [ AND contains multiple lines (JSON structure)
            // - Contains file paths with line numbers (Read tool output)
            // - Is extremely long (> 3000 chars, likely file/API response)
            const looksLikeJSON =
                (content.trim().startsWith('{') || content.trim().startsWith('[')) &&
                content.split('\n').length > 3;  // Multi-line JSON

            const looksLikeFileContent = /^\s*\d+→/.test(content);  // Line numbers from Read tool

            const isTooLong = content.length > 3000;  // Increased from 1000

            const looksLikeToolOutput = looksLikeJSON || looksLikeFileContent || isTooLong;

            if (!looksLikeToolOutput) {
                // Update current agent indicator
                this.ui.updateCurrentAgent(data.agent);

                // Show agent message
                this.ui.addAgentOutput(data.agent, data.content, data.level);
            }
        });

        this.ws.on('agent_start', (data) => {
            this.ui.updateCurrentAgent(data.agent);
            this.ui.addAgentOutput(data.agent, `Starting ${data.agent}...`, 'info');
        });

        this.ws.on('agent_complete', (data) => {
            this.ui.updateCurrentAgent('-');
            this.ui.addAgentOutput(
                data.agent,
                `Completed in ${data.duration.toFixed(2)}s`,
                'success'
            );
        });

        // MCP Log events
        this.ws.on('mcp_log', (data) => {
            this.ui.addMCPLog(
                data.message,
                data.level || 'info',
                data.timestamp
            );
        });

        // Pipeline events
        this.ws.on('pipeline_update', (data) => {
            this.ui.updatePipelineStage(data.stage, data.status);
            if (data.status === 'running') {
                this.ui.updateCurrentStage(data.stage);
            }
        });

        // Issue events
        this.ws.on('issue_update', (data) => {
            this.ui.addAgentOutput(
                'System',
                `Issue #${data.issue_id}: ${data.status}`,
                data.status === 'failed' ? 'error' : 'info'
            );
        });

        // Tech stack detection
        this.ws.on('tech_stack_detected', (data) => {
            console.log('[TECH STACK] Detected:', data);
            this.ui.updateTechStack(data);
        });

        // Success/Error messages
        this.ws.on('success', (data) => {
            this.ui.showSuccess(data.message);
        });

        this.ws.on('error', (data) => {
            const errorMsg = data && data.message ? data.message : 'An error occurred';
            console.error('System error:', errorMsg);
            this.ui.showError(errorMsg);
        });
    }

    setupUIListeners() {
        // Start button
        this.ui.elements.startBtn.addEventListener('click', async () => {
            await this.startSystem();
        });

        // Stop button
        this.ui.elements.stopBtn.addEventListener('click', async () => {
            await this.stopSystem();
        });

        // Project selection
        this.ui.elements.projectSelect.addEventListener('change', async (e) => {
            if (e.target.value) {
                this.ui.elements.projectId.value = e.target.value;
                await this.loadIssues(e.target.value);
            }
        });

        // Refresh projects button
        this.ui.elements.refreshProjects.addEventListener('click', async () => {
            await this.loadProjects();
        });

        // Refresh issues button
        this.ui.elements.refreshIssues.addEventListener('click', async () => {
            const projectId = this.ui.elements.projectSelect.value || this.ui.elements.projectId.value;
            if (projectId) {
                await this.loadIssues(projectId);
            } else {
                this.ui.showError('Please select or enter a project ID first');
            }
        });
    }

    async startSystem() {
        try {
            // Get and validate configuration (may throw validation errors)
            const config = this.ui.getConfiguration();

            // Debug logging
            console.log('Starting system with config:', config);

            // Additional validation
            if (!config.project_id || config.project_id.trim() === '') {
                this.ui.showError('Please select a project from the dropdown or enter a GitLab project ID');
                return;
            }

            if (config.mode === 'single_issue' && !config.specific_issue) {
                this.ui.showError('Please enter an issue number');
                return;
            }

            this.ui.showInfo('Starting system...');
            this.ui.updateSystemStatus('starting');

            // Send start command via WebSocket for real-time updates
            this.ws.send('start_system', { config });

            // WebSocket events will handle the response
            this.systemRunning = true;
            this.startTime = Date.now();
            this.startUptimeCounter();
            this.ui.updateSystemStatus('running');
            this.ui.resetPipeline();
        } catch (error) {
            this.ui.showError(`Failed to start system: ${error.message}`);
            this.ui.updateSystemStatus('idle');
        }
    }

    async stopSystem() {
        try {
            this.ui.showInfo('Stopping system...');

            // Send stop command via WebSocket
            this.ws.send('stop_system');

            // Also call API
            const response = await this.api.stopSystem();

            if (response.success) {
                this.systemRunning = false;
                this.stopUptimeCounter();
                this.ui.updateSystemStatus('idle');
                this.ui.updateCurrentStage('-');
                this.ui.updateProgress(0);
                this.ui.showSuccess('System stopped');
            }
        } catch (error) {
            this.ui.showError(`Failed to stop system: ${error.message}`);
        }
    }

    handleSystemStatus(status) {
        // Update UI based on system status
        this.ui.updateSystemStatus(status.running ? 'running' : 'idle');

        if (status.current_stage) {
            this.ui.updateCurrentStage(status.current_stage);
        }

        if (status.current_issue !== undefined) {
            this.ui.updateCurrentIssue(status.current_issue);
        }

        if (status.current_branch !== undefined) {
            this.ui.updateCurrentBranch(status.current_branch);
        }

        if (status.progress !== undefined) {
            this.ui.updateProgress(status.progress);
        }

        if (status.stats) {
            this.ui.updateStatistics(status.stats);
        }

        // Update running state
        this.systemRunning = status.running;

        if (status.running && status.start_time && !this.uptimeInterval) {
            this.startTime = new Date(status.start_time).getTime();
            this.startUptimeCounter();
        } else if (!status.running && this.uptimeInterval) {
            this.stopUptimeCounter();
        }
    }

    startUptimeCounter() {
        this.stopUptimeCounter(); // Clear any existing interval

        this.uptimeInterval = setInterval(() => {
            if (this.startTime) {
                const uptime = Math.floor((Date.now() - this.startTime) / 1000);
                this.ui.updateUptime(uptime);
            }
        }, 1000);
    }

    stopUptimeCounter() {
        if (this.uptimeInterval) {
            clearInterval(this.uptimeInterval);
            this.uptimeInterval = null;
        }
    }

    async loadInitialData() {
        try {
            // Load default configuration
            const defaults = await this.api.getDefaultConfig();
            this.ui.setConfiguration(defaults);

            // Get current system status
            const status = await this.api.getSystemStatus();
            this.handleSystemStatus(status);

            // Load statistics
            const stats = await this.api.getStatistics();
            this.ui.updateStatistics(stats);

            // Load projects
            await this.loadProjects();

            // Load LLM providers and configuration
            await this.ui.loadLLMProviders();

        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }

    async loadProjects() {
        try {
            this.ui.showInfo('Loading projects...');
            const projects = await this.api.getProjects();
            this.ui.populateProjects(projects);
            this.ui.showInfo(`Loaded ${projects.length} projects`);
        } catch (error) {
            this.ui.showError(`Failed to load projects: ${error.message}`);
        }
    }

    async loadIssues(projectId) {
        try {
            this.ui.showInfo('Loading issues...');
            const issues = await this.api.getProjectIssues(projectId);
            this.ui.populateIssues(issues);
            this.ui.showInfo(`Loaded ${issues.length} issues`);
        } catch (error) {
            this.ui.showError(`Failed to load issues: ${error.message}`);
        }
    }

    // Auto-detection removed - backend now handles this automatically

    selectIssue(issueNumber) {
        // Set single issue mode and fill in the issue number
        this.ui.elements.executionMode.value = 'single_issue';
        this.ui.elements.issueNumber.value = issueNumber;
        this.ui.elements.issueNumberGroup.style.display = 'block';

        // Switch to agent output tab
        this.ui.switchTab('agent-output');

        this.ui.showInfo(`Selected issue #${issueNumber}`);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});

// Handle page unload
window.addEventListener('beforeunload', (event) => {
    if (window.app && window.app.systemRunning) {
        event.preventDefault();
        event.returnValue = 'System is still running. Are you sure you want to leave?';
    }
});