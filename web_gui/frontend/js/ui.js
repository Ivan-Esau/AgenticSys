/**
 * UI Manager - Handles all DOM manipulation and UI updates
 */

class UIManager {
    constructor() {
        this.elements = this.cacheElements();
        this.setupEventListeners();
        this.activeTab = 'agent-output';
    }

    cacheElements() {
        return {
            // Status elements
            connectionStatus: document.getElementById('connectionStatus'),
            statusDot: document.getElementById('statusDot'),
            statusText: document.getElementById('statusText'),
            systemStatus: document.getElementById('systemStatus'),
            currentStage: document.getElementById('currentStage'),
            progressBar: document.getElementById('progressBar'),
            progressText: document.getElementById('progressText'),

            // Form elements
            projectSelect: document.getElementById('projectSelect'),
            projectId: document.getElementById('projectId'),
            executionMode: document.getElementById('executionMode'),
            issueNumber: document.getElementById('issueNumber'),
            issueNumberGroup: document.getElementById('issueNumberGroup'),
            language: document.getElementById('language'),
            framework: document.getElementById('framework'),
            database: document.getElementById('database'),
            testing: document.getElementById('testing'),
            deployment: document.getElementById('deployment'),
            cicd: document.getElementById('cicd'),
            autoMerge: document.getElementById('autoMerge'),
            debugMode: document.getElementById('debugMode'),
            minCoverage: document.getElementById('minCoverage'),

            // LLM Configuration
            llmProvider: document.getElementById('llmProvider'),
            llmModel: document.getElementById('llmModel'),
            llmTemperature: document.getElementById('llmTemperature'),

            // Buttons
            startBtn: document.getElementById('startBtn'),
            stopBtn: document.getElementById('stopBtn'),
            clearBtn: document.getElementById('clearBtn'),
            themeToggle: document.getElementById('themeToggle'),
            refreshProjects: document.getElementById('refreshProjects'),
            autoDetectBtn: document.getElementById('autoDetectBtn'),
            refreshIssues: document.getElementById('refreshIssues'),

            // Output areas
            agentOutput: document.getElementById('agentOutput'),
            toolList: document.getElementById('toolList'),

            // Pipeline stages
            stages: {
                planning: document.getElementById('stage-planning'),
                coding: document.getElementById('stage-coding'),
                testing: document.getElementById('stage-testing'),
                review: document.getElementById('stage-review')
            },

            // Statistics
            stats: {
                totalIssues: document.getElementById('statTotalIssues'),
                processed: document.getElementById('statProcessed'),
                successRate: document.getElementById('statSuccessRate'),
                agentCalls: document.getElementById('statAgentCalls'),
                toolCalls: document.getElementById('statToolCalls'),
                uptime: document.getElementById('statUptime')
            },

            // Tab elements
            tabButtons: document.querySelectorAll('.tab-button'),
            tabPanes: document.querySelectorAll('.tab-pane')
        };
    }

    setupEventListeners() {
        // Mode change listener
        this.elements.executionMode.addEventListener('change', (e) => {
            this.elements.issueNumberGroup.style.display =
                e.target.value === 'single_issue' ? 'block' : 'none';
        });

        // LLM provider change listener
        this.elements.llmProvider.addEventListener('change', async (e) => {
            await this.loadModelsForProvider(e.target.value);
        });

        // Clear button
        this.elements.clearBtn.addEventListener('click', () => {
            this.clearOutput();
        });

        // Theme toggle
        this.elements.themeToggle.addEventListener('click', () => {
            this.toggleTheme();
        });

        // Tab switching
        this.elements.tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
    }

    // Connection status
    updateConnectionStatus(connected) {
        if (connected) {
            this.elements.statusDot.className = 'status-dot connected';
            this.elements.statusText.textContent = 'Connected';
        } else {
            this.elements.statusDot.className = 'status-dot disconnected';
            this.elements.statusText.textContent = 'Disconnected';
        }
    }

