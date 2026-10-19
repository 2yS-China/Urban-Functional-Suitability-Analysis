"""
城市片区功能适宜性分析 - 知识推理引擎

核心职责：
1. 多跳推理：追溯"单元 → POI → 基础设施 → 关键区域"的因果链
2. 证据提取：收集推理路径上的关系证据
3. 规则验证：检查单元是否满足功能评价准则
4. 自然语言转换：将推理链转为可读文本
"""

from typing import List, Dict, Optional, Tuple, Set
from collections import deque
from dataclasses import dataclass
from .knowledge_graph_builder import (
    SpatialKnowledgeGraph, 
    Node, 
    Relation, 
    RelationType,
    NodeType
)


@dataclass
class ReasoningStep:
    """推理步骤"""
    source_node: Node
    relation: Relation
    target_node: Node
    evidence: str
    
    def to_dict(self):
        return {
            'source': {
                'id': self.source_node.id,
                'type': self.source_node.type.value,
                'name': self.source_node.properties.get('name', self.source_node.id)
            },
            'relation': self.relation.relation_type.value,
            'target': {
                'id': self.target_node.id,
                'type': self.target_node.type.value,
                'name': self.target_node.properties.get('name', self.target_node.id)
            },
            'evidence': self.evidence
        }


class ReasoningChain:
    """推理链"""
    
    def __init__(self):
        self.steps: List[ReasoningStep] = []
        self.confidence: float = 1.0
    
    def add_step(self, source_node: Node, relation: Relation, 
                 target_node: Node, evidence: str):
        """添加推理步骤"""
        step = ReasoningStep(
            source_node=source_node,
            relation=relation,
            target_node=target_node,
            evidence=evidence
        )
        self.steps.append(step)
    
    def to_natural_language(self) -> str:
        """转为自然语言描述"""
        if not self.steps:
            return ""
        
        parts = []
        for i, step in enumerate(self.steps):
            source_name = step.source_node.properties.get('name', step.source_node.id)
            target_name = step.target_node.properties.get('name', step.target_node.id)
            rel_desc = self._relation_to_chinese(step.relation.relation_type)
            
            if i == 0:
                parts.append(f"{source_name}{rel_desc}{target_name}")
            else:
                parts.append(f"{rel_desc}{target_name}")
            
            if step.evidence:
                parts.append(f"（{step.evidence}）")
        
        return "".join(parts)
    
    def _relation_to_chinese(self, rel_type: RelationType) -> str:
        """关系类型转中文"""
        mapping = {
            RelationType.NEAR: "靠近",
            RelationType.SERVES_BY: "由",
            RelationType.CONNECTS_TO: "连接到",
            RelationType.REQUIRES: "要求",
            RelationType.SATISFIES: "满足",
            RelationType.SUITABLE_FOR: "适宜于",
            RelationType.DOMINATED_BY: "主导功能为"
        }
        result = mapping.get(rel_type, rel_type.value)
        return result if result else ""
    
    def to_dict(self):
        return {
            'steps': [step.to_dict() for step in self.steps],
            'confidence': self.confidence,
            'natural_language': self.to_natural_language()
        }


