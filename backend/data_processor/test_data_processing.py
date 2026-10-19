"""
测试数据处理模块
验证数据标准化和网格生成功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.data_processor import normalize_data, generate_analysis_units
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_data_processing():
    """测试完整的数据处理流程"""
    
    print("=" * 70)
    print("测试数据处理模块".center(70))
    print("=" * 70)
    print()
    
    # 数据文件路径
    boundary_file = "backend/sample_data/sample_boundary.geojson"
    poi_file = "backend/sample_data/sample_poi.geojson"
    roads_file = "backend/sample_data/sample_roads_grid.geojson"
    
    # 检查文件是否存在
    for file_path in [boundary_file, poi_file, roads_file]:
        if not Path(file_path).exists():
            print(f"⚠ 警告: {file_path} 不存在")
            print("请先运行示例数据生成脚本")
            return
    
    try:
        # 1. 标准化边界数据
        print("步骤 1: 标准化边界数据")
        print("-" * 70)
        boundary_gdf = normalize_data(
            boundary_file,
            data_type='boundary',
            source_type='geojson'
        )
        print(f"[OK] 边界数据标准化完成")
        print(f"  字段: {list(boundary_gdf.columns)}")
        print(f"  记录数: {len(boundary_gdf)}")
        print(f"  坐标系: {boundary_gdf.crs}")
        print()
        
        # 2. 标准化POI数据
        print("步骤 2: 标准化POI数据")
        print("-" * 70)
        poi_gdf = normalize_data(
            poi_file,
            data_type='poi',
            source_type='default'
        )
        print(f"[OK] POI数据标准化完成")
        print(f"  字段: {list(poi_gdf.columns)}")
        print(f"  记录数: {len(poi_gdf)}")
        print(f"  类别: {poi_gdf['category'].unique()}")
        print()
        
        # 3. 标准化路网数据
        print("步骤 3: 标准化路网数据")
        print("-" * 70)
        roads_gdf = normalize_data(
            roads_file,
            data_type='roads',
            source_type='default'
        )
        print(f"[OK] 路网数据标准化完成")
        print(f"  字段: {list(roads_gdf.columns)}")
        print(f"  记录数: {len(roads_gdf)}")
        print(f"  道路等级: {roads_gdf['road_level'].value_counts().to_dict()}")
        print()
        
        # 4. 生成方形网格
        print("步骤 4: 生成方形网格（100m）")
        print("-" * 70)
        grid_gdf = generate_analysis_units(
            boundary_gdf,
            mode='grid',
            grid_size=0.001,  # 约100m（经纬度）
            grid_type='square',
            overlap_threshold=0.5
        )
        print(f"[OK] 方形网格生成完成")
        print(f"  单元数: {len(grid_gdf)}")
        print(f"  字段: {list(grid_gdf.columns)}")
        print(f"  平均面积: {grid_gdf['area'].mean():.2f}")
        print()
        
        # 5. 生成六边形网格（对比）
        print("步骤 5: 生成六边形网格（100m）")
        print("-" * 70)
        hex_grid_gdf = generate_analysis_units(
            boundary_gdf,
            mode='grid',
            grid_size=0.001,
            grid_type='hexagon',
            overlap_threshold=0.5
        )
        print(f"[OK] 六边形网格生成完成")
        print(f"  单元数: {len(hex_grid_gdf)}")
        print()
        
        # 6. 保存结果
        print("步骤 6: 保存处理结果")
        print("-" * 70)
        output_dir = Path("backend/sample_data/processed")
        output_dir.mkdir(exist_ok=True)
        
        boundary_gdf.to_file(output_dir / "boundary_normalized.geojson", driver='GeoJSON')
        poi_gdf.to_file(output_dir / "poi_normalized.geojson", driver='GeoJSON')
        roads_gdf.to_file(output_dir / "roads_normalized.geojson", driver='GeoJSON')
        grid_gdf.to_file(output_dir / "grid_square_100m.geojson", driver='GeoJSON')
        hex_grid_gdf.to_file(output_dir / "grid_hexagon_100m.geojson", driver='GeoJSON')
        
        print(f"[OK] 所有结果已保存到: {output_dir}")
        print()
        
        # 总结
        print("=" * 70)
        print("数据处理测试完成！".center(70))
        print("=" * 70)
        print()
        print("处理结果:")
        print(f"  - 边界: {len(boundary_gdf)} 个要素")
        print(f"  - POI: {len(poi_gdf)} 个点位")
        print(f"  - 路网: {len(roads_gdf)} 条道路")
        print(f"  - 方形网格: {len(grid_gdf)} 个单元")
        print(f"  - 六边形网格: {len(hex_grid_gdf)} 个单元")
        print()
        print("[OK] Phase 1.1 数据处理模块验证通过")
        
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_data_processing()
    sys.exit(0 if success else 1)