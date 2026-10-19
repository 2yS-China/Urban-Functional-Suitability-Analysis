/**
 * 地图管理模块
 */

const MapManager = {
    map: null,
    layers: {
        boundary: null,
        results: null,
        selected: null
    },

    init(containerId = 'map') {
        // 初始化地图
        this.map = L.map(containerId, {
            center: [23.1291, 113.2644], // 默认广州
            zoom: 12,
            zoomControl: true
        });

        // 添加底图
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(this.map);

        return this.map;
    },

    // 添加边界图层
    addBoundary(geojson) {
        if (this.layers.boundary) {
            this.map.removeLayer(this.layers.boundary);
        }

        this.layers.boundary = L.geoJSON(geojson, {
            style: {
                color: '#2c3e50',
                weight: 2,
                fillOpacity: 0.1
            }
        }).addTo(this.map);

        // 自动缩放到边界范围
        this.map.fitBounds(this.layers.boundary.getBounds());
    },

    // 显示分析结果
    showResults(geojson) {
        if (this.layers.results) {
            this.map.removeLayer(this.layers.results);
        }

        // 功能颜色映射
        const functionColors = {
            '居住': '#e74c3c',
            '商业': '#f39c12',
            '办公': '#3498db',
            '工业': '#95a5a6',
            '公共服务': '#9b59b6',
            '公园绿地': '#27ae60',
            '交通枢纽': '#34495e'
        };

        this.layers.results = L.geoJSON(geojson, {
            style: (feature) => {
                const func = feature.properties.recommended_function;
                return {
                    fillColor: functionColors[func] || '#bdc3c7',
                    fillOpacity: 0.6,
                    color: '#fff',
                    weight: 1
                };
            },
            onEachFeature: (feature, layer) => {
                const props = feature.properties;
                const func = props.recommended_function;
                const score = props[`${func}_score`];
                
                // 添加点击事件
                layer.on('click', () => {
                    this.selectUnit(feature);
                });

                // 添加悬停提示 - 包含适宜性等级信息
                const suitabilityLevel = props.suitability_level || 'unknown';
                const suitabilityLabel = props.suitability_label || '未知';
                const dataCompleteness = props.data_completeness ? (props.data_completeness * 100).toFixed(0) : 'N/A';
                
                // 根据等级设置颜色标识
                let levelColor = '#999';
                if (suitabilityLevel === 'suitable') levelColor = '#27ae60';
                else if (suitabilityLevel === 'moderate') levelColor = '#f39c12';
                else if (suitabilityLevel === 'unsuitable') levelColor = '#e74c3c';
                
                layer.bindTooltip(
                    `<b>单元ID:</b> ${props.unit_id}<br>` +
                    `<b>推荐功能:</b> ${func}<br>` +
                    `<b>适宜性得分:</b> ${score ? score.toFixed(2) : 'N/A'}<br>` +
                    `<b>适宜性等级:</b> <span style="color:${levelColor};font-weight:bold">${suitabilityLabel}</span><br>` +
                    `<b>数据完整性:</b> ${dataCompleteness}%`,
                    { sticky: true }
                );
            }
        }).addTo(this.map);

        // 更新图例
        this.updateLegend(functionColors, geojson);

        // 自动缩放
        this.map.fitBounds(this.layers.results.getBounds());
    },

    // 选中单元
    selectUnit(feature) {
        if (this.layers.selected) {
            this.map.removeLayer(this.layers.selected);
        }

        this.layers.selected = L.geoJSON(feature, {
            style: {
                color: '#f1c40f',
                weight: 3,
                fillOpacity: 0
            }
        }).addTo(this.map);

        // 触发自定义事件
        const event = new CustomEvent('unitSelected', {
            detail: feature.properties
        });
        document.dispatchEvent(event);
    },

    // 更新图例
    updateLegend(functionColors, geojson) {
        const legendDiv = document.getElementById('map-legend');
        const itemsDiv = document.getElementById('legend-items');
        
        // 获取实际出现的功能类型
        const functions = new Set();
        geojson.features.forEach(f => {
            functions.add(f.properties.recommended_function);
        });

        itemsDiv.innerHTML = '';
        functions.forEach(func => {
            const item = document.createElement('div');
            item.className = 'legend-item';
            item.innerHTML = `
                <div class="legend-color" style="background: ${functionColors[func]}"></div>
                <span>${func}</span>
            `;
            itemsDiv.appendChild(item);
        });

        legendDiv.style.display = 'block';
    },

    // 清除所有图层
    clearLayers() {
        Object.values(this.layers).forEach(layer => {
            if (layer) {
                this.map.removeLayer(layer);
            }
        });
        this.layers = {
            boundary: null,
            results: null,
            selected: null
        };
        document.getElementById('map-legend').style.display = 'none';
    }
};