class ReasoningEngine:
    """知识推理引擎"""
    
    def __init__(self, kg: SpatialKnowledgeGraph):
        self.kg = kg
    
    def explain_suitability(self, unit_id: str, function: str, 
                           max_depth: int = 4) -> List[ReasoningChain]:
        """
        解释适宜性：为什么单元X适合功能Y
        
        推理路径示例：
        单元X -> NEAR -> 地铁站M -> SERVES_BY -> L2号线 -> CONNECTS_TO -> CBD
              -> SATISFIES -> 居住规则(800m内有地铁)
        
        参数:
            unit_id: 单元ID
            function: 功能类型（如"居住"）
            max_depth: 最大推理深度
            
        返回:
            推理链列表
        """
        chains = []
        
        # 1. 查找单元节点
        unit_node = self.kg.get_node(unit_id)
        if not unit_node:
            return chains
        
        # 2. 查找功能节点
        function_node_id = f"func_{function}"
        function_node = self.kg.get_node(function_node_id)
        if not function_node:
            return chains
        
        # 3. 查找单元到功能的适宜性关系
        suitability_rels = self.kg.get_outgoing_relations(
            unit_id, RelationType.SUITABLE_FOR
        )
        target_rel = next((r for r in suitability_rels if r.target == function_node_id), None)
        
        if not target_rel:
            return chains
        
        # 4. 查找支持适宜性的证据链
        # 4.1 基于POI的证据链（单元 -> POI -> 基础设施 -> 区域）
        poi_chains = self._find_poi_evidence_chains(unit_id, function, max_depth)
        chains.extend(poi_chains)
        
        # 4.2 基于规则的证据链（单元 -> 规则满足）
        rule_chains = self._find_rule_evidence_chains(unit_id, function_node, max_depth)
        chains.extend(rule_chains)
        
        return chains
    
    def _find_poi_evidence_chains(self, unit_id: str, function: str, 
                                  max_depth: int) -> List[ReasoningChain]:
        """
        查找基于POI的证据链
        
        路径模式：单元 --NEAR--> POI --SERVES_BY--> 基础设施 --CONNECTS_TO--> 区域
        """
        chains = []
        unit_node = self.kg.get_node(unit_id)
        
        # 查找单元附近的POI
        near_rels = self.kg.get_outgoing_relations(unit_id, RelationType.NEAR)
        
        for near_rel in near_rels:
            poi_node = self.kg.get_node(near_rel.target)
            if not poi_node or poi_node.type != NodeType.POI:
                continue
            
            # 创建推理链
            chain = ReasoningChain()
            
            # 步骤1：单元 -> POI
            distance = near_rel.properties.get('distance', 0) if near_rel.properties else 0
            evidence1 = f"距离{distance:.0f}米" if distance > 0 else ""
            chain.add_step(unit_node, near_rel, poi_node, evidence1)
            
            # 查找POI的服务关系（POI -> 基础设施）
            serves_rels = self.kg.get_outgoing_relations(poi_node.id, RelationType.SERVES_BY)
            
            for serves_rel in serves_rels:
                infra_node = self.kg.get_node(serves_rel.target)
                if not infra_node or infra_node.type != NodeType.INFRASTRUCTURE:
                    continue
                
                # 步骤2：POI -> 基础设施
                evidence2 = f"{infra_node.properties.get('name', '')}服务"
                chain.add_step(poi_node, serves_rel, infra_node, evidence2)
                
                # 查找基础设施连接的区域
                connects_rels = self.kg.get_outgoing_relations(
                    infra_node.id, RelationType.CONNECTS_TO
                )
                
                for connects_rel in connects_rels[:2]:  # 最多展示2个连接区域
                    area_node = self.kg.get_node(connects_rel.target)
                    if area_node:
                        # 步骤3：基础设施 -> 区域
                        evidence3 = ""
                        chain.add_step(infra_node, connects_rel, area_node, evidence3)
                
                if len(chain.steps) >= 2:  # 至少有2步推理
                    chains.append(chain)
                    break  # 每个POI只取一条最佳链
            
            if len(chain.steps) == 1:  # 只有单元->POI，无后续推理
                chains.append(chain)
        
        return chains
    
    def _find_rule_evidence_chains(self, unit_id: str, function_node: Node, 
                                   max_depth: int) -> List[ReasoningChain]:
        """
        查找基于规则的证据链
        
        路径模式：功能 --REQUIRES--> 规则 <--SATISFIES-- 单元
        """
        chains = []
        unit_node = self.kg.get_node(unit_id)
        
        # 查找功能要求的规则
        requires_rels = self.kg.get_outgoing_relations(
            function_node.id, RelationType.REQUIRES
        )
        
        for req_rel in requires_rels:
            rule_node = self.kg.get_node(req_rel.target)
            if not rule_node or rule_node.type != NodeType.RULE:
                continue
            
            # 检查单元是否满足该规则
            satisfies_rels = self.kg.get_outgoing_relations(
                unit_id, RelationType.SATISFIES
            )
            satisfies_rel = next(
                (r for r in satisfies_rels if r.target == rule_node.id), 
                None
            )
            
            if satisfies_rel:
                chain = ReasoningChain()
                evidence = rule_node.properties.get('description', '')
                chain.add_step(unit_node, satisfies_rel, rule_node, evidence)
                chains.append(chain)
        
        return chains
    
    def find_path(self, start_node_id: str, end_node_id: str, 
                  max_depth: int = 4) -> Optional[ReasoningChain]:
        """
        广度优先搜索，查找两个节点之间的最短推理路径
        
        参数:
            start_node_id: 起始节点ID
            end_node_id: 目标节点ID
            max_depth: 最大搜索深度
            
        返回:
            推理链（如果找到路径）
        """
        if start_node_id == end_node_id:
            return None
        
        queue = deque([(start_node_id, [])])
        visited: Set[str] = {start_node_id}
        
        while queue and len(visited) < 10000:  # 防止无限循环
            current_id, path = queue.popleft()
            
            if len(path) >= max_depth:
                continue
            
            # 获取当前节点的所有出边
            relations = self.kg.get_outgoing_relations(current_id)
            
            for rel in relations:
                if rel.target not in visited:
                    visited.add(rel.target)
                    
                    # 构建新路径
                    source_node = self.kg.get_node(current_id)
                    target_node = self.kg.get_node(rel.target)
                    
                    if not source_node or not target_node:
                        continue
                    
                    new_path = path + [(source_node, rel, target_node)]
                    
                    # 检查是否到达目标
                    if rel.target == end_node_id:
                        chain = ReasoningChain()
                        for src, r, tgt in new_path:
                            evidence = self._extract_evidence(r)
                            chain.add_step(src, r, tgt, evidence)
                        return chain
                    
                    queue.append((rel.target, new_path))
        
        return None
    
    def _extract_evidence(self, relation: Relation) -> str:
        """提取关系的证据描述"""
        if relation.relation_type == RelationType.NEAR:
            dist = relation.properties.get('distance', 0) if relation.properties else 0
            return f"距离{dist:.0f}米" if dist > 0 else ""
        elif relation.relation_type == RelationType.SERVES_BY:
            return "服务于该线路"
        elif relation.relation_type == RelationType.CONNECTS_TO:
            return "连接到核心区域"
        elif relation.relation_type == RelationType.SATISFIES:
            return "满足要求"
        elif relation.relation_type == RelationType.SUITABLE_FOR:
            score = relation.weight
            return f"适宜性得分{score:.2f}"
        return ""
    
    def get_all_evidence(self, unit_id: str, function: str) -> Dict:
        """
        获取单元适宜某功能的所有证据（用于完整解释）
        
        返回:
            {
                'poi_chains': [...],      # POI证据链
                'rule_chains': [...],     # 规则证据链
                'similar_units': [...],   # 相似单元
                'spatial_context': {...}  # 空间上下文
            }
        """
        result = {
            'poi_chains': [],
            'rule_chains': [],
            'similar_units': [],
            'spatial_context': {}
        }
        
        # 1. POI证据链
        poi_chains = self._find_poi_evidence_chains(unit_id, function, max_depth=4)
        result['poi_chains'] = [chain.to_dict() for chain in poi_chains]
        
        # 2. 规则证据链
        function_node = self.kg.get_node(f"func_{function}")
        if function_node:
            rule_chains = self._find_rule_evidence_chains(unit_id, function_node, max_depth=2)
            result['rule_chains'] = [chain.to_dict() for chain in rule_chains]
        
        # 3. 相似单元
        similar_rels = self.kg.get_outgoing_relations(unit_id, RelationType.SIMILAR_TO)
        result['similar_units'] = [
            {
                'unit_id': rel.target,
                'similarity': rel.weight,
                'function': self.kg.get_node(rel.target).properties.get('recommended_function', '')
                    if self.kg.get_node(rel.target) else ''
            }
            for rel in similar_rels[:5]  # 最多5个相似单元
        ]
        
        # 4. 空间上下文
        adjacent_rels = self.kg.get_outgoing_relations(unit_id, RelationType.ADJACENT)
        result['spatial_context'] = {
            'adjacent_count': len(adjacent_rels),
            'adjacent_functions': self._get_adjacent_functions(adjacent_rels)
        }
        
        return result
    
    def _get_adjacent_functions(self, adjacent_rels: List[Relation]) -> Dict[str, int]:
        """统计相邻单元的功能分布"""
        function_counts = {}
        for rel in adjacent_rels:
            neighbor = self.kg.get_node(rel.target)
            if neighbor:
                func = neighbor.properties.get('recommended_function', 'unknown')
                function_counts[func] = function_counts.get(func, 0) + 1
        return function_counts