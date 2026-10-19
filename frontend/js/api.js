/**
 * API调用模块
 */

const API_BASE_URL = 'http://localhost:8000';

const API = {
    // 项目管理
    async createProject(name, description = '') {
        const response = await fetch(`${API_BASE_URL}/api/projects`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });
        return this.handleResponse(response);
    },

    async listProjects() {
        const response = await fetch(`${API_BASE_URL}/api/projects`);
        return this.handleResponse(response);
    },

    async getProject(projectId) {
        const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}`);
        return this.handleResponse(response);
    },

    async deleteProject(projectId) {
        const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}`, {
            method: 'DELETE'
        });
        return this.handleResponse(response);
    },

    // 数据上传
    async uploadData(projectId, dataType, file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(
            `${API_BASE_URL}/api/projects/${projectId}/data/${dataType}`,
            {
                method: 'POST',
                body: formData
            }
        );
        return this.handleResponse(response);
    },

    async getDataStatus(projectId) {
        const response = await fetch(
            `${API_BASE_URL}/api/projects/${projectId}/data/status`
        );
        return this.handleResponse(response);
    },

    // 分析任务
    async startAnalysis(projectId, params) {
        const response = await fetch(
            `${API_BASE_URL}/api/projects/${projectId}/analyze`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            }
        );
        return this.handleResponse(response);
    },

    async getTaskStatus(taskId) {
        const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`);
        return this.handleResponse(response);
    },

    async getResults(projectId) {
        const response = await fetch(
            `${API_BASE_URL}/api/projects/${projectId}/results`
        );
        return this.handleResponse(response);
    },

    // 知识问答
    async askQuestion(projectId, question, options = {}) {
        const response = await fetch(
            `${API_BASE_URL}/api/projects/${projectId}/qa`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question, ...options })
            }
        );
        return this.handleResponse(response);
    },

    // 响应处理
    async handleResponse(response) {
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || data.detail || '请求失败');
        }
        
        return data;
    }
};