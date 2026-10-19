import json

with open('backend/data/projects/osm_test_20260920_122458/processed/grid_with_features.geojson', encoding='utf-8') as f:
    data = json.load(f)

props = data['features'][0]['properties']
print('=== green/eco/water related ===')
for k in sorted(props.keys()):
    if 'green' in k.lower() or 'eco' in k.lower() or 'water' in k.lower() or 'dist_to_' in k:
        print(f'  {k}: {props[k]}')

print()
print('=== ALL cols with distinct values (checking first 100 features) ===')
all_cols = sorted(props.keys())
n = min(100, len(data['features']))
for c in all_cols:
    vals = [f['properties'].get(c) for f in data['features'][:n]]
    unique = len(set(str(v) for v in vals))
    if unique <= 2:
        print(f'  CONSTANT: {c} = {vals[0]}')