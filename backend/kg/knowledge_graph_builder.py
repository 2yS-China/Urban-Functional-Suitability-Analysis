"""
城市片区功能适宜性分析 - 知识图谱构建模块

核心职责：
1. 将 GIS 空间分析结果转化为结构化知识图谱
2. 支持空间关系、适宜性关系、要素关系的表达
3. 提供灵活的图查询接口
"""

import json
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


# ============ 图谱节点定义 ============

class NodeType(Enum):
    """节点类型枚举"""
    UNIT = "unit"              # 分析单元（网格/地块）
    FEATURE = "feature"        # 空间要素（POI、交通设施等）
    FUNCTION = "function"      # 功能类型（居住、商业等）
    REGION = "region"          # 片区整体
    POI = "poi"               # POI实体（具体的地铁站、商场等）
    INFRASTRUCTURE = "infra"   # 基础设施线路（地铁线、公交线）
    RULE = "rule"             # 评价规则节点
    CONSTRAINT = "constraint"  # 约束节点（生态红线、基本农田、灾害风险等）


@dataclass
class Node:
    """通用节点结构"""
    id: str
    type: NodeType
    properties: Dict[str, Any]
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type.value,
            'properties': self.properties
        }


@dataclass
class UnitNode(Node):
    """分析单元节点"""
    def __init__(self, unit_id: str, geometry: Any, area: float, 
                 centroid: Tuple[float, float], features: Dict[str, float]):
        super().__init__(
            id=unit_id,
            type=NodeType.UNIT,
            properties={
                'geometry': self._geometry_to_geojson(geometry),
                'area': area,
                'centroid': {'lon': centroid[0], 'lat': centroid[1]},
                'features': features  # 空间特征向量
            }
        )
    
    @staticmethod
    def _geometry_to_geojson(geometry):
        """将 Shapely 几何转为 GeoJSON"""
        return json.loads(json.dumps(geometry.__geo_interface__))


@dataclass
class FeatureNode(Node):
    """空间要素节点（POI、交通设施等）"""
    def __init__(self, feature_id: str, feature_type: str, 
                 location: Tuple[float, float], properties: Dict[str, Any]):
        super().__init__(
            id=feature_id,
            type=NodeType.FEATURE,
            properties={
                'feature_type': feature_type,  # 'metro', 'bus', 'poi_商业' 等
                'location': {'lon': location[0], 'lat': location[1]},
                **properties
            }
        )


@dataclass
class FunctionNode(Node):
    """功能类型节点"""
    def __init__(self, function_type: str, description: str, criteria: Dict):
        super().__init__(
            id=f"func_{function_type}",
            type=NodeType.FUNCTION,
            properties={
                'function_type': function_type,
                'description': description,
                'criteria': criteria  # 适宜性评价准则
            }
        )


@dataclass
class POINode(Node):
    """POI实体节点（具体的地铁站、商场等）"""
    def __init__(self, poi_id: str, category: str, name: str, 
                 location: Tuple[float, float], attributes: Dict[str, Any] = None):
        super().__init__(
            id=poi_id,
            type=NodeType.POI,
            properties={
                'category': category,  # '地铁站', '公交站', '商场', '学校'
                'name': name,
                'location': {'lon': location[0], 'lat': location[1]},
                'attributes': attributes or {}  # 扩展属性（地铁线路、服务范围等）
            }
        )


@dataclass
class ConstraintNode(Node):
    """约束节点（生态红线、基本农田、灾害风险、水体等）"""
    def __init__(self, constraint_id: str, constraint_type: str, 
                 severity: str, description: str, affected_functions: List[str]):
        super().__init__(
            id=constraint_id,
            type=NodeType.CONSTRAINT,
            properties={
                'constraint_type': constraint_type,  # 'ecological_redline', 'farmland', 'flood_risk', 'geological_hazard', 'water_body'
                'severity': severity,  # 'strict'(严格禁止), 'strong'(强约束), 'moderate'(中度), 'soft'(软约束)
                'description': description,
                'affected_functions': affected_functions  # 受影响的功能类型列表
            }
        )


