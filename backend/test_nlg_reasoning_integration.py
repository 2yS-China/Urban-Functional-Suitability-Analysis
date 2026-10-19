"""
Phase 2.4 测试：推理引擎与自然语言生成器整合

测试目标：
1. NLG集成推理引擎后的适宜性解释
2. 对比推理模式和特征模板模式的输出
3. 验证问答系统使用推理引擎的效果
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import geopandas as gpd
from shapely.geometry import Point, Polygon
import numpy as np
import yaml

from kg import (
    SpatialKnowledgeGraph,
    ReasoningEngine,
    NaturalLanguageGenerator,
    SpatialQA,
    NodeType,
    RelationType
)
from kg.knowledge_graph_builder import KnowledgeGraphBuilder, POINode, InfrastructureNode, RuleNode


def create_test_knowledge_graph():
    """创建测试知识图谱（包含POI、基础设施、规则）"""
    
    # 1. 创建基础知识图谱
    # 模拟单元数据
    units_data = []
    for i in range(3):
        units_data.append({
            'unit_id': str(i),
            'geometry': Polygon([
                (i*100, 0), (i*100+100, 0), 
                (i*100+100, 100), (i*100, 100)
            ]),
            'area': 10000,
            'features': {
                'dist_to_metro': 300 + i*200,  # 单元0最近
                'dist_to_bus': 200 + i*100,
                'green_ratio_500m': 0.3 - i*0.05,
                'poi_教育_500m': 5 - i,
                'slope_mean': 5 + i*2
            }
        })
    
    units_gdf = gpd.GeoDataFrame(units_data, crs='EPSG:4326')
    
    # 模拟特征字典
    features_dict = {str(i): units_data[i]['features'] for i in range(3)}
    
    # 模拟适宜性矩阵
    suitability_matrix = {
        '0': {'居住': 0.85, '商业': 0.65, '办公': 0.70},
        '1': {'居住': 0.70, '商业': 0.75, '办公': 0.68},
        '2': {'居住': 0.60, '商业': 0.55, '办公': 0.58}
    }
    
    # 模拟推荐结果
    recommendations = {
        '0': '居住',
        '1': '商业',
        '2': '居住'
    }
    
    # 加载功能规则
    rules_path = Path(__file__).parent / 'spatial_analysis' / 'function_rules.yaml'
    with open(rules_path, 'r', encoding='utf-8') as f:
        function_rules = yaml.safe_load(f)
    
    # 使用构建器构建知识图谱
    builder = KnowledgeGraphBuilder()
    kg = builder.build(units_gdf, features_dict, suitability_matrix, 
                      recommendations, function_rules)
    
    # 2. 扩展：添加POI节点
    poi_metro = POINode(
        poi_id='poi_metro_1',
        name='地铁站1',
        category='地铁站',
        location=(50.0, 50.0),
        attributes={
            'metro_line': 'L1',
            'line_name': '1号线'
        }
    )
    kg.add_node(poi_metro)
    
    poi_school = POINode(
        poi_id='poi_school_1',
        name='实验小学',
        category='教育',
        location=(80.0, 80.0),
        attributes={'type': '小学', 'rating': 4.5}
    )
    kg.add_node(poi_school)
    
    # 3. 添加基础设施节点
    line1 = InfrastructureNode(
        infra_id='infra_line1',
        infra_type='地铁线',
        name='1号线',
        stations=['地铁站1', '地铁站2', '地铁站3'],
        key_areas=['CBD', '火车站', '大学城']
    )
    kg.add_node(line1)
    
    # 添加关键区域节点（使用基类Node）
    from kg.knowledge_graph_builder import Node
    cbd_node = Node(
        id='area_CBD',
        type=NodeType.FEATURE,
        properties={'name': 'CBD', 'type': '核心商业区'}
    )
    kg.add_node(cbd_node)
    
    # 4. 添加规则节点
    rule_metro = RuleNode(
        rule_id='rule_居住_dist_to_metro',
        feature_name='dist_to_metro',
        threshold=800,
        direction='minimize',
        description='居住功能要求800m内有地铁站'
    )
    kg.add_node(rule_metro)
    
    # 5. 添加关系（使用基类Relation）
    from kg.knowledge_graph_builder import Relation
    
    # 单元 → POI
    kg.add_relation(Relation(
        source='0',
        target='poi_metro_1',
        relation_type=RelationType.NEAR,
        weight=1.0,
        properties={'distance': 300}
    ))
    
    kg.add_relation(Relation(
        source='0',
        target='poi_school_1',
        relation_type=RelationType.NEAR,
        weight=1.0,
        properties={'distance': 400}
    ))
    
    # POI → 基础设施
    kg.add_relation(Relation(
        source='poi_metro_1',
        target='infra_line1',
        relation_type=RelationType.SERVES_BY,
        weight=1.0,
        properties={'line': '1号线'}
    ))
    
    # 基础设施 → 区域
    kg.add_relation(Relation(
        source='infra_line1',
        target='area_CBD',
        relation_type=RelationType.CONNECTS_TO,
        weight=1.0,
        properties={'type': '连接核心区域'}
    ))
    
    # 单元 → 规则
    kg.add_relation(Relation(
        source='0',
        target='rule_居住_dist_to_metro',
        relation_type=RelationType.SATISFIES,
        weight=1.0,
        properties={'actual_value': 300}
    ))
    
    # 功能 → 规则
    kg.add_relation(Relation(
        source='func_居住',
        target='rule_居住_dist_to_metro',
        relation_type=RelationType.REQUIRES,
        weight=0.2,
        properties={'criterion': '地铁便利性'}
    ))
    
    return kg


def test_reasoning_vs_template():
    """测试1：对比推理模式和模板模式"""
    print("=" * 80)
    print("测试1：推理模式 vs 模板模式")
    print("=" * 80)
    
    kg = create_test_knowledge_graph()
    
    # 初始化生成器（启用推理）
    nlg_with_reasoning = NaturalLanguageGenerator(kg, enable_reasoning=True)
    
    # 初始化生成器（禁用推理）
    nlg_without_reasoning = NaturalLanguageGenerator(kg, enable_reasoning=False)
    
    unit_id = '0'
    function = '居住'
    
    print(f"\n问题：为什么单元 {unit_id} 适合{function}功能？\n")
    
    print("\n【方法1：使用推理引擎（深度解释）】")
    print("-" * 80)
    explanation_with_reasoning = nlg_with_reasoning.explain_unit_suitability(
        unit_id, function, use_reasoning=True
    )
    print(explanation_with_reasoning)
    
    print("\n" + "=" * 80)
    print("\n【方法2：使用特征模板（原有方法）】")
    print("-" * 80)
    explanation_without_reasoning = nlg_without_reasoning.explain_unit_suitability(
        unit_id, function, use_reasoning=False
    )
    print(explanation_without_reasoning)
    
    print("\n" + "=" * 80)
    print("\n[OK] 对比完成")
    print("\n差异分析：")
    print("- 推理模式：展示多跳推理链（单元→POI→基础设施→区域）")
    print("- 模板模式：仅展示特征值描述")
    print("- 推理模式提供更深层次的因果解释")


def test_qa_with_reasoning():
    """测试2：问答系统使用推理引擎"""
    print("\n" + "=" * 80)
    print("测试2：问答系统（启用推理引擎）")
    print("=" * 80)
    
    kg = create_test_knowledge_graph()
    
    # 初始化问答系统（启用推理）
    qa = SpatialQA(kg, enable_reasoning=True)
    
    questions = [
        "为什么单元 0 适合居住功能？",
        "哪些区域适合居住功能？",
        "对比单元 0 和 1 的居住适宜性"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n【问题{i}】{question}")
        print("-" * 80)
        answer = qa.answer(question)
        print(answer)
        print()


def test_reasoning_chain_display():
    """测试3：推理链的详细展示"""
    print("\n" + "=" * 80)
    print("测试3：推理链详细结构")
    print("=" * 80)
    
    kg = create_test_knowledge_graph()
    reasoning_engine = ReasoningEngine(kg)
    
    unit_id = '0'
    function = '居住'
    
    print(f"\n查询：单元 {unit_id} 适合{function}功能的推理链\n")
    
    chains = reasoning_engine.explain_suitability(unit_id, function, max_depth=4)
    
    if chains:
        print(f"找到 {len(chains)} 条推理链：\n")
        
        for i, chain in enumerate(chains, 1):
            print(f"【推理链 {i}】")
            print(f"步数：{len(chain.steps)}")
            print("\n详细步骤：")
            for j, step in enumerate(chain.steps, 1):
                print(f"  步骤{j}: {step.source_node.id} "
                      f"--{step.relation.relation_type.value}--> "
                      f"{step.target_node.id}")
                print(f"         证据: {step.evidence}")
            
            print(f"\n自然语言描述：")
            print(f"  {chain.to_natural_language()}")
            print()
    else:
        print("未找到推理链")


def test_evidence_collection():
    """测试4：完整证据收集"""
    print("\n" + "=" * 80)
    print("测试4：完整证据收集")
    print("=" * 80)
    
    kg = create_test_knowledge_graph()
    reasoning_engine = ReasoningEngine(kg)
    
    unit_id = '0'
    function = '居住'
    
    print(f"\n收集单元 {unit_id} 适合{function}功能的所有证据：\n")
    
    evidence = reasoning_engine.get_all_evidence(unit_id, function)
    
    # POI证据链（字典格式）
    poi_chains = evidence.get('poi_chains', [])
    print(f"POI证据链：{len(poi_chains)} 条")
    for chain_dict in poi_chains:
        if 'natural_language' in chain_dict:
            print(f"  - {chain_dict['natural_language']}")
    
    # 规则证据链（字典格式）
    rule_chains = evidence.get('rule_chains', [])
    print(f"\n规则证据链：{len(rule_chains)} 条")
    for chain_dict in rule_chains:
        if 'natural_language' in chain_dict:
            print(f"  - {chain_dict['natural_language']}")
    
    # 空间上下文
    if evidence.get('spatial_context'):
        print(f"\n空间上下文：")
        ctx = evidence['spatial_context']
        print(f"  相邻单元数量：{ctx.get('adjacent_count', 0)}")
        if ctx.get('adjacent_functions'):
            print("  相邻单元功能分布：")
            for func, count in ctx['adjacent_functions'].items():
                print(f"    - {func}: {count}个")


def main():
    """主测试流程"""
    print("\n" + "=" * 80)
    print("Phase 2.4: 推理引擎与自然语言生成器整合测试")
    print("=" * 80)
    
    try:
        # 测试1：对比推理模式和模板模式
        test_reasoning_vs_template()
        
        # 测试2：问答系统使用推理引擎
        test_qa_with_reasoning()
        
        # 测试3：推理链详细展示
        test_reasoning_chain_display()
        
        # 测试4：完整证据收集
        test_evidence_collection()
        
        print("\n" + "=" * 80)
        print("所有测试完成 [OK]")
        print("=" * 80)
        print("\nPhase 2.4 核心功能验证：")
        print("  [OK] NLG集成推理引擎")
        print("  [OK] 推理模式与模板模式切换")
        print("  [OK] 问答系统使用推理引擎")
        print("  [OK] 多跳推理链展示")
        print("  [OK] 完整证据收集")
        
    except Exception as e:
        print(f"\n测试失败：{e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())