# Phase 2.3: 知识推理引擎

## 概述

Phase 2.3 为知识图谱系统添加了**多跳推理能力**，实现了从"单元适合居住，因为靠近地铁站"到"单元X靠近地铁站M，地铁站M服务L2号线，L2号线连接CBD"这样的深层推理链。

## 实现功能

### 1. 扩展节点类型

**新增节点类型（`backend/kg/knowledge_graph_builder.py`）：**
- `POI`：POI实体节点（具体的地铁站、商场等）
- `INFRASTRUCTURE`：基础设施线路节点（地铁线、公交线）
- `RULE`：评价规则节点

**新增节点类：**
- `POINode`：POI实体，包含位置、类别、属性（如地铁线路）
- `InfrastructureNode`：基础设施，包含线路名、站点列表、连接的关键区域
- `RuleNode`：评价规则，包含特征名、阈值、方向、描述

### 2. 扩展关系类型

**新增关系类型：**
- `SERVES_BY`：POI由基础设施服务（如"地铁站M由2号线服务"）
- `CONNECTS_TO`：基础设施连接到区域（如"2号线连接CBD"）
- `SATISFIES`：单元满足规则（如"单元X满足800m内有地铁的要求"）
- `REQUIRES`：功能要求准则（如"居住功能要求地铁便利性"）

### 3. 推理引擎（`backend/kg/reasoning_engine.py`）

**核心类：**

#### `ReasoningChain`
推理链数据结构，包含：
- `steps`：推理步骤列表
- `to_natural_language()`：转为自然语言描述

#### `ReasoningEngine`
推理引擎主类，提供：

**方法1：`explain_suitability(unit_id, function, max_depth=4)`**
解释单元为何适合某功能，返回推理链列表。

推理路径示例：
```
单元X -> NEAR -> 地铁站M -> SERVES_BY -> L2号线 -> CONNECTS_TO -> CBD
      -> SATISFIES -> 居住规则(800m内有地铁)
```

**方法2：`find_path(start_node_id, end_node_id, max_depth=4)`**
使用BFS查找两个节点之间的最短推理路径。

**方法3：`get_all_evidence(unit_id, function)`**
获取单元适宜某功能的所有证据，包括：
- `poi_chains`：基于POI的证据链
- `rule_chains`：基于规则的证据链
- `similar_units`：相似单元列表
- `spatial_context`：空间上下文（相邻单元功能分布）

**推理策略：**
- **POI证据链**：单元 → POI → 基础设施 → 区域
- **规则证据链**：功能 → 规则 ← 单元（满足关系）
- **广度优先搜索**：查找最短推理路径，防止无限循环

### 4. POI数据增强（`backend/sample_data/generate_sample_poi.py`）

**扩展POI生成脚本：**
- 为地铁站添加线路信息（`metro_line`, `line_name`, `key_areas`）
- 生成地铁线路配置文件（`metro_lines.json`）

**地铁线路配置示例：**
```json
{
  "L1": {
    "name": "1号线",
    "key_areas": ["CBD", "火车站", "机场"]
  },
  "L2": {
    "name": "2号线",
    "key_areas": ["CBD", "高新区", "大学城"]
  }
}
```

### 5. 测试验证（`backend/test_reasoning_simple.py`）

**测试用例：**

#### 测试1：适宜性解释（多跳推理）
问题："为什么单元0适合居住功能？"

推理链1（POI链）：
```
0 --邻近--> 地铁站1（距离500米）
  --服务于--> 1号线（1号线服务）
  --连接到--> CBD
  --连接到--> 火车站
```

推理链2（规则链）：
```
0 --满足--> rule_居住_dist_to_metro（居住功能要求800m内有地铁）
```

#### 测试2：路径查找
查找单元0到CBD的连接路径（3步）：
```
0 --邻近--> 地铁站1（距离500米）
  --服务于--> 1号线（服务于该线路）
  --连接到--> CBD（连接到核心区域）
```

#### 测试3：完整证据收集
- POI证据链：1条
- 规则证据链：1条
- 空间上下文：相邻单元功能分布

## 技术架构

### 推理流程

```
输入：单元ID + 功能类型
  ↓
1. 查找单元→功能的适宜性关系
  ↓
2. 查找功能的评价规则
  ↓
3. 对每个规则构建证据链（BFS搜索）
  ↓
4. 提取关系证据（距离、线路、区域）
  ↓
5. 转为自然语言描述
  ↓
输出：推理链列表（JSON + 自然语言）
```

### 数据流

```
GIS空间数据
  ↓
POI实体化 + 基础设施节点 + 规则节点
  ↓
关系构建（NEAR/SERVES_BY/CONNECTS_TO/SATISFIES/REQUIRES）
  ↓
推理引擎（BFS搜索 + 证据提取）
  ↓
推理链（结构化 + 自然语言）
```

## 文件清单

### 核心模块
- `backend/kg/knowledge_graph_builder.py`：扩展节点和关系类型（+150行）
- `backend/kg/reasoning_engine.py`：推理引擎实现（358行）
- `backend/kg/__init__.py`：模块导出更新

### 数据生成
- `backend/sample_data/generate_sample_poi.py`：扩展POI元数据生成（+50行）
- `backend/sample_data/metro_lines.json`：地铁线路配置（新增）

