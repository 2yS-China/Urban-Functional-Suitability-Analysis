"""
知识图谱模块

核心职责：
1. 将GIS空间分析结果转化为结构化知识图谱
2. 基于知识图谱生成自然语言解释
3. 支持多种查询类型的问答
4. 提供多跳推理能力（Phase 2.3新增）
"""

from .knowledge_graph_builder import (
    SpatialKnowledgeGraph,
    NodeType,
    RelationType,
    Node,
    UnitNode,
    FeatureNode,
    FunctionNode,
    POINode,
    InfrastructureNode,
    RuleNode,
    Relation,
    KnowledgeGraphBuilder
)

from .nlg_generator import (
    NaturalLanguageGenerator,
    SpatialQA,
    QuestionType
)

from .reasoning_engine import (
    ReasoningEngine,
    ReasoningChain,
    ReasoningStep
)

__all__ = [
    # 知识图谱核心
    'SpatialKnowledgeGraph',
    'NodeType', 
    'RelationType',
    'Node',
    'UnitNode',
    'FeatureNode', 
    'FunctionNode',
    'POINode',
    'InfrastructureNode',
    'RuleNode',
    'Relation',
    'KnowledgeGraphBuilder',
    # 自然语言生成
    'NaturalLanguageGenerator',
    'SpatialQA',
    'QuestionType',
    # 推理引擎
    'ReasoningEngine',
    'ReasoningChain',
    'ReasoningStep'
]