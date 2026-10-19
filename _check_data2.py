import json

with open('backend/data/projects/osm_test_20260920_122458/processed/grid_with_features.geojson', encoding='utf-8') as f:
    data = json.load(f)

n = len(data['features'])
print(f'Total features: {n}')
print()

# Check ALL columns for uniqueness
all_cols = sorted(data['features'][0]['properties'].keys())
print('=== Column diversity (all features) ===')
for c in all_cols:
    vals = [f['properties'].get(c) for f in data['features']]
    unique = len(set(str(v) for v in vals))
    if unique <= 3:
        print(f'  CONSTANT: {c} = {vals[0]} (unique={unique})')

# Check which columns have good diversity
print()
print('=== Columns with good diversity (>10 unique) ===')
for c in all_cols:
    vals = [f['properties'].get(c) for f in data['features']]
    unique = len(set(str(v) for v in vals))
    if unique > 10:
        num_vals = [v for v in vals if isinstance(v, (int, float))]
        if num_vals:
            print(f'  {c}: unique={unique}, min={min(num_vals):.4f}, max={max(num_vals):.4f}')
        else:
            print(f'  {c}: unique={unique}')