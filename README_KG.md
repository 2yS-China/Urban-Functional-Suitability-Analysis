# 知识图谱构建与自然语言问答 - 使用指南

## 概述

本模块实现了将 GIS 空间分析结果转化为知识图谱，并提供基于知识图谱的自然语言问答能力。

**核心价值**：
- 将空间分析结果**结构化存储**为图谱，支持灵活查询
- 将**数据转为文字**，生成人类可读的分析解释
- 支持**交互式问答**，按需响应用户查询

---

## 文件结构

```
├── knowledge_graph_builder.py   # 知识图谱构建核心
├── nlg_generator.py             # 自然语言生成模块
├── demo_full_pipeline.py        # 完整流程演示
└── README_KG.md                 # 本说明文档
```

---

## 快速开始

### 1. 运行完整演示

```bash
python demo_full_pipeline.py
```

这会：
1. 创建模拟的 GIS 数据（3x3 网格）
2. 执行空间分析（特征提取、适宜性评价）
3. 构建知识图谱并保存为 `knowledge_graph_demo.json`
4. 演示 4 种问答类型

**预期输出**：
```
==================================================
城市片区功能适宜性分析 - 知识图谱构建与问答演示
==================================================
准备模拟 GIS 数据...
  - 创建了 9 个分析单元

执行空间分析...
  - 提取空间特征...
  - 计算适宜性得分...
  - 生成功能推荐...
  - 完成 9 个单元的分析

构建知识图谱...
- 添加单元节点...
- 添加功能节点...
- 构建相邻关系...
  - 添加了 24 条相邻关系
- 构建适宜性关系...
  - 添加了 36 条适宜性关系
- 构建主导功能关系...
- 构建相似关系...
  - 添加了 15 条相似关系 (threshold=0.8)
图谱构建完成: 13 个节点, 84 条关系

知识图谱已保存到: knowledge_graph_demo.json

==================================================
知识图谱问答系统已启动
==================================================

问题 1: 为什么单元 U_0_0 适合居住功能？
────────────────────────────────────────────────

## 单元 U_0_0 - 居住功能适宜性分析

属于**较适宜区域**（得分 0.68）

### 主要原因

1. 距离地铁站约 650 米，交通便利
2. 周边绿地覆盖率达 18.5%
3. 周边有 2 所教育设施
...
```

---

## 核心模块说明

### 1. 知识图谱构建 (`knowledge_graph_builder.py`)

#### 图谱结构

**节点类型**：
- `UNIT`：分析单元（网格/地块）
- `FEATURE`：空间要素（POI、交通设施等）
- `FUNCTION`：功能类型（居住、商业等）

**关系类型**：
- `相邻`：单元之间的空间邻接
- `适宜`：单元对某功能的适宜性
- `主导功能`：单元的推荐功能
- `相似`：单元之间的特征相似度
- `邻近`：单元与要素的距离关系

#### 核心类

**`SpatialKnowledgeGraph`**：知识图谱数据结构
```python
kg = SpatialKnowledgeGraph()

# 添加节点
kg.add_node(unit_node)

# 添加关系
kg.add_relation(relation)

# 查询
suitable_units = kg.find_suitable_units('商业', min_score=0.6)
neighbors = kg.get_adjacent_units('U_0_0')

# 序列化
kg.save_to_file('kg.json')
kg_loaded = SpatialKnowledgeGraph.load_from_file('kg.json')
```

**`KnowledgeGraphBuilder`**：构建器
```python
builder = KnowledgeGraphBuilder()
kg = builder.build(
    units_gdf=units_gdf,              # GeoDataFrame
    features_dict=features_dict,       # {unit_id: {feature_name: value}}
    suitability_matrix=suitability,    # {unit_id: {function: score}}
    recommendations=recommendations,   # {unit_id: function}
    function_rules=function_rules      # 功能规则配置
)
```

---

### 2. 自然语言生成 (`nlg_generator.py`)

#### 特征描述模板

在 `FEATURE_DESCRIPTIONS` 中定义了每种特征的描述模板：

