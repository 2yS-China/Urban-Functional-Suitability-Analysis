# Implementation Scope and Known Integration Limitations

The documentation update preserves application source, configuration, dependencies, and launch scripts. These notes describe the generic input workflow and current integration coverage.

## User-provided study areas

The project is a reusable analysis tool. Users upload their own boundary, POI, and optional road datasets in supported formats. Included examples are for demonstration and are not a required or fixed study site. Requiring appropriate input data is part of this workflow.

Suitability rules and field mappings may need to be adapted to the study area and source schema. Uploading arbitrary imagery or an unsupported file is not equivalent to supplying the structured spatial inputs expected by the analysis.

## Interface and API coverage

| Item | Current behavior |
| --- | --- |
| Grid modes | The UI submits `square`. The generator also implements `hexagon`; the analysis worker explicitly rejects `parcel`. |
| Terrain | The UI submits `include_terrain: false`; it does not enable the existing backend DEM path. |
| Buffer radius | UI and API accept `buffer_radius`, but the worker does not pass it to feature extraction. Changing it should not be assumed to change the calculation. |
| Additional inputs | Upload routes and lower-level modules recognize more inputs than the worker forwards. Water, rainfall, soil, GDP, and several constraint layers are incompletely connected. |
| Comparison questions | The API requires at least two explicit `unit_ids`. The browser sends only `question`, including when using its comparison template. |

Sources: [analysis worker](../backend/api/analysis_worker.py), [analysis routes](../backend/api/routes/analysis_routes.py), [Q&A routes](../backend/api/routes/qa_routes.py), [frontend](../frontend/app.js).

## Score interpretation

Weights and thresholds are in [`function_rules.yaml`](../backend/spatial_analysis/function_rules.yaml). Feature extraction uses proxies and fallback constants; population density can be estimated from POI density. Missing criteria can receive a default score of `0.5`.

Scores are therefore rule-based suitability indices, not observed probabilities or validated planning accuracy. Some distance calculations use approximate degree-to-meter conversions. Data quality and geographic calibration need separate evaluation.

## Environment and deployment

- Python 3.10 or 3.11 is the documented target for the existing dependency pins. NumPy 1.24 [lists Python 3.8–3.11 support](https://numpy.org/doc/1.24/release/1.24.0-notes.html).
- Clean dependency installation and full application startup were not validated in this documentation task.
- The frontend points to `http://localhost:8000` and loads external resources. The complete application needs a backend and is not a standalone static webpage.
- Existing Windows launch scripts are retained; use the README's manual environment instructions as the primary setup guide.
- Public hosting, authentication, and production operation are outside the verified scope.

## Checks performed

- Read active entry points, routes, analysis worker, rules, and core processing modules.
- Counted the features in the included OSM files.
- Checked the original classification-to-label sequence: the NumPy classification output is assigned to a DataFrame column, and `.map()` is then correctly called on that Pandas Series. This focused check passed.
- Compared preserved source, settings, and scripts byte-for-byte with the supplied archive.

No complete test-suite pass, end-to-end success, or performance benchmark is claimed.