### 测试脚本
- `backend/test_reasoning_simple.py`：简化测试脚本（314行）
- `backend/test_reasoning.py`：完整测试脚本（预留，用于实际数据集）

### 输出文件
- `backend/sample_data/knowledge_graph_reasoning_test.json`：测试知识图谱

## 使用示例

### 基础用法

```python
from kg import ReasoningEngine, KnowledgeGraphBuilder

# 1. 构建知识图谱（包含POI实体和基础设施）
kg_builder = KnowledgeGraphBuilder()
kg = kg_builder.build(units_gdf, features_dict, suitability_matrix, 
                      recommendations, function_rules)

# 扩展：添加POI节点、基础设施节点、关系
# ... (见test_reasoning_simple.py)

# 2. 初始化推理引擎
reasoning_engine = ReasoningEngine(kg)

# 3. 解释适宜性
chains = reasoning_engine.explain_suitability("0", "居住", max_depth=4)

for chain in chains:
    print(chain.to_natural_language())
    # 输出：0靠近地铁站1（距离500米），由1号线，1号线服务连接到CBD连接到火车站

# 4. 查找路径
path = reasoning_engine.find_path("0", "area_CBD", max_depth=5)
if path:
    print(f"找到{len(path.steps)}步路径")

# 5. 获取所有证据
evidence = reasoning_engine.get_all_evidence("0", "居住")
print(f"POI证据链: {len(evidence['poi_chains'])}条")
print(f"规则证据链: {len(evidence['rule_chains'])}条")
```

## 核心特性

### 1. 多跳推理
- 支持4跳以上的推理深度
- 自动追溯因果链：单元 → POI → 基础设施 → 区域

### 2. 证据溯源
- 距离证据：具体米数
- 服务关系：哪条线路服务哪个设施
- 连接关系：基础设施连接哪些关键区域
- 规则满足：单元如何满足评价准则

### 3. 可解释性
- 推理链结构化输出（JSON）
- 自然语言描述生成
- 分层解释（直接证据 + 规则符合 + 关联优势）

### 4. 性能优化
- BFS搜索，避免深度遍历
- 访问集合防止重复
- 推理深度限制（默认4跳）
- 节点数量上限（防止无限循环）

## 测试结果

**运行测试：**
```bash
cd backend
python test_reasoning_simple.py
```

**测试输出：**
```
知识图谱统计:
  - 节点数: 18
  - 关系数: 11

【测试1：适宜性解释】
找到 2 条证据链

证据链 1：
  1. 0 --邻近--> 地铁站1 (距离500米)
  2. 地铁站1 --服务于--> 1号线 (1号线服务)
  3. 1号线 --连接到--> CBD
  4. 1号线 --连接到--> 火车站

自然语言描述：
  0靠近地铁站1（距离500米），由1号线，1号线服务连接到CBD连接到火车站

证据链 2：
  1. 0 --满足--> rule_居住_dist_to_metro (居住功能要求800m内有地铁)

【测试2：路径查找】
找到路径（3 步）

【测试3：完整证据收集】
POI证据链: 1 条
规则证据链: 1 条

[OK] 保存测试知识图谱: sample_data/knowledge_graph_reasoning_test.json

核心功能验证：
  [OK] 多跳推理：单元 → POI → 基础设施 → 区域
  [OK] 证据提取：距离、服务关系、连接关系
  [OK] 路径查找：BFS搜索最短推理路径
  [OK] 自然语言转换：推理链转可读文本
```

## 与传统知识图谱的对比

| 维度 | 传统学术知识图谱 | Phase 2.3 推理引擎 |
|------|------------------|-------------------|
| **推理能力** | 基于本体的逻辑推理 | 基于图遍历的路径推理 |
| **推理深度** | 多层本体继承 | 4跳关系链 |
| **证据形式** | 三元组 | 带权重和属性的关系 |
| **可解释性** | 中（需映射到自然语言） | 强（直接生成自然语言） |
| **适用场景** | 通用知识推理 | 空间决策解释 |

## 后续优化方向

### Phase 2.4（未来）：高级推理能力
- 冲突检测：识别矛盾规则
- 替代方案推理：条件不满足时的备选
- 权衡分析：解释"为什么选A而不是B"
- 时序推理：考虑动态变化（如"地铁在建中"）

### Phase 2.5（未来）：外部知识融合
- 从OpenStreetMap自动获取POI元数据
- 集成城市总体规划数据
- 融合房价、人口等统计数据

## 依赖

无新增外部库，使用已有的：
- `geopandas`：空间数据处理
- `shapely`：几何计算
- `collections.deque`：BFS队列（标准库）

## 总结

Phase 2.3 成功实现了知识推理引擎，核心亮点：

1. **多跳推理**：从"靠近地铁"深化到"靠近哪条地铁线、该线连接哪里"
2. **证据溯源**：每步推理都有具体证据（距离、线路、区域）
3. **自然语言**：推理链自动转为可读文本
4. **模块化设计**：推理引擎独立模块，易于扩展

这为用户提供了从"给出结论"到"解释为什么"的能力提升，显著增强了系统的可解释性和可信度。