// 配置
const API_BASE_URL = 'http://localhost:8000';

// 全局状态
let currentProject = null;
let currentTask = null;
let map = null;
let mapLayers = {
    // 基础数据
    boundary: null,
    poi: null,
    roads: null,
    water_bodies: null,
    // 地形环境
    dem: null,
    landuse: null,
    soil_type: null,
    precipitation: null,
    // 约束条件
    ecological_redline: null,
    farmland_protection: null,
    built_area: null,
    city_center: null,
    // 风险评估
    flood_risk: null,
    geological_hazard: null,
    gdp_density: null,
    // 分析结果
    results: null,
    selected: null
};

// 图层配置
const LAYER_CONFIG = {
    // 矢量图层
    poi: { type: 'vector', endpoint: 'poi', color: '#e74c3c', icon: '📍' },
    roads: { type: 'vector', endpoint: 'roads', color: '#3498db', weight: 2 },
    water_bodies: { type: 'vector', endpoint: 'water_bodies', color: '#00bcd4' },
    ecological_redline: { type: 'vector', endpoint: 'ecological_redline', color: '#ff9800', dashArray: '5,5' },
    farmland_protection: { type: 'vector', endpoint: 'farmland_protection', color: '#8bc34a', dashArray: '5,5' },
    built_area: { type: 'vector', endpoint: 'built_area', color: '#795548', fillOpacity: 0.3 },
    city_center: { type: 'vector', endpoint: 'city_center', color: '#f44336', fillOpacity: 0.3 },
    // 栅格图层
    dem: { type: 'raster', endpoint: 'dem', colormap: 'terrain' },
    landuse: { type: 'raster', endpoint: 'landuse', colormap: 'landuse' },
    soil_type: { type: 'raster', endpoint: 'soil_type', colormap: 'soil' },
    precipitation: { type: 'raster', endpoint: 'precipitation', colormap: 'blues' },
    flood_risk: { type: 'raster', endpoint: 'flood_risk', colormap: 'redness' },
    geological_hazard: { type: 'raster', endpoint: 'geological_hazard', colormap: 'redness' },
    gdp_density: { type: 'raster', endpoint: 'gdp_density', colormap: 'ylorbr' }
};

// 已加载的图层缓存
const loadedLayers = new Set();

// ========== WGS-84 → GCJ-02 坐标转换（高德地图使用 GCJ-02） ==========
const _PI = Math.PI;
const _A = 6378245.0;       // 克拉索夫斯基椭球长半轴
const _EE = 0.00669342162296594323;  // 偏心率平方

function _transformLat(x, y) {
    let ret = -100.0 + 2.0*x + 3.0*y + 0.2*y*y + 0.1*x*y + 0.2*Math.sqrt(Math.abs(x));
    ret += (20.0*Math.sin(6.0*x*_PI) + 20.0*Math.sin(2.0*x*_PI)) * 2.0/3.0;
    ret += (20.0*Math.sin(y*_PI) + 40.0*Math.sin(y/3.0*_PI)) * 2.0/3.0;
    ret += (160.0*Math.sin(y/12.0*_PI) + 320.0*Math.sin(y*_PI/30.0)) * 2.0/3.0;
    return ret;
}

function _transformLon(x, y) {
    let ret = 300.0 + x + 2.0*y + 0.1*x*x + 0.1*x*y + 0.1*Math.sqrt(Math.abs(x));
    ret += (20.0*Math.sin(6.0*x*_PI) + 20.0*Math.sin(2.0*x*_PI)) * 2.0/3.0;
    ret += (20.0*Math.sin(x*_PI) + 40.0*Math.sin(x/3.0*_PI)) * 2.0/3.0;
    ret += (150.0*Math.sin(x/12.0*_PI) + 300.0*Math.sin(x/30.0*_PI)) * 2.0/3.0;
    return ret;
}

function wgs84ToGcj02(lng, lat) {
    let dLat = _transformLat(lng - 105.0, lat - 35.0);
    let dLng = _transformLon(lng - 105.0, lat - 35.0);
    const radLat = lat / 180.0 * _PI;
    let magic = Math.sin(radLat);
    magic = 1 - _EE * magic * magic;
    const sqrtMagic = Math.sqrt(magic);
    dLat = (dLat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtMagic) * _PI);
    dLng = (dLng * 180.0) / (_A / sqrtMagic * Math.cos(radLat) * _PI);
    return { lng: lng + dLng, lat: lat + dLat };
}

