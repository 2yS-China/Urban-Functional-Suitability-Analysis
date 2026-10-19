"""
Phase 2.3 测试：知识推理引擎
测试多跳推理、证据链构建和自然语言生成
"""

import sys
from pathlib import Path
import geopandas as gpd
import json

# 添加backend到路径
sys.path.insert(0, str(Path(__file__).parent))

from kg.knowledge_graph_builder import (
    KnowledgeGraphBuilder,
    POINode,
    InfrastructureNode,
    RuleNode,
    Relation,
    RelationType
)
from kg.reasoning_engine import ReasoningEngine
from kg.nlg_generator import NaturalLanguageGenerator


def load_test_data():
    """加载测试数据"""
    print("加载测试数据...")
    
    # 加载分析结果
    results_file = "sample_data/processed/suitability_results.geojson"
    if not Path(results_file).exists():
        print(f"错误: 分析结果文件不存在: {results_file}")
        return None, None, None, None
    
    units_gdf = gpd.read_file(results_file)
    
    # 加载POI数据
    poi_file = "sample_data/sample_poi.geojson"
    if not Path(poi_file).exists():
        print(f"错误: POI文件不存在: {poi_file}")
        return None, None, None, None
    
    poi_gdf = gpd.read_file(poi_file)
    
    # 加载地铁线路信息
    metro_file = "sample_data/metro_lines.json"
    metro_lines = {}
    if Path(metro_file).exists():
        with open(metro_file, 'r', encoding='utf-8') as f:
            metro_lines = json.load(f)
    
    # 加载功能规则
    from spatial_analysis.function_rules_loader import load_function_rules
    function_rules = load_function_rules()
    
    print(f"  - 单元数: {len(units_gdf)}")
    print(f"  - POI数: {len(poi_gdf)}")
    print(f"  - 地铁线路: {len(metro_lines)}条")
    
    return units_gdf, poi_gdf, metro_lines, function_rules


def build_enhanced_knowledge_graph(units_gdf, poi_gdf, metro_lines, function_rules):
    """构建增强的知识图谱（包含POI实体和基础设施节点）"""
    print("\n构建增强知识图谱...")
    
    # 使用已有的KnowledgeGraphBuilder
    builder = KnowledgeGraphBuilder()
    
    # 准备数据
    features_dict = {}
    suitability_matrix = {}
    recommendations = {}
    
    for idx, row in units_gdf.iterrows():
        unit_id = str(idx)
        
        # 提取特征
        feature_cols = [col for col in units_gdf.columns 
                       if col.startswith('feat_') or col.startswith('dist_')]
        features_dict[unit_id] = {col: row[col] for col in feature_cols if col in row}
        
        # 提取适宜性得分
        score_cols = [col for col in units_gdf.columns if col.startswith('score_')]
        suitability_matrix[unit_id] = {
            col.replace('score_', ''): row[col] 
            for col in score_cols if col in row
        }
        
        # 提取推荐功能
        if 'recommended_function' in row:
            recommendations[unit_id] = row['recommended_function']
    
    # 构建基础知识图谱
    kg = builder.build(
        units_gdf.head(50),  # 使用前50个单元
        features_dict,
        suitability_matrix,
        recommendations,
        function_rules
    )
    
    # 扩展1：添加POI实体节点
    print("- 添加POI实体节点...")
    poi_count = 0
    for idx, poi in poi_gdf.iterrows():
        poi_node = POINode(
            poi_id=f"poi_{poi['type']}_{idx}",
            category=poi['type'],
            name=poi.get('name', f"{poi['type']}{idx}"),
            location=(poi.geometry.x, poi.geometry.y),
            attributes={
                'metro_line': poi.get('metro_line'),
                'line_name': poi.get('line_name'),
                'key_areas': poi.get('key_areas', '').split(',') if poi.get('key_areas') else []
            }
        )
        kg.add_node(poi_node)
        poi_count += 1
        
        if poi_count >= 30:  # 限制POI数量
            break
    
    print(f"  添加了 {poi_count} 个POI节点")
    
    # 扩展2：添加基础设施节点（地铁线路）
    print("- 添加基础设施节点...")
    for line_id, line_info in metro_lines.items():
        infra_node = InfrastructureNode(
            infra_id=f"metro_line_{line_id}",
            infra_type='metro',
            name=line_info['name'],
            stations=[],  # 简化处理
            key_areas=line_info['key_areas']
        )
        kg.add_node(infra_node)
    
    print(f"  添加了 {len(metro_lines)} 个地铁线路节点")
    
    # 扩展3：添加区域节点
    print("- 添加区域节点...")
    all_areas = set()
    for line_info in metro_lines.values():
        all_areas.update(line_info['key_areas'])
    
    from kg.knowledge_graph_builder import Node, NodeType
    for area in all_areas:
        area_node = Node(
            id=f"area_{area}",
            type=NodeType.REGION,
            properties={'name': area, 'type': '关键区域'}
        )
        kg.add_node(area_node)
    
    print(f"  添加了 {len(all_areas)} 个区域节点")
    
    # 扩展4：构建POI与单元的关系（NEAR）
    print("- 构建单元-POI关系...")
    near_rel_count = 0
    for unit_idx, unit in units_gdf.head(50).iterrows():
        unit_id = str(unit_idx)
        unit_geom = unit.geometry
        
        # 查找附近的POI（800m内）
        for poi_idx, poi in poi_gdf.head(30).iterrows():
            distance = unit_geom.centroid.distance(poi.geometry) * 111000  # 转为米
            
            if distance <= 800:
                rel = Relation(
                    source=unit_id,
                    target=f"poi_{poi['type']}_{poi_idx}",
                    relation_type=RelationType.NEAR,
                    weight=1.0,
                    properties={'distance': distance}
                )
                kg.add_relation(rel)
                near_rel_count += 1
    
    print(f"  添加了 {near_rel_count} 条NEAR关系")
    
    # 扩展5：构建POI与基础设施的关系（SERVES_BY）
    print("- 构建POI-基础设施关系...")
    serves_count = 0
    for poi_idx, poi in poi_gdf.head(30).iterrows():
        if poi['type'] == '地铁站' and 'metro_line' in poi and poi['metro_line']:
            rel = Relation(
                source=f"poi_{poi['type']}_{poi_idx}",
                target=f"metro_line_{poi['metro_line']}",
                relation_type=RelationType.SERVES_BY,
                weight=1.0
            )
            kg.add_relation(rel)
            serves_count += 1
    
    print(f"  添加了 {serves_count} 条SERVES_BY关系")
    
    # 扩展6：构建基础设施与区域的关系（CONNECTS_TO）
    print("- 构建基础设施-区域关系...")
    connects_count = 0
    for line_id, line_info in metro_lines.items():
        for area in line_info['key_areas']:
            rel = Relation(
                source=f"metro_line_{line_id}",
                target=f"area_{area}",
                relation_type=RelationType.CONNECTS_TO,
                weight=1.0
            )
            kg.add_relation(rel)
            connects_count += 1
    
    print(f"  添加了 {connects_count} 条CONNECTS_TO关系")
    
    # 扩展7：添加规则节点和REQUIRES关系
    print("- 添加规则节点...")
    rule_count = 0
    for function, rules in function_rules.items():
        if function == 'function_types' or not isinstance(rules, dict):
            continue
        
        for criterion in rules.get('criteria', []):
            rule_id = f"rule_{function}_{criterion['feature']}"
            rule_node = RuleNode(
                rule_id=rule_id,
                feature_name=criterion['feature'],
                threshold=criterion.get('threshold', 0),
                direction=criterion.get('direction', ''),
                description=f"{function}功能要求{criterion['feature']}"
            )
            kg.add_node(rule_node)
            
            # 功能 -> 规则的REQUIRES关系
            rel = Relation(
                source=f"func_{function}",
                target=rule_id,
                relation_type=RelationType.REQUIRES,
                weight=criterion.get('weight', 0.1)
            )
            kg.add_relation(rel)
            rule_count += 1
    
    print(f"  添加了 {rule_count} 个规则节点和REQUIRES关系")
    
    print(f"\n知识图谱统计:")
    print(f"  - 总节点数: {len(kg.nodes)}")
    print(f"  - 总关系数: {len(kg.relations)}")
    
    return kg