@dataclass
class InfrastructureNode(Node):
    """基础设施线路节点（地铁线、公交线）"""
    def __init__(self, infra_id: str, infra_type: str, name: str, 
                 stations: List[str], key_areas: List[str]):
        super().__init__(
            id=infra_id,
            type=NodeType.INFRASTRUCTURE,
            properties={
                'infra_type': infra_type,  # 'metro', 'bus', 'highway'
                'name': name,
                'stations': stations,  # 站点/节点列表
                'key_areas': key_areas  # 连接的关键区域 ['CBD', '高新区']
            }
        )


@dataclass
class RuleNode(Node):
    """评价规则节点"""
    def __init__(self, rule_id: str, feature_name: str, threshold: float, 
                 direction: str, description: str):
        super().__init__(
            id=rule_id,
            type=NodeType.RULE,
            properties={
                'feature_name': feature_name,  # 'dist_to_metro'
                'threshold': threshold,         # 800
                'direction': direction,         # 'minimize' / 'maximize'
                'description': description      # '居住功能要求800m内有地铁'
            }
        )


# ============ 图谱关系定义 ============

class RelationType(Enum):
    """关系类型枚举"""
    ADJACENT = "相邻"           # 单元之间的相邻关系
    CONTAINS = "包含"           # 单元包含要素
    NEAR = "邻近"              # 单元邻近要素（一定距离内）
    SUITABLE_FOR = "适宜"      # 单元适宜某功能
    DOMINATED_BY = "主导功能"   # 单元的主导功能
    SIMILAR_TO = "相似"        # 单元之间的特征相似
    SERVES_BY = "服务于"       # POI由基础设施服务
    CONNECTS_TO = "连接到"     # 基础设施连接到区域
    SATISFIES = "满足"         # 单元满足规则
    REQUIRES = "要求"          # 功能要求准则
    CONSTRAINED_BY = "受约束"  # 单元受约束影响
    CONFLICTS_WITH = "冲突"    # 功能与约束冲突


@dataclass
class Relation:
    """通用关系结构"""
    source: str              # 源节点 ID
    target: str              # 目标节点 ID
    relation_type: RelationType
    weight: float           # 关系权重/强度
    properties: Dict[str, Any] = None
    
    def to_dict(self):
        return {
            'source': self.source,
            'target': self.target,
            'relation_type': self.relation_type.value,
            'weight': self.weight,
            'properties': self.properties or {}
        }


# ============ 知识图谱核心类 ============