function convertGeoJsonCoords(geojson) {
    if (!geojson || !geojson.features) return geojson;
    const converted = JSON.parse(JSON.stringify(geojson));
    converted.features.forEach(f => {
        if (f.geometry) f.geometry.coordinates = _convertCoords(f.geometry.type, f.geometry.coordinates);
    });
    return converted;
}

function _convertCoords(type, coords) {
    const c = ([lng, lat]) => { const r = wgs84ToGcj02(lng, lat); return [r.lng, r.lat]; };
    if (type === 'Point') return c(coords);
    if (type === 'MultiPoint' || type === 'LineString') return coords.map(c);
    if (type === 'MultiLineString' || type === 'Polygon') return coords.map(ring => ring.map(c));
    if (type === 'MultiPolygon') return coords.map(polygon => polygon.map(ring => ring.map(c)));
    return coords;
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadProjects();
});

// 初始化地图
function initMap() {
    map = L.map('map').setView([23.1, 113.3], 11);
    
    // 高德地图图层（卫星影像 + 路网标注）
    const gdSatellite = L.tileLayer('http://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}', {
        subdomains: ['1', '2', '3', '4'],
        attribution: '© 高德地图'
    });
    
    const gdRoadNet = L.tileLayer('http://webst0{s}.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}', {
        subdomains: ['1', '2', '3', '4'],
        attribution: '© 高德地图'
    });
    
    // 默认使用卫星影像 + 路网标注
    gdSatellite.addTo(map);
    gdRoadNet.addTo(map);
    
    // 可选：添加图层控制
    const baseLayers = {
        '高德卫星': gdSatellite
    };
    
    const overlays = {
        '路网标注': gdRoadNet
    };
    
    L.control.layers(baseLayers, overlays, { position: 'topright' }).addTo(map);
}

// API调用
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
        ...options,
        headers: {
            ...options.headers
        }
    };
    
    // 如果不是FormData，添加JSON头
    if (!(options.body instanceof FormData)) {
        config.headers['Content-Type'] = 'application/json';
    }
    
    try {
        const response = await fetch(url, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || data.detail || '请求失败');
        }
        
        return data;
    } catch (error) {
        alert('错误: ' + error.message);
        throw error;
    }
}

// === 项目管理 ===

async function loadProjects() {
    try {
        const result = await apiCall('/api/projects');
        const projects = result.data.projects;
        
        const listEl = document.getElementById('projectList');
        if (projects.length === 0) {
            listEl.innerHTML = '<li style="padding: 12px; color: #666;">暂无项目</li>';
            return;
        }
        
        listEl.innerHTML = projects.map(p => `
            <li class="project-item" onclick="selectProject('${p.id}')">
                <div class="project-name">${p.name}</div>
                <div class="project-meta">${p.created_at.split('T')[0]}</div>
            </li>
        `).join('');
    } catch (error) {
        document.getElementById('projectList').innerHTML = '<li style="padding: 12px; color: red;">加载失败</li>';
    }
}

function showCreateProject() {
    document.getElementById('viewProjectList').classList.add('hidden');
    document.getElementById('viewCreateProject').classList.remove('hidden');
}

function showProjectList() {
    document.getElementById('viewCreateProject').classList.add('hidden');
    document.getElementById('viewWorkspace').classList.add('hidden');
    document.getElementById('viewProjectList').classList.remove('hidden');
    currentProject = null;
    clearMap();
}

async function createProject(event) {
    event.preventDefault();
    
    const name = document.getElementById('projectName').value;
    const description = document.getElementById('projectDesc').value;
    
    try {
        const result = await apiCall('/api/projects', {
            method: 'POST',
            body: JSON.stringify({ name, description })
        });
        
        alert('项目创建成功');
        document.getElementById('projectName').value = '';
        document.getElementById('projectDesc').value = '';
        showProjectList();
        loadProjects();
    } catch (error) {
        // 错误已在apiCall中处理
    }
}

async function selectProject(projectId) {
    try {
        const result = await apiCall(`/api/projects/${projectId}`);
        currentProject = result.data;
        showWorkspace();
    } catch (error) {
        // 错误已在apiCall中处理
    }
}

