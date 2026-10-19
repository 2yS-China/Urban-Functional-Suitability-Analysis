"""
完整使用示例：从 GIS 数据到知识图谱问答

展示完整流程：
1. 准备 GIS 数据
2. 空间分析（特征提取、适宜性评价）
3. 构建知识图谱
4. 自然语言问答
"""

import numpy as np
import geopandas as gpd
from shapely.geometry import box, Point
import json

from knowledge_graph_builder import (
    SpatialKnowledgeGraph, 
    KnowledgeGraphBuilder
)
from nlg_generator import SpatialQA


# ============ 第 1 步：准备模拟 GIS 数据 ============

def prepare_mock_data():
    """
    准备模拟的 GIS 数据
    实际使用中，这些数据来自 Shapefile、GeoJSON 等
    """
    print("准备模拟 GIS 数据...")
    
    # 创建 3x3 网格单元
    units = []
    for i in range(3):
        for j in range(3):
            geom = box(i*100, j*100, (i+1)*100, (j+1)*100)  # 100m x 100m 网格
            units.append({
                'geometry': geom,
                'unit_id': f"U_{i}_{j}"
            })
    
    units_gdf = gpd.GeoDataFrame(units)
    units_gdf = units_gdf.set_index('unit_id')
    
    print(f"  - 创建了 {len(units_gdf)} 个分析单元")
    
    return units_gdf


# ============ 第 2 步：空间分析 ============

def perform_spatial_analysis(units_gdf):
    """
    执行空间分析：特征提取 + 适宜性评价
    """
    print("\n执行空间分析...")
    
    # 2.1 特征提取（模拟）
    print("  - 提取空间特征...")
    features_dict = {}
    
    for unit_id, row in units_gdf.iterrows():
        centroid = row.geometry.centroid
        
        # 模拟不同位置的特征差异
        x, y = centroid.x, centroid.y
        
        features_dict[unit_id] = {
            # 区位特征（左下角交通更好）
            'dist_to_metro': 800 - (x + y) * 2 + np.random.randint(-50, 50),
            'dist_to_bus': 400 - (x + y) + np.random.randint(-30, 30),
            'metro_count_800m': max(0, int(3 - (x + y) / 100)),
            
            # 环境特征（右上角环境更好）
            'green_ratio_500m': min(0.5, 0.1 + (x + y) / 600 + np.random.random() * 0.1),
            
            # POI 特征
            'poi_教育_500m': np.random.randint(0, 5),
            'poi_商业_500m': np.random.randint(2, 15),
            'poi_医疗_500m': np.random.randint(0, 3),
            
            # 人口密度（中心区域更高）
            'population_density_1km': 8000 + (150 - abs(x-150) - abs(y-150)) * 50,
            
            # 地形特征
            'slope_mean': max(0, 2 + np.random.normal(0, 3)),
            'elevation_mean': 50 + y * 0.5 + np.random.randint(-5, 5)
        }
    
    # 2.2 适宜性评价（基于简单规则）
    print("  - 计算适宜性得分...")
    suitability_matrix = {}
    
    for unit_id, features in features_dict.items():
        scores = {}
        
        # 居住适宜性
        score_res = 0
        score_res += min(1.0, 800 / max(features['dist_to_metro'], 100)) * 0.3
        score_res += features['green_ratio_500m'] * 0.2
        score_res += min(1.0, features['poi_教育_500m'] / 3) * 0.2
        score_res += max(0, 1 - features['slope_mean'] / 20) * 0.15
        score_res += min(1.0, features['poi_医疗_500m'] / 2) * 0.15
        scores['居住'] = min(1.0, score_res)
        
        # 商业适宜性
        score_com = 0
        score_com += min(1.0, features['metro_count_800m'] / 2) * 0.35
        score_com += min(1.0, features['population_density_1km'] / 12000) * 0.3
        score_com += min(1.0, features['poi_商业_500m'] / 10) * 0.2
        score_com += min(1.0, 500 / max(features['dist_to_metro'], 100)) * 0.15
        scores['商业'] = min(1.0, score_com)
        
        # 办公适宜性
        score_off = 0
        score_off += min(1.0, 600 / max(features['dist_to_metro'], 100)) * 0.4
        score_off += min(1.0, features['metro_count_800m'] / 2) * 0.3
        score_off += min(1.0, features['poi_商业_500m'] / 8) * 0.3
        scores['办公'] = min(1.0, score_off)
        
        # 绿地休闲适宜性
        score_green = 0
        score_green += features['green_ratio_500m'] * 0.5
        score_green += max(0, 1 - features['slope_mean'] / 15) * 0.3
        score_green += min(1.0, features['elevation_mean'] / 80) * 0.2
        scores['绿地休闲'] = min(1.0, score_green)
        
        suitability_matrix[unit_id] = scores
    
    # 2.3 功能推荐（选择最高得分）
    print("  - 生成功能推荐...")
    recommendations = {}
    for unit_id, scores in suitability_matrix.items():
        best_function = max(scores.items(), key=lambda x: x[1])[0]
        recommendations[unit_id] = best_function
    
    print(f"  - 完成 {len(suitability_matrix)} 个单元的分析")
    
    return features_dict, suitability_matrix, recommendations


