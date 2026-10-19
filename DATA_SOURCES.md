# Data Sources and Third-Party Components

## OpenStreetMap inputs

The original dataset README describes `backend/test_data_osm/` as OpenStreetMap extracts downloaded on **2026-09-20**. Feature counts were checked directly in the supplied files; the upstream data was not downloaded again for this documentation update.

Recorded bounding box: west **116.30**, east **116.35**, south **39.98**, north **40.02** (longitude/latitude).

| File | Features | Role |
| --- | ---: | --- |
| `boundary.geojson` | 1 | Study boundary |
| `poi.geojson` | 1,351 | Points of interest |
| `roads.geojson` | 2,352 | Road segments |
| `water_bodies.geojson` | 51 | Optional water features |
| `green_spaces.geojson` | 384 | Additional green-space reference data |

File availability does not establish pipeline integration: the current worker does not normalize and forward uploaded water data, and `green_spaces` is not an upload category under that exact name.

**Attribution:** © OpenStreetMap contributors.

**License:** [Open Data Commons Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/).

See [OpenStreetMap attribution information](https://www.openstreetmap.org/copyright) and the [original dataset notes](backend/test_data_osm/README.md).

## Synthetic and development examples

The boundary, POI, and road generators in `backend/sample_data/` create synthetic scenarios. These examples should not be presented as observed urban conditions.

The supplied archive does not establish an external source for every raster or development fixture. Those files are retained as development examples; no additional provenance or accuracy claim is made for them.

Generated caches, saved project runs, intermediate results, and generated HTML visualizations are omitted from the GitHub preparation copy. Input examples and source scripts are retained.

## Map display and dependencies

- The active frontend loads Leaflet from a CDN and Amap/AutoNavi satellite and road tiles. This basemap is separate from the OSM input dataset.
- Python dependency pins are in [`backend/requirements.txt`](backend/requirements.txt).
- `backend/lib/` includes graph-visualization resources, including vis-network and Tom Select. Original files and embedded notices are preserved.
- Third-party libraries, map services, and datasets retain their respective licenses and terms.

## Software license status

The original README stated “MIT License,” but the archive did not include a standalone `LICENSE` file. This documentation update does not grant a new software license. The rights holder should confirm the intended license before adding its text or a license badge. Software licensing does not replace the separate terms of third-party data or dependencies.
