"""Diagnostic: check POI categories and feature names via hex decoding"""
import geopandas as gpd
import json

# Load raw POI
path = 'data/projects/osm_test_20260920_122458/raw/poi_poi.geojson'
with open(path, encoding='utf-8') as f:
    poi_gj = json.load(f)

cats = set()
for feat in poi_gj['features']:
    cats.add(feat['properties']['category'])

print("POI categories:")
for c in sorted(cats):
    hex_repr = ' '.join(f'{ord(ch):04x}' for ch in c)
    print(f"  '{c}' -> hex: {hex_repr}")

# Now check grid feature columns
grid_path = 'data/projects/osm_test_20260920_122458/processed/grid_with_features.geojson'
with open(grid_path, encoding='utf-8') as f:
    grid_gj = json.load(f)

print("\nGrid POI columns:")
for key in grid_gj['features'][0]['properties'].keys():
    if 'poi' in key.lower():
        hex_repr = ' '.join(f'{ord(ch):04x}' for ch in key)
        print(f"  '{key}' -> hex: {hex_repr}")

print("\nGrid dist_to columns:")
for key in grid_gj['features'][0]['properties'].keys():
    if key.startswith('dist_to'):
        hex_repr = ' '.join(f'{ord(ch):04x}' for ch in key)
        print(f"  '{key}' -> hex: {hex_repr}")

# Check what feature extractor code expects
print("\n--- Feature extractor code expects ---")
expected_categories = ['居住', '商业服务', '公共服务', '绿地公园', '交通设施', '办公场所', '工业仓储']
for c in expected_categories:
    hex_repr = ' '.join(f'{ord(ch):04x}' for ch in c)
    in_poi = c in cats
    # Check partial match
    partial = [cat for cat in cats if c[:2] in cat or cat[:2] in c]
    print(f"  '{c}' (hex: {hex_repr}): in POI data = {in_poi}, partial matches = {partial}")