# ============ 第 3 步：构建知识图谱 ============

def build_knowledge_graph(units_gdf, features_dict, suitability_matrix, recommendations):
    """
    构建知识图谱
    """
    print("\n构建知识图谱...")
    
    # 功能规则配置
    function_rules = {
        '居住': {
            'description': '居住功能，适合建设住宅小区',
            'criteria': {
                'dist_to_metro': {'weight': 0.3, 'direction': 'minimize'},
                'green_ratio_500m': {'weight': 0.2, 'direction': 'maximize'}
            }
        },
        '商业': {
            'description': '商业功能，适合建设商业综合体',
            'criteria': {
                'metro_count_800m': {'weight': 0.35, 'direction': 'maximize'},
                'population_density_1km': {'weight': 0.3, 'direction': 'maximize'}
            }
        },
        '办公': {
            'description': '办公功能，适合建设写字楼',
            'criteria': {
                'dist_to_metro': {'weight': 0.4, 'direction': 'minimize'}
            }
        },
        '绿地休闲': {
            'description': '绿地休闲功能，适合建设公园绿地',
            'criteria': {
                'green_ratio_500m': {'weight': 0.5, 'direction': 'maximize'}
            }
        }
    }
    
    # 构建
    builder = KnowledgeGraphBuilder()
    kg = builder.build(
        units_gdf=units_gdf,
        features_dict=features_dict,
        suitability_matrix=suitability_matrix,
        recommendations=recommendations,
        function_rules=function_rules
    )
    
    return kg


# ============ 第 4 步：自然语言问答 ============

def interactive_qa(kg, recommendations):
    """
    交互式问答
    """
    print("\n" + "="*60)
    print("知识图谱问答系统已启动")
    print("="*60)
    
    qa = SpatialQA(kg)
    
    # 预设问题示例
    example_questions = [
        "为什么单元 U_0_0 适合居住功能？",
        "哪些区域适合商业开发？",
        "对比单元 U_0_0 和 U_2_2 的商业适宜性",
        "给出整体分析结果概览"
    ]
    
    print("\n预设问题演示：\n")
    
    for i, question in enumerate(example_questions, 1):
        print(f"\n{'─'*60}")
        print(f"问题 {i}: {question}")
        print(f"{'─'*60}\n")
        
        if '概览' in question:
            answer = qa.answer(question, context={'recommendations': recommendations})
        else:
            answer = qa.answer(question)
        
        print(answer)
    
    print("\n" + "="*60)
    print("演示完成")
    print("="*60)


# ============ 主流程 ============

def main():
    """
    主流程：完整演示
    """
    print("="*60)
    print("城市片区功能适宜性分析 - 知识图谱构建与问答演示")
    print("="*60)
    
    # 第 1 步：准备数据
    units_gdf = prepare_mock_data()
    
    # 第 2 步：空间分析
    features_dict, suitability_matrix, recommendations = perform_spatial_analysis(units_gdf)
    
    # 第 3 步：构建知识图谱
    kg = build_knowledge_graph(units_gdf, features_dict, suitability_matrix, recommendations)
    
    # 保存知识图谱
    output_file = 'knowledge_graph_demo.json'
    kg.save_to_file(output_file)
    print(f"\n知识图谱已保存到: {output_file}")
    
    # 输出图谱统计
    stats = kg.to_dict()['statistics']
    print(f"\n图谱统计:")
    print(f"  - 节点数: {stats['node_count']}")
    print(f"  - 关系数: {stats['relation_count']}")
    print(f"  - 节点类型: {stats['node_types']}")
    print(f"  - 关系类型: {stats['relation_types']}")
    
    # 第 4 步：问答演示
    interactive_qa(kg, recommendations)
    
    # 附加：展示原始数据样例
    print("\n" + "="*60)
    print("附：原始分析数据样例")
    print("="*60)
    
    sample_unit = 'U_0_0'
    print(f"\n单元 {sample_unit} 的特征:")
    for feature, value in features_dict[sample_unit].items():
        print(f"  - {feature}: {value:.2f}")
    
    print(f"\n单元 {sample_unit} 的适宜性得分:")
    for func, score in suitability_matrix[sample_unit].items():
        print(f"  - {func}: {score:.2f}")
    
    print(f"\n推荐功能: {recommendations[sample_unit]}")


if __name__ == "__main__":
    main()