```python
FEATURE_DESCRIPTIONS = {
    'dist_to_metro': {
        'name': '地铁站距离',
        'unit': '米',
        'good_threshold': 800,
        'templates': {
            'excellent': '距离地铁站仅 {value:.0f} 米，交通极为便利',
            'good': '距离地铁站约 {value:.0f} 米，交通便利',
            # ...
        }
    },
    # ...
}
```

**扩展方法**：添加新特征描述时，只需在字典中新增条目。

#### 核心类

**`NaturalLanguageGenerator`**：文本生成器
```python
nlg = NaturalLanguageGenerator(kg)

# 解释单元适宜性
text = nlg.explain_unit_suitability('U_0_0', '居住')

# 查询适宜区域
text = nlg.find_suitable_regions('商业', min_score=0.6, top_n=5)

# 对比分析
text = nlg.compare_units(['U_0_0', 'U_1_1'], '商业')

# 统计概览
text = nlg.generate_summary(recommendations)
```

**`SpatialQA`**：问答系统
```python
qa = SpatialQA(kg)

# 自动识别问题类型并回答
answer = qa.answer("为什么单元 U_0_0 适合居住功能？")
answer = qa.answer("哪些区域适合商业开发？")
answer = qa.answer("对比单元 A 和单元 B 的商业适宜性")
answer = qa.answer("给出整体分析结果概览", 
                   context={'recommendations': recommendations})
```

---

## 实际项目集成

### 步骤 1: 准备 GIS 数据

```python
import geopandas as gpd

# 读取分析单元（网格或地块）
units_gdf = gpd.read_file('units.shp')

# 读取 POI、路网等要素
poi_df = gpd.read_file('poi.shp')
roads_gdf = gpd.read_file('roads.shp')
```

### 步骤 2: 空间分析

```python
# 特征提取（使用你的空间分析模块）
features_dict = extract_spatial_features(units_gdf, poi_df, roads_gdf)

# 适宜性评价（使用你的评价模块）
suitability_matrix = evaluate_suitability(features_dict, rules_config)

# 功能推荐
recommendations = recommend_functions(suitability_matrix)
```

### 步骤 3: 构建知识图谱

```python
from knowledge_graph_builder import KnowledgeGraphBuilder

builder = KnowledgeGraphBuilder()
kg = builder.build(
    units_gdf=units_gdf,
    features_dict=features_dict,
    suitability_matrix=suitability_matrix,
    recommendations=recommendations,
    function_rules=your_function_rules
)

# 保存
kg.save_to_file('results/knowledge_graph.json')
```

### 步骤 4: 提供问答接口

```python
from nlg_generator import SpatialQA

# 加载知识图谱
kg = SpatialKnowledgeGraph.load_from_file('results/knowledge_graph.json')

# 初始化问答系统
qa = SpatialQA(kg)

# 在 Web API 中使用
@app.post("/api/qa")
def ask_question(question: str):
    answer = qa.answer(question, context={'recommendations': recommendations})
    return {"question": question, "answer": answer}
```

---

## 支持的问题类型

### 1. 单元适宜性解释
**问题格式**：`为什么单元 <unit_id> 适合 <function> 功能？`

**示例**：
- 为什么单元 U_0_0 适合居住功能？
- 为什么单元 A_123 适合商业功能？

**返回**：Markdown 格式的解释文本，包括：
- 适宜性得分和等级
- 关键影响因素（3-5 条）
- 位置和面积信息

### 2. 区域查询
**问题格式**：`哪些区域适合 <function> 功能？` 或 `哪里适合 <function> 开发？`

**示例**：
- 哪些区域适合商业开发？
- 哪里适合建设住宅？

**返回**：适宜性得分排序的单元列表，每个单元包含关键影响因素。

### 3. 对比分析
**问题格式**：`对比单元 <unit_id_1> 和 <unit_id_2> 的 <function> 适宜性`

**示例**：
- 对比单元 U_0_0 和 U_2_2 的商业适宜性
- 比较 A 和 B 的居住适宜性

**返回**：对比表格 + 差异原因分析。

### 4. 统计概览
**问题格式**：`给出整体分析结果概览` 或 `统计分析结果`

