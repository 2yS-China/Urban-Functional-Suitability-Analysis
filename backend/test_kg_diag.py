"""Diagnose why overview returns no data"""
import sys
sys.path.insert(0, r"D:\code\城市片区功能适宜性分析\backend")

from kg.knowledge_graph_builder import SpatialKnowledgeGraph, NodeType, RelationType

kg_path = r"D:\code\城市片区功能适宜性分析\backend\data\projects\osm_test_20260920_122458\results\knowledge_graph.json"
kg = SpatialKnowledgeGraph.load_from_file(kg_path)

print("=== KG loaded ===")
print(f"Nodes: {len(kg.nodes)}, Relations: {len(kg.relations)}")

# Check UNIT nodes
unit_nodes = kg.get_nodes_by_type(NodeType.UNIT)
print(f"\nUNIT nodes: {len(unit_nodes)}")
if unit_nodes:
    print(f"  First 3 IDs: {[n.id for n in unit_nodes[:3]]}")
    print(f"  First 3 types: {[n.type for n in unit_nodes[:3]]}")

# Check dominant function for first unit
if unit_nodes:
    first_id = unit_nodes[0].id
    print(f"\n--- Debug: get_unit_dominant_function('{first_id}') ---")
    rels = kg.get_outgoing_relations(first_id)
    print(f"  Total outgoing relations: {len(rels)}")
    dom_rels = kg.get_outgoing_relations(first_id, RelationType.DOMINATED_BY)
    print(f"  DOMINATED_BY relations: {len(dom_rels)}")
    for r in dom_rels:
        print(f"    {r.source} -> {r.target} (weight={r.weight})")

# Check index
print(f"\n--- Index check ---")
outgoing_keys = list(kg._index['outgoing'].keys())[:5]
print(f"  First 5 outgoing keys: {outgoing_keys}")
print(f"  Total outgoing keys: {len(kg._index['outgoing'])}")

by_type = kg._index.get('by_type', {})
print(f"  by_type keys: {by_type.keys()}")
for k, v in by_type.items():
    print(f"    {k}: {len(v)} nodes")

# Check SUITABLE_FOR
suit_rels = [r for r in kg.relations if r.relation_type == RelationType.SUITABLE_FOR]
print(f"\nSUITABLE_FOR relations: {len(suit_rels)}")
if suit_rels:
    print(f"  Sample: {suit_rels[0].source} -> {suit_rels[0].target} w={suit_rels[0].weight}")

# Check a few units for dominant function
print(f"\n--- Sample: dominant functions for first 5 units ---")
count_with_func = 0
for node in unit_nodes[:5]:
    func = kg.get_unit_dominant_function(node.id)
    print(f"  {node.id}: {func}")
    if func:
        count_with_func += 1

# Count all units with dominant functions
print(f"\n--- Counting all units with dominant functions ---")
all_with_func = sum(1 for n in unit_nodes if kg.get_unit_dominant_function(n.id))
print(f"  Units with dominant function: {all_with_func} / {len(unit_nodes)}")