"""分析知识图谱内容"""
import json
from collections import Counter

# 加载知识图谱
with open('sample_data/processed/knowledge_graph.json', 'r', encoding='utf-8') as f:
    kg = json.load(f)

print("="*60)
print("知识图谱内容分析")
print("="*60)

# 节点统计
nodes = kg['nodes']
print(f"\n总节点数: {len(nodes)}")

node_types = Counter([n['type'] for n in nodes])
print("\n节点类型分布:")
for ntype, count in node_types.items():
    print(f"  {ntype}: {count}")

# 关系统计
relations = kg['relations']
print(f"\n总关系数: {len(relations)}")

rel_types = Counter([r['relation_type'] for r in relations])
print("\n关系类型分布:")
for rtype, count in rel_types.items():
    print(f"  {rtype}: {count}")

# 单元节点详情（抽样）
print("\n单元节点示例（前3个）:")
unit_nodes = [n for n in nodes if n['type'] == 'unit'][:3]
for node in unit_nodes:
    print(f"\n  节点ID: {node['id']}")
    print(f"  面积: {node['properties']['area']:.6f}")
    print(f"  中心点: ({node['properties']['centroid']['lon']:.6f}, {node['properties']['centroid']['lat']:.6f})")
    if 'recommended_function' in node['properties']:
        print(f"  推荐功能: {node['properties']['recommended_function']}")
    features = node['properties'].get('features', {})
    print(f"  特征数量: {len(features)}")

# 功能节点详情
print("\n功能节点列表:")
func_nodes = [n for n in nodes if n['type'] == 'function']
for node in func_nodes:
    print(f"  {node['id']}: {node['properties'].get('name', 'N/A')}")

# 适宜性关系抽样
suitable_rels = [r for r in relations if r['relation_type'] == '适宜'][:5]
print(f"\n适宜性关系示例（前5条）:")
for rel in suitable_rels:
    props = rel.get('properties', {})
    print(f"  {rel['source']} -> {rel['target']}: 得分={props.get('score', 0):.3f}, 等级={props.get('level', 'N/A')}")

# 相邻关系统计
adjacent_rels = [r for r in relations if r['relation_type'] == '相邻']
print(f"\n相邻关系数量: {len(adjacent_rels)}")

# 相似关系统计
similar_rels = [r for r in relations if r['relation_type'] == '相似']
print(f"相似关系数量: {len(similar_rels)}")
if similar_rels:
    similarities = [r['properties']['similarity'] for r in similar_rels if 'properties' in r and 'similarity' in r['properties']]
    if similarities:
        print(f"  相似度范围: {min(similarities):.3f} ~ {max(similarities):.3f}")
        print(f"  平均相似度: {sum(similarities)/len(similarities):.3f}")