# Field Golden Benchmark Directory

This directory is reserved for **actual anonymized client and site construction drawings** (`.dxf` and `.pdf`).

## Protocol for Real Field Drawings (Requirements 12 & 13)

1. **Physical Files Only**: Place the actual drawing files (`drawing.dxf` or `drawing.pdf`) into subfolders here (e.g. `tests/field_golden/FIELD_001/`).
2. **Never Recreate Geometry in Code**: The test engine must genuinely parse the raw drawing file. Under no circumstances should lines or rooms be hardcoded in Python.
3. **Audit Verification Sheet**: Each drawing folder must include a `verified_measurements.yaml` audited by a professional QS.

### Expected `verified_measurements.yaml` Schema

```yaml
drawing_id: FIELD-001
drawing_filename: drawing.dxf
drawing_quality_score: 0.88 # Estimated drawing hygiene (layers, snaps, text quality)

verified:
  rooms:
    meeting_room:
      area_sqm: 41.72
      perimeter_m: 26.12
    reception:
      area_sqm: 28.50
      perimeter_m: 21.40

  doors:
    single_leaf: 3
    double_leaf: 1
    glass: 0

  partitions:
    PT-01: 72.40 # sqm
    PT-02: 18.00 # sqm

  skirting:
    SK-01: 24.80 # rm
    SK-02: 18.20 # rm

field_metrics:
  estimator_manual_corrections: 0
  measured_review_duration_minutes: null # Set only if timed in live study
```

### Automation Quality Reporting

When real field drawings are evaluated, the benchmark runner aggregates:
- **Area MAE / MAPE**
- **Door Precision & Recall**
- **Partition Variance %**
- **Auto-measured % vs Review-required % vs Unresolved %**
- **Exceptions Count & Types**
