"""
功能推荐模块
基于适宜性得分为每个单元推荐最佳功能
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FunctionRecommender:
    """功能推荐器"""
    
    def __init__(
        self,
        mode: str = 'max_score',
        min_acceptable_score: float = 0.4,
        spatial_coordination: bool = True
    ):
        """
        初始化推荐器
        
        Args:
            mode: 推荐模式（max_score/balanced/constraint_first）
            min_acceptable_score: 最小可接受分数
            spatial_coordination: 是否考虑空间协调
        """
        self.mode = mode
        self.min_acceptable_score = min_acceptable_score
        self.spatial_coordination = spatial_coordination
        
    def recommend(
        self,
        evaluation_result: gpd.GeoDataFrame,
        function_types: List[str]
    ) -> gpd.GeoDataFrame:
        """
        为所有单元推荐功能
        
        Args:
            evaluation_result: 适宜性评价结果
            function_types: 功能类型列表
            
        Returns:
            包含推荐结果的GeoDataFrame
        """
        result = evaluation_result.copy()
        
        logger.info(f"开始功能推荐，模式: {self.mode}")
        
        if self.mode == 'max_score':
            result = self._recommend_max_score(result, function_types)
        elif self.mode == 'balanced':
            result = self._recommend_balanced(result, function_types)
        elif self.mode == 'constraint_first':
            result = self._recommend_constraint_first(result, function_types)
        else:
            raise ValueError(f"不支持的推荐模式: {self.mode}")
        
        # 空间协调优化
        if self.spatial_coordination and len(result) > 0:
            logger.info("应用空间协调优化...")
            result = self._spatial_coordination_optimization(result, function_types)
        
        # 统计推荐结果
        self._log_statistics(result)
        
        return result
    
    def _recommend_max_score(
        self,
        data: gpd.GeoDataFrame,
        function_types: List[str]
    ) -> gpd.GeoDataFrame:
        """最大得分推荐：选择得分最高的功能"""
        result = data.copy()
        
        score_columns = [f'score_{ft}' for ft in function_types]
        
        # 找到每个单元的最高得分功能
        result['recommended_function'] = result[score_columns].idxmax(axis=1).str.replace('score_', '')
        result['recommendation_score'] = result[score_columns].max(axis=1)
        
        # 得分过低的标记为"待定"
        low_score_mask = result['recommendation_score'] < self.min_acceptable_score
        result.loc[low_score_mask, 'recommended_function'] = '待定'
        
        # 次优选择
        result['second_choice'] = result[score_columns].apply(
            lambda row: row.nlargest(2).index[-1].replace('score_', '') if len(row) >= 2 else '',
            axis=1
        )
        result['second_score'] = result[score_columns].apply(
            lambda row: row.nlargest(2).iloc[-1] if len(row) >= 2 else 0.0,
            axis=1
        )
        
        return result
    
    def _recommend_balanced(
        self,
        data: gpd.GeoDataFrame,
        function_types: List[str]
    ) -> gpd.GeoDataFrame:
        """平衡推荐：考虑整体功能分布平衡"""
        result = self._recommend_max_score(data, function_types)
        
        # 计算各功能当前分配数量
        func_counts = result['recommended_function'].value_counts()
        total_units = len(result[result['recommended_function'] != '待定'])
        
        if total_units == 0:
            return result
        
        # 目标：每种功能至少占5%
        min_ratio = 0.05
        min_count = int(total_units * min_ratio)
        
        for func_type in function_types:
            current_count = func_counts.get(func_type, 0)
            
            if current_count < min_count:
                needed = min_count - current_count
                
                # 找到该功能得分较高但未被推荐的单元
                candidates = result[
                    (result['recommended_function'] != func_type) &
                    (result[f'score_{func_type}'] > self.min_acceptable_score)
                ].copy()
                
                if len(candidates) > 0:
                    # 按该功能得分排序
                    candidates = candidates.sort_values(f'score_{func_type}', ascending=False)
                    
                    # 选择前N个
                    selected_ids = candidates.head(needed).index
                    result.loc[selected_ids, 'recommended_function'] = func_type
                    result.loc[selected_ids, 'recommendation_score'] = result.loc[selected_ids, f'score_{func_type}']
        
        return result
    
    def _recommend_constraint_first(
        self,
        data: gpd.GeoDataFrame,
        function_types: List[str]
    ) -> gpd.GeoDataFrame:
        """约束优先推荐：先满足关键功能需求"""
        # 关键功能优先级
        priority = ['公共服务', '绿地休闲', '居住', '商业', '办公', '工业', '综合']
        
        result = data.copy()
        result['recommended_function'] = '待定'
        result['recommendation_score'] = 0.0
        
        assigned = np.zeros(len(result), dtype=bool)
        
        for func_type in priority:
            if func_type not in function_types:
                continue
            
            score_col = f'score_{func_type}'
            
            # 找到该功能得分高且未分配的单元
            candidates = result[
                (~assigned) &
                (result[score_col] >= self.min_acceptable_score)
            ].copy()
            
            if len(candidates) == 0:
                continue
            
            # 选择得分最高的一批
            threshold = candidates[score_col].quantile(0.7)  # 前30%
            selected_mask = (
                (~assigned) &
                (result[score_col] >= threshold)
            )
            
            result.loc[selected_mask, 'recommended_function'] = func_type
            result.loc[selected_mask, 'recommendation_score'] = result.loc[selected_mask, score_col]
            assigned = assigned | selected_mask.values
        
        # 剩余单元使用最大得分策略
        remaining = result[~assigned]
        if len(remaining) > 0:
            score_columns = [f'score_{ft}' for ft in function_types]
            result.loc[~assigned, 'recommended_function'] = remaining[score_columns].idxmax(axis=1).str.replace('score_', '')
            result.loc[~assigned, 'recommendation_score'] = remaining[score_columns].max(axis=1)
        
        return result
    
    def _spatial_coordination_optimization(
        self,
        data: gpd.GeoDataFrame,
        function_types: List[str],
        iterations: int = 3
    ) -> gpd.GeoDataFrame:
        """
        空间协调优化：调整局部不协调的功能分配
        
        Args:
            data: 推荐结果
            function_types: 功能类型列表
            iterations: 迭代次数
        """
        result = data.copy()
        
        # 功能相容性矩阵（简化版）
        compatibility = {
            '居住': {'商业': 0.8, '公共服务': 0.9, '绿地休闲': 0.9, '办公': 0.6, '工业': 0.2, '综合': 0.8},
            '商业': {'居住': 0.8, '公共服务': 0.8, '办公': 0.9, '工业': 0.3, '绿地休闲': 0.6, '综合': 0.9},
            '办公': {'商业': 0.9, '居住': 0.6, '公共服务': 0.7, '绿地休闲': 0.7, '工业': 0.4, '综合': 0.8},
            '工业': {'工业': 1.0, '办公': 0.4, '商业': 0.3, '居住': 0.2, '公共服务': 0.3, '绿地休闲': 0.3, '综合': 0.4},
            '公共服务': {'居住': 0.9, '商业': 0.8, '办公': 0.7, '绿地休闲': 0.8, '工业': 0.3, '综合': 0.8},
            '绿地休闲': {'居住': 0.9, '商业': 0.6, '公共服务': 0.8, '办公': 0.7, '工业': 0.3, '综合': 0.7},
            '综合': {'居住': 0.8, '商业': 0.9, '办公': 0.8, '公共服务': 0.8, '绿地休闲': 0.7, '工业': 0.4}
        }
        
        for iteration in range(iterations):
            adjusted_count = 0
            
            for idx, unit in result.iterrows():
                current_func = unit['recommended_function']
                
                if current_func == '待定' or pd.isna(current_func):
                    continue
                
                # 找到邻接单元（简化：使用距离阈值）
                centroid = unit.geometry.centroid
                buffer = centroid.buffer(0.002)  # 约200m
                
                neighbors = result[
                    (result.index != idx) &
                    (result.geometry.centroid.within(buffer))
                ]
                
                if len(neighbors) == 0:
                    continue
                
                # 计算与邻居的协调度
                neighbor_funcs = neighbors['recommended_function'].value_counts()
                
                coordination_score = 0.0
                for neighbor_func, count in neighbor_funcs.items():
                    if neighbor_func == '待定' or pd.isna(neighbor_func):
                        continue
                    
                    compat = compatibility.get(current_func, {}).get(neighbor_func, 0.5)
                    coordination_score += compat * count
                
                coordination_score /= len(neighbors)
                
                # 如果协调度过低，考虑更换功能
                if coordination_score < 0.5:
                    # 尝试其他得分较高的功能
                    score_columns = [f'score_{ft}' for ft in function_types]
                    scores = unit[score_columns].astype(float)
                    
                    # 获取前3个候选
                    top3 = scores.nlargest(3)
                    
                    for alt_score_col in top3.index:
                        alt_func = alt_score_col.replace('score_', '')
                        alt_score = top3[alt_score_col]
                        
                        if alt_score < self.min_acceptable_score:
                            continue
                        
                        # 计算备选功能的协调度
                        alt_coordination = 0.0
                        for neighbor_func, count in neighbor_funcs.items():
                            if neighbor_func == '待定':
                                continue
                            compat = compatibility.get(alt_func, {}).get(neighbor_func, 0.5)
                            alt_coordination += compat * count
                        alt_coordination /= len(neighbors)
                        
                        # 如果备选功能协调度更高，则更换
                        if alt_coordination > coordination_score + 0.2:
                            result.loc[idx, 'recommended_function'] = alt_func
                            result.loc[idx, 'recommendation_score'] = alt_score
                            adjusted_count += 1
                            break
            
            logger.info(f"  迭代 {iteration + 1}: 调整 {adjusted_count} 个单元")
            
            if adjusted_count == 0:
                break
        
        return result
    
    def _log_statistics(self, result: gpd.GeoDataFrame):
        """记录推荐统计信息"""
        total = len(result)
        func_dist = result['recommended_function'].value_counts()
        
        logger.info("功能推荐统计:")
        for func, count in func_dist.items():
            ratio = count / total * 100
            logger.info(f"  {func}: {count} ({ratio:.1f}%)")


# 便捷函数
def recommend_functions(
    evaluation_result: gpd.GeoDataFrame,
    function_types: List[str],
    mode: str = 'max_score',
    **kwargs
) -> gpd.GeoDataFrame:
    """
    便捷函数：执行功能推荐
    
    Args:
        evaluation_result: 评价结果
        function_types: 功能类型列表
        mode: 推荐模式
        **kwargs: 其他参数
        
    Returns:
        推荐结果
    """
    recommender = FunctionRecommender(mode=mode, **kwargs)
    return recommender.recommend(evaluation_result, function_types)