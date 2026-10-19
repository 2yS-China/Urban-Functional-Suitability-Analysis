"""
知识图谱可视化模块

生成交互式网页版知识图谱，支持：
1. 节点颜色编码（按类型）
2. 关系类型可视化
3. 交互式缩放、拖拽
4. 节点详情查看
"""

from pyvis.network import Network
import networkx as nx
from pathlib import Path
from typing import Optional, Dict, List
from kg.knowledge_graph_builder import KnowledgeGraphBuilder, NodeType, RelationType


class KnowledgeGraphVisualizer:
    """知识图谱可视化器"""
    
    # 节点颜色配置
    NODE_COLORS = {
        NodeType.UNIT: '#4A90E2',      # 蓝色 - 单元节点
        NodeType.FUNCTION: '#E24A4A',  # 红色 - 功能节点
        NodeType.FEATURE: '#4AE290',   # 绿色 - 要素节点
    }
    
    # 关系颜色配置
    RELATION_COLORS = {
        RelationType.ADJACENT: '#CCCCCC',        # 灰色 - 相邻
        RelationType.SUITABLE_FOR: '#4AE24A',    # 绿色 - 适宜
        RelationType.DOMINATED_BY: '#E2A04A',    # 橙色 - 主导
        RelationType.SIMILAR_TO: '#A04AE2',      # 紫色 - 相似
        RelationType.CONTAINS: '#4AC8E2',        # 青色 - 包含
        RelationType.NEAR: '#E24AC8',            # 粉色 - 邻近
    }
    
    # 节点大小配置
    NODE_SIZES = {
        NodeType.UNIT: 15,
        NodeType.FUNCTION: 30,
        NodeType.FEATURE: 20,
    }
    
    def __init__(self, kg: KnowledgeGraphBuilder):
        """
        初始化可视化器
        
        Args:
            kg: 知识图谱构建器实例
        """
        self.kg = kg
        
    def create_interactive_html(
        self,
        output_path: str,
        title: str = "城市功能适宜性知识图谱",
        height: str = "800px",
        width: str = "100%",
        physics_enabled: bool = True,
        show_buttons: bool = True,
        filter_relation_types: Optional[List[RelationType]] = None,
        max_units: Optional[int] = 50
    ) -> str:
        """
        生成交互式HTML可视化
        
        Args:
            output_path: 输出HTML文件路径
            title: 图谱标题
            height: 画布高度
            width: 画布宽度
            physics_enabled: 是否启用物理引擎（自动布局）
            show_buttons: 是否显示控制按钮
            filter_relation_types: 要显示的关系类型列表（None表示全部）
            max_units: 最多显示的单元节点数（避免图谱过大）
            
        Returns:
            生成的HTML文件路径
        """
        # 创建pyvis网络对象
        net = Network(
            height=height,
            width=width,
            bgcolor="#ffffff",
            font_color="black",
            directed=True,
            notebook=False
        )
        
        # 设置物理引擎
        if physics_enabled:
            # 启用物理引擎进行初始布局，稳定后自动禁用
            net.set_options("""
            {
                "physics": {
                    "enabled": true,
                    "barnesHut": {
                        "gravitationalConstant": -8000,
                        "centralGravity": 0.3,
                        "springLength": 150,
                        "springConstant": 0.04,
                        "damping": 0.09,
                        "avoidOverlap": 0.5
                    },
                    "minVelocity": 0.1,
                    "stabilization": {
                        "enabled": true,
                        "iterations": 500,
                        "fit": true
                    }
                },
                "nodes": {
                    "font": {
                        "size": 14,
                        "face": "Arial"
                    },
                    "borderWidth": 2,
                    "borderWidthSelected": 4
                },
                "edges": {
                    "width": 2,
                    "arrows": {
                        "to": {
                            "enabled": true,
                            "scaleFactor": 0.5
                        }
                    },
                    "smooth": {
                        "enabled": true,
                        "type": "dynamic"
                    }
                },
                "interaction": {
                    "hover": true,
                    "tooltipDelay": 100,
                    "hideEdgesOnDrag": false,
                    "hideEdgesOnZoom": false
                }
            }
            """)
        else:
            # 完全禁用物理引擎，使用静态布局
            net.set_options("""
            {
                "physics": {
                    "enabled": false
                },
                "nodes": {
                    "font": {
                        "size": 14,
                        "face": "Arial"
                    },
                    "borderWidth": 2,
                    "borderWidthSelected": 4
                },
                "edges": {
                    "width": 2,
                    "arrows": {
                        "to": {
                            "enabled": true,
                            "scaleFactor": 0.5
                        }
                    },
                    "smooth": {
                        "enabled": true,
                        "type": "continuous"
                    }
                },
                "interaction": {
                    "hover": true,
                    "tooltipDelay": 100,
                    "dragNodes": true,
                    "dragView": true,
                    "zoomView": true
                }
            }
            """)
        
        # 添加节点
        unit_count = 0
        for node in self.kg.nodes.values():
            node_type = node.type
            
            # 限制单元节点数量
            if node_type == NodeType.UNIT:
                if max_units and unit_count >= max_units:
                    continue
                unit_count += 1
            
            # 节点颜色和大小
            color = self.NODE_COLORS.get(node_type, '#999999')
            size = self.NODE_SIZES.get(node_type, 15)
            
            # 节点标签
            label = self._get_node_label(node)
            
            # 节点标题（鼠标悬停显示）
            title = self._get_node_tooltip(node)
            
            net.add_node(
                node.id,
                label=label,
                title=title,
                color=color,
                size=size,
                shape='dot' if node_type == NodeType.UNIT else 'box'
            )
        
        # 获取已添加的节点ID集合
        added_node_ids = set(net.get_nodes())
        
        # 添加边（关系）
        for rel in self.kg.relations:
            rel_type = rel.relation_type
            
            # 过滤关系类型
            if filter_relation_types and rel_type not in filter_relation_types:
                continue
            
            # 确保两端节点都存在
            if rel.source not in added_node_ids or rel.target not in added_node_ids:
                continue
            
            # 关系颜色
            color = self.RELATION_COLORS.get(rel_type, '#999999')
            
            # 关系标签
            label = self._get_relation_label(rel)
            
            # 关系标题
            title = self._get_relation_tooltip(rel)
            
            net.add_edge(
                rel.source,
                rel.target,
                title=title,
                label=label,
                color=color,
                width=1 if rel_type == RelationType.ADJACENT else 2
            )
        
        # 添加控制按钮（pyvis版本兼容性问题，暂时禁用）
        # if show_buttons:
        #     net.show_buttons(filter_=['physics', 'nodes', 'edges'])
        
        # 保存HTML
        output_path = str(Path(output_path).resolve())
        net.save_graph(output_path)
        
        # 添加自定义样式和图例
        self._add_custom_styles(output_path, title)
        
        return output_path
    
    def _get_node_label(self, node) -> str:
        """生成节点标签"""
        node_type = node.type
        
        if node_type == NodeType.UNIT:
            # 单元节点：显示ID（简化）
            unit_id = node.id
            # 如果是U_X_Y格式，提取后缀
            if unit_id.startswith('U_'):
                parts = unit_id.split('_')
                if len(parts) >= 3:
                    return f"{parts[1]},{parts[2]}"
            return unit_id
        
        elif node_type == NodeType.FUNCTION:
            # 功能节点：显示功能名称
            return node.properties.get('name', node.id)
        
        elif node_type == NodeType.FEATURE:
            # 要素节点：显示要素名称
            return node.properties.get('name', node.id)
        
        return node.id
    
    def _get_node_tooltip(self, node) -> str:
        """生成节点鼠标悬停提示"""
        node_type = node.type
        props = node.properties
        
        if node_type == NodeType.UNIT:
            # 单元节点提示
            lines = [
                f"<b>单元ID:</b> {node.id}",
                f"<b>面积:</b> {props.get('area', 0):.2f} m²",
            ]
            
            # 中心点
            centroid = props.get('centroid', {})
            if isinstance(centroid, dict):
                lines.append(f"<b>中心点:</b> ({centroid.get('lon', 0):.6f}, {centroid.get('lat', 0):.6f})")
            
            # 显示推荐功能
            if 'recommended_function' in props:
                lines.append(f"<b>推荐功能:</b> {props['recommended_function']}")
            
            # 显示部分特征
            features = props.get('features', {})
            if features:
                lines.append("<b>关键特征:</b>")
                for key, value in list(features.items())[:3]:
                    lines.append(f"  • {key}: {value:.3f}")
            
            return "<br>".join(lines)
        
        elif node_type == NodeType.FUNCTION:
            # 功能节点提示
            lines = [
                f"<b>功能类型:</b> {props.get('name', node.id)}",
                f"<b>描述:</b> {props.get('description', '城市功能类型')}",
            ]
            return "<br>".join(lines)
        
        elif node_type == NodeType.FEATURE:
            # 要素节点提示
            lines = [
                f"<b>要素:</b> {props.get('name', node.id)}",
                f"<b>类别:</b> {props.get('category', '未知')}",
            ]
            return "<br>".join(lines)
        
        return node.id
    
    def _get_relation_label(self, rel) -> str:
        """生成关系标签"""
        rel_type = rel.relation_type
        
        # 只为某些关系类型显示标签
        if rel_type == RelationType.SUITABLE_FOR:
            props = rel.properties or {}
            score = props.get('score', 0)
            return f"{score:.2f}"
        
        return ""
    
    def _get_relation_tooltip(self, rel) -> str:
        """生成关系鼠标悬停提示"""
        rel_type = rel.relation_type
        props = rel.properties or {}
        
        type_names = {
            RelationType.ADJACENT: "相邻关系",
            RelationType.SUITABLE_FOR: "适宜性关系",
            RelationType.DOMINATED_BY: "主导关系",
            RelationType.SIMILAR_TO: "相似关系",
            RelationType.CONTAINS: "包含关系",
            RelationType.NEAR: "邻近关系",
        }
        
        lines = [
            f"<b>关系类型:</b> {type_names.get(rel_type, rel_type.value)}",
            f"<b>起点:</b> {rel.source}",
            f"<b>终点:</b> {rel.target}",
        ]
        
        # 添加特定属性
        if rel_type == RelationType.SUITABLE_FOR:
            score = props.get('score', 0)
            level = props.get('level', '未知')
            lines.append(f"<b>适宜性得分:</b> {score:.3f}")
            lines.append(f"<b>适宜性等级:</b> {level}")
        
        elif rel_type == RelationType.SIMILAR_TO:
            similarity = props.get('similarity', 0)
            lines.append(f"<b>相似度:</b> {similarity:.3f}")
        
        return "<br>".join(lines)
    
    def _add_custom_styles(self, html_path: str, title: str):
        """添加自定义样式和图例"""
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 添加标题和图例
        legend_html = f"""
        <div style="position: absolute; top: 10px; left: 10px; background: white; 
                    padding: 15px; border: 2px solid #ddd; border-radius: 8px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1); z-index: 1000; 
                    font-family: Arial, sans-serif;">
            <h2 style="margin: 0 0 15px 0; font-size: 18px; color: #333;">{title}</h2>
            
            <div style="margin-bottom: 15px;">
                <h3 style="font-size: 14px; margin: 0 0 8px 0; color: #666;">节点类型</h3>
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <div style="width: 12px; height: 12px; background: {self.NODE_COLORS[NodeType.UNIT]}; 
                                border-radius: 50%; margin-right: 8px;"></div>
                    <span style="font-size: 12px;">单元节点</span>
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <div style="width: 12px; height: 12px; background: {self.NODE_COLORS[NodeType.FUNCTION]}; 
                                margin-right: 8px;"></div>
                    <span style="font-size: 12px;">功能节点</span>
                </div>
                <div style="display: flex; align-items: center;">
                    <div style="width: 12px; height: 12px; background: {self.NODE_COLORS[NodeType.FEATURE]}; 
                                border-radius: 50%; margin-right: 8px;"></div>
                    <span style="font-size: 12px;">要素节点</span>
                </div>
            </div>
            
            <div>
                <h3 style="font-size: 14px; margin: 0 0 8px 0; color: #666;">关系类型</h3>
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <div style="width: 20px; height: 2px; background: {self.RELATION_COLORS[RelationType.SUITABLE_FOR]}; 
                                margin-right: 8px;"></div>
                    <span style="font-size: 12px;">适宜性</span>
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <div style="width: 20px; height: 2px; background: {self.RELATION_COLORS[RelationType.DOMINATED_BY]}; 
                                margin-right: 8px;"></div>
                    <span style="font-size: 12px;">主导</span>
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <div style="width: 20px; height: 2px; background: {self.RELATION_COLORS[RelationType.SIMILAR_TO]}; 
                                margin-right: 8px;"></div>
                    <span style="font-size: 12px;">相似</span>
                </div>
                <div style="display: flex; align-items: center;">
                    <div style="width: 20px; height: 2px; background: {self.RELATION_COLORS[RelationType.ADJACENT]}; 
                                margin-right: 8px;"></div>
                    <span style="font-size: 12px;">相邻</span>
                </div>
            </div>
            
            <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #eee; 
                        font-size: 11px; color: #999;">
                提示：拖拽节点、滚轮缩放、点击查看详情
            </div>
        </div>
        """
        
        # 在body标签后插入图例
        content = content.replace('<body>', f'<body>\n{legend_html}')
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(content)