**返回**：
- 功能分布统计（表格）
- 空间特征统计（平均值）
- 适宜性分布

---

## 自定义扩展

### 扩展 1: 添加新特征描述

在 `nlg_generator.py` 的 `FEATURE_DESCRIPTIONS` 中添加：

```python
FEATURE_DESCRIPTIONS['你的新特征'] = {
    'name': '特征中文名',
    'unit': '单位',
    'good_threshold': 阈值,
    'templates': {
        'excellent': '优秀时的描述模板 {value:.0f}',
        'good': '良好时的描述模板 {value:.0f}',
        'moderate': '中等时的描述模板 {value:.0f}',
        'poor': '较差时的描述模板 {value:.0f}'
    }
}
```

### 扩展 2: 添加新关系类型

在 `knowledge_graph_builder.py` 的 `RelationType` 中添加：

```python
class RelationType(Enum):
    # 已有关系...
    YOUR_NEW_RELATION = "你的新关系"
```

然后在 `KnowledgeGraphBuilder._build_xxx_relations()` 中构建该关系。

### 扩展 3: 支持新问题类型

在 `nlg_generator.py` 的 `SpatialQA.answer()` 中添加识别规则：

```python
def answer(self, question: str, context: Optional[Dict] = None) -> str:
    # 已有识别...
    
    elif '你的关键词' in question:
        return self._answer_your_new_type(question)
```

---

## 性能优化

### 大规模数据处理

当单元数量 > 1000 时：

1. **相邻关系构建优化**：使用空间索引
```python
from rtree import index

idx = index.Index()
for i, unit in units_gdf.iterrows():
    idx.insert(i, unit.geometry.bounds)

# 快速查找相邻候选
candidates = list(idx.intersection(target_bounds))
```

2. **相似关系阈值调高**：减少关系数量
```python
# 从 0.8 提高到 0.9
builder._build_similarity_relations(features_dict, threshold=0.9)
```

3. **分批处理**：大数据集分块构建
```python
for chunk in chunked(units_gdf, chunk_size=500):
    kg_chunk = builder.build(chunk, ...)
    merge_graphs(kg_main, kg_chunk)
```

---

## 常见问题

### Q1: 如何加载已有的知识图谱？
```python
kg = SpatialKnowledgeGraph.load_from_file('path/to/kg.json')
```

### Q2: 如何查询特定单元的所有关系？
```python
# 出边
outgoing = kg.get_outgoing_relations('U_0_0')

# 入边
incoming = kg.get_incoming_relations('U_0_0')

# 相邻单元
neighbors = kg.get_adjacent_units('U_0_0')
```

### Q3: 如何修改特征描述模板？
直接编辑 `nlg_generator.py` 中的 `FEATURE_DESCRIPTIONS` 字典。

### Q4: 问答系统能否使用 LLM？
可以。将 `SpatialQA.answer()` 中的规则匹配替换为调用 LLM：

```python
def answer(self, question: str, context: Optional[Dict] = None) -> str:
    # 提取图谱上下文
    graph_context = self._extract_context_for_question(question)
    
    # 调用 LLM
    prompt = f"基于以下知识图谱数据回答问题:\n{graph_context}\n\n问题: {question}"
    answer = llm_client.generate(prompt)
    
    return answer
```

但注意：
- LLM 可能产生幻觉，需验证答案与图谱一致性
- 成本更高，适合复杂推理问题
- 简单查询用模板更快更准确

---

## 依赖库

```txt
geopandas>=0.12.0
shapely>=2.0.0
numpy>=1.24.0
rtree>=1.0.0  # 可选，用于空间索引加速
```

安装：
```bash
pip install geopandas shapely numpy rtree
```

---

## 下一步

1. **集成到 Web API**：参考 FastAPI 示例集成问答接口
2. **可视化**：将问答结果中的单元 ID 映射到地图高亮
3. **扩展问题类型**：支持更复杂的查询（如"找出同时适合居住和商业的区域"）
4. **机器学习增强**：训练 NLP 模型提升意图识别准确率

---

## 联系与反馈

如有问题或建议，请提交 Issue 或 Pull Request。