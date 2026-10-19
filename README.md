# Urban Functional Suitability Analysis

**A GIS decision-support prototype for exploring urban land-use suitability through spatial analysis, interactive maps, and knowledge-graph explanations.**

[中文说明](README.zh-CN.md) · [Known issues](docs/KNOWN_ISSUES.md) · [Data sources](DATA_SOURCES.md)

## Overview

Choosing a suitable urban function involves transport access, surrounding services, environmental conditions, and relationships between adjacent areas. This project explores how spatial analysis can make those relationships easier to inspect.

Users upload their own study boundary, POIs, and optional road data in the supported formats. The workflow is reusable across study areas; the included datasets are optional examples, not a fixed study site.

The system divides the uploaded study area into analysis units, extracts spatial indicators, applies configurable suitability rules, and presents recommendations on a map. A knowledge graph connects units, indicators, and functions to support explanations of the results.

**Status: Alpha prototype.** The interface and generated explanations are primarily in Chinese. See [implementation scope](docs/KNOWN_ISSUES.md) for current UI and API coverage.

## Main components

| Component | Implementation |
| --- | --- |
| Data management | Projects, boundary and POI uploads, optional road data |
| Spatial processing | Normalization, grids, proximity, density, accessibility, and geometry indicators |
| Suitability evaluation | Multi-criteria scoring with YAML-defined weights and constraints |
| Recommendation | Function ranking and neighborhood coordination rules |
| Map exploration | Layer controls, function-score views, and clickable unit details |
| Explanation | Keyword detection, knowledge-graph queries, and template-based text generation |

The seven configured functions are **Residential, Commercial, Office, Industrial, Public Services, Green Space & Recreation, and Mixed Use** (`居住`, `商业`, `办公`, `工业`, `公共服务`, `绿地休闲`, `综合`).

The analysis is rule-based. The current Q&A route does not call an external large language model, and the core workflow requires no LLM API key.

## Interaction flow

1. Create a project and upload boundary and POI data.
2. Add road data and select a grid size.
3. Submit an analysis task and follow its progress.
4. Inspect recommended functions and individual scores on the map.
5. Ask a supported question about the generated results.

Example questions after a successful analysis with a knowledge graph:

- `哪些区域适合商业开发？` — Which areas are suitable for commercial use?
- `为什么单元 UNIT_0001 适合居住？` — Why is this unit suitable for residential use? Use an actual ID from your results.
- `整体分析结果如何？` — What is the overall result?

Comparison queries require explicit `unit_ids` through the API; the current chat interface does not supply that field.

## Technology

| Layer | Tools |
| --- | --- |
| Interface | HTML, CSS, vanilla JavaScript, Leaflet |
| API | Python, FastAPI, Uvicorn |
| Spatial analysis | GeoPandas, Shapely, PyProj, Rtree, Rasterio |
| Numerical processing | NumPy, Pandas, SciPy |
| Rules and graph utilities | PyYAML, custom graph modules, NetworkX, PyVis |
| Persistence | Local project folders, GeoJSON, JSON |

The active entry point is `frontend/index.html`, which loads `frontend/app.js`. The separate `frontend/js/` implementation is retained but not loaded by that page.

## Local setup

Use **Python 3.10 or 3.11** as the setup target for the existing dependency pins. This is a compatibility recommendation, not a clean-install validation. The pinned NumPy 1.24 series [documents support through Python 3.11](https://numpy.org/doc/1.24/release/1.24.0-notes.html).

From the repository root:

**Windows Command Prompt**

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r backend/requirements.txt
```

**macOS / Linux**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Start the backend in the activated terminal:

```bash
cd backend
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Open a second terminal at the repository root, activate the same environment, then start the frontend:

```bash
cd frontend
python -m http.server 8080 --bind 127.0.0.1
```

- Interface: [http://localhost:8080](http://localhost:8080)
- API reference: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health endpoint: [http://localhost:8000/health](http://localhost:8000/health)

The active frontend points to the local backend at port 8000. Internet access is needed for the Leaflet CDN and Amap/AutoNavi basemap. These are local-development instructions, not a hosted deployment procedure.

## Example data

Start with the small OpenStreetMap example in `backend/test_data_osm/`:

| Upload category | File | Features |
| --- | --- | ---: |
| Boundary — required | `boundary.geojson` | 1 |
| POIs — required | `poi.geojson` | 1,351 |
| Roads — optional | `roads.geojson` | 2,352 |

Vector uploads accept GeoJSON and zipped Shapefiles. Additional raster and constraint inputs are not fully connected to the web analysis pipeline; see [known issues](docs/KNOWN_ISSUES.md).

Synthetic examples and generators are retained in `backend/sample_data/`. To regenerate its boundary, POI, and road samples, run **from the repository root**:

```bash
python backend/sample_data/generate_sample_area.py
python backend/sample_data/generate_sample_poi.py
python backend/sample_data/generate_sample_roads.py
```

These commands may overwrite existing synthetic samples. Select boundary, POI, and road files from the same study area; do not mix synthetic and OSM examples.

## Repository guide

| Path | Purpose |
| --- | --- |
| `backend/api/` | API routes, analysis tasks, project storage |
| `backend/data_processor/` | Normalization, grids, rasters, vector constraints |
| `backend/spatial_analysis/` | Feature extraction, scoring, recommendations |
| `backend/spatial_analysis/function_rules.yaml` | Criteria, weights, constraints |
| `backend/kg/` | Knowledge graphs, reasoning, explanations |
| `backend/test_data_osm/` | Small real-world input examples |
| `backend/sample_data/` | Synthetic examples and generators |
| `frontend/` | Browser interface and map interactions |
| `docs/` | Current issues and publishing notes |

Generated project folders, caches, bytecode, and bulky intermediate outputs are excluded from this distribution and covered by `.gitignore`. The application creates its project storage on startup.

## Scope and limitations

- Scores depend on configured rules, proxy indicators, and missing-data defaults. They are exploratory indices, not measured probabilities or validated planning decisions.
- The current UI submits square grids with terrain analysis disabled. Other backend capabilities are not all exposed or connected in the UI.
- No clean-environment, end-to-end run was performed during this documentation review. The review does not establish an accuracy, speed, or scalability benchmark.
- Existing phase reports and technical plans are retained as development history. Their completion statements may differ from the current source; use this README and the known-issues document for the current scope.

## Documentation and attribution

- [Known issues](docs/KNOWN_ISSUES.md)
- [Data sources and third-party components](DATA_SOURCES.md)
- [API development notes](backend/README_API.md)
- [Original technical plan](项目技术方案.md)
- [Publishing notes / 上传说明](docs/PUBLISHING.zh-CN.md)

OpenStreetMap example data: © OpenStreetMap contributors, under the [Open Database License](https://opendatacommons.org/licenses/odbl/1-0/). See [attribution information](https://www.openstreetmap.org/copyright).

A standalone software `LICENSE` file is not included. The original README mentioned MIT; the software license should be confirmed by the rights holder. Third-party data and dependencies retain their own licenses.
