"""
测试完整分析流程
"""
import sys
import geopandas as gpd
from pathlib import Path

# 添加backend目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """测试所有必需的导入"""
    print("1. Test imports...")
    try:
        from data_processor.normalizer import DataNormalizer
        from data_processor.grid_generator import GridGenerator
        from spatial_analysis.feature_extractor import FeatureExtractor
        from spatial_analysis.suitability_evaluator import SuitabilityEvaluator
        from spatial_analysis.recommender import FunctionRecommender
        print("[OK] All imports successful")
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        return False

def test_normalizer():
    """测试数据标准化器"""
    print("\n2. Test normalizer...")
    try:
        from data_processor.normalizer import DataNormalizer
        normalizer = DataNormalizer()
        
        # 使用测试数据
        test_boundary = Path("test_data_osm/boundary.geojson")
        if test_boundary.exists():
            gdf = normalizer.normalize_boundary(str(test_boundary), "default")
            print(f"[OK] Normalized boundary: {len(gdf)} features")
            return True
        else:
            print("[SKIP] Test data not found")
            return True
    except Exception as e:
        print(f"[FAIL] Normalization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_grid_generator():
    """测试网格生成器"""
    print("\n3. Test grid generator...")
    try:
        from data_processor.grid_generator import GridGenerator
        generator = GridGenerator()
        
        # 检查方法是否存在
        if hasattr(generator, 'generate_grid'):
            print("[OK] generate_grid method exists")
        else:
            print("[FAIL] generate_grid method not found")
            return False
        
        # 使用测试数据生成网格
        test_boundary = Path("test_data_osm/boundary.geojson")
        if test_boundary.exists():
            boundary_gdf = gpd.read_file(test_boundary)
            grid_gdf = generator.generate_grid(
                boundary=boundary_gdf,
                grid_size=100,
                mode='square',
                overlap_threshold=0.5
            )
            print(f"[OK] Generated grid: {len(grid_gdf)} cells")
            return True
        else:
            print("[SKIP] Test data not found")
            return True
    except Exception as e:
        print(f"[FAIL] Grid generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_feature_extractor():
    """测试特征提取器"""
    print("\n4. Test feature extractor...")
    try:
        from spatial_analysis.feature_extractor import FeatureExtractor
        extractor = FeatureExtractor()
        print("[OK] Feature extractor initialized")
        return True
    except Exception as e:
        print(f"[FAIL] Feature extractor initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Analysis Flow Test")
    print("=" * 60)
    
    results = []
    results.append(("Import Test", test_imports()))
    results.append(("Normalizer Test", test_normalizer()))
    results.append(("Grid Generator Test", test_grid_generator()))
    results.append(("Feature Extractor Test", test_feature_extractor()))
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("[PASS] All tests passed" if all_passed else "[FAIL] Some tests failed"))
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())