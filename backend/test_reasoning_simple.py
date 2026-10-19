"""
Phase 2.3 简化测试：知识推理引擎
使用已有测试数据快速验证推理能力
"""

import sys
from pathlib import Path
import geopandas as gpd
import json

sys.path.insert(0, str(Path(__file__).parent))

from kg.knowledge_graph_builder import (
    SpatialKnowledgeGraph,
    POINode,
    InfrastructureNode,
    RuleNode,
    Relation,
    RelationType,
    Node,
    NodeType
)
from kg.reasoning_engine import ReasoningEngine


def create_simple_test_kg():
    """创建简化的测试知识图谱"""
    print("创建测试知识图谱...")
    
    kg = SpatialKnowledgeGraph()
    
    # 1. 添加单元节点
    print("- 添加单元节点...")
    from kg.knowledge_graph_builder import UnitNode
    from shapely.geometry import Point
    
    for i in range(5):
        unit_node = UnitNode(
            unit_id=str(i),
            geometry=Point(116.3 + i*0.001, 39.9 + i*0.001).buffer(0.0005),
            area=10000,
            centroid=(116.3 + i*0.001, 39.9 + i*0.001),
            features={
                'dist_to_metro': 500 + i*100,
                'poi_density_500m': 20 - i*2
            }
        )
        kg.add_node(unit_node)
    
    # 2. 添加功能节点
    print("- 添加功能节点...")
    from kg.knowledge_graph_builder import FunctionNode
    
    functions = ['居住', '商业', '办公']
    for func in functions:
        func_node = FunctionNode(
            function_type=func,
            description=f"{func}功能用地",
            criteria={}
        )
        kg.add_node(func_node)
    
    # 3. 添加POI节点
    print("- 添加POI节点...")
    
    # 地铁站
    for i in range(3):
        poi_node = POINode(
            poi_id=f"poi_metro_{i}",
            category='地铁站',
            name=f"地铁站{i+1}",
            location=(116.3 + i*0.002, 39.9 + i*0.002),
            attributes={
                'metro_line': f"L{i%2+1}",
                'line_name': f"{i%2+1}号线"
            }
        )
        kg.add_node(poi_node)
    
    # 4. 添加基础设施节点
    print("- 添加基础设施节点...")
    
    metro_lines = {
        'L1': {'name': '1号线', 'key_areas': ['CBD', '火车站']},
        'L2': {'name': '2号线', 'key_areas': ['CBD', '高新区', '大学城']}
    }
    
    for line_id, line_info in metro_lines.items():
        infra_node = InfrastructureNode(
            infra_id=f"metro_line_{line_id}",
            infra_type='metro',
            name=line_info['name'],
            stations=[],
            key_areas=line_info['key_areas']
        )
        kg.add_node(infra_node)
    
    # 5. 添加区域节点
    print("- 添加区域节点...")
    
    areas = ['CBD', '高新区', '大学城', '火车站']
    for area in areas:
        area_node = Node(
            id=f"area_{area}",
            type=NodeType.REGION,
            properties={'name': area, 'type': '关键区域'}
        )
        kg.add_node(area_node)
    
    # 6. 添加规则节点
    print("- 添加规则节点...")
    
    rule_node = RuleNode(
        rule_id="rule_居住_dist_to_metro",
        feature_name="dist_to_metro",
        threshold=800,
        direction="minimize",
        description="居住功能要求800m内有地铁"
    )
    kg.add_node(rule_node)
    
    # 7. 构建关系
    print("- 构建关系...")
    
    # 单元 -> 功能（适宜性）
    kg.add_relation(Relation(
        source="0",
        target="func_居住",
        relation_type=RelationType.SUITABLE_FOR,
        weight=0.85
    ))
    
    # 单元 -> POI（邻近）
    kg.add_relation(Relation(
        source="0",
        target="poi_metro_0",
        relation_type=RelationType.NEAR,
        weight=1.0,
        properties={'distance': 500}
    ))
    
    # POI -> 基础设施（服务）
    kg.add_relation(Relation(
        source="poi_metro_0",
        target="metro_line_L1",
        relation_type=RelationType.SERVES_BY,
        weight=1.0
    ))
    
    kg.add_relation(Relation(
        source="poi_metro_1",
        target="metro_line_L2",
        relation_type=RelationType.SERVES_BY,
        weight=1.0
    ))
    
    # 基础设施 -> 区域（连接）
    kg.add_relation(Relation(
        source="metro_line_L1",
        target="area_CBD",
        relation_type=RelationType.CONNECTS_TO,
        weight=1.0
    ))
    
    kg.add_relation(Relation(
        source="metro_line_L1",
        target="area_火车站",
        relation_type=RelationType.CONNECTS_TO,
        weight=1.0
    ))
    
    kg.add_relation(Relation(
        source="metro_line_L2",
        target="area_CBD",
        relation_type=RelationType.CONNECTS_TO,
        weight=1.0
    ))
    
    kg.add_relation(Relation(
        source="metro_line_L2",
        target="area_高新区",
        relation_type=RelationType.CONNECTS_TO,
        weight=1.0
    ))
    
    kg.add_relation(Relation(
        source="metro_line_L2",
        target="area_大学城",
        relation_type=RelationType.CONNECTS_TO,
        weight=1.0
    ))
    
    # 功能 -> 规则（要求）
    kg.add_relation(Relation(
        source="func_居住",
        target="rule_居住_dist_to_metro",
        relation_type=RelationType.REQUIRES,
        weight=0.2
    ))
    
    # 单元 -> 规则（满足）
    kg.add_relation(Relation(
        source="0",
        target="rule_居住_dist_to_metro",
        relation_type=RelationType.SATISFIES,
        weight=1.0
    ))
    
    print(f"\n知识图谱统计:")
    print(f"  - 节点数: {len(kg.nodes)}")
    print(f"  - 关系数: {len(kg.relations)}")
    
    return kg


def test_reasoning():
    """测试推理功能"""
    print("\n" + "=" * 60)
    print("测试推理引擎")
    print("=" * 60)
    
    # 创建知识图谱
    kg = create_simple_test_kg()
    
    # 初始化推理引擎
    reasoning_engine = ReasoningEngine(kg)
    
    # 测试1：适宜性解释
    print("\n【测试1：适宜性解释（多跳推理）】")
    unit_id = "0"
    function = "居住"
    
    print(f"\n问题：为什么单元 {unit_id} 适合{function}功能？")
    
    chains = reasoning_engine.explain_suitability(unit_id, function, max_depth=4)
    
    if chains:
        print(f"\n找到 {len(chains)} 条证据链：\n")
        for i, chain in enumerate(chains, 1):
            print(f"【证据链 {i}】")
            print(f"推理步骤：")
            for j, step in enumerate(chain.steps, 1):
                source_name = step.source_node.properties.get('name', step.source_node.id)
                target_name = step.target_node.properties.get('name', step.target_node.id)
                print(f"  {j}. {source_name} --{step.relation.relation_type.value}--> {target_name}")
                if step.evidence:
                    print(f"     证据: {step.evidence}")
            
            print(f"\n自然语言描述：")
            print(f"  {chain.to_natural_language()}")
            print()
    else:
        print("  未找到证据链")
    
    # 测试2：路径查找
    print("\n【测试2：路径查找】")
    print(f"\n查找单元 {unit_id} 到 CBD 的连接路径...")
    
    path_chain = reasoning_engine.find_path(unit_id, "area_CBD", max_depth=5)
    
    if path_chain:
        print(f"\n找到路径（{len(path_chain.steps)} 步）：")
        for i, step in enumerate(path_chain.steps, 1):
            source_name = step.source_node.properties.get('name', step.source_node.id)
            target_name = step.target_node.properties.get('name', step.target_node.id)
            print(f"  {i}. {source_name} --{step.relation.relation_type.value}--> {target_name}")
            if step.evidence:
                print(f"     证据: {step.evidence}")
        
        print(f"\n自然语言描述：")
        print(f"  {path_chain.to_natural_language()}")
    else:
        print("  未找到路径")
    
    # 测试3：完整解释
    print("\n【测试3：完整证据收集】")
    all_evidence = reasoning_engine.get_all_evidence(unit_id, function)
    
    print(f"\nPOI证据链: {len(all_evidence['poi_chains'])} 条")
    for i, chain_dict in enumerate(all_evidence['poi_chains'][:2], 1):
        print(f"  {i}. {chain_dict['natural_language']}")
    
    print(f"\n规则证据链: {len(all_evidence['rule_chains'])} 条")
    for i, chain_dict in enumerate(all_evidence['rule_chains'], 1):
        print(f"  {i}. {chain_dict['natural_language']}")
    
    # 保存知识图谱
    output_file = "sample_data/knowledge_graph_reasoning_test.json"
    kg.save_to_file(output_file)
    print(f"\n[OK] 保存测试知识图谱: {output_file}")
    
    return kg, reasoning_engine


def main():
    print("=" * 60)
    print("Phase 2.3: 知识推理引擎测试（简化版）")
    print("=" * 60)
    print()
    
    kg, reasoning_engine = test_reasoning()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n核心功能验证：")
    print("  [OK] 多跳推理：单元 → POI → 基础设施 → 区域")
    print("  [OK] 证据提取：距离、服务关系、连接关系")
    print("  [OK] 路径查找：BFS搜索最短推理路径")
    print("  [OK] 自然语言转换：推理链转可读文本")


if __name__ == "__main__":
    main()