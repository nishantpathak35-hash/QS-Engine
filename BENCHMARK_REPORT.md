# QS Benchmark Report — Phase-1 Reliability & Capability Validation

**Report Generation Date:** 2026-09-07  
**Benchmark Suite 1 (Generated File-Based Golden Benchmark):** `/tests/golden_real_files/` (10 Programmatically Generated DXF & Vector PDF Files)  
**Benchmark Suite 2 (Field Golden Benchmark - Ready for Anonymized Client Drawings):** `/tests/field_golden/`  
**Benchmark Suite 3 (Synthetic In-Memory Baseline):** `/tests/golden_real/`  
**Evaluation Standard:** IS 1200 / POMI / CPWD Statutory Measurement Rules  
**Core Authority Law:** *"Geometry measures. Semantics classify. Rules decide applicability. Calculators calculate. Exceptions protect accuracy. Real drawings are the acceptance benchmark."*

---

## 1. Generated File-Based Golden Benchmark (`/tests/golden_real_files/`)

> [!IMPORTANT]
> These fixtures are physical files on disk (`.dxf` and `.pdf`) created programmatically. They are valuable automated regression tests for formula and deduction verification, but they are **NOT** real client/site drawings. Their 0.00% variance proves mathematical and deduction correctness on synthetic vectors, not field accuracy on uncurated client drawings.

| Drawing Filename | Format | Archetype | Rooms | Verified Floor (sqm) | Measured Floor (sqm) | Floor Var % | Verified Skirting (m) | Measured Skirting (m) | Skirting Var % | Door Prec. / Recall | Status |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **PROJECT_01_GROUND_FLOOR.dxf** | DXF | Corporate HQ Ground Floor | 3 | 155.22 | 155.22 | **0.00%** | 78.64 | 78.64 | **0.00%** | 100% / 100% (4/4) | `PASSED` |
| **PROJECT_02_EXECUTIVE_SUITE.dxf**| DXF | Executive Management Suite | 3 | 68.00 | 68.00 | **0.00%** | 53.00 | 53.00 | **0.00%** | 100% / 100% (3/3) | `PASSED` |
| **PROJECT_03_TECH_HUB.dxf** | DXF | Tech Developer Facility | 3 | 118.50 | 118.50 | **0.00%** | 63.20 | 63.20 | **0.00%** | 100% / 100% (3/3) | `PASSED` |
| **PROJECT_04_CLINIC.dxf** | DXF | Medical Healthcare Clinic | 3 | 75.00 | 75.00 | **0.00%** | 56.20 | 56.20 | **0.00%** | 100% / 100% (3/3) | `PASSED` |
| **PROJECT_05_DESIGN_AGENCY.dxf** | DXF | Creative Design Studio | 3 | 100.00 | 100.00 | **0.00%** | 64.20 | 64.20 | **0.00%** | 100% / 100% (3/3) | `PASSED` |
| **PROJECT_06_LAW_FIRM.dxf** | DXF | Legal Chambers & Library | 3 | 92.00 | 92.00 | **0.00%** | 64.20 | 64.20 | **0.00%** | 100% / 100% (3/3) | `PASSED` |
| **PROJECT_07_FITNESS_STUDIO.dxf**| DXF | Commercial Fitness Centre | 3 | 115.00 | 115.00 | **0.00%** | 68.20 | 68.20 | **0.00%** | 100% / 100% (3/3) | `PASSED` |
| **PROJECT_08_RETAIL_SHOWROOM.dxf**| DXF | Retail Boutique Showroom | 3 | 145.00 | 145.00 | **0.00%** | 72.20 | 72.20 | **0.00%** | 100% / 100% (3/3) | `PASSED` |
| **PROJECT_09_TRAINING_CENTRE.pdf**| PDF | Training Facility (1:100) | 2 | 105.00 | 105.00 | **0.00%** | 60.00 | 60.00 | **0.00%** | N/A (0 doors) | `PASSED` |
| **PROJECT_10_COWORKING.pdf** | PDF | Coworking Space (1:100) | 2 | 92.00 | 92.00 | **0.00%** | 50.00 | 50.00 | **0.00%** | N/A (0 doors) | `PASSED` |

---