class SpatialKnowledgeGraph:
    """
    空间分析知识图谱
    
    图谱结构：
    - nodes: {node_id: Node}
    - relations: [(source, target, relation_type, weight, properties)]
    - index: 多种索引加速查询
    """
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.relations: List[Relation] = []
        
        # 索引结构（加速查询）
        self._index = {
            'by_type': {},           # 按节点类型索引
            'outgoing': {},          # 出边索引：node_id -> [relations]
            'incoming': {},          # 入边索引：node_id -> [relations]
            'by_relation_type': {}   # 按关系类型索引
        }
    
    # ===== 节点操作 =====
    
    def add_node(self, node: Node):
        """添加节点"""
        self.nodes[node.id] = node
        
        # 更新类型索引
        node_type = node.type.value
        if node_type not in self._index['by_type']:
            self._index['by_type'][node_type] = []
        self._index['by_type'][node_type].append(node.id)
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """获取节点"""
        return self.nodes.get(node_id)
    
    def get_nodes_by_type(self, node_type: NodeType) -> List[Node]:
        """获取指定类型的所有节点"""
        node_ids = self._index['by_type'].get(node_type.value, [])
        return [self.nodes[nid] for nid in node_ids]
    
    # ===== 关系操作 =====
    
    def add_relation(self, relation: Relation):
        """添加关系"""
        self.relations.append(relation)
        
        # 更新出边索引
        if relation.source not in self._index['outgoing']:
            self._index['outgoing'][relation.source] = []
        self._index['outgoing'][relation.source].append(relation)
        
        # 更新入边索引
        if relation.target not in self._index['incoming']:
            self._index['incoming'][relation.target] = []
        self._index['incoming'][relation.target].append(relation)
        
        # 更新关系类型索引
        rel_type = relation.relation_type.value
        if rel_type not in self._index['by_relation_type']:
            self._index['by_relation_type'][rel_type] = []
        self._index['by_relation_type'][rel_type].append(relation)
    
    def get_outgoing_relations(self, node_id: str, 
                               relation_type: Optional[RelationType] = None) -> List[Relation]:
        """获取节点的出边"""
        relations = self._index['outgoing'].get(node_id, [])
        if relation_type:
            relations = [r for r in relations if r.relation_type == relation_type]
        return relations
    
    def get_incoming_relations(self, node_id: str,
                               relation_type: Optional[RelationType] = None) -> List[Relation]:
        """获取节点的入边"""
        relations = self._index['incoming'].get(node_id, [])
        if relation_type:
            relations = [r for r in relations if r.relation_type == relation_type]
        return relations
    
    def get_neighbors(self, node_id: str, relation_type: Optional[RelationType] = None) -> List[str]:
        """获取邻居节点 ID"""
        outgoing = self.get_outgoing_relations(node_id, relation_type)
        return [r.target for r in outgoing]
    
    # ===== 图查询 =====
    
    def find_suitable_units(self, function_type: str, min_score: float = 0.6) -> List[Tuple[str, float]]:
        """
        查询适合某功能的单元
        返回: [(unit_id, score)]
        """
        relations = self._index['by_relation_type'].get(RelationType.SUITABLE_FOR.value, [])
        
        results = []
        for rel in relations:
            if rel.target == f"func_{function_type}" and rel.weight >= min_score:
                results.append((rel.source, rel.weight))
        
        # 按得分排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def find_nearby_features(self, unit_id: str, feature_type: str, max_distance: float = 500) -> List[Dict]:
        """
        查询单元周边的要素
        """
        relations = self.get_outgoing_relations(unit_id, RelationType.NEAR)
        
        nearby = []
        for rel in relations:
            feature_node = self.get_node(rel.target)
            if (feature_node and 
                feature_node.properties.get('feature_type') == feature_type and
                rel.properties.get('distance', float('inf')) <= max_distance):
                nearby.append({
                    'feature_id': rel.target,
                    'distance': rel.properties['distance'],
                    'properties': feature_node.properties
                })
        
        # 按距离排序
        nearby.sort(key=lambda x: x['distance'])
        return nearby
    
    def get_unit_dominant_function(self, unit_id: str) -> Optional[str]:
        """获取单元的主导功能"""
        relations = self.get_outgoing_relations(unit_id, RelationType.DOMINATED_BY)
        if relations:
            return relations[0].target.replace('func_', '')
        return None
    
    def get_adjacent_units(self, unit_id: str) -> List[str]:
        """获取相邻单元"""
        return self.get_neighbors(unit_id, RelationType.ADJACENT)
    
    # ===== 序列化 =====
    
    def to_dict(self) -> Dict:
        """导出为字典"""
        return {
            'nodes': [node.to_dict() for node in self.nodes.values()],
            'relations': [rel.to_dict() for rel in self.relations],
            'statistics': {
                'node_count': len(self.nodes),
                'relation_count': len(self.relations),
                'node_types': {k: len(v) for k, v in self._index['by_type'].items()},
                'relation_types': {k: len(v) for k, v in self._index['by_relation_type'].items()}
            }
        }
    
    def save_to_file(self, filepath: str):
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'SpatialKnowledgeGraph':
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        kg = cls()
        
        # 重建节点
        for node_data in data['nodes']:
            node = Node(
                id=node_data['id'],
                type=NodeType(node_data['type']),
                properties=node_data['properties']
            )
            kg.add_node(node)
        
        # 重建关系
        for rel_data in data['relations']:
            relation = Relation(
                source=rel_data['source'],
                target=rel_data['target'],
                relation_type=RelationType(rel_data['relation_type']),
                weight=rel_data['weight'],
                properties=rel_data.get('properties')
            )
            kg.add_relation(relation)
        
        return kg


# ============ 知识图谱构建器 ============

