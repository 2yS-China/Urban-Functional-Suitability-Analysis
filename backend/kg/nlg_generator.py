"""
城市片区功能适宜性分析 - 自然语言生成模块

核心职责：
1. 基于知识图谱生成自然语言解释
2. 支持多种查询类型的文本生成
3. 提供模板化的可控生成
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
import re
from .knowledge_graph_builder import (
    SpatialKnowledgeGraph, 
    RelationType, 
    NodeType
)
from .reasoning_engine import ReasoningEngine, ReasoningChain


# ============ 问题类型枚举 ============

class QuestionType(Enum):
    """问答类型枚举"""
    EXPLAIN = "适宜性解释"      # 为什么某单元适合某功能
    QUERY = "区域查询"          # 哪些区域适合某功能
    COMPARE = "对比分析"        # 对比多个单元
    SUMMARY = "统计概览"        # 整体分析结果
    HELP = "帮助"               # 显示帮助信息


# ============ 要素描述模板 ============

FEATURE_DESCRIPTIONS = {
    # 距离类特征
    'dist_to_metro': {
        'name': '地铁站距离',
        'unit': '米',
        'good_threshold': 800,
        'templates': {
            'excellent': '距离地铁站仅 {value:.0f} 米，交通极为便利',
            'good': '距离地铁站约 {value:.0f} 米，交通便利',
            'moderate': '距离地铁站 {value:.0f} 米，交通可达',
            'poor': '距离地铁站较远（{value:.0f} 米），交通便利性一般'
        }
    },
    'dist_to_bus': {
        'name': '公交站距离',
        'unit': '米',
        'good_threshold': 500,
        'templates': {
            'excellent': '公交站就在 {value:.0f} 米范围内',
            'good': '周边 {value:.0f} 米内有公交站',
            'moderate': '公交站距离适中（{value:.0f} 米）',
            'poor': '距离公交站较远（{value:.0f} 米）'
        }
    },
    
    # 比例类特征
    'green_ratio_500m': {
        'name': '绿地覆盖率',
        'unit': '%',
        'good_threshold': 0.3,
        'templates': {
            'excellent': '周边 500 米范围内绿地覆盖率高达 {value:.1f}%，环境优美',
            'good': '周边绿地覆盖率达 {value:.1f}%，环境宜居',
            'moderate': '周边绿地覆盖率 {value:.1f}%',
            'poor': '周边绿地较少（覆盖率 {value:.1f}%）'
        }
    },
    
    # 数量类特征
    'poi_教育_500m': {
        'name': '教育设施数量',
        'unit': '所',
        'good_threshold': 2,
        'templates': {
            'excellent': '周边有 {value:.0f} 所教育设施，学区资源充足',
            'good': '周边有 {value:.0f} 所教育设施',
            'moderate': '周边教育设施 {value:.0f} 所',
            'poor': '周边教育设施较少（{value:.0f} 所）'
        }
    },
    'poi_商业_500m': {
        'name': '商业设施数量',
        'unit': '个',
        'good_threshold': 5,
        'templates': {
            'excellent': '周边商业设施密集（{value:.0f} 个），商业氛围浓厚',
            'good': '周边有 {value:.0f} 个商业设施',
            'moderate': '周边商业设施 {value:.0f} 个',
            'poor': '周边商业设施较少（{value:.0f} 个）'
        }
    },
    'metro_count_800m': {
        'name': '地铁站数量',
        'unit': '个',
        'good_threshold': 1,
        'templates': {
            'excellent': '800 米范围内有 {value:.0f} 个地铁站，交通枢纽区位优越',
            'good': '800 米范围内有 {value:.0f} 个地铁站',
            'moderate': '附近有地铁站 {value:.0f} 个',
            'poor': '地铁可达性一般'
        }
    },
    
    # 密度类特征
    'population_density_1km': {
        'name': '人口密度',
        'unit': '人/km²',
        'good_threshold': 10000,
        'templates': {
            'excellent': '周边 1 公里人口密度达 {value:.0f} 人/km²，人气旺盛',
            'good': '周边人口密度 {value:.0f} 人/km²，有一定人气',
            'moderate': '周边人口密度 {value:.0f} 人/km²',
            'poor': '周边人口密度较低（{value:.0f} 人/km²）'
        }
    },
    
    # 地形类特征
    'slope_mean': {
        'name': '平均坡度',
        'unit': '度',
        'good_threshold': 5,
        'templates': {
            'excellent': '地势平坦（平均坡度 {value:.1f}°），开发条件优越',
            'good': '地势较为平坦（坡度 {value:.1f}°）',
            'moderate': '地势起伏适中（坡度 {value:.1f}°）',
            'poor': '地势较陡（坡度 {value:.1f}°），开发难度较大'
        }
    },
    'elevation_mean': {
        'name': '平均海拔',
        'unit': '米',
        'good_threshold': None,
        'templates': {
            'default': '海拔 {value:.0f} 米'
        }
    }
}


# ============ 功能适宜性描述 ============

FUNCTION_SUITABILITY_TEMPLATES = {
    'excellent': '属于**高度适宜区域**（得分 {score:.2f}）',
    'good': '属于**较适宜区域**（得分 {score:.2f}）',
    'moderate': '属于**中等适宜区域**（得分 {score:.2f}）',
    'poor': '**适宜性较低**（得分 {score:.2f}）'
}


def get_suitability_level(score: float) -> str:
    """根据得分判断适宜性等级"""
    if score >= 0.8:
        return 'excellent'
    elif score >= 0.6:
        return 'good'
    elif score >= 0.4:
        return 'moderate'
    else:
        return 'poor'


# ============ 自然语言生成器 ============

class NaturalLanguageGenerator:
    """
    自然语言生成器
    基于知识图谱和模板生成可读文本
    
    Phase 2.4 更新：集成推理引擎，支持多跳推理解释
    """
    
    def __init__(self, kg: SpatialKnowledgeGraph, enable_reasoning: bool = True):
        self.kg = kg
        self.reasoning_engine = ReasoningEngine(kg) if enable_reasoning else None
    
    # ===== 单元适宜性解释 =====
    
    def explain_unit_suitability(self, unit_id: str, function_type: str, 
                                use_reasoning: bool = True, max_depth: int = 4) -> str:
        """
        解释为什么某个单元适合某种功能
        
        Phase 2.4 更新：
        - use_reasoning=True 时使用推理引擎生成深度解释
        - use_reasoning=False 时使用原有基于特征模板的方法
        """
        unit_node = self.kg.get_node(unit_id)
        if not unit_node:
            return f"未找到单元 {unit_id}"
        
        # 获取适宜性得分
        suitable_relations = self.kg.get_outgoing_relations(unit_id, RelationType.SUITABLE_FOR)
        score = None
        for rel in suitable_relations:
            if rel.target == f"func_{function_type}":
                score = rel.weight
                break
        
        if score is None:
            return f"单元 {unit_id} 没有 {function_type} 功能的适宜性评分"
        
        # 开始生成文本
        level = get_suitability_level(score)
        text = f"## 单元 {unit_id} - {function_type}功能适宜性分析\n\n"
        text += FUNCTION_SUITABILITY_TEMPLATES[level].format(score=score) + "\n\n"
        
        # Phase 2.4: 使用推理引擎生成深度解释
        if use_reasoning and self.reasoning_engine:
            text += self._generate_reasoning_explanation(unit_id, function_type, max_depth)
        else:
            # 原有方法：基于特征模板
            text += self._generate_feature_explanation(unit_id, function_type, unit_node)
        
        # 添加空间位置信息
        centroid = unit_node.properties.get('centroid', {})
        text += f"\n**位置**: ({centroid.get('lon', 0):.6f}, {centroid.get('lat', 0):.6f})\n"
        text += f"**面积**: {unit_node.properties.get('area', 0):.0f} 平方米\n"
        
        return text
    
    def _generate_reasoning_explanation(self, unit_id: str, function_type: str, 
                                       max_depth: int = 4) -> str:
        """
        使用推理引擎生成深度解释（Phase 2.4 新增）
        """
        text = "### 适宜性分析（基于推理链）\n\n"
        
        # 获取推理链
        try:
            reasoning_chains = self.reasoning_engine.explain_suitability(
                unit_id, function_type, max_depth
            )
            
            if not reasoning_chains:
                # 降级到特征模板方法
                unit_node = self.kg.get_node(unit_id)
                return self._generate_feature_explanation(unit_id, function_type, unit_node)
            
            # 简化版：直接展示所有推理链
            text += "#### 推理证据链\n\n"
            for i, chain in enumerate(reasoning_chains, 1):
                nl_text = chain.to_natural_language()
                if nl_text:
                    text += f"{i}. {nl_text}\n"
            text += "\n"
            
            # 3. 空间上下文（可选）
            evidence = self.reasoning_engine.get_all_evidence(unit_id, function_type)
            if evidence.get('spatial_context'):
                text += "#### 周边环境\n\n"
                spatial_ctx = evidence['spatial_context']
                if spatial_ctx.get('adjacent_functions'):
                    func_dist = spatial_ctx['adjacent_functions']
                    top_funcs = sorted(func_dist.items(), key=lambda x: x[1], reverse=True)[:3]
                    text += "相邻单元功能分布：\n"
                    for func, count in top_funcs:
                        text += f"- {func}: {count}个单元\n"
                text += "\n"
            
        except Exception as e:
            # 出错时降级到特征模板方法
            text += f"（推理引擎暂不可用，使用基础分析）\n\n"
            unit_node = self.kg.get_node(unit_id)
            text += self._generate_feature_explanation(unit_id, function_type, unit_node)
        
        return text
    
    def _generate_feature_explanation(self, unit_id: str, function_type: str, 
                                     unit_node) -> str:
        """
        使用特征模板生成解释（原有方法）
        """
        text = "### 主要原因\n\n"
        
        # 提取关键影响因素
        features = unit_node.properties.get('features', {})
        key_factors = self._analyze_key_factors(features, function_type, 
                                               unit_node.properties.get('suitability_score', 0))
        
        if key_factors:
            for i, factor in enumerate(key_factors[:15], 1):  # 最多列15条
                text += f"{i}. {factor}\n"
        
        return text
    
    def _analyze_key_factors(self, features: Dict[str, float], 
                            function_type: str, score: float) -> List[str]:
        """
        分析影响适宜性的关键因素
        遍历单元中所有已上传的特征，为每个有效特征生成描述
        
        优先级：先输出功能相关的关键特征，再输出其他有效特征
        """
        if not features:
            return []
        
        factors = []
        described_keys = set()
        
        # 第一优先级：功能相关的关键特征
        key_features = self._get_key_features_for_function(function_type)
        for feature_name in key_features:
            if feature_name in features and feature_name not in described_keys:
                value = features[feature_name]
                if self._is_feature_valid(feature_name, value):
                    desc = self._describe_feature(feature_name, value)
                    if desc:
                        factors.append(desc)
                        described_keys.add(feature_name)
        
        # 第二优先级：遍历所有剩余有效特征
        for feature_name, value in features.items():
            if feature_name in described_keys:
                continue
            if self._is_feature_valid(feature_name, value):
                desc = self._describe_feature(feature_name, value)
                if desc:
                    factors.append(desc)
                    described_keys.add(feature_name)
        
        return factors
    
    def _is_feature_valid(self, feature_name: str, value: float) -> bool:
        """判断特征值是否有效（非0且非缺失）"""
        # 过滤掉元数据特征（不属于空间分析特征）
        metadata_features = {'centroid_x', 'centroid_y', 'centroid_x_labeled', 
                           'centroid_y_labeled', 'compactness', 'boundary_complexity',
                           'area', 'boundary_area', 'max_score'}
        if feature_name in metadata_features or feature_name.startswith('centroid'):
            return False
        
        if value is None:
            return False
        if value == 0 or (isinstance(value, float) and abs(value) < 1e-6):
            # 距离类、数量类特征的0值是有效信息
            if 'dist_' in feature_name or 'count' in feature_name:
                return True
            # 密度、比例等类特征0值通常表示无数据
            return False
        return True
    
    def _get_key_features_for_function(self, function_type: str) -> List[str]:
        """获取某功能的关键特征列表"""
        feature_priority = {
            '居住': [
                'dist_to_metro', 'green_ratio_500m', 'poi_教育_500m', 
                'slope_mean', 'dist_to_bus'
            ],
            '商业': [
                'metro_count_800m', 'population_density_1km', 
                'poi_商业_500m', 'dist_to_metro'
            ],
            '办公': [
                'dist_to_metro', 'metro_count_800m', 'poi_商业_500m'
            ],
            '工业': [
                'dist_to_metro', 'slope_mean', 'population_density_1km'
            ],
            '公共服务': [
                'dist_to_metro', 'dist_to_bus', 'population_density_1km', 
                'green_ratio_500m'
            ],
            '绿地': [
                'green_ratio_500m', 'slope_mean', 'elevation_mean'
            ],
            '绿地休闲': [
                'green_ratio_500m', 'slope_mean', 'elevation_mean'
            ],
            '混合': [
                'dist_to_metro', 'poi_商业_500m', 'population_density_1km',
                'green_ratio_500m'
            ]
        }
        return feature_priority.get(function_type, list(FEATURE_DESCRIPTIONS.keys()))
    
    def _describe_feature(self, feature_name: str, value: float) -> Optional[str]:
        """将特征值转为描述性文本，支持预定义模板和动态特征名解析"""
        
        # 优先使用预定义模板
        if feature_name in FEATURE_DESCRIPTIONS:
            return self._describe_known_feature(feature_name, value)
        
        # 动态特征名解析
        return self._describe_dynamic_feature(feature_name, value)
    
    def _describe_known_feature(self, feature_name: str, value: float) -> Optional[str]:
        """使用预定义模板描述已知特征"""
        config = FEATURE_DESCRIPTIONS[feature_name]
        templates = config['templates']
        
        # 如果是比例类特征，转为百分比
        if config['unit'] == '%':
            value = value * 100
        
        # 对于0值，使用default模板（如果有），否则返回None
        if value == 0 or (isinstance(value, float) and abs(value) < 1e-6):
            if 'default' in templates:
                return templates['default'].format(value=value)
            return None
        
        # 判断等级
        level = 'default'
        if 'good_threshold' in config and config['good_threshold'] is not None:
            threshold = config['good_threshold']
            
            if 'dist_' in feature_name:
                if value <= threshold * 0.5:
                    level = 'excellent'
                elif value <= threshold:
                    level = 'good'
                elif value <= threshold * 1.5:
                    level = 'moderate'
                else:
                    level = 'poor'
            else:
                if value >= threshold * 1.5:
                    level = 'excellent'
                elif value >= threshold:
                    level = 'good'
                elif value >= threshold * 0.5:
                    level = 'moderate'
                else:
                    level = 'poor'
        
        if level in templates:
            return templates[level].format(value=value)
        elif 'default' in templates:
            return templates['default'].format(value=value)
        else:
            return f"{config['name']}: {value:.2f} {config['unit']}"
    
    def _describe_dynamic_feature(self, feature_name: str, value: float) -> Optional[str]:
        """
        解析动态特征名并生成描述文本
        支持常见命名约定：
        - dist_to_XXX → 距离XXX
        - poi_count_XXX_500m / poi_density_XXX_500m → POI设施
        - road_density_500m → 道路密度
        - green_density_500m → 绿地密度
        - building_density → 建筑密度
        - land_use_XXX → 土地利用
        - population_XXX → 人口
        - 以其他模式作为通用处理
        """
        
        # 距离类: dist_to_XXX
        m = re.match(r'^dist_to_(.+)$', feature_name)
        if m:
            target = m.group(1)
            if value < 200:
                return f"距离{target}仅 {value:.0f} 米，极为便利"
            elif value < 500:
                return f"距离{target}约 {value:.0f} 米，较为便利"
            elif value < 1000:
                return f"距离{target} {value:.0f} 米，可达性良好"
            else:
                return f"距离{target}较远（{value:.0f} 米）"
        
        # POI数量类: poi_count_XXX_XXXm
        m = re.match(r'^poi_count_(.+?)_(\d+)m$', feature_name)
        if m:
            poi_type, radius = m.group(1), m.group(2)
            if value >= 10:
                return f"{radius}米范围内有 {value:.0f} 个{poi_type} POI，密度较高"
            elif value >= 3:
                return f"{radius}米范围内有 {value:.0f} 个{poi_type} POI"
            elif value > 0:
                return f"{radius}米范围内有 {value:.0f} 个{poi_type} POI，数量较少"
            return None
        
        # POI密度类: poi_density_XXX_XXXm
        m = re.match(r'^poi_density_(.+?)_(\d+)m$', feature_name)
        if m:
            poi_type, radius = m.group(1), m.group(2)
            if value > 50:
                return f"{radius}米范围内{poi_type} POI密度很高（{value:.0f}），设施密集"
            elif value > 20:
                return f"{radius}米范围内{poi_type} POI密度为 {value:.0f}，设施充足"
            elif value > 5:
                return f"{radius}米范围内有{poi_type}设施 {value:.0f} 处"
            elif value > 0:
                return f"{radius}米范围内{poi_type}设施较少（{value:.0f}）"
            return None
        
        # 绿地密度: green_density_500m / green_density_1000m
        m = re.match(r'^green_density_(\d+)m$', feature_name)
        if m:
            radius = m.group(1)
            if value > 0.3:
                return f"{radius}米范围内绿地密度较高（{value:.2f}），环境优美"
            elif value > 0.1:
                return f"{radius}米范围内有一定绿地分布（密度 {value:.2f}）"
            elif value > 0:
                return f"{radius}米范围内绿地较少（密度 {value:.2f}）"
            return None
        
        # 道路密度: road_density_500m
        m = re.match(r'^road_density_(\d+)m$', feature_name)
        if m:
            radius = m.group(1)
            if value > 0.8:
                return f"{radius}米范围内道路密度较高（{value:.2f}），路网发达"
            elif value > 0.4:
                return f"{radius}米范围内道路密度适中（{value:.2f}）"
            else:
                return f"{radius}米范围内道路密度较低（{value:.2f}）"
        
        # 道路可达性: road_accessibility
        if feature_name == 'road_accessibility':
            if value > 0.8:
                return "交通可达性很高，道路网络完善"
            elif value > 0.5:
                return "交通可达性良好"
            else:
                return "交通可达性一般"
        
        # 人口密度: population_density_XXXm
        m = re.match(r'^population_density_(\d+)m$', feature_name)
        if m:
            radius = m.group(1)
            if value > 15000:
                return f"{radius}米范围内人口密度达 {value:.0f} 人/km²，人气旺盛"
            elif value > 8000:
                return f"{radius}米范围内人口密度 {value:.0f} 人/km²，有一定人气"
            elif value > 2000:
                return f"{radius}米范围内人口密度 {value:.0f} 人/km²"
            else:
                return f"{radius}米范围内人口密度较低（{value:.0f} 人/km²）"
        
        # 建筑密度: building_density / building_density_500m
        m = re.match(r'^building_density(?:_(\d+)m)?$', feature_name)
        if m:
            suffix = f"（{m.group(1)}米范围内）" if m.group(1) else ""
            if value > 0.5:
                return f"建筑密度{suffix}较高（{value:.2f}），开发强度大"
            elif value > 0.2:
                return f"建筑密度{suffix}适中（{value:.2f}）"
            else:
                return f"建筑密度{suffix}较低（{value:.2f}）"
        
        # 绿地率: green_ratio_XXXm
        m = re.match(r'^green_ratio_(\d+)m$', feature_name)
        if m:
            radius = m.group(1)
            pct = value * 100
            if pct > 30:
                return f"{radius}米范围内绿地覆盖率达 {pct:.1f}%，环境优美"
            elif pct > 15:
                return f"{radius}米范围内绿地覆盖率为 {pct:.1f}%"
            else:
                return f"{radius}米范围内绿地覆盖率较低（{pct:.1f}%）"
        
        # 土地利用混合度: land_use_mixedness / land_use_mixedness_500m
        m = re.match(r'^land_use_mixedness(?:_(\d+)m)?$', feature_name)
        if m:
            suffix = f"（{m.group(1)}米范围内）" if m.group(1) else ""
            if value > 0.7:
                return f"土地利用混合度{suffix}较高（{value:.2f}），功能多样"
            elif value > 0.4:
                return f"土地利用混合度{suffix}适中（{value:.2f}）"
            else:
                return f"土地利用混合度{suffix}较低（{value:.2f}）"
        
        # 混合使用潜力: mixed_use_potential
        if feature_name == 'mixed_use_potential':
            if value > 0.7:
                return f"混合使用潜力较高（{value:.2f}），适合发展综合体"
            elif value > 0.4:
                return f"混合使用潜力适中（{value:.2f}）"
            else:
                return f"混合使用潜力较低（{value:.2f}）"
        
        # 连通性: connectivity
        if feature_name == 'connectivity':
            if value > 0.8:
                return "区域连通性很高，交通网络完善"
            elif value > 0.5:
                return "区域连通性良好"
            else:
                return "区域连通性一般"
        
        # 生态价值: ecological_value
        if feature_name == 'ecological_value':
            if value > 0.7:
                return "生态价值较高，自然环境良好"
            elif value > 0.4:
                return "生态价值适中"
            else:
                return "生态价值较低"
        
        # 水源距离: dist_to_water_source
        if feature_name == 'dist_to_water_source':
            if value < 200:
                return "距离水源很近（{:.0f} 米），水资源丰富".format(value)
            elif value < 500:
                return "距离水源较近（{:.0f} 米）".format(value)
            else:
                return "距离水源较远（{:.0f} 米）".format(value)
        
        # 土地成本指数: land_cost_index
        if feature_name == 'land_cost_index':
            if value > 0.7:
                return f"区位成本指数较高（{value:.2f}），地价较贵"
            elif value > 0.4:
                return f"区位成本指数适中（{value:.2f}）"
            else:
                return f"区位成本指数较低（{value:.2f}）"
        
        # 可视性: visibility
        if feature_name == 'visibility':
            if value > 0.7:
                return "区域可视性良好，展示效果好"
            elif value > 0.4:
                return "区域可视性一般"
            else:
                return "区域可视性较差"
        
        # 现有绿地率: existing_green_ratio
        if feature_name == 'existing_green_ratio':
            pct = value * 100
            if pct > 30:
                return f"现有绿地覆盖率 {pct:.1f}%，生态基础好"
            elif pct > 15:
                return f"现有绿地覆盖率 {pct:.1f}%"
            else:
                return f"现有绿地覆盖率较低（{pct:.1f}%）"
        
        # 通用数量类: count_XXX 或 *_count
        m = re.match(r'^(?:count_|.*_count$)', feature_name)
        if m:
            clean_name = feature_name.replace('_count', '').replace('count_', '')
            return f"{clean_name}数量: {value:.0f}"
        
        # 通用密度类: *_density
        m = re.match(r'^(.+)_density(?:_(\d+)m)?$', feature_name)
        if m:
            if value == 0 or (isinstance(value, float) and abs(value) < 1e-6):
                return None  # 密度为0通常表示无数据
            cat, radius = m.group(1), m.group(2)
            suffix = f"（{radius}米范围内）" if radius else ""
            return f"{cat}{suffix}密度为 {value:.2f}"
        
        # 通用面积/比例类: *_ratio, *_area, *_pct
        m = re.match(r'^(.+)_ratio$', feature_name)
        if m:
            return f"{m.group(1)}比率为 {value:.4f}"
        
        # 通用指数类: *_index, *_potential
        m = re.match(r'^(.+?)_(?:index|potential|score)$', feature_name)
        if m:
            cat = m.group(1).replace('_', ' ')
            return f"{cat}指数/得分为 {value:.2f}"
        
        # 兜底：通用描述
        # 将 feature_name 中的下划线转为更可读的文本
        readable_name = feature_name.replace('_', ' ')
        if isinstance(value, float) and value != int(value):
            return f"{readable_name}: {value:.2f}"
        else:
            return f"{readable_name}: {value:.0f}"
    
    # ===== 区域查询 =====
    
    def find_suitable_regions(self, function_type: str, min_score: float = 0.6, top_n: int = 5) -> str:
        """
        查询适合某功能的区域，并生成文本
        """
        suitable_units = self.kg.find_suitable_units(function_type, min_score)
        
        if not suitable_units:
            return f"未找到适宜性得分高于 {min_score} 的 {function_type} 区域"
        
        text = f"## 适合 {function_type} 功能的区域\n\n"
        text += f"共找到 **{len(suitable_units)}** 个高适宜性单元（得分 ≥ {min_score}）\n\n"
        
        # 只展示前 N 个
        for i, (unit_id, score) in enumerate(suitable_units[:top_n], 1):
            text += f"### {i}. 单元 {unit_id} （得分 {score:.2f}）\n\n"
            
            # 获取关键特征
            unit_node = self.kg.get_node(unit_id)
            if unit_node:
                features = unit_node.properties.get('features', {})
                key_factors = self._analyze_key_factors(features, function_type, score)
                
                if key_factors:
                    for factor in key_factors[:6]:  # 每个单元列6条关键特征
                        text += f"- {factor}\n"
                text += "\n"
        
        if len(suitable_units) > top_n:
            text += f"（还有 {len(suitable_units) - top_n} 个单元未展示）\n"
        
        return text
    
    # ===== 对比分析 =====
    
    def compare_units(self, unit_ids: List[str], function_type: str) -> str:
        """
        对比多个单元对某功能的适宜性
        """
        text = f"## {function_type} 功能适宜性对比\n\n"
        
        units_data = []
        for unit_id in unit_ids:
            unit_node = self.kg.get_node(unit_id)
            if not unit_node:
                continue
            
            # 获取得分
            suitable_relations = self.kg.get_outgoing_relations(unit_id, RelationType.SUITABLE_FOR)
            score = 0
            for rel in suitable_relations:
                if rel.target == f"func_{function_type}":
                    score = rel.weight
                    break
            
            units_data.append({
                'id': unit_id,
                'score': score,
                'features': unit_node.properties.get('features', {})
            })
        
        # 按得分排序
        units_data.sort(key=lambda x: x['score'], reverse=True)
        
        # 生成对比表格
        text += "| 单元 | 得分 | 等级 |\n"
        text += "|------|------|------|\n"
        for data in units_data:
            level_cn = {
                'excellent': '高度适宜',
                'good': '较适宜',
                'moderate': '中等适宜',
                'poor': '不太适宜'
            }.get(get_suitability_level(data['score']), '未知')
            
            text += f"| {data['id']} | {data['score']:.2f} | {level_cn} |\n"
        
        text += "\n"
        
        # 差异分析
        if len(units_data) >= 2:
            text += "### 差异原因\n\n"
            best = units_data[0]
            worst = units_data[-1]
            
            text += f"**最适宜单元 {best['id']}** 相比 **{worst['id']}** 的优势：\n\n"
            
            key_features = self._get_key_features_for_function(function_type)
            advantages = []
            
            for feature_name in key_features:
                if feature_name in best['features'] and feature_name in worst['features']:
                    best_val = best['features'][feature_name]
                    worst_val = worst['features'][feature_name]
                    
                    # 距离类：越小越好
                    if 'dist_' in feature_name:
                        if best_val < worst_val * 0.8:
                            diff = worst_val - best_val
                            advantages.append(
                                f"- {FEATURE_DESCRIPTIONS[feature_name]['name']}更近（少 {diff:.0f} 米）"
                            )
                    # 其他：越大越好
                    else:
                        if best_val > worst_val * 1.2:
                            diff_pct = (best_val - worst_val) / worst_val * 100
                            advantages.append(
                                f"- {FEATURE_DESCRIPTIONS[feature_name]['name']}更高（高 {diff_pct:.1f}%）"
                            )
            
            if advantages:
                text += "\n".join(advantages[:5])  # 最多5条
            else:
                text += "两者特征较为接近，差异主要体现在综合评价上。\n"
        
        return text
    
    # ===== 统计概览 =====
    
    def generate_summary(self, recommendations: Dict[str, str]) -> str:
        """
        生成整体分析结果概览
        """
        text = "## 分析结果概览\n\n"
        
        unit_nodes = self.kg.get_nodes_by_type(NodeType.UNIT)
        total_units = len(unit_nodes)
        
        text += f"本次分析共涵盖 **{total_units}** 个空间单元。\n\n"
        
        # 功能分布统计
        text += "### 功能分布\n\n"
        function_stats = {}
        for unit_id, func in recommendations.items():
            function_stats[func] = function_stats.get(func, 0) + 1
        
        # 生成饼图数据（Markdown表格形式）
        text += "| 功能类型 | 单元数 | 占比 |\n"
        text += "|---------|--------|------|\n"
        for func, count in sorted(function_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_units * 100
            text += f"| {func} | {count} | {percentage:.1f}% |\n"
        
        text += "\n"
        
        # 空间特征统计
        text += "### 空间特征\n\n"
        
        # 计算平均值
        all_features = [node.properties.get('features', {}) for node in unit_nodes]
        
        if all_features and all_features[0]:
            feature_names = list(all_features[0].keys())
            
            for feature_name in ['dist_to_metro', 'green_ratio_500m', 'population_density_1km']:
                if feature_name not in feature_names:
                    continue
                
                values = [f.get(feature_name, 0) for f in all_features]
                avg_value = sum(values) / len(values)
                
                if feature_name in FEATURE_DESCRIPTIONS:
                    config = FEATURE_DESCRIPTIONS[feature_name]
                    unit = config['unit']
                    
                    # 比例类转百分比
                    if unit == '%':
                        avg_value *= 100
                    
                    text += f"- **{config['name']}平均值**: {avg_value:.1f} {unit}\n"
        
        # 高适宜性单元统计
        text += "\n### 适宜性分布\n\n"
        high_suit_count = 0
        for node in unit_nodes:
            suitable_relations = self.kg.get_outgoing_relations(node.id, RelationType.SUITABLE_FOR)
            if any(rel.weight > 0.7 for rel in suitable_relations):
                high_suit_count += 1
        
        text += f"- 高适宜性单元（任意功能得分 > 0.7）：**{high_suit_count}** 个\n"
        text += f"- 占比：**{high_suit_count/total_units*100:.1f}%**\n"
        
        return text


# ============ 问答系统 ============

class SpatialQA:
    """
    空间分析问答系统
    基于知识图谱和自然语言生成器回答问题
    
    Phase 2.4 更新：支持推理引擎
    """
    
    def __init__(self, kg: SpatialKnowledgeGraph, enable_reasoning: bool = True):
        self.kg = kg
        self.nlg = NaturalLanguageGenerator(kg, enable_reasoning=enable_reasoning)
        self.enable_reasoning = enable_reasoning
    
    def answer(self, question: str, context: Optional[Dict] = None) -> str:
        """
        回答问题（简单规则匹配）
        """
        question = question.strip()
        
        # 意图识别（简化版）
        if '为什么' in question and '适合' in question:
            return self._answer_why_suitable(question)
        
        elif '哪些' in question or '哪里' in question:
            return self._answer_where(question)
        
        elif '对比' in question or '比较' in question:
            return self._answer_comparison(question)
        
        elif '概览' in question or '统计' in question or '总结' in question:
            if context and 'recommendations' in context:
                return self.nlg.generate_summary(context['recommendations'])
            else:
                return "请提供分析结果数据（recommendations）"
        
        else:
            return self._show_help()
    
    def _answer_why_suitable(self, question: str) -> str:
        """回答'为什么适合'类问题
        
        Phase 2.4 更新：默认使用推理引擎生成深度解释
        """
        # 简单提取（实际应用可用NLP模型）
        
        # 提取单元ID - 支持多种格式
        unit_match = re.search(r'(?:单元|网格\s*)?([A-Za-z0-9_]+(?:_[A-Za-z0-9_]+)*)', question)
        if not unit_match:
            return "请在问题中明确指定单元ID，例如：为什么单元 U_0_0 适合居住功能？"
        
        unit_id = unit_match.group(1)
        
        # 提取功能类型 - 扩展列表，支持更多表述
        functions = ['居住', '商业', '办公', '工业', '公共服务', '绿地休闲', '绿地', '综合', '交通', '住宅', '商务']
        function_type = None
        for func in functions:
            if func in question:
                # 标准化功能类型名称
                if func in ['住宅']:
                    function_type = '居住'
                elif func in ['商务']:
                    function_type = '商业'
                elif func in ['绿地']:
                    function_type = '绿地休闲'
                else:
                    function_type = func
                break
        
        if not function_type:
            return f"请在问题中指定功能类型，例如：居住、商业、办公、工业、公共服务、绿地休闲、综合等"
        
        # Phase 2.4: 默认使用推理引擎
        return self.nlg.explain_unit_suitability(
            unit_id, function_type, 
            use_reasoning=self.enable_reasoning
        )
    
    def _answer_where(self, question: str) -> str:
        """回答'哪里适合'类问题"""
        functions = ['居住', '商业', '办公', '工业', '公共服务', '绿地休闲', '绿地', '综合', '交通', '住宅', '商务']
        function_type = None
        for func in functions:
            if func in question:
                if func in ['住宅']:
                    function_type = '居住'
                elif func in ['商务']:
                    function_type = '商业'
                elif func in ['绿地']:
                    function_type = '绿地休闲'
                else:
                    function_type = func
                break
        
        if not function_type:
            return "请在问题中指定功能类型，例如：哪些区域适合商业开发？"
        
        return self.nlg.find_suitable_regions(function_type, min_score=0.6, top_n=5)
    
    def _answer_comparison(self, question: str) -> str:
        """回答对比类问题"""
        
        # 提取单元ID列表
        unit_ids = re.findall(r'[A-Za-z0-9_]+(?:_[A-Za-z0-9_]+)*', question)
        
        # 过滤掉功能名称等
        functions = ['居住', '商业', '办公', '工业', '公共服务', '绿地休闲', '绿地', '综合', '交通', '住宅', '商务']
        unit_ids = [uid for uid in unit_ids if uid not in functions and '单元' not in uid]
        
        if len(unit_ids) < 2:
            return "请在问题中指定至少两个单元ID，例如：对比单元 U_0_0 和 U_1_1 的商业适宜性"
        
        # 提取功能类型
        function_type = None
        for func in functions:
            if func in question:
                function_type = func
                break
        
        if not function_type:
            function_type = '居住'  # 默认
        
        return self.nlg.compare_units(unit_ids[:5], function_type)  # 最多对比5个
    
    def _show_help(self) -> str:
        """显示帮助信息"""
        return """
## 支持的问题类型

### 1. 单元适宜性解释
**示例**: 为什么单元 U_0_0 适合居住功能？

### 2. 区域查询
**示例**: 哪些区域适合商业开发？

### 3. 对比分析
**示例**: 对比单元 U_0_0 和 U_1_1 的商业适宜性

### 4. 统计概览
**示例**: 给出整体分析结果概览

---

**提示**: 请在问题中明确指定单元ID（如 U_0_0）和功能类型（如居住、商业、办公等）
        """.strip()


# ============ 使用示例 ============

if __name__ == "__main__":
    from knowledge_graph_builder import SpatialKnowledgeGraph
    
    # 加载知识图谱
    kg = SpatialKnowledgeGraph.load_from_file('knowledge_graph.json')
    
    # 初始化问答系统
    qa = SpatialQA(kg)
    
    # 测试问题
    questions = [
        "为什么单元 U_0_0 适合居住功能？",
        "哪些区域适合商业开发？",
        "对比单元 U_0_0 和 U_1_1 的商业适宜性",
    ]
    
    for q in questions:
        print(f"\n{'='*60}")
        print(f"问题: {q}")
        print(f"{'='*60}")
        answer = qa.answer(q)
        print(answer)