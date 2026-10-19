"""Diagnostic: check why calculate_derived_features doesn't compute from POI data"""
import geopandas as gpd
import numpy as np

path = 'data/projects/osm_test_20260920_122458/processed/grid_with_features.geojson'
features = gpd.read_file(path, encoding='utf-8')

# Check all POI column names (exact repr)
target = 'poi_density_居住_1000m'
print(f"Target column: {repr(target)}")
print(f"Match check: {target in features.columns}")
print()

# Find all columns containing '1000m' and 'poi'
for col in features.columns:
    if '1000m' in col and ('poi' in col.lower() or '密度' in col):
        eq = (col == target)
        print(f"  {repr(col)} == target: {eq}")
        print(f"    len={len(col)}, chars={[hex(ord(c)) for c in col]}")
        print()

# Also try with a fresh string from the actual column
for col in features.columns:
    if '居住' in col:
        eq = (col == target)
        print(f"  Found: {repr(col)}")
        print(f"  == target: {eq}")
        # Try if it matches any of the expected patterns
        expected = f"poi_density_居住_1000m"
        print(f"  == expected: {col == expected}")
        print()