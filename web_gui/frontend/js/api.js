/**
 * API client for REST endpoints
 */

class APIClient {
    constructor(baseURL = null) {
        this.baseURL = baseURL || `http://${window.location.hostname}:8000/api`;
    }

    async request(method, endpoint, data = null) {
        const url = `${this.baseURL}${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, options);

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${method} ${endpoint}`, error);
            throw error;
        }
    }

    // System endpoints
    async startSystem(config) {
        return this.request('POST', '/system/start', config);
    }

    async stopSystem() {
        return this.request('POST', '/system/stop');
    }

    async getSystemStatus() {
        return this.request('GET', '/system/status');
    }

    // Project endpoints
    async getProjects() {
        return this.request('GET', '/projects');
    }

    async getProjectIssues(projectId, state = 'opened') {
        return this.request('GET', `/projects/${projectId}/issues?state=${state}`);
    }

    async detectTechStack(projectId) {
        return this.request('POST', `/projects/${projectId}/detect-tech`);
    }

    // Configuration endpoints
    async getDefaultConfig() {
        return this.request('GET', '/config/defaults');
    }

    // Statistics endpoints
    async getStatistics() {
        return this.request('GET', '/stats');
    }

    // Agent endpoints
    async getAgentsInfo() {
        return this.request('GET', '/agents');
    }
}

// Export for use in other modules
window.APIClient = APIClient;