class KnowledgeGraphBuilder:
    """
    从 GIS 分析结果构建知识图谱
    """
    
    def __init__(self):
        self.kg = SpatialKnowledgeGraph()
    
    def build(self, units_gdf, features_dict, suitability_matrix, 
              recommendations, function_rules) -> SpatialKnowledgeGraph:
        """
        完整构建流程
        
        参数:
            units_gdf: GeoDataFrame，分析单元
            features_dict: Dict，每个单元的特征向量 {unit_id: {feature_name: value}}
            suitability_matrix: Dict，适宜性得分 {unit_id: {function: score}}
            recommendations: Dict，功能推荐结果 {unit_id: function}
            function_rules: Dict，功能评价规则配置
        """
        print("构建知识图谱...")
        
        # 1. 添加单元节点
        self._add_unit_nodes(units_gdf, features_dict)
        
        # 2. 添加功能节点
        self._add_function_nodes(function_rules)
        
        # 3. 添加空间要素节点（如果有独立的要素数据）
        # self._add_feature_nodes(poi_data, metro_data)
        
        # 4. 构建空间关系（相邻）
        self._build_adjacency_relations(units_gdf)
        
        # 5. 构建适宜性关系
        self._build_suitability_relations(suitability_matrix)
        
        # 6. 构建主导功能关系
        self._build_dominant_function_relations(recommendations)
        
        # 7. 构建特征相似关系(可选，Top-K策略避免关系爆炸)
        self._build_similarity_relations(features_dict, threshold=0.95, top_k=3)
        
        print(f"图谱构建完成: {len(self.kg.nodes)} 个节点, {len(self.kg.relations)} 条关系")
        return self.kg
    
    def _add_unit_nodes(self, units_gdf, features_dict):
        """添加单元节点"""
        print("- 添加单元节点...")
        for idx, row in units_gdf.iterrows():
            unit_id = str(row.get('unit_id', idx))
            node = UnitNode(
                unit_id=unit_id,
                geometry=row.geometry,
                area=row.geometry.area,
                centroid=(row.geometry.centroid.x, row.geometry.centroid.y),
                features=features_dict.get(unit_id, {})
            )
            self.kg.add_node(node)
    
    def _add_function_nodes(self, function_rules):
        """添加功能类型节点"""
        print("- 添加功能节点...")
        for function_type, rule in function_rules.items():
            # 跳过非功能类型的键（如 function_types）
            if function_type == 'function_types' or not isinstance(rule, dict):
                continue
                
            node = FunctionNode(
                function_type=function_type,
                description=rule.get('description', ''),
                criteria=rule.get('criteria', {})
            )
            self.kg.add_node(node)
    
    def _build_adjacency_relations(self, units_gdf):
        """构建相邻关系"""
        print("- 构建相邻关系...")
        count = 0
        for i, unit1 in units_gdf.iterrows():
            for j, unit2 in units_gdf.iterrows():
                if i >= j:
                    continue
                if unit1.geometry.touches(unit2.geometry):
                    uid1 = str(unit1.get('unit_id', i))
                    uid2 = str(unit2.get('unit_id', j))
                    # 双向关系
                    self.kg.add_relation(Relation(
                        source=uid1,
                        target=uid2,
                        relation_type=RelationType.ADJACENT,
                        weight=1.0
                    ))
                    self.kg.add_relation(Relation(
                        source=uid2,
                        target=uid1,
                        relation_type=RelationType.ADJACENT,
                        weight=1.0
                    ))
                    count += 2
        print(f"  - 添加了 {count} 条相邻关系")
    
    def _build_suitability_relations(self, suitability_matrix):
        """构建适宜性关系"""
        print("- 构建适宜性关系...")
        count = 0
        for unit_id, scores in suitability_matrix.items():
            for function_type, score in scores.items():
                if score > 0.3:  # 只记录有一定适宜性的关系
                    self.kg.add_relation(Relation(
                        source=str(unit_id),
                        target=f"func_{function_type}",
                        relation_type=RelationType.SUITABLE_FOR,
                        weight=score
                    ))
                    count += 1
        print(f"  - 添加了 {count} 条适宜性关系")
    
    def _build_dominant_function_relations(self, recommendations):
        """构建主导功能关系"""
        print("- 构建主导功能关系...")
        for unit_id, function_type in recommendations.items():
            self.kg.add_relation(Relation(
                source=str(unit_id),
                target=f"func_{function_type}",
                relation_type=RelationType.DOMINATED_BY,
                weight=1.0
            ))
    
    def _build_similarity_relations(self, features_dict, threshold=0.95, top_k=5):
        """
        构建特征相似关系（Top-K策略）
        
        Args:
            features_dict: 特征字典
            threshold: 相似度阈值（提升到0.95）
            top_k: 每个单元保留的最相似邻居数量
        """
        print("- 构建相似关系...")
        
        # 提取特征矩阵
        unit_ids = list(features_dict.keys())
        feature_names = list(next(iter(features_dict.values())).keys())
        
        feature_matrix = np.array([
            [features_dict[uid].get(fname, 0) for fname in feature_names]
            for uid in unit_ids
        ])
        
        # 归一化
        norms = np.linalg.norm(feature_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1  # 避免除零
        feature_matrix_norm = feature_matrix / norms
        
        # 计算余弦相似度
        similarity_matrix = np.dot(feature_matrix_norm, feature_matrix_norm.T)
        
        count = 0
        for i in range(len(unit_ids)):
            # Top-K策略：每个单元只保留最相似的K个邻居
            similarities = similarity_matrix[i, :]
            similarities[i] = -1  # 排除自己
            
            if top_k > 0:
                top_indices = np.argsort(similarities)[-top_k:]
                for j in top_indices:
                    sim = similarities[j]
                    if sim >= threshold and j > i:  # 避免重复
                        self.kg.add_relation(Relation(
                            source=str(unit_ids[i]),
                            target=str(unit_ids[j]),
                            relation_type=RelationType.SIMILAR_TO,
                            weight=float(sim),
                            properties={'similarity': float(sim)}
                        ))
                        count += 1
        
        print(f"  - 添加了 {count} 条相似关系 (threshold={threshold}, top_k={top_k})")


# ============ 使用示例 ============

if __name__ == "__main__":
    # 模拟数据
    import geopandas as gpd
    from shapely.geometry import box
    
    # 创建示例单元
    units = []
    for i in range(3):
        for j in range(3):
            geom = box(i, j, i+1, j+1)
            units.append({'geometry': geom, 'unit_id': f"U_{i}_{j}"})
    
    units_gdf = gpd.GeoDataFrame(units)
    
    # 模拟特征
    features_dict = {
        f"U_{i}_{j}": {
            'dist_to_metro': np.random.randint(100, 1000),
            'green_ratio': np.random.random(),
            'poi_count': np.random.randint(0, 10)
        }
        for i in range(3) for j in range(3)
    }
    
    # 模拟适宜性得分
    suitability_matrix = {
        unit_id: {
            '居住': np.random.random(),
            '商业': np.random.random(),
            '绿地': np.random.random()
        }
        for unit_id in features_dict.keys()
    }
    
    # 模拟推荐结果
    recommendations = {
        unit_id: max(scores.items(), key=lambda x: x[1])[0]
        for unit_id, scores in suitability_matrix.items()
    }
    
    # 功能规则
    function_rules = {
        '居住': {'description': '居住功能', 'criteria': {}},
        '商业': {'description': '商业功能', 'criteria': {}},
        '绿地': {'description': '绿地休闲', 'criteria': {}}
    }
    
    # 构建知识图谱
    builder = KnowledgeGraphBuilder()
    kg = builder.build(
        units_gdf=units_gdf,
        features_dict=features_dict,
        suitability_matrix=suitability_matrix,
        recommendations=recommendations,
        function_rules=function_rules
    )
    
    # 保存
    kg.save_to_file('knowledge_graph.json')
    
    # 查询示例
    print("\n=== 查询示例 ===")
    print(f"适合居住的单元: {kg.find_suitable_units('居住', min_score=0.6)}")
    print(f"U_0_0 的相邻单元: {kg.get_adjacent_units('U_0_0')}")
    print(f"U_1_1 的主导功能: {kg.get_unit_dominant_function('U_1_1')}")