## 2. Truthful Benchmark Metrics (Audit Requirements 10, 11 & 13)

### A. Geometry Metrics (Measured on Generated Files)
| Metric | Target | Result | Status |
| :--- | :---: | :---: | :---: |
| **Room Area Mean Absolute Error (MAE)** | $\le 0.50\%$ | **0.00%** | `VERIFIED` |
| **Room Perimeter Error** | $\le 0.50\%$ | **0.00%** | `VERIFIED` |
| **Wall Centerline Length Error** | $\le 0.50\%$ | **0.00%** | `VERIFIED` |

### B. Object Detection Metrics
| Metric | Target | Result | Notes |
| :--- | :---: | :---: | :--- |
| **Door Identification Precision** | $\ge 98.0\%$ | **100.0%** (25 / 25 doors) | Measured on synthetic DXF blocks |
| **Door Identification Recall** | $\ge 95.0\%$ | **100.0%** (25 / 25 doors) | Measured on synthetic DXF blocks |
| **Window Precision** | $\ge 95.0\%$ | **NOT MEASURED** | Dataset currently has no window benchmark annotations |
| **Window Recall** | $\ge 90.0\%$ | **NOT MEASURED** | Dataset currently has no window benchmark annotations |

### C. Quantity Surveying (BOQ) Metrics
| Metric | Target | Result | Notes |
| :--- | :---: | :---: | :--- |
| **Flooring Quantity Variance** | $\le 1.0\%$ | **0.00%** | Verified against explicit finish codes |
| **Skirting Quantity Variance** | $\le 1.0\%$ | **0.00%** | Verified with door deduction math |
| **Partition Quantity Variance** | $\le 1.0\%$ | **NOT MEASURED (Files 1-10)** | Measured end-to-end in `test_partition_takeoff_e2e.py` |
| **Ceiling Quantity Variance** | $\le 1.0\%$ | **0.00%** | Verified boundary gross area |

### D. Human Effort & QA Metrics
| Metric | Target | Result | Notes |
| :--- | :---: | :---: | :--- |
| **Exceptions per Drawing** | $\le 2.0$ | **0.40** | Purely unassigned finish alerts |
| **Manual Geometric Corrections Required** | $0$ | **0** | Clean synthetic boundary topologies |
| **Average Estimator Review Time** | $\le 10\text{ mins}$ | **NOT MEASURED** | Requires live field human-in-the-loop study |

---

## 3. Synthetic Ground-Truth Benchmark (`/tests/golden_real/`)

> [!NOTE]
> This suite tests internal formula accuracy, IS 1200 door rebate calculations, and deduction math on programmatically defined geometry rectangles. It does not replace the file-based physical benchmark in Section 1.

- **Suite Path:** `/tests/golden_real/test_real_benchmark_suite.py`
- **Number of Cases:** 10 synthetic project archetypes
- **Outcome:** 10 / 10 passed with 0.00% mathematical error on IS 1200 deduction rules.

---

## 4. Key Architectural Integrity Confirmations

1. **No Fictitious Finish Guessing**: A room without finish annotation or project mapping yields `FL-RAW` and `CL-RAW` with `UNKNOWN_FLOOR_FINISH` / `UNKNOWN_CEILING_FINISH`. Never defaults to Vitrified Tile or Gypsum.
2. **Door Subtype Segregation**: Single-leaf doors ($\le 1.25\text{m}$) route to `DR-01`, double-leaf doors ($\ge 1.35\text{m}$) route to `DR-02`, and unclassified doors yield `DR-UNKNOWN` with `REVIEW_REQUIRED`.
3. **Double Quantity Prevention**: `SK-01` and `SK-02` evaluate distinct `applies_when` constraints, preventing double perimeter takeoff in the same room.
4. **Multi-Page Vector PDF Pipeline**: All pages of multi-page PDFs are extracted, walls filtered via `WallDetector`, and room entities attributed with `drawing_id`, `page_number`, and `page_scale`.
5. **Spatial Revision Engine**: Symmetrically matched rooms across revisions (e.g. `Conference Room` $\rightarrow$ `Boardroom`, $\text{IoU} \ge 0.95$) are flagged as `MODIFIED` rather than inflating takeoff with `REMOVED + ADDED`.
