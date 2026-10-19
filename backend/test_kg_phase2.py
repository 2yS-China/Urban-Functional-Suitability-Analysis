"""
Phase 2 测试脚本 - 知识图谱与自然语言生成

测试内容：
1. 从空间分析结果构建知识图谱
2. 保存和加载知识图谱
3. 测试各种问答查询
4. 生成自然语言解释
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import geopandas as gpd
import pandas as pd
import yaml
from spatial_analysis.feature_extractor import FeatureExtractor
from spatial_analysis.suitability_evaluator import SuitabilityEvaluator
from spatial_analysis.recommender import FunctionRecommender
from kg.knowledge_graph_builder import KnowledgeGraphBuilder, NodeType
from kg.nlg_generator import SpatialQA


def main():
    print("=" * 60)
    print("Phase 2 测试：知识图谱与自然语言生成")
    print("=" * 60)
    
    # ===== 1. 加载分析结果 =====
    print("\n步骤 1: 加载空间分析结果...")
    
    data_dir = project_root / "sample_data" / "processed"
    
    # 加载网格和分析结果
    grid_path = data_dir / "grid_square_100m.geojson"
    if not grid_path.exists():
        print(f"错误: 找不到网格文件 {grid_path}")
        return
    
    grid_gdf = gpd.read_file(grid_path)
    print(f"- 加载网格：{len(grid_gdf)} 个单元")
    
    # 加载规范化数据
    boundary_gdf = gpd.read_file(data_dir / "boundary_normalized.geojson")
    poi_gdf = gpd.read_file(data_dir / "poi_normalized.geojson")
    roads_gdf = gpd.read_file(data_dir / "roads_normalized.geojson")
    
    # ===== 2. 运行空间分析 =====
    print("\n步骤 2: 执行空间分析（缩减规模）...")
    
    # 只取前50个单元进行测试（加快速度）
    grid_small = grid_gdf.head(50).copy()
    print(f"- 使用 {len(grid_small)} 个单元进行测试")
    
    # 特征提取
    extractor = FeatureExtractor()
    
    # 使用 extract_all_features 批量提取
    grid_with_features = extractor.extract_all_features(
        units=grid_small,
        poi_data=poi_gdf,
        roads_data=roads_gdf
    )
    
    # 转换为字典格式
    features_dict = {}
    for idx, row in grid_with_features.iterrows():
        # 提取所有非几何列作为特征
        features = {
            col: row[col] for col in grid_with_features.columns 
            if col not in ['geometry', 'id'] and not pd.isna(row[col])
        }
        features_dict[str(idx)] = features
    
    print(f"- 特征提取完成：{len(features_dict)} 个单元")
    
    # 适宜性评价
    rules_path = project_root / "spatial_analysis" / "function_rules.yaml"
    evaluator = SuitabilityEvaluator(rules_config_path=str(rules_path))
    
    evaluation_gdf, details_gdf = evaluator.evaluate_all_functions(grid_with_features)
    
    print(f"- 适宜性评价完成")
    print(f"  - 评价功能类型: {evaluator.function_types}")
    
    # 功能推荐
    recommender = FunctionRecommender()
    result_gdf = recommender.recommend(evaluation_gdf, evaluator.function_types)
    
    print(f"- 功能推荐完成")
    
    # 构建 features_dict 和 suitability_matrix 供知识图谱使用
    features_dict = {}
    suitability_matrix = {}
    recommendations = {}
    
    for idx, row in result_gdf.iterrows():
        unit_id = str(idx)
        
        # 特征字典
        features = {
            col: row[col] for col in result_gdf.columns 
            if col not in ['geometry', 'id', 'unit_id', 'recommended_function', 'recommendation_score', 
                          'second_choice', 'second_score', 'reason'] 
            and not col.startswith('score_')
            and not pd.isna(row[col])
        }
        features_dict[unit_id] = features
        
        # 适宜性得分矩阵
        scores = {}
        for func_type in evaluator.function_types:
            score_col = f'score_{func_type}'
            if score_col in row:
                scores[func_type] = row[score_col]
        suitability_matrix[unit_id] = scores
        
        # 推荐结果
        recommendations[unit_id] = row['recommended_function']
    
    # ===== 3. 构建知识图谱 =====
    print("\n步骤 3: 构建知识图谱...")
    
    # 加载功能规则
    with open(rules_path, 'r', encoding='utf-8') as f:
        function_rules = yaml.safe_load(f)
    
    builder = KnowledgeGraphBuilder()
    kg = builder.build(
        units_gdf=grid_small,
        features_dict=features_dict,
        suitability_matrix=suitability_matrix,
        recommendations=recommendations,
        function_rules=function_rules
    )
    
    # 保存知识图谱
    kg_path = data_dir / "knowledge_graph.json"
    kg.save_to_file(str(kg_path))
    print(f"- 知识图谱已保存到: {kg_path}")
    
    # ===== 4. 测试问答系统 =====
    print("\n步骤 4: 测试问答系统...")
    
    qa = SpatialQA(kg)
    
    # 测试问题列表
    test_questions = [
        ("适宜性解释", "为什么单元 0 适合公共服务功能？"),
        ("区域查询", "哪些区域适合商业开发？"),
        ("对比分析", f"对比单元 0 和单元 5 的居住适宜性"),
        ("统计概览", "给出整体分析结果概览"),
    ]
    
    for category, question in test_questions:
        print(f"\n{'='*60}")
        print(f"[{category}] {question}")
        print('='*60)
        
        if category == "统计概览":
            answer = qa.answer(question, context={'recommendations': recommendations})
        else:
            answer = qa.answer(question)
        
        print(answer)
    
    # ===== 5. 直接调用NLG方法测试 =====
    print("\n\n步骤 5: 测试自然语言生成器直接调用...")
    
    from kg.nlg_generator import NaturalLanguageGenerator
    nlg = NaturalLanguageGenerator(kg)
    
    # 测试：查找最适合商业的区域
    print("\n" + "="*60)
    print("查询：最适合商业的前3个区域")
    print("="*60)
    result = nlg.find_suitable_regions("商业", min_score=0.3, top_n=3)
    print(result)
    
    # 测试：单元详细解释
    print("\n" + "="*60)
    print("查询：单元 0 适合公共服务的原因")
    print("="*60)
    result = nlg.explain_unit_suitability("0", "公共服务")
    print(result)
    
    print("\n" + "="*60)
    print("Phase 2 测试完成！")
    print("="*60)
    
    # 输出统计（重新导入NodeType，因为之前可能被局部变量覆盖）
    from kg.knowledge_graph_builder import NodeType as NT
    print(f"\n知识图谱统计:")
    print(f"- 节点数量: {len(kg.nodes)}")
    print(f"- 关系数量: {len(kg.relations)}")
    print(f"- 单元节点: {len(kg.get_nodes_by_type(NT.UNIT))} 个")
    print(f"- 功能节点: {len(kg.get_nodes_by_type(NT.FUNCTION))} 个")
    
    print(f"\n关系类型分布:")
    for rel_type, rels in kg._index['by_relation_type'].items():
        print(f"- {rel_type}: {len(rels)} 条")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()