async function deleteCurrentProject() {
    if (!currentProject) return;
    
    if (!confirm(`确定删除项目"${currentProject.name}"吗？`)) {
        return;
    }
    
    try {
        await apiCall(`/api/projects/${currentProject.id}`, {
            method: 'DELETE'
        });
        
        alert('项目已删除');
        showProjectList();
        loadProjects();
    } catch (error) {
        // 错误已在apiCall中处理
    }
}

// === 工作区视图 ===

function showWorkspace() {
    document.getElementById('viewProjectList').classList.add('hidden');
    document.getElementById('viewWorkspace').classList.remove('hidden');
    
    // 更新项目信息
    document.getElementById('currentProjectInfo').innerHTML = `
        <div class="project-name">${currentProject.name}</div>
        <div class="project-meta">${currentProject.description || '无描述'}</div>
        <div style="margin-top: 8px;">
            <div class="data-status">
                <span class="status-badge ${currentProject.data_status.boundary ? 'active' : ''}">边界</span>
                <span class="status-badge ${currentProject.data_status.poi ? 'active' : ''}">POI</span>
                <span class="status-badge ${currentProject.data_status.roads ? 'active' : ''}">路网</span>
            </div>
        </div>
    `;
    
    document.getElementById('mainTitle').textContent = currentProject.name;
    
    // 更新数据上传区域
    updateDataUploadArea();
    
    // 自动加载已上传的数据图层
    loadExistingDataLayers();
    
    // 检查分析状态
    if (currentProject.analysis_status === 'completed') {
        loadAnalysisResults();
    }
}

function updateDataUploadArea() {
    const dataTypes = [
        // 必需数据
        { key: 'boundary', label: '边界数据', required: true, accept: '.geojson,.json,.zip', category: '基础数据' },
        { key: 'poi', label: 'POI数据', required: true, accept: '.geojson,.json,.zip', category: '基础数据' },
        
        // 交通数据
        { key: 'roads', label: '路网数据', required: false, accept: '.geojson,.json,.zip', category: '交通可达性' },
        
        // 地形地貌
        { key: 'dem', label: 'DEM地形数据（高程、坡度）', required: false, accept: '.tif,.tiff', category: '地形地质' },
        
        // 气候环境
        { key: 'precipitation', label: '年降水量数据', required: false, accept: '.tif,.tiff', category: '气候环境' },
        
        // 土地与土壤
        { key: 'landuse', label: '土地利用数据', required: false, accept: '.tif,.tiff', category: '土地资源' },
        { key: 'soil_type', label: '土壤类型数据', required: false, accept: '.tif,.tiff', category: '土地资源' },
        
        // 水体
        { key: 'water_bodies', label: '水体数据', required: false, accept: '.geojson,.json,.zip', category: '水资源' },
        
        // 经济数据
        { key: 'gdp_density', label: 'GDP密度数据', required: false, accept: '.tif,.tiff', category: '经济指标' },
        
        // 约束边界
        { key: 'ecological_redline', label: '生态保护红线', required: false, accept: '.geojson,.json,.zip', category: '保护区约束' },
        { key: 'farmland_protection', label: '基本农田保护区', required: false, accept: '.geojson,.json,.zip', category: '保护区约束' },
        { key: 'built_area', label: '建成区范围', required: false, accept: '.geojson,.json,.zip', category: '建设现状' },
        
        // 灾害风险
        { key: 'flood_risk', label: '洪涝灾害风险', required: false, accept: '.tif,.tiff', category: '灾害风险' },
        { key: 'geological_hazard', label: '地质灾害易发性', required: false, accept: '.tif,.tiff', category: '灾害风险' },
        
        // 城市中心
        { key: 'city_center', label: '城市中心点', required: false, accept: '.geojson,.json,.zip', category: '城市结构' }
    ];
    
    // 按类别分组显示
    const categories = {};
    dataTypes.forEach(dt => {
        if (!categories[dt.category]) {
            categories[dt.category] = [];
        }
        categories[dt.category].push(dt);
    });
    
    let html = '';
    for (const [category, items] of Object.entries(categories)) {
        // 检查该分类下是否有已上传数据
        const hasUploaded = items.some(dt => currentProject.data_status[dt.key]);
        const openAttr = hasUploaded ? 'open' : '';
        
        html += `<details style="margin-bottom: 12px; border: 1px solid #eee; border-radius: 6px; overflow: hidden;" ${openAttr}>
            <summary style="cursor: pointer; padding: 10px 12px; background: ${hasUploaded ? '#e8f5e9' : '#f5f5f5'}; font-weight: 500; color: #333; display: flex; align-items: center; gap: 8px;">
                <span style="color: ${hasUploaded ? '#4caf50' : '#999'};">${hasUploaded ? '✓' : '○'}</span>
                <span>${category}</span>
                <span style="font-size: 12px; color: #999; margin-left: auto;">${items.filter(dt => currentProject.data_status[dt.key]).length}/${items.length}</span>
            </summary>
            <div style="padding: 12px; background: white;">`;
        
        items.forEach(dt => {
            html += `
            <div style="margin-bottom: 12px; padding: 8px; border-radius: 4px; background: ${currentProject.data_status[dt.key] ? '#f8fff8' : '#fafafa'};">
                <label style="display: block; margin-bottom: 6px; font-weight: 500;">${dt.label}${dt.required ? ' *' : ''}</label>
                <input type="file" 
                       id="file_${dt.key}" 
                       accept="${dt.accept}"
                       onchange="uploadData('${dt.key}')" 
                       ${currentProject.data_status[dt.key] ? 'disabled' : ''}>
                ${currentProject.data_status[dt.key] ? 
                    '<small style="color: green;">✓ 已上传</small>' : ''}
            </div>`;
        });
        
        html += '</div></details>';
    }
    
    document.getElementById('dataUploadArea').innerHTML = html;
}

