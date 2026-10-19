/**
 * 主应用逻辑
 */

const App = {
    currentProject: null,
    currentTask: null,
    pollInterval: null,

    init() {
        this.bindEvents();
        this.loadProjects();
    },

    bindEvents() {
        // 项目列表
        document.getElementById('create-project-btn').addEventListener('click', () => {
            this.showCreateProjectModal();
        });

        document.getElementById('cancel-create').addEventListener('click', () => {
            this.hideCreateProjectModal();
        });

        document.getElementById('confirm-create').addEventListener('click', () => {
            this.createProject();
        });

        document.getElementById('back-to-projects').addEventListener('click', () => {
            this.showProjectList();
        });

        // 数据上传
        document.getElementById('upload-btn').addEventListener('click', () => {
            this.uploadData();
        });

        // 分析
        document.getElementById('start-analysis-btn').addEventListener('click', () => {
            this.startAnalysis();
        });

        // 问答
        document.getElementById('ask-btn').addEventListener('click', () => {
            this.askQuestion();
        });

        // 监听单元选中事件
        document.addEventListener('unitSelected', (e) => {
            this.onUnitSelected(e.detail);
        });
    },

    // 显示项目列表
    async showProjectList() {
        document.getElementById('project-list-view').style.display = 'block';
        document.getElementById('workspace-view').style.display = 'none';
        document.getElementById('back-to-projects').style.display = 'none';
        document.getElementById('current-project').textContent = '未选择项目';
        
        this.currentProject = null;
        this.loadProjects();
    },

    // 加载项目列表
    async loadProjects() {
        const container = document.getElementById('projects-container');
        container.innerHTML = '<p class="loading">加载中...</p>';

        try {
            const result = await API.listProjects();
            const projects = result.data.projects;

            if (projects.length === 0) {
                container.innerHTML = '<p class="info-text">暂无项目，点击"新建项目"开始</p>';
                return;
            }

            container.innerHTML = '';
            projects.forEach(project => {
                const card = this.createProjectCard(project);
                container.appendChild(card);
            });
        } catch (error) {
            container.innerHTML = `<p class="info-text">加载失败: ${error.message}</p>`;
        }
    },

    // 创建项目卡片
    createProjectCard(project) {
        const card = document.createElement('div');
        card.className = 'project-card';
        
        const date = new Date(project.created_at).toLocaleString('zh-CN');
        
        card.innerHTML = `
            <h3>${project.name}</h3>
            <p>${project.description || '无描述'}</p>
            <div class="project-meta">创建时间: ${date}</div>
            <div class="project-actions">
                <button class="btn btn-primary btn-open">打开</button>
                <button class="btn btn-danger btn-delete">删除</button>
            </div>
        `;

        card.querySelector('.btn-open').addEventListener('click', (e) => {
            e.stopPropagation();
            this.openProject(project);
        });

        card.querySelector('.btn-delete').addEventListener('click', (e) => {
            e.stopPropagation();
            this.deleteProject(project);
        });

        return card;
    },

    // 显示创建项目模态框
    showCreateProjectModal() {
        document.getElementById('create-project-modal').style.display = 'flex';
        document.getElementById('project-name').value = '';
        document.getElementById('project-description').value = '';
    },

    // 隐藏创建项目模态框
    hideCreateProjectModal() {
        document.getElementById('create-project-modal').style.display = 'none';
    },

    // 创建项目
    async createProject() {
        const name = document.getElementById('project-name').value.trim();
        const description = document.getElementById('project-description').value.trim();

        if (!name) {
            alert('请输入项目名称');
            return;
        }

        try {
            await API.createProject(name, description);
            this.hideCreateProjectModal();
            this.loadProjects();
        } catch (error) {
            alert(`创建失败: ${error.message}`);
        }
    },

    // 打开项目
    async openProject(project) {
        this.currentProject = project;
        
        document.getElementById('project-list-view').style.display = 'none';
        document.getElementById('workspace-view').style.display = 'block';
        document.getElementById('back-to-projects').style.display = 'inline-block';
        document.getElementById('current-project').textContent = project.name;

        // 初始化地图
        if (!MapManager.map) {
            MapManager.init();
        } else {
            MapManager.clearLayers();
        }

        // 加载数据状态
        await this.loadDataStatus();

        // 如果有分析结果，加载结果
        if (project.analysis_status === 'completed') {
            await this.loadResults();
        }
    },

    // 删除项目
    async deleteProject(project) {
        if (!confirm(`确定要删除项目"${project.name}"吗？此操作不可恢复。`)) {
            return;
        }

        try {
            await API.deleteProject(project.id);
            this.loadProjects();
        } catch (error) {
            alert(`删除失败: ${error.message}`);
        }
    },

    // 加载数据状态
    async loadDataStatus() {
        try {
            const result = await API.getDataStatus(this.currentProject.id);
            const dataStatus = result.data.data_status;

            // 更新状态显示
            this.updateStatusBadge('boundary', dataStatus.boundary);
            this.updateStatusBadge('poi', dataStatus.poi);
            this.updateStatusBadge('roads', dataStatus.roads);

            // 更新分析按钮状态
            const canAnalyze = dataStatus.boundary && dataStatus.poi;
            document.getElementById('start-analysis-btn').disabled = !canAnalyze;
        } catch (error) {
            console.error('加载数据状态失败:', error);
        }
    },

    // 更新状态徽章
    updateStatusBadge(dataType, uploaded) {
        const badge = document.getElementById(`${dataType}-status`);
        if (uploaded) {
            badge.textContent = '已上传';
            badge.classList.add('uploaded');
        } else {
            badge.textContent = '未上传';
            badge.classList.remove('uploaded');
        }
    },

    // 上传数据
    async uploadData() {
        const dataType = document.getElementById('data-type-select').value;
        const fileInput = document.getElementById('file-input');
        const file = fileInput.files[0];

        if (!file) {
            alert('请选择文件');
            return;
        }

        const uploadBtn = document.getElementById('upload-btn');
        uploadBtn.disabled = true;
        uploadBtn.textContent = '上传中...';

        try {
            await API.uploadData(this.currentProject.id, dataType, file);
            alert('上传成功');
            fileInput.value = '';
            await this.loadDataStatus();
        } catch (error) {
            alert(`上传失败: ${error.message}`);
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = '上传';
        }
    },

    // 开始分析
    async startAnalysis() {
        const gridSize = parseInt(document.getElementById('grid-size').value);
        const bufferRadius = parseInt(document.getElementById('buffer-radius').value);

        const params = {
            grid_mode: 'square',
            grid_size: gridSize,
            buffer_radius: bufferRadius,
            include_terrain: false,
            build_knowledge_graph: true
        };

        const startBtn = document.getElementById('start-analysis-btn');
        startBtn.disabled = true;
        startBtn.textContent = '分析中...';

        try {
            const result = await API.startAnalysis(this.currentProject.id, params);
            this.currentTask = result.data.task_id;
            
            // 显示进度
            document.getElementById('task-progress').style.display = 'block';
            
            // 开始轮询任务状态
            this.startPollingTask();
        } catch (error) {
            alert(`启动分析失败: ${error.message}`);
            startBtn.disabled = false;
            startBtn.textContent = '开始分析';
        }
    },

    // 轮询任务状态
    startPollingTask() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }

        this.pollInterval = setInterval(async () => {
            try {
                const result = await API.getTaskStatus(this.currentTask);
                const task = result.data;

                // 更新进度
                document.getElementById('progress-fill').style.width = `${task.progress}%`;
                document.getElementById('progress-text').textContent = task.message;

                // 任务完成
                if (task.status === 'completed') {
                    clearInterval(this.pollInterval);
                    document.getElementById('progress-text').textContent = '分析完成！';
                    
                    setTimeout(async () => {
                        document.getElementById('task-progress').style.display = 'none';
                        document.getElementById('start-analysis-btn').disabled = false;
                        document.getElementById('start-analysis-btn').textContent = '开始分析';
                        
                        // 加载结果
                        await this.loadResults();
                    }, 1000);
                }

                // 任务失败
                if (task.status === 'failed') {
                    clearInterval(this.pollInterval);
                    alert(`分析失败: ${task.message}`);
                    document.getElementById('task-progress').style.display = 'none';
                    document.getElementById('start-analysis-btn').disabled = false;
                    document.getElementById('start-analysis-btn').textContent = '开始分析';
                }
            } catch (error) {
                console.error('轮询任务状态失败:', error);
            }
        }, 2000); // 每2秒轮询一次
    },

    // 加载分析结果
    async loadResults() {
        try {
            const result = await API.getResults(this.currentProject.id);
            const data = result.data;

            // 显示地图结果
            MapManager.showResults(data.geojson);

            // 显示统计信息
            this.showResultsSummary(data.statistics);

            // 启用问答功能
            document.getElementById('ask-btn').disabled = false;
        } catch (error) {
            console.error('加载结果失败:', error);
        }
    },

    // 显示结果摘要
    showResultsSummary(stats) {
        const container = document.getElementById('results-summary');
        
        if (!stats) {
            container.innerHTML = '<p class="info-text">暂无统计数据</p>';
            return;
        }

        let html = `
            <div class="result-item">
                <div class="result-label">总单元数</div>
                <div class="result-value">${stats.total_units}</div>
            </div>
        `;

        // 功能分布
        if (stats.function_counts) {
            html += '<h4 style="margin-top: 15px; font-size: 14px;">功能分布</h4>';
            Object.entries(stats.function_counts).forEach(([func, count]) => {
                html += `
                    <div class="result-item">
                        <div class="result-label">${func}</div>
                        <div class="result-value">${count} 个单元</div>
                    </div>
                `;
            });
        }

        // 适宜性等级分布
        if (stats.suitability_distribution) {
            html += '<h4 style="margin-top: 15px; font-size: 14px;">适宜性等级分布</h4>';
            
            // 定义等级颜色和标签
            const levelConfig = {
                'suitable': { color: '#27ae60', label: '适宜' },
                'moderate': { color: '#f39c12', label: '一般适宜' },
                'unsuitable': { color: '#e74c3c', label: '不适宜' }
            };
            
            Object.entries(stats.suitability_distribution).forEach(([level, count]) => {
                const config = levelConfig[level] || { color: '#999', label: level };
                html += `
                    <div class="result-item">
                        <div class="result-label">
                            <span style="display:inline-block;width:12px;height:12px;background:${config.color};margin-right:6px;border-radius:2px;"></span>
                            ${config.label}
                        </div>
                        <div class="result-value">${count} 个单元</div>
                    </div>
                `;
            });
        }

        // 数据完整性统计
        if (stats.avg_data_completeness !== undefined) {
            html += `
                <div class="result-item" style="margin-top: 15px;">
                    <div class="result-label">平均数据完整性</div>
                    <div class="result-value">${(stats.avg_data_completeness * 100).toFixed(1)}%</div>
                </div>
            `;
        }

        container.innerHTML = html;
    },

    // 单元被选中
    onUnitSelected(properties) {
        // 自动填充问题
        const question = `为什么单元${properties.unit_id}适合${properties.recommended_function}？`;
        document.getElementById('qa-input').value = question;
    },

    // 提问
    async askQuestion() {
        const question = document.getElementById('qa-input').value.trim();
        
        if (!question) {
            alert('请输入问题');
            return;
        }

        const askBtn = document.getElementById('ask-btn');
        askBtn.disabled = true;
        askBtn.textContent = '思考中...';

        try {
            const result = await API.askQuestion(this.currentProject.id, question);
            const answer = result.data.answer;

            // 显示答案
            document.getElementById('qa-answer').style.display = 'block';
            document.getElementById('answer-content').textContent = answer;
        } catch (error) {
            alert(`提问失败: ${error.message}`);
        } finally {
            askBtn.disabled = false;
            askBtn.textContent = '提问';
        }
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});