    // System status
    updateSystemStatus(status) {
        this.elements.systemStatus.textContent = status.charAt(0).toUpperCase() + status.slice(1);

        if (status === 'running') {
            this.elements.startBtn.disabled = true;
            this.elements.stopBtn.disabled = false;
        } else {
            this.elements.startBtn.disabled = false;
            this.elements.stopBtn.disabled = true;
        }
    }

    updateProgress(progress) {
        this.elements.progressBar.style.width = `${progress}%`;
        this.elements.progressText.textContent = `${Math.round(progress)}%`;
    }

    updateCurrentStage(stage) {
        this.elements.currentStage.textContent = stage || '-';
    }

    // Pipeline updates
    updatePipelineStage(stageName, status) {
        const stage = this.elements.stages[stageName];
        if (!stage) return;

        // Update data attribute and status text
        stage.setAttribute('data-status', status);
        const statusElement = stage.querySelector('.stage-status');
        if (statusElement) {
            statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        }
    }

    resetPipeline() {
        Object.values(this.elements.stages).forEach(stage => {
            stage.setAttribute('data-status', 'pending');
            const statusElement = stage.querySelector('.stage-status');
            if (statusElement) {
                statusElement.textContent = 'Pending';
            }
        });
    }

    // Output management
    addAgentOutput(agent, content, level = 'info', timestamp = null) {
        const time = timestamp || new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = 'output-entry';
        entry.innerHTML = `
            <div class="output-header">
                <span class="output-agent">[${agent}]</span>
                <span class="output-timestamp">${time}</span>
            </div>
            <div class="output-content ${level}">${this.escapeHtml(content)}</div>
        `;

        // Clear placeholder message if present
        const placeholder = this.elements.agentOutput.querySelector('.output-message');
        if (placeholder) {
            placeholder.remove();
        }

        this.elements.agentOutput.appendChild(entry);
        this.elements.agentOutput.scrollTop = this.elements.agentOutput.scrollHeight;
    }

    addToolUsage(agent, tool, duration, success = true, timestamp = null) {
        const time = timestamp || new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = 'tool-entry';
        entry.innerHTML = `
            <div class="tool-header">
                <span class="tool-name">${tool}</span>
                <span class="tool-duration">${duration}ms</span>
            </div>
            <div class="tool-agent">Agent: ${agent}</div>
            <div class="tool-status ${success ? 'success' : 'failed'}">
                ${success ? '✅ Success' : '❌ Failed'}
            </div>
            <div class="tool-time">${time}</div>
        `;

        // Clear placeholder message if present
        const placeholder = this.elements.toolList.querySelector('.tool-message');
        if (placeholder) {
            placeholder.remove();
        }

        this.elements.toolList.appendChild(entry);
        this.elements.toolList.scrollTop = this.elements.toolList.scrollHeight;
    }

    clearOutput() {
        this.elements.agentOutput.innerHTML =
            '<div class="output-message">Output cleared. Waiting for new messages...</div>';
        this.elements.toolList.innerHTML =
            '<div class="tool-message">No tool usage yet.</div>';
    }

    // Statistics
    updateStatistics(stats) {
        if (stats.total_issues !== undefined) {
            this.elements.stats.totalIssues.textContent = stats.total_issues;
        }
        if (stats.processed_issues !== undefined) {
            this.elements.stats.processed.textContent = stats.processed_issues;
        }
        if (stats.success_rate !== undefined) {
            this.elements.stats.successRate.textContent = `${Math.round(stats.success_rate)}%`;
        }
        if (stats.agent_calls !== undefined) {
            this.elements.stats.agentCalls.textContent = stats.agent_calls;
        }
        if (stats.tool_calls !== undefined) {
            this.elements.stats.toolCalls.textContent = stats.tool_calls;
        }
        if (stats.uptime !== undefined) {
            this.updateUptime(stats.uptime);
        }
    }

    updateUptime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        const formatted = [hours, minutes, secs]
            .map(v => v.toString().padStart(2, '0'))
            .join(':');