async function uploadData(dataType) {
    const fileInput = document.getElementById(`file_${dataType}`);
    const file = fileInput.files[0];
    
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const result = await apiCall(`/api/projects/${currentProject.id}/data/${dataType}`, {
            method: 'POST',
            body: formData
        });
        
        alert(`${dataType}数据上传成功`);
        
        // 刷新项目信息
        const projectResult = await apiCall(`/api/projects/${currentProject.id}`);
        currentProject = projectResult.data;
        showWorkspace();
        
        // 上传成功后自动加载到地图
        await loadDataLayer(dataType);
        
    } catch (error) {
        fileInput.value = '';
    }
}

// === 分析任务 ===

async function startAnalysis(event) {
    event.preventDefault();
    
    // 检查必需数据
    if (!currentProject.data_status.boundary || !currentProject.data_status.poi) {
        alert('请先上传边界和POI数据');
        return;
    }
    
    const params = {
        grid_mode: 'square',
        grid_size: parseInt(document.getElementById('gridSize').value),
        buffer_radius: parseInt(document.getElementById('bufferRadius').value),
        include_terrain: false,
        build_knowledge_graph: true
    };
    
    try {
        const result = await apiCall(`/api/projects/${currentProject.id}/analyze`, {
            method: 'POST',
            body: JSON.stringify(params)
        });
        
        currentTask = result.data.task_id;
        document.getElementById('analyzeBtn').disabled = true;
        document.getElementById('taskProgress').classList.remove('hidden');
        
        // 开始轮询任务状态
        pollTaskStatus();
    } catch (error) {
        // 错误已在apiCall中处理
    }
}

async function pollTaskStatus() {
    if (!currentTask) return;
    
    try {
        const result = await apiCall(`/api/tasks/${currentTask}`);
        const task = result.data;
        
        // 更新进度
        const progressBar = document.getElementById('progressBar');
        const taskMessage = document.getElementById('taskMessage');
        
        progressBar.style.width = task.progress + '%';
        progressBar.textContent = task.progress + '%';
        taskMessage.textContent = task.message;
        
        if (task.status === 'completed') {
            alert('分析完成！');
            document.getElementById('analyzeBtn').disabled = false;
            currentTask = null;
            loadAnalysisResults();
        } else if (task.status === 'failed') {
            alert('分析失败: ' + task.error);
            document.getElementById('analyzeBtn').disabled = false;
            currentTask = null;
        } else {
            // 继续轮询
            setTimeout(pollTaskStatus, 2000);
        }
    } catch (error) {
        currentTask = null;
        document.getElementById('analyzeBtn').disabled = false;
    }
}

// === 结果展示 ===

