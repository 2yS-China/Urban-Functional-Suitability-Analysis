"""
测试知识图谱可视化

从已有的knowledge_graph.json加载图谱并生成交互式网页
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from kg.knowledge_graph_builder import SpatialKnowledgeGraph, NodeType, RelationType
from kg.graph_visualizer import KnowledgeGraphVisualizer


def main():
    print("=" * 60)
    print("知识图谱可视化生成")
    print("=" * 60)
    
    # 加载已有的知识图谱
    kg_path = project_root / "sample_data" / "processed" / "knowledge_graph.json"
    
    if not kg_path.exists():
        print(f"\n错误: 找不到知识图谱文件 {kg_path}")
        print("请先运行 test_kg_phase2.py 生成知识图谱")
        return
    
    print(f"\n步骤 1: 加载知识图谱...")
    kg = SpatialKnowledgeGraph.load_from_file(str(kg_path))
    print(f"- 加载完成：{len(kg.nodes)} 个节点，{len(kg.relations)} 条关系")
    
    # 创建可视化器
    print(f"\n步骤 2: 创建可视化...")
    visualizer = KnowledgeGraphVisualizer(kg)
    
    # 生成完整图谱（限制单元数量避免过于复杂）
    output_dir = project_root / "sample_data" / "visualizations"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n正在生成可视化文件...")
    
    # 1. 完整图谱（最多50个单元）- 静态布局
    full_html = output_dir / "knowledge_graph_full.html"
    visualizer.create_interactive_html(
        output_path=str(full_html),
        title="城市功能适宜性知识图谱 - 完整视图",
        height="900px",
        physics_enabled=False,  # 静态布局
        show_buttons=True,
        max_units=50
    )
    print(f"[完成] 完整图谱: {full_html}")
    
    # 2. 仅适宜性关系（更清晰）- 静态布局
    suitability_html = output_dir / "knowledge_graph_suitability.html"
    visualizer.create_interactive_html(
        output_path=str(suitability_html),
        title="城市功能适宜性知识图谱 - 适宜性视图",
        height="900px",
        physics_enabled=False,  # 静态布局
        show_buttons=True,
        filter_relation_types=[
            RelationType.SUITABLE_FOR,
            RelationType.DOMINATED_BY
        ],
        max_units=50
    )
    print(f"[完成] 适宜性图谱: {suitability_html}")
    
    # 3. 空间关系网络 - 静态布局
    spatial_html = output_dir / "knowledge_graph_spatial.html"
    visualizer.create_interactive_html(
        output_path=str(spatial_html),
        title="城市功能适宜性知识图谱 - 空间关系视图",
        height="900px",
        physics_enabled=False,  # 静态布局
        show_buttons=True,
        filter_relation_types=[
            RelationType.ADJACENT,
            RelationType.SIMILAR_TO
        ],
        max_units=30  # 空间关系较多，减少节点
    )
    print(f"[完成] 空间关系图谱: {spatial_html}")
    
    print("\n" + "=" * 60)
    print("可视化生成完成！")
    print("=" * 60)
    print(f"\n生成了 3 个交互式网页：")
    print(f"1. 完整视图: {full_html.name}")
    print(f"2. 适宜性视图: {suitability_html.name}")
    print(f"3. 空间关系视图: {spatial_html.name}")
    print(f"\n保存位置: {output_dir}")
    print(f"\n使用浏览器打开HTML文件即可查看")
    print(f"支持：拖拽节点、滚轮缩放、点击查看详情")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print(f"\n错误: {e}")
        traceback.print_exc()