        this.elements.stats.uptime.textContent = formatted;
    }

    // Configuration
    getConfiguration() {
        const mode = this.elements.executionMode.value;
        const projectId = this.elements.projectSelect.value || this.elements.projectId.value.trim();

        const config = {
            project_id: projectId,
            mode: mode,
            tech_stack: {
                language: this.elements.language.value.trim() || 'Python',
                framework: this.elements.framework.value.trim() || null,
                database: this.elements.database.value.trim() || null,
                testing: this.elements.testing.value.trim() || 'pytest',
                deployment: this.elements.deployment.value.trim() || null,
                ci_cd: this.elements.cicd.value.trim() || 'GitLab CI'
            },
            auto_merge: this.elements.autoMerge.checked,
            debug: this.elements.debugMode.checked,
            min_coverage: parseFloat(this.elements.minCoverage.value) || 70.0,
            llm_config: this.getLLMConfiguration()
        };

        if (mode === 'single_issue') {
            config.specific_issue = parseInt(this.elements.issueNumber.value);
        }

        return config;
    }

    setConfiguration(config) {
        if (config.project_id) {
            this.elements.projectId.value = config.project_id;
        }
        if (config.mode) {
            this.elements.executionMode.value = config.mode;
            this.elements.issueNumberGroup.style.display =
                config.mode === 'single_issue' ? 'block' : 'none';
        }
        if (config.tech_stack) {
            if (config.tech_stack.language) {
                this.elements.language.value = config.tech_stack.language;
            }
            if (config.tech_stack.framework) {
                this.elements.framework.value = config.tech_stack.framework;
            }
            if (config.tech_stack.testing) {
                this.elements.testing.value = config.tech_stack.testing;
            }
        }
    }

    // Tab management
    switchTab(tabName) {
        this.activeTab = tabName;

        this.elements.tabButtons.forEach(button => {
            if (button.dataset.tab === tabName) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });

        this.elements.tabPanes.forEach(pane => {
            if (pane.id === tabName) {
                pane.classList.add('active');
            } else {
                pane.classList.remove('active');
            }
        });
    }

    // Theme management
    toggleTheme() {
        const currentTheme = document.body.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.body.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);

        // Update theme icon
        const icon = this.elements.themeToggle.querySelector('.theme-icon');
        icon.textContent = newTheme === 'dark' ? '[Light]' : '[Dark]';
    }

    loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.body.setAttribute('data-theme', savedTheme);

        const icon = this.elements.themeToggle.querySelector('.theme-icon');
        icon.textContent = savedTheme === 'dark' ? '[Light]' : '[Dark]';
    }

    // Projects and Issues
    populateProjects(projects) {
        const select = this.elements.projectSelect;
        select.innerHTML = '<option value="">Select a project...</option>';

        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = project.name || `Project ${project.id}`;
            option.dataset.description = project.description || '';
            select.appendChild(option);
        });
    }

    populateIssues(issues) {
        const tbody = document.getElementById('issuesTableBody');
        if (!tbody) return;

        if (!issues || issues.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">No issues found.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        issues.forEach(issue => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>#${issue.iid || issue.id}</td>
                <td>${this.escapeHtml(issue.title)}</td>
                <td>${this.formatLabels(issue.labels)}</td>
                <td>${issue.state}</td>
                <td>
                    <button class="btn btn-small btn-primary" onclick="app.selectIssue(${issue.iid || issue.id})">
                        Select
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    formatLabels(labels) {
        if (!labels || labels.length === 0) return '';
        return labels.map(label =>
            `<span class="label-tag">${this.escapeHtml(label)}</span>`
        ).join('');
    }

    updateTechStack(techStack) {
        if (techStack.language) this.elements.language.value = techStack.language;
        if (techStack.framework) this.elements.framework.value = techStack.framework;
        if (techStack.database) this.elements.database.value = techStack.database;
        if (techStack.testing) this.elements.testing.value = techStack.testing;
        if (techStack.deployment) this.elements.deployment.value = techStack.deployment;
        if (techStack.ci_cd) this.elements.cicd.value = techStack.ci_cd;
    }

    // Utility
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showError(message) {
        this.addAgentOutput('System', `Error: ${message}`, 'error');
    }

    showSuccess(message) {
        this.addAgentOutput('System', message, 'success');
    }

    showInfo(message) {
        this.addAgentOutput('System', message, 'info');
    }

    // LLM Configuration
    async loadLLMProviders() {
        try {
            console.log('[DEBUG] Starting loadLLMProviders...');

            // Check if elements exist
            if (!this.elements.llmProvider) {
                console.error('[ERROR] llmProvider element not found');
                return;
            }

            console.log('[DEBUG] Fetching /api/llm/providers...');
            const response = await fetch('/api/llm/providers');
            console.log('[DEBUG] Response status:', response.status);

            const data = await response.json();
            console.log('[DEBUG] Providers data:', data);

            // Clear existing options
            this.elements.llmProvider.innerHTML = '<option value="">Select provider...</option>';

            // Add providers
            data.providers.forEach(provider => {
                const option = document.createElement('option');
                option.value = provider;
                option.textContent = provider.charAt(0).toUpperCase() + provider.slice(1);
                if (provider === data.default) {
                    option.selected = true;
                }
                this.elements.llmProvider.appendChild(option);
                console.log('[DEBUG] Added provider:', provider);
            });

            // Load models for default provider
            if (data.default) {
                console.log('[DEBUG] Loading models for default provider:', data.default);
                await this.loadModelsForProvider(data.default);
            }

            // Load current configuration
            console.log('[DEBUG] Loading current LLM config...');
            await this.loadCurrentLLMConfig();

            console.log('[DEBUG] LLM providers loaded successfully');
        } catch (error) {
            console.error('Failed to load LLM providers:', error);
            this.showError('Failed to load LLM providers');
        }
    }

    async loadModelsForProvider(provider) {
        console.log('[DEBUG] loadModelsForProvider called with:', provider);

        if (!provider) {
            console.log('[DEBUG] No provider specified, setting default option');
            this.elements.llmModel.innerHTML = '<option value="">Select provider first</option>';
            return;
        }

        try {
            console.log('[DEBUG] Setting loading state for models...');
            this.elements.llmModel.innerHTML = '<option value="">Loading models...</option>';

            console.log('[DEBUG] Fetching /api/llm/models/' + provider);
            const response = await fetch(`/api/llm/models/${provider}`);
            console.log('[DEBUG] Models response status:', response.status);

            const data = await response.json();
            console.log('[DEBUG] Models data:', data);

            // Clear existing options
            this.elements.llmModel.innerHTML = '<option value="">Select model...</option>';

            // Add models
            Object.entries(data.models).forEach(([modelId, modelName]) => {
                const option = document.createElement('option');
                option.value = modelId;
                option.textContent = modelName;
                if (modelId === data.default) {
                    option.selected = true;
                }
                this.elements.llmModel.appendChild(option);
                console.log('[DEBUG] Added model:', modelId, modelName);
            });

            console.log('[DEBUG] Models loaded successfully for provider:', provider);
        } catch (error) {
            console.error(`Failed to load models for ${provider}:`, error);
            this.elements.llmModel.innerHTML = '<option value="">Error loading models</option>';
        }
    }

    async loadCurrentLLMConfig() {
        try {
            console.log('[DEBUG] Loading current LLM configuration...');

            const response = await fetch('/api/llm/current');
            console.log('[DEBUG] Current config response status:', response.status);

            const config = await response.json();
            console.log('[DEBUG] Current config data:', config);

            // Set current values
            this.elements.llmProvider.value = config.provider;
            this.elements.llmTemperature.value = config.temperature;
            console.log('[DEBUG] Set provider and temperature:', config.provider, config.temperature);

            // Load models and set current model
            await this.loadModelsForProvider(config.provider);
            this.elements.llmModel.value = config.model;
            console.log('[DEBUG] Set model:', config.model);

            console.log('[DEBUG] Current LLM config loaded successfully');
        } catch (error) {
            console.error('Failed to load current LLM config:', error);
        }
    }

    getLLMConfiguration() {
        return {
            provider: this.elements.llmProvider.value,
            model: this.elements.llmModel.value,
            temperature: parseFloat(this.elements.llmTemperature.value) || 0.7
        };
    }
}

// Export for use in other modules
window.UIManager = UIManager;