async function loadAnalysisResults() {
    try {
        const result = await apiCall(`/api/projects/${currentProject.id}/results`);
        const data = result.data;
        
        // 显示结果区域
        document.getElementById('resultsSection').classList.remove('hidden');
        document.getElementById('qaSection').classList.remove('hidden');
        
        // 统计信息
        const stats = data.statistics;
        if (stats) {
            const statsHtml = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">${stats.total_units}</div>
                        <div class="stat-label">单元总数</div>
                    </div>
                    ${Object.entries(stats.function_counts || {}).slice(0, 3).map(([func, count]) => `
                        <div class="stat-card">
                            <div class="stat-value">${count}</div>
                            <div class="stat-label">${func}</div>
                        </div>
                    `).join('')}
                </div>
            `;
            document.getElementById('resultStats').innerHTML = statsHtml;
        }
        
        // 加载GeoJSON到地图（复用 /results 已返回的 geojson，避免重复请求）
        if (data.analysis_status === 'completed') {
            await loadResultsToMap(null, data.geojson);
        }
    } catch (error) {
        // 错误已在apiCall中处理
    }
}

// === 地图操作 ===

function clearMap() {
    Object.values(mapLayers).forEach(layer => {
        if (layer) map.removeLayer(layer);
    });
    mapLayers = { 
        boundary: null, 
        poi: null, 
        roads: null, 
        water_bodies: null, 
        grids: null, 
        results: null 
    };
}

// === 地图可视化 ===

async function loadDataLayer(dataType) {
    try {
        // 从API获取GeoJSON数据
        const result = await apiCall(`/api/projects/${currentProject.id}/data/${dataType}/view`);
        let geojson = result.data;
        
        // WGS-84 → GCJ-02 坐标转换（高德地图使用GCJ-02坐标系）
        geojson = convertGeoJsonCoords(geojson);
        
        // 移除旧图层
        if (mapLayers[dataType]) {
            map.removeLayer(mapLayers[dataType]);
        }
        
        // 根据数据类型渲染不同样式
        switch(dataType) {
            case 'boundary':
                renderBoundaryLayer(geojson);
                break;
            case 'poi':
                renderPOILayer(geojson);
                break;
            case 'roads':
                renderRoadsLayer(geojson);
                break;
            case 'water_bodies':
                renderWaterBodiesLayer(geojson);
                break;
            // 新增图层类型
            case 'ecological_redline':
                renderConstraintLayer(dataType, geojson, '#FF9800', '生态红线');
                break;
            case 'farmland_protection':
                renderConstraintLayer(dataType, geojson, '#8BC34A', '基本农田');
                break;
            case 'built_area':
                renderConstraintLayer(dataType, geojson, '#795548', '建成区');
                break;
            case 'city_center':
                renderConstraintLayer(dataType, geojson, '#F44336', '城市中心');
                break;
            // 栅格类数据（使用边界框表示）
            case 'dem':
            case 'landuse':
            case 'soil_type':
            case 'precipitation':
            case 'flood_risk':
            case 'geological_hazard':
            case 'gdp_density':
                renderRasterLayer(dataType, geojson);
                break;
            default:
                renderDefaultLayer(dataType, geojson);
        }
        
        console.log(`${dataType} 图层加载成功`);
    } catch (error) {
        console.error(`加载${dataType}图层失败:`, error);
    }
}

// 渲染约束条件图层（生态红线、基本农田等）
function renderConstraintLayer(dataType, geojson, color, label) {
    mapLayers[dataType] = L.geoJSON(geojson, {
        style: {
            color: color,
            fillColor: color,
            fillOpacity: 0.3,
            weight: 2,
            dashArray: '5, 5'
        },
        onEachFeature: (feature, layer) => {
            let popupContent = `<div><strong>${label}</strong><br>`;
            if (feature.properties) {
                Object.entries(feature.properties).forEach(([key, value]) => {
                    if (key !== 'geometry' && typeof value !== 'object') {
                        popupContent += `${key}: ${value}<br>`;
                    }
                });
            }
            popupContent += '</div>';
            layer.bindPopup(popupContent);
        }
    }).addTo(map);
}

// 渲染栅格类数据图层（使用边界框 + 图例）
function renderRasterLayer(dataType, geojson) {
    const rasterInfo = {
        dem: { label: '地形(DEM)', color: '#8B4513', unit: 'm' },
        landuse: { label: '土地利用', color: '#228B22', unit: '' },
        soil_type: { label: '土壤类型', color: '#D2691E', unit: '' },
        precipitation: { label: '降水分布', color: '#4169E1', unit: 'mm' },
        flood_risk: { label: '洪涝风险', color: '#DC143C', unit: '' },
        geological_hazard: { label: '地质灾害', color: '#FF4500', unit: '' },
        gdp_density: { label: 'GDP密度', color: '#FFD700', unit: '元/km²' }
    };
    
    const info = rasterInfo[dataType] || { label: dataType, color: '#666', unit: '' };
    
    // 如果有边界信息，创建矩形图层
    if (geojson && geojson.features && geojson.features.length > 0) {
        mapLayers[dataType] = L.geoJSON(geojson, {
            style: {
                color: info.color,
                fillColor: info.color,
                fillOpacity: 0.4,
                weight: 1
            },
            onEachFeature: (feature, layer) => {
                layer.bindPopup(`<div><strong>${info.label}</strong><br>栅格数据层</div>`);
            }
        }).addTo(map);
    } else {
        console.log(`${dataType} 无有效数据`);
    }
}

// 加载项目已存在的数据图层
async function loadExistingDataLayers() {
    if (!currentProject || !currentProject.data_status) {
        return;
    }
    
    // 遍历所有已上传的数据类型
    const dataTypes = Object.keys(currentProject.data_status).filter(
        key => currentProject.data_status[key] && key !== 'results'
    );
    
    for (const dataType of dataTypes) {
        // 如果该类型数据已上传，自动加载到地图
        await loadDataLayer(dataType);
    }
}

function renderBoundaryLayer(geojson) {
    mapLayers.boundary = L.geoJSON(geojson, {
        style: {
            color: '#2196F3',
            weight: 3,
            fillOpacity: 0,
            dashArray: '5, 5'
        }
    }).addTo(map);
    
    // 缩放到边界范围
    map.fitBounds(mapLayers.boundary.getBounds());
}

function renderPOILayer(geojson) {
    // POI分类图标配置
    const poiIcons = {
        '餐饮': '🍽️',
        '学校': '🏫',
        '医院': '🏥',
        '购物': '🛒',
        '公园': '🌳',
        '交通': '🚇',
        '银行': '🏦',
        '其他': '📍'
    };
    
    mapLayers.poi = L.geoJSON(geojson, {
        pointToLayer: (feature, latlng) => {
            const type = feature.properties.type || feature.properties.category || '其他';
            const icon = poiIcons[type] || poiIcons['其他'];
            
            return L.marker(latlng, {
                icon: L.divIcon({
                    html: `<div style="font-size: 20px;">${icon}</div>`,
                    className: 'poi-marker',
                    iconSize: [30, 30]
                })
            });
        },
        onEachFeature: (feature, layer) => {
            const props = feature.properties;
            const popupContent = `
                <strong>${props.name || 'POI'}</strong><br>
                类型: ${props.type || props.category || '未知'}<br>
                ${props.address ? `地址: ${props.address}` : ''}
            `;
            layer.bindPopup(popupContent);
        }
    }).addTo(map);
}

function renderRoadsLayer(geojson) {
    mapLayers.roads = L.geoJSON(geojson, {
        style: feature => {
            const roadType = feature.properties.road_type || feature.properties.type || 'default';
            
            // 根据道路等级设置样式
            const styles = {
                '高速': { color: '#FF5722', weight: 4 },
                '主干道': { color: '#FF9800', weight: 3 },
                '次干道': { color: '#FFC107', weight: 2 },
                'default': { color: '#FFE082', weight: 1 }
            };
            
            return styles[roadType] || styles.default;
        },
        onEachFeature: (feature, layer) => {
            const props = feature.properties;
            const popupContent = `
                <strong>道路</strong><br>
                名称: ${props.name || '未命名'}<br>
                类型: ${props.road_type || props.type || '未知'}
            `;
            layer.bindPopup(popupContent);
        }
    }).addTo(map);
}

function renderWaterBodiesLayer(geojson) {
    mapLayers.water_bodies = L.geoJSON(geojson, {
        style: {
            color: '#03A9F4',
            fillColor: '#81D4FA',
            fillOpacity: 0.5,
            weight: 2
        },
        onEachFeature: (feature, layer) => {
            const props = feature.properties;
            const popupContent = `
                <strong>水体</strong><br>
                名称: ${props.name || '未命名'}
            `;
            layer.bindPopup(popupContent);
        }
    }).addTo(map);
}

function renderDefaultLayer(dataType, geojson) {
    mapLayers[dataType] = L.geoJSON(geojson, {
        style: {
            color: '#9C27B0',
            fillOpacity: 0.3,
            weight: 2
        }
    }).addTo(map);
}

function loadBoundaryToMap(bounds) {
    if (bounds && bounds.length === 4) {
        const [minLng, minLat, maxLng, maxLat] = bounds;
        map.fitBounds([[minLat, minLng], [maxLat, maxLng]]);
    }
}

async function loadResultsToMap(functionType = null, geojsonData = null) {
    try {
        // 优先使用传入的 geojson（/results 已返回）；否则回退到 /results/view
        let geojson = geojsonData;
        if (!geojson) {
            const result = await apiCall(`/api/projects/${currentProject.id}/results/view`);
            geojson = result.data;
        }
        
        // WGS-84 → GCJ-02 坐标转换
        geojson = convertGeoJsonCoords(geojson);
        
        // 清除旧图层
        if (mapLayers.results) {
            map.removeLayer(mapLayers.results);
        }
        
        // 功能颜色映射
        const functionColors = {
            '居住': '#FF6B6B',
            '商业': '#FFA500',
            '办公': '#4ECDC4',
            '工业': '#95A5A6',
            '公共服务': '#A8E6CF',
            '绿地休闲': '#66BB6A',
            '综合': '#9B59B6'
        };
        
        // 获取当前显示的功能类型（如果没指定则使用推荐功能）
        const displayFunction = functionType || 'recommended';
        
        // 添加新图层
        mapLayers.results = L.geoJSON(geojson, {
            style: feature => {
                const props = feature.properties;
                let score, func;
                
                if (displayFunction === 'recommended') {
                    func = props.recommended_function;
                    score = props[`score_${func}`] || 0;
                } else {
                    func = displayFunction;
                    score = props[`score_${displayFunction}`] || 0;
                }
                
                // 根据评分计算颜色深度
                const baseColor = functionColors[func] || '#CCCCCC';
                const opacity = 0.3 + (score * 0.5); // 0.3-0.8之间
                
                return {
                    fillColor: baseColor,
                    fillOpacity: opacity,
                    color: '#333',
                    weight: 1
                };
            },
            onEachFeature: (feature, layer) => {
                const props = feature.properties;
                
                // 构建popup内容
                let popupContent = `
                    <div style="min-width: 200px;">
                        <strong>网格 ${props.unit_id || props.id}</strong><br><br>
                        <strong>推荐功能：</strong> ${props.recommended_function}<br><br>
                        <strong>各功能评分：</strong><br>
                `;
                
                const functions = ['居住', '商业', '办公', '工业', '公共服务', '绿地休闲', '综合'];
                functions.forEach(func => {
                    const score = props[`score_${func}`];
                    if (score !== undefined) {
                        const bar = '█'.repeat(Math.round(score * 10));
                        popupContent += `${func}: ${score.toFixed(2)} ${bar}<br>`;
                    }
                });
                
                popupContent += `</div>`;
                layer.bindPopup(popupContent);
            }
        }).addTo(map);
        
        // 调整视图
        if (mapLayers.results.getBounds().isValid()) {
            map.fitBounds(mapLayers.results.getBounds());
        }
        
        console.log('分析结果图层加载成功');
    } catch (error) {
        console.error('加载分析结果图层失败:', error);
    }
}

// === 知识问答 ===

// 问题模板
const QUESTION_TEMPLATES = [
    { text: '为什么单元 U_0_0 适合居住功能？', icon: '🏠' },
    { text: '哪些区域适合商业开发？', icon: '🛒' },
    { text: '对比单元 U_0_0 和 U_1_1 的办公适宜性', icon: '📊' },
    { text: '哪些区域适合建设公园？', icon: '🌳' },
    { text: '工业用地适宜性最高的区域在哪里？', icon: '🏭' }
];

// 显示问题模板
function showQuestionTemplates() {
    const messagesEl = document.getElementById('qaMessages');
    if (messagesEl.children.length > 0) return; // 已有消息时不显示模板
    
    let templatesHtml = '<div class="question-templates"><p style="color: #666; font-size: 12px; margin-bottom: 8px;">快捷问题：</p>';
    QUESTION_TEMPLATES.forEach((template, index) => {
        templatesHtml += `<button onclick="fillQuestion('${template.text}')" style="display: block; width: 100%; text-align: left; padding: 8px; margin-bottom: 4px; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer; font-size: 12px;">${template.icon} ${template.text}</button>`;
    });
    templatesHtml += '</div>';
    messagesEl.innerHTML = templatesHtml;
}

// 填充问题
function fillQuestion(question) {
    document.getElementById('qaInput').value = question;
}

async function askQuestion() {
    const input = document.getElementById('qaInput');
    const question = input.value.trim();
    
    if (!question) return;
    
    try {
        const result = await apiCall(`/api/projects/${currentProject.id}/qa`, {
            method: 'POST',
            body: JSON.stringify({ question })
        });
        
        const data = result.data;
        
        // 显示问答
        const messagesEl = document.getElementById('qaMessages');
        // 清除模板
        messagesEl.innerHTML = '';
        
        const messageHtml = `
            <div class="qa-message">
                <div class="qa-question">Q: ${data.question}</div>
                <div class="qa-answer">A: ${data.answer}</div>
            </div>
        `;
        messagesEl.innerHTML += messageHtml;
        messagesEl.scrollTop = messagesEl.scrollHeight;
        
        // 清空输入
        input.value = '';
    } catch (error) {
        // 错误已在apiCall中处理
    }
}

// 初始化时显示问题模板
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(showQuestionTemplates, 100);
});

// === 图层控制 ===

function toggleLayerControl() {
    const control = document.getElementById('layerControl');
    control.classList.toggle('hidden');
}

async function toggleLayer(layerName) {
    const checkbox = document.getElementById(`layer_${layerName}`);
    
    if (checkbox.checked) {
        // 如果图层已加载，直接显示
        if (mapLayers[layerName]) {
            map.addLayer(mapLayers[layerName]);
        } else {
            // 懒加载：首次显示时加载数据
            await loadLayerData(layerName);
        }
    } else {
        // 隐藏图层
        if (mapLayers[layerName]) {
            map.removeLayer(mapLayers[layerName]);
        }
    }
}

async function loadLayerData(layerName) {
    if (!currentProject) {
        alert('请先选择项目');
        return;
    }
    
    const config = LAYER_CONFIG[layerName];
    if (!config) {
        console.warn(`未知图层类型: ${layerName}`);
        return;
    }
    
    try {
        const endpoint = `/api/projects/${currentProject.id}/data/${config.endpoint}`;
        const result = await apiCall(endpoint);
        let geojson = result.data;
        
        // WGS-84 → GCJ-02 坐标转换
        geojson = convertGeoJsonCoords(geojson);
        
        if (!geojson || !geojson.features || geojson.features.length === 0) {
            console.log(`${layerName} 图层无数据`);
            return;
        }
        
        // 根据图层类型创建不同的样式
        if (config.type === 'vector') {
            mapLayers[layerName] = L.geoJSON(geojson, {
                style: {
                    color: config.color || '#333',
                    weight: config.weight || 1,
                    fillColor: config.color || '#333',
                    fillOpacity: config.fillOpacity || 0.5,
                    dashArray: config.dashArray || null
                },
                onEachFeature: (feature, layer) => {
                    // 添加弹出窗口
                    let popupContent = `<div><strong>${layerName}</strong><br>`;
                    if (feature.properties) {
                        Object.entries(feature.properties).forEach(([key, value]) => {
                            if (key !== 'geometry' && typeof value !== 'object') {
                                popupContent += `${key}: ${value}<br>`;
                            }
                        });
                    }
                    popupContent += '</div>';
                    layer.bindPopup(popupContent);
                }
            }).addTo(map);
        } else if (config.type === 'raster') {
            // 栅格图层处理 - 使用边界框显示
            if (geojson.bbox) {
                const bounds = [
                    [geojson.bbox[1], geojson.bbox[0]],
                    [geojson.bbox[3], geojson.bbox[2]]
                ];
                
                // 创建临时图片图层（实际项目中应使用真实栅格服务）
                mapLayers[layerName] = L.rectangle(bounds, {
                    color: config.color || '#666',
                    weight: 1,
                    fillOpacity: 0.3,
                    dashArray: '5,5'
                }).addTo(map);
                
                mapLayers[layerName].bindPopup(`<div><strong>${layerName}</strong><br>栅格数据层</div>`);
            }
        }
        
        loadedLayers.add(layerName);
        console.log(`${layerName} 图层加载成功`);
    } catch (error) {
        console.error(`加载 ${layerName} 图层失败:`, error);
    }
}

async function changeResultFunction() {
    const select = document.getElementById('resultFunctionType');
    const functionType = select.value === 'recommended' ? null : select.value;
    await loadResultsToMap(functionType);
}