def test_reasoning(kg):
    """测试推理能力"""
    print("\n" + "=" * 60)
    print("测试推理引擎")
    print("=" * 60)
    
    # 初始化推理引擎
    reasoning_engine = ReasoningEngine(kg)
    
    # 测试1：单元适宜性解释
    print("\n【测试1：适宜性解释】")
    unit_id = "0"  # 第一个单元
    function = "居住"
    
    print(f"\n问题：为什么单元 {unit_id} 适合{function}功能？")
    
    chains = reasoning_engine.explain_suitability(unit_id, function, max_depth=4)
    
    if chains:
        print(f"\n找到 {len(chains)} 条证据链：\n")
        for i, chain in enumerate(chains, 1):
            print(f"证据链 {i}:")
            for j, step in enumerate(chain.steps, 1):
                print(f"  {j}. {step.source_node.id} --{step.relation.relation_type.value}--> "
                      f"{step.target_node.id}")
                if step.evidence:
                    print(f"     ({step.evidence})")
            
            print(f"\n  自然语言: {chain.to_natural_language()}\n")
    else:
        print("  未找到证据链")
    
    # 测试2：路径查找
    print("\n【测试2：路径查找】")
    print(f"\n查找单元 {unit_id} 到 CBD 的路径...")
    
    path_chain = reasoning_engine.find_path(unit_id, "area_CBD", max_depth=5)
    
    if path_chain:
        print(f"\n找到路径 ({len(path_chain.steps)} 步):")
        for i, step in enumerate(path_chain.steps, 1):
            print(f"  {i}. {step.source_node.id} --{step.relation.relation_type.value}--> "
                  f"{step.target_node.id}")
            if step.evidence:
                print(f"     ({step.evidence})")
        
        print(f"\n  自然语言: {path_chain.to_natural_language()}")
    else:
        print("  未找到路径")
    
    # 测试3：完整证据收集
    print("\n【测试3：完整证据收集】")
    all_evidence = reasoning_engine.get_all_evidence(unit_id, function)
    
    print(f"\nPOI证据链数量: {len(all_evidence['poi_chains'])}")
    print(f"规则证据链数量: {len(all_evidence['rule_chains'])}")
    print(f"相似单元数量: {len(all_evidence['similar_units'])}")
    print(f"空间上下文: {all_evidence['spatial_context']}")
    
    return reasoning_engine


def main():
    print("=" * 60)
    print("Phase 2.3: 知识推理引擎测试")
    print("=" * 60)
    print()
    
    # 1. 加载数据
    units_gdf, poi_gdf, metro_lines, function_rules = load_test_data()
    if units_gdf is None:
        return
    
    # 2. 构建增强知识图谱
    kg = build_enhanced_knowledge_graph(units_gdf, poi_gdf, metro_lines, function_rules)
    
    # 3. 保存知识图谱
    output_file = "sample_data/processed/knowledge_graph_enhanced.json"
    kg.save_to_file(output_file)
    print(f"\n[OK] 保存增强知识图谱: {output_file}")
    
    # 4. 测试推理
    reasoning_engine = test_reasoning(kg)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()