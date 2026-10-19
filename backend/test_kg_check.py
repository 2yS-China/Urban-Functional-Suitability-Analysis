"""Check KG data structure"""
import json

kg_path = r"D:\code\城市片区功能适宜性分析\backend\data\projects\osm_test_20260920_122458\results\knowledge_graph.json"
with open(kg_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Relation type counts
rel_types = {}
for r in data['relations']:
    rt = r['relation_type']
    rel_types[rt] = rel_types.get(rt, 0) + 1
print("Relation types:", rel_types)

# Node type counts
node_types = {}
for n in data['nodes']:
    nt = n['type']
    node_types[nt] = node_types.get(nt, 0) + 1
print("Node types:", node_types)

# Check DOMINATED_BY sample
dominated = [r for r in data['relations'] if r['relation_type'] == '主导功能']
print(f"\nDOMINATED_BY count: {len(dominated)}")
if dominated:
    print("Sample source:", dominated[0]['source'], "-> target:", dominated[0]['target'])

# Check SUITABLE_FOR sample
suitable = [r for r in data['relations'] if r['relation_type'] == '适宜']
print(f"\nSUITABLE_FOR count: {len(suitable)}")
if suitable:
    print("Sample source:", suitable[0]['source'], "-> target:", suitable[0]['target'], "weight:", suitable[0]['weight'])

# Check node IDs for UNIT nodes
unit_nodes = [n for n in data['nodes'] if n['type'] == '单元']
print(f"\nUNIT node count: {len(unit_nodes)}")
if unit_nodes:
    print("Sample node IDs:", [n['id'] for n in unit_nodes[:3]])