"""
适宜性评价模块
基于多准则评价方法计算各功能类型的适宜性得分
"""

import geopandas as gpd
import numpy as np
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SuitabilityEvaluator:
    """适宜性评价器"""
    
    # 适宜性等级划分阈值
    SUITABILITY_LEVELS = {
        'suitable': {'min': 0.7, 'label': '适宜', 'description': '条件良好，非常适合该功能'},
        'moderate': {'min': 0.4, 'label': '一般适宜', 'description': '条件一般，可考虑该功能'},
        'unsuitable': {'min': 0.0, 'label': '不适宜', 'description': '条件较差，不适合该功能'}
    }
    
    def __init__(self, rules_config_path: Optional[str] = None):
        """
        初始化评价器
        
        Args:
            rules_config_path: 评价规则配置文件路径
        """
        if rules_config_path is None:
            rules_config_path = Path(__file__).parent / "function_rules.yaml"
        
        with open(rules_config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.function_types = self.config['function_types']
        self.scoring_config = self.config['scoring']
        
        logger.info(f"加载评价规则: {len(self.function_types)} 种功能类型")
    
    def evaluate_all_functions(
        self,
        features: gpd.GeoDataFrame
    ) -> Tuple[gpd.GeoDataFrame, Dict[str, gpd.GeoDataFrame]]:
        """
        评价所有功能类型的适宜性
        
        Args:
            features: 包含特征的GeoDataFrame
            
        Returns:
            (综合结果GeoDataFrame, 各功能详细得分字典)
        """
        result = features.copy()
        detailed_scores = {}
        
        logger.info("开始适宜性评价...")
        
        for func_type in self.function_types:
            logger.info(f"评价功能: {func_type}")
            
            # 评价单个功能
            scores, details = self.evaluate_single_function(features, func_type)
            
            # 添加到结果
            result[f'score_{func_type}'] = scores
            detailed_scores[func_type] = details
        
        # 确定推荐功能（每个单元得分最高的功能）
        score_columns = [f'score_{ft}' for ft in self.function_types]
        result['recommended_function'] = result[score_columns].idxmax(axis=1).str.replace('score_', '')
        result['max_score'] = result[score_columns].max(axis=1)
        
        logger.info("适宜性评价完成")
        
        return result, detailed_scores
    
    def evaluate_single_function(
        self,
        features: gpd.GeoDataFrame,
        function_type: str
    ) -> Tuple[np.ndarray, gpd.GeoDataFrame]:
        """
        评价单个功能类型的适宜性
        
        Args:
            features: 特征数据
            function_type: 功能类型
            
        Returns:
            (得分数组, 详细得分GeoDataFrame)
        """
        if function_type not in self.config:
            raise ValueError(f"未找到功能类型配置: {function_type}")
        
        func_config = self.config[function_type]
        criteria = func_config['criteria']
        
        # 初始化详细得分记录
        details = features[['unit_id', 'geometry']].copy()
        
        # 1. 计算各准则得分
        criterion_scores = []
        criterion_weights = []
        missing_features = []  # 记录缺失的特征
        
        for criterion in criteria:
            feature_name = criterion['feature']
            weight = criterion['weight']
            
            if feature_name not in features.columns:
                logger.warning(f"特征 '{feature_name}' 不存在，使用默认得分0.5")
                score = np.full(len(features), 0.5)
                missing_features.append(feature_name)
            else:
                feature_values = features[feature_name].values
                # 检查是否有大量缺失值
                nan_ratio = np.sum(np.isnan(feature_values)) / len(feature_values)
                if nan_ratio > 0.3:
                    logger.warning(f"特征 '{feature_name}' 缺失率 {nan_ratio:.1%}，可能影响评价准确性")
                    missing_features.append(feature_name)
                score = self._score_criterion(feature_values, criterion)
            
            criterion_scores.append(score)
            criterion_weights.append(weight)
            details[f'{feature_name}_score'] = score
        
        # 2. 加权求和
        criterion_scores = np.array(criterion_scores)
        criterion_weights = np.array(criterion_weights)
        
        # 归一化权重
        criterion_weights = criterion_weights / criterion_weights.sum()
        
        weighted_scores = criterion_scores * criterion_weights[:, np.newaxis]
        final_scores = weighted_scores.sum(axis=0)
        
        # 3. 应用约束条件
        if 'constraints' in func_config:
            final_scores = self._apply_constraints(
                final_scores,
                features,
                func_config['constraints']
            )
        
        # 4. 计算数据完整性置信度
        total_criteria = len(criteria)
        missing_count = len(missing_features)
        data_completeness = 1.0 - (missing_count / total_criteria) if total_criteria > 0 else 1.0
        
        details['final_score'] = final_scores
        details['data_completeness'] = data_completeness
        details['missing_features'] = str(missing_features) if missing_features else '[]'
        
        # 5. 添加适宜性等级划分
        details['suitability_level'] = self._classify_suitability(final_scores)
        details['suitability_label'] = details['suitability_level'].map(
            lambda x: self.SUITABILITY_LEVELS[x]['label']
        )
        
        return final_scores, details
    
    def _classify_suitability(self, scores: np.ndarray) -> np.ndarray:
        """
        将得分转换为适宜性等级
        
        Args:
            scores: 得分数组（0-1）
            
        Returns:
            等级数组（suitable/moderate/unsuitable）
        """
        levels = np.empty(len(scores), dtype='U20')
        
        # 按阈值划分等级
        levels[scores >= self.SUITABILITY_LEVELS['suitable']['min']] = 'suitable'
        levels[(scores >= self.SUITABILITY_LEVELS['moderate']['min']) & 
               (scores < self.SUITABILITY_LEVELS['suitable']['min'])] = 'moderate'
        levels[scores < self.SUITABILITY_LEVELS['moderate']['min']] = 'unsuitable'
        
        return levels
    
    def _score_criterion(
        self,
        values: np.ndarray,
        criterion: Dict
    ) -> np.ndarray:
        """
        为单个准则打分
        
        Args:
            values: 特征值数组
            criterion: 准则配置
            
        Returns:
            得分数组（0-1）
        """
        direction = criterion['direction']
        ideal_range = criterion['ideal_range']
        acceptable_range = criterion['acceptable_range']
        
        scores = np.zeros_like(values, dtype=float)
        
        ideal_min, ideal_max = ideal_range
        accept_min, accept_max = acceptable_range
        
        for i, val in enumerate(values):
            if np.isnan(val):
                scores[i] = 0.5  # 缺失值默认中等得分
                continue
            
            if direction == 'minimize':
                # 越小越好
                if val <= ideal_max:
                    scores[i] = 1.0
                elif val <= accept_max:
                    # 线性衰减
                    scores[i] = 1.0 - (val - ideal_max) / (accept_max - ideal_max) * 0.6
                else:
                    scores[i] = 0.0
            
            elif direction == 'maximize':
                # 越大越好
                if val >= ideal_min:
                    scores[i] = 1.0
                elif val >= accept_min:
                    # 线性上升
                    scores[i] = 0.4 + (val - accept_min) / (ideal_min - accept_min) * 0.6
                else:
                    scores[i] = 0.0
            
            # 确保得分在[0, 1]范围内
            scores[i] = np.clip(scores[i], 0.0, 1.0)
        
        return scores
    
    def _apply_constraints(
        self,
        scores: np.ndarray,
        features: gpd.GeoDataFrame,
        constraints: List[Dict]
    ) -> np.ndarray:
        """
        应用硬约束条件
        
        Args:
            scores: 原始得分
            features: 特征数据
            constraints: 约束配置列表
            
        Returns:
            应用约束后的得分
        """
        constrained_scores = scores.copy()
        
        for constraint in constraints:
            feature_name = constraint['feature']
            
            if feature_name not in features.columns:
                continue
            
            values = features[feature_name].values
            
            # 最小值约束
            if 'min' in constraint:
                min_val = constraint['min']
                mask = values < min_val
                constrained_scores[mask] *= 0.3  # 不满足约束，大幅降低得分
            
            # 最大值约束
            if 'max' in constraint:
                max_val = constraint['max']
                mask = values > max_val
                constrained_scores[mask] *= 0.3
        
        return constrained_scores
    
    def get_feature_importance(
        self,
        function_type: str
    ) -> Dict[str, float]:
        """
        获取某功能类型的特征重要性
        
        Args:
            function_type: 功能类型
            
        Returns:
            特征重要性字典
        """
        if function_type not in self.config:
            return {}
        
        func_config = self.config[function_type]
        criteria = func_config['criteria']
        
        importance = {}
        for criterion in criteria:
            feature = criterion['feature']
            weight = criterion['weight']
            importance[feature] = weight
        
        return importance
    
    def explain_score(
        self,
        unit_features: Dict,
        function_type: str
    ) -> Dict:
        """
        解释某单元某功能的得分
        
        Args:
            unit_features: 单元的特征字典
            function_type: 功能类型
            
        Returns:
            解释字典，包含各准则得分和原因
        """
        if function_type not in self.config:
            return {'error': f'未知功能类型: {function_type}'}
        
        func_config = self.config[function_type]
        criteria = func_config['criteria']
        
        explanation = {
            'function_type': function_type,
            'criteria_scores': [],
            'final_score': 0.0
        }
        
        total_score = 0.0
        total_weight = 0.0
        missing_features = []  # 记录缺失的特征
        
        for criterion in criteria:
            feature = criterion['feature']
            weight = criterion['weight']
            
            if feature not in unit_features:
                missing_features.append(feature)
                continue
            
            value = unit_features[feature]
            # 检查值是否为NaN
            if np.isnan(value):
                missing_features.append(feature)
                continue
            
            score = self._score_criterion(np.array([value]), criterion)[0]
            
            crit_info = {
                'feature': feature,
                'description': criterion.get('description', feature),
                'value': value,
                'score': score,
                'weight': weight,
                'direction': criterion['direction']
            }
            
            explanation['criteria_scores'].append(crit_info)
            total_score += score * weight
            total_weight += weight
        
        # 计算数据完整性
        total_criteria = len(criteria)
        missing_count = len(missing_features)
        data_completeness = 1.0 - (missing_count / total_criteria) if total_criteria > 0 else 1.0
        
        explanation['data_completeness'] = data_completeness
        explanation['missing_features'] = missing_features
        
        if total_weight > 0:
            final_score = total_score / total_weight
            explanation['final_score'] = final_score
            
            # 添加适宜性等级信息
            explanation['suitability_level'] = self._classify_suitability(np.array([final_score]))[0]
            explanation['suitability_label'] = self.SUITABILITY_LEVELS[explanation['suitability_level']]['label']
            explanation['suitability_description'] = self.SUITABILITY_LEVELS[explanation['suitability_level']]['description']
        else:
            # 如果没有有效数据，返回中性结果
            explanation['final_score'] = 0.5
            explanation['suitability_level'] = 'moderate'
            explanation['suitability_label'] = '一般适宜'
            explanation['suitability_description'] = '数据不足，无法准确评价'
        
        return explanation


# 便捷函数
def evaluate_suitability(
    features: gpd.GeoDataFrame,
    rules_config_path: Optional[str] = None
) -> Tuple[gpd.GeoDataFrame, Dict]:
    """
    便捷函数：执行适宜性评价
    
    Args:
        features: 特征数据
        rules_config_path: 规则配置路径
        
    Returns:
        (评价结果, 详细得分)
    """
    evaluator = SuitabilityEvaluator(rules_config_path)
    return evaluator.evaluate_all_functions(features)