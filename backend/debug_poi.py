"""Diagnostic: check what POI categories are in the OSM data"""
import geopandas as gpd

# Load raw POI data
path = 'data/projects/osm_test_20260920_122458/raw/poi_poi.geojson'
poi = gpd.read_file(path, encoding='utf-8')
print(f"Total POIs: {len(poi)}")
print(f"\nPOI columns: {list(poi.columns)}")

if 'category' in poi.columns:
    cats = poi['category'].value_counts()
    print(f"\nPOI categories ({len(cats)}):")
    for cat, count in cats.items():
        print(f"  {repr(cat)}: {count} POIs")

# Also check what feature names were generated in the grid
grid_path = 'data/projects/osm_test_20260920_122458/processed/grid_with_features.geojson'
grid = gpd.read_file(grid_path, encoding='utf-8')

print(f"\nGrid feature columns with 'poi':")
for col in grid.columns:
    if 'poi' in col.lower():
        print(f"  {repr(col)}")

print(f"\nGrid feature columns with 'dist_to':")
for col in grid.columns:
    if col.startswith('dist_to'):
        print(f"  {repr(col)}")