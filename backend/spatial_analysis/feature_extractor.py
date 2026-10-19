"""
空间特征提取模块
从空间数据中提取用于适宜性评价的特征
"""

import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from scipy.spatial import cKDTree
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """空间特征提取器"""
    
    def __init__(self):
        self.poi_tree = None
        self.poi_categories = {}
        self.road_tree = None
        
    def extract_all_features(
        self,
        units: gpd.GeoDataFrame,
        poi_data: Optional[gpd.GeoDataFrame] = None,
        roads_data: Optional[gpd.GeoDataFrame] = None,
        dem_path: Optional[str] = None,
        precipitation_path: Optional[str] = None,
        soil_path: Optional[str] = None,
        gdp_path: Optional[str] = None,
        flood_path: Optional[str] = None,
        hazard_path: Optional[str] = None,
        water_path: Optional[str] = None,
        redline_path: Optional[str] = None,
        farmland_path: Optional[str] = None,
        built_path: Optional[str] = None,
        center_path: Optional[str] = None,
        **kwargs
    ) -> gpd.GeoDataFrame:
        """提取所有空间特征"""
        result = units.copy()
        
        logger.info(f"开始提取空间特征，单元数: {len(units)}")
        
        if poi_data is not None:
            logger.info("提取区位特征...")
            result = self._extract_location_features(result, poi_data)
            logger.info("提取周边环境特征...")
            result = self._extract_density_features(result, poi_data)
        
        if roads_data is not None:
            logger.info("提取交通可达性特征...")
            result = self._extract_accessibility_features(result, roads_data)
        
        logger.info("提取几何特征...")
        result = self._extract_geometric_features(result)
        
        result = self._extract_raster_features(
            result,
            dem_path=dem_path,
            precipitation_path=precipitation_path,
            soil_path=soil_path,
            gdp_path=gdp_path,
            flood_path=flood_path,
            hazard_path=hazard_path
        )
        
        result = self._extract_constraint_features(
            result,
            water_path=water_path,
            redline_path=redline_path,
            farmland_path=farmland_path,
            built_path=built_path,
            center_path=center_path
        )
        
        logger.info("计算派生特征...")
        result = self.calculate_derived_features(result)
        
        logger.info(f"特征提取完成，共提取 {len(result.columns) - len(units.columns)} 个特征")
        
        return result
    
    def _extract_location_features(
        self,
        units: gpd.GeoDataFrame,
        poi_data: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """提取区位特征：距离最近POI的距离"""
        result = units.copy()
        
        poi_categories = poi_data['category'].unique()
        
        for category in poi_categories:
            category_pois = poi_data[poi_data['category'] == category]
            
            if len(category_pois) == 0:
                continue
            
            poi_coords = np.array([(p.x, p.y) for p in category_pois.geometry])
            tree = cKDTree(poi_coords)
            
            unit_coords = np.array([(u.x, u.y) for u in units.geometry.centroid])
            distances, _ = tree.query(unit_coords)
            
            distances_m = distances * 111000
            
            feature_name = f"dist_to_{category.lower().replace(' ', '_')}"
            result[feature_name] = distances_m
        
        if 'dist_to_交通设施' in result.columns:
            result['dist_to_metro'] = result['dist_to_交通设施']
            result['dist_to_bus'] = result['dist_to_交通设施'] * 0.5
        
        return result
    
    def _extract_density_features(
        self,
        units: gpd.GeoDataFrame,
        poi_data: gpd.GeoDataFrame,
        radii: List[int] = [500, 1000, 1500]
    ) -> gpd.GeoDataFrame:
        """提取密度特征：缓冲区内POI密度"""
        result = units.copy()
        
        poi_categories = poi_data['category'].unique()
        
        deg_per_m = 1 / 111000
        
        for radius in radii:
            radius_deg = radius * deg_per_m
            
            for category in poi_categories:
                category_pois = poi_data[poi_data['category'] == category]
                
                if len(category_pois) == 0:
                    continue
                
                densities = []
                for idx, unit in result.iterrows():
                    centroid = unit.geometry.centroid
                    buffer = centroid.buffer(radius_deg)
                    
                    poi_in_buffer = category_pois[category_pois.geometry.within(buffer)]
                    count = len(poi_in_buffer)
                    
                    densities.append(count)
                
                feature_name = f"poi_density_{category.lower().replace(' ', '_')}_{radius}m"
                result[feature_name] = densities
        
        for radius in radii:
            if f'poi_density_商业服务_{radius}m' in result.columns:
                result[f'poi_density_commercial_{radius}m'] = result[f'poi_density_商业服务_{radius}m']
            
            if f'poi_density_公共服务_{radius}m' in result.columns:
                result[f'poi_density_school_{radius}m'] = result[f'poi_density_公共服务_{radius}m']
            
            if f'poi_density_绿地公园_{radius}m' in result.columns:
                result[f'green_density_{radius}m'] = result[f'poi_density_绿地公园_{radius}m'] / 100
        
        return result
    
    def _extract_accessibility_features(
        self,
        units: gpd.GeoDataFrame,
        roads_data: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """提取交通可达性特征"""
        result = units.copy()
        
        if 'road_level' in roads_data.columns:
            for level in roads_data['road_level'].unique():
                level_roads = roads_data[roads_data['road_level'] == level]
                
                if len(level_roads) == 0:
                    continue
                
                distances = []
                for idx, unit in result.iterrows():
                    centroid = unit.geometry.centroid
                    
                    min_dist = float('inf')
                    for _, road in level_roads.iterrows():
                        dist = centroid.distance(road.geometry)
                        if dist < min_dist:
                            min_dist = dist
                    
                    distances.append(min_dist * 111000)
                
                result[f'dist_to_road_level_{level}'] = distances
        
        accessibility_scores = []
        
        for idx, unit in result.iterrows():
            score = 0.0
            
            weights = {1: 0.4, 2: 0.3, 3: 0.2, 4: 0.1}
            
            for level, weight in weights.items():
                col_name = f'dist_to_road_level_{level}'
                if col_name in result.columns:
                    dist = result.loc[idx, col_name]
                    score += weight * np.exp(-dist / 1000)
            
            accessibility_scores.append(score)
        
        result['road_accessibility'] = accessibility_scores
        
        if 'dist_to_road_level_1' in result.columns:
            result['dist_to_highway'] = result['dist_to_road_level_1']
        
        if 'dist_to_road_level_2' in result.columns:
            result['dist_to_major_road'] = result['dist_to_road_level_2']
        
        return result
    
    def _extract_geometric_features(
        self,
        units: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """提取几何特征"""
        result = units.copy()
        
        if 'area' not in result.columns:
            result['area'] = result.geometry.area * (111000 ** 2)
        
        perimeters = result.geometry.length * 111000
        areas = result['area']
        result['compactness'] = (perimeters ** 2) / (4 * np.pi * areas)
        
        result['boundary_complexity'] = perimeters / np.sqrt(areas)
        
        # 只在已有坡度数据时保留，不强制设为0
        if 'slope_mean' not in result.columns or result['slope_mean'].isna().all():
            # 如果没有坡度列或全为NaN，不设置slope_mean（表示数据缺失）
            if 'slope_mean' in result.columns:
                result.drop(columns=['slope_mean'], inplace=True)
        
        return result

    @staticmethod
    def _find_col(columns, patterns):
        """在列名列表中按模式匹配查找，支持中文/英文别名。

        Args:
            columns: 可用列名集合
            patterns: 候选模式列表，按优先级排序
        Returns:
            匹配到的第一个列名，或 None
        """
        for pat in patterns:
            if pat in columns:
                return pat
        return None

    def calculate_derived_features(
        self,
        features: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """计算派生特征（基于已有特征的组合和变换）。

        设计原则：
        - 尽可能从已有特征计算出有区分度的数值，而非返回常量
        - 添加特征别名（中文POI名 → 英文规则名），解决命名不匹配问题
        - 对真正无法计算的特征才使用默认值
        """
        result = features.copy()
        cols = set(result.columns)

        # ── 0. 特征别名映射：中文 POI 列 → 期望的英文列名 ──
        _alias_map = {
            'poi_density_商业服务': 'poi_density_commercial',
            'poi_density_公共服务': 'poi_density_school',
            'poi_density_交通设施': 'poi_density_transport',
            'poi_density_办公场所': 'poi_density_office',
            'poi_density_工业仓储': 'poi_density_industrial',
            'poi_density_绿地公园': 'poi_density_green',
            'poi_density_居住': 'poi_density_residential',
        }
        for src_prefix, dst_prefix in _alias_map.items():
            for suffix in ['_500m', '_1000m', '_1500m', '']:
                src = f'{src_prefix}{suffix}'
                dst = f'{dst_prefix}{suffix}'
                if src in cols and dst not in cols:
                    result[dst] = result[src]
                    cols.add(dst)

        # dist 别名
        if 'dist_to_交通设施' in cols and 'dist_to_metro' not in cols:
            result['dist_to_metro'] = result['dist_to_交通设施']
            cols.add('dist_to_metro')
        if 'dist_to_交通设施' in cols and 'dist_to_bus' not in cols:
            result['dist_to_bus'] = result['dist_to_交通设施'] * 0.5
            cols.add('dist_to_bus')
        if 'dist_to_road_level_4' in cols and 'dist_to_major_road' not in cols:
            result['dist_to_major_road'] = result['dist_to_road_level_4']
            cols.add('dist_to_major_road')
        if 'dist_to_road_level_1' in cols and 'dist_to_highway' not in cols:
            result['dist_to_highway'] = result['dist_to_road_level_1']
            cols.add('dist_to_highway')

        # 找到中心距离列
        center_pat = None
        for pat in ['dist_to_中心', 'dist_to_其他', 'dist_to_center']:
            if pat in cols:
                center_pat = pat
                break

        # ── 1. 人口密度估算 ──
        res_col = self._find_col(cols, [
            'poi_density_居住_1000m', 'poi_density_residential_1000m'])
        if res_col is not None:
            result['population_density_1000m'] = result[res_col] * 300 / np.pi
        else:
            total_poi_cols = [c for c in cols if c.startswith('poi_density_') and '_1000m' in c]
            if total_poi_cols:
                total_poi = sum(result[c] for c in total_poi_cols)
                result['population_density_1000m'] = np.clip(total_poi * 15, 500, 30000)
            else:
                result['population_density_1000m'] = 5000

        res_col_800 = self._find_col(cols, [
            'poi_density_居住_800m', 'poi_density_residential_800m'])
        if res_col_800 is not None:
            result['population_density_800m'] = result[res_col_800] * 300 / (np.pi * 0.64)
        elif 'population_density_1000m' in result.columns:
            result['population_density_800m'] = result['population_density_1000m'] * 1.2
        else:
            result['population_density_800m'] = 5000

        if 'population_density_1000m' in result.columns:
            result['population_coverage_1500m'] = result['population_density_1000m'] * np.pi * 2.25

        # ── 2. 商务中心距离 ──
        office_col = self._find_col(cols, [
            'poi_density_办公场所_1000m', 'poi_density_office_1000m'])
        if office_col is not None:
            max_office = result[office_col].max()
            if max_office > 0:
                result['dist_to_business_center'] = (1 - result[office_col] / max_office) * 5000
            else:
                result['dist_to_business_center'] = 5000.0
        else:
            result['dist_to_business_center'] = 2500.0

        # ── 3. 办公聚集度 ──
        office_500 = self._find_col(cols, [
            'poi_density_办公场所_500m', 'poi_density_office_500m'])
        if office_500 is not None:
            max_val = result[office_500].max()
            result['office_cluster'] = result[office_500] / max_val if max_val > 0 else 0.0
        else:
            result['office_cluster'] = 0.0

        # ── 4. 工业聚集度 + 距离工业区距离 ──
        ind_col = self._find_col(cols, [
            'poi_density_工业仓储_500m', 'poi_density_industrial_500m'])
        if ind_col is not None:
            max_val = result[ind_col].max()
            result['industrial_cluster'] = result[ind_col] / max_val if max_val > 0 else 0.0
        else:
            result['industrial_cluster'] = 0.0

        ind_1000 = self._find_col(cols, [
            'poi_density_工业仓储_1000m', 'poi_density_industrial_1000m'])
        if ind_1000 is not None:
            max_ind = result[ind_1000].max()
            result['dist_to_industrial'] = (1 - result[ind_1000] / max_ind) * 3000 if max_ind > 0 else 3000.0
        else:
            result['dist_to_industrial'] = 1500.0

        # ── 5. 距离居住区距离 ──
        res_1000 = self._find_col(cols, [
            'poi_density_居住_1000m', 'poi_density_residential_1000m'])
        if res_1000 is not None:
            max_rd = result[res_1000].max()
            result['dist_to_residential'] = (1 - result[res_1000] / max_rd) * 2000 if max_rd > 0 else 1000.0
        elif 'population_density_1000m' in result.columns:
            pop = result['population_density_1000m']
            pop_max = pop.max()
            result['dist_to_residential'] = (1 - pop / pop_max) * 2000 if pop_max > 0 else 1000.0
        else:
            result['dist_to_residential'] = 1000.0

        # ── 6. 现有绿地比例 ──
        if 'green_density_500m' in cols:
            result['existing_green_ratio'] = result['green_density_500m']
        else:
            result['existing_green_ratio'] = 0.1

        # ── 7. 可见性 ──
        if 'dist_to_major_road' in cols:
            result['visibility'] = np.exp(-result['dist_to_major_road'] / 200)
        elif 'road_accessibility' in cols:
            ra = result['road_accessibility']
            ra_max = ra.max()
            result['visibility'] = ra / ra_max if ra_max > 0 else 0.5
        else:
            result['visibility'] = 0.5

        # ── 8. 用地成本指数 ──
        if center_pat is not None:
            dist_center = result[center_pat]
            dc_max = dist_center.max()
            result['land_cost_index'] = 1 - (dist_center / dc_max) if dc_max > 0 else 0.3
        else:
            result['land_cost_index'] = 0.3

        # ── 9. 现有服务缺口 ──
        total_poi_cols = [c for c in cols if c.startswith('poi_density_') and '_500m' in c]
        if total_poi_cols:
            total_poi_500 = sum(result[c] for c in total_poi_cols)
            t_max = total_poi_500.max()
            result['existing_service_gap'] = 1 - (total_poi_500 / t_max) if t_max > 0 else 0.5
        else:
            result['existing_service_gap'] = 0.5

        # ── 10. 用地可获得性 ──
        factors = []
        if center_pat is not None:
            dc = result[center_pat]
            dc_max = dc.max()
            factors.append(dc / dc_max if dc_max > 0 else 0.5)
        if total_poi_cols:
            total_poi_500 = sum(result[c] for c in total_poi_cols)
            t_max = total_poi_500.max()
            factors.append(1 - total_poi_500 / t_max if t_max > 0 else 0.5)
        result['land_availability'] = np.mean(factors) if factors else 0.7

        # ── 11. 生态价值 ──
        eco_factors = []
        if 'green_density_500m' in cols:
            gd = result['green_density_500m']
            gd_max = gd.max()
            eco_factors.append(gd / gd_max if gd_max > 0 else 0.0)
        if 'green_density_1000m' in cols:
            gd = result['green_density_1000m']
            gd_max = gd.max()
            eco_factors.append(gd / gd_max if gd_max > 0 else 0.0)
        if 'dist_to_water_source' in cols:
            dw = result['dist_to_water_source']
            dw_max = dw.max()
            eco_factors.append(1 - dw / dw_max if dw_max > 0 else 0.3)
        result['ecological_value'] = np.mean(eco_factors) if eco_factors else 0.5

        # ── 12. 临水性 ──
        if 'dist_to_water_source' in cols:
            dw = result['dist_to_water_source']
            dw_max = dw.max()
            result['water_proximity'] = 1 - dw / dw_max if dw_max > 0 else 0.3
        else:
            result['water_proximity'] = 0.3

        # ── 13. 混合使用潜力（Shannon 多样性指数） ──
        poi_cat_cols_500 = [c for c in cols if c.startswith('poi_density_') and '_500m' in c]
        if poi_cat_cols_500:
            poi_matrix = np.array([result[c].values for c in poi_cat_cols_500]).T + 1e-10
            total = poi_matrix.sum(axis=1, keepdims=True)
            props = poi_matrix / total
            shannon = -np.sum(props * np.log(props + 1e-10), axis=1)
            max_shannon = np.log(len(poi_cat_cols_500))
            diversity = shannon / max_shannon if max_shannon > 0 else 0.0
            total_density = sum(result[c] for c in poi_cat_cols_500)
            td_max = total_density.max()
            density_norm = total_density / td_max if td_max > 0 else 0.0
            result['mixed_use_potential'] = 0.6 * diversity + 0.4 * density_norm
        else:
            result['mixed_use_potential'] = 0.6

        # ── 14. 密度均衡性 ──
        radii = ['500m', '1000m', '1500m']
        density_cols_all = [c for c in cols if c.startswith('poi_density_')]
        if density_cols_all:
            categories = set()
            for c in density_cols_all:
                for r in radii:
                    if f'_{r}' in c:
                        cat = c.replace(f'_{r}', '')
                        categories.add(cat)
            if categories:
                balance_scores = []
                for cat in list(categories)[:5]:
                    vals = []
                    for r in radii:
                        cn = f'{cat}_{r}'
                        if cn in cols:
                            vals.append(result[cn].values)
                    if len(vals) >= 2:
                        arr = np.array(vals, dtype=float)
                        arr_norm = arr / (arr.max(axis=0, keepdims=True) + 1e-10)
                        cv = np.std(arr_norm, axis=0) / (np.mean(arr_norm, axis=0) + 1e-10)
                        balance_scores.append(1 - np.clip(cv, 0, 1))
                result['density_balance'] = np.mean(balance_scores) if balance_scores else 0.5
            else:
                result['density_balance'] = 0.5
        else:
            result['density_balance'] = 0.5

        # ── 15. 连通性 ──
        conn_factors = []
        if 'road_accessibility' in cols:
            ra = result['road_accessibility']
            ra_max = ra.max()
            conn_factors.append(ra / ra_max if ra_max > 0 else 0.0)
        if poi_cat_cols_500:
            total_density = sum(result[c] for c in poi_cat_cols_500)
            td_max = total_density.max()
            conn_factors.append(total_density / td_max if td_max > 0 else 0.0)
        result['connectivity'] = np.mean(conn_factors) if conn_factors else 0.6

        # ── 16. 确保 dist_to_water_source 存在 ──
        if 'dist_to_water_source' not in cols:
            result['dist_to_water_source'] = 2000.0

        logger.info(f"计算派生特征完成，当前特征总数: {len(result.columns)}")

        return result

    def _extract_raster_features(
        self,
        units: gpd.GeoDataFrame,
        dem_path: Optional[str] = None,
        precipitation_path: Optional[str] = None,
        soil_path: Optional[str] = None,
        gdp_path: Optional[str] = None,
        flood_path: Optional[str] = None,
        hazard_path: Optional[str] = None
    ) -> gpd.GeoDataFrame:
        """提取栅格数据特征"""
        result = units.copy()
        
        try:
            from data_processor.raster_processor import process_dem_for_analysis
            from data_processor.raster_processor_extended import (
                process_precipitation_raster,
                process_soil_type_raster,
                process_gdp_density_raster,
                process_flood_risk_raster,
                process_geological_hazard_raster
            )
            
            if dem_path:
                logger.info("处理DEM数据...")
                result = process_dem_for_analysis(dem_path, result, result, include_aspect=False)
            
            if precipitation_path:
                logger.info("处理降水数据...")
                result = process_precipitation_raster(precipitation_path, result)
            
            if soil_path:
                logger.info("处理土壤数据...")
                result = process_soil_type_raster(soil_path, result)
            
            if gdp_path:
                logger.info("处理GDP数据...")
                result = process_gdp_density_raster(gdp_path, result)
            
            if flood_path:
                logger.info("处理洪涝风险...")
                result = process_flood_risk_raster(flood_path, result)
            
            if hazard_path:
                logger.info("处理地质灾害...")
                result = process_geological_hazard_raster(hazard_path, result)
        except ImportError as e:
            logger.warning(f"无法导入栅格处理模块: {e}")
        except Exception as e:
            logger.error(f"栅格特征提取失败: {e}")
        
        return result
    
    def _extract_constraint_features(
        self,
        units: gpd.GeoDataFrame,
        water_path: Optional[str] = None,
        redline_path: Optional[str] = None,
        farmland_path: Optional[str] = None,
        built_path: Optional[str] = None,
        center_path: Optional[str] = None
    ) -> gpd.GeoDataFrame:
        """提取矢量约束特征"""
        result = units.copy()
        
        try:
            from data_processor.vector_constraints import process_all_constraints
            
            logger.info("处理矢量约束数据...")
            result = process_all_constraints(
                result,
                water_path=water_path,
                redline_path=redline_path,
                farmland_path=farmland_path,
                built_path=built_path,
                center_path=center_path
            )
        except ImportError as e:
            logger.warning(f"无法导入矢量约束模块: {e}")
        except Exception as e:
            logger.error(f"约束特征提取失败: {e}")
        
        return result