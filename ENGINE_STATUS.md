# QS Quantification Engine — Verified Capability Status Matrix

**Last Full Audit:** 2026-09-08  
**Automated Test Suite Status:** **168 / 168 Passing (100%)**  
**Benchmark Suite Status:** **30 / 30 Generated File Golden Tests Passing (0.00% Variance)**  
**Core Authority Law:** *"Geometry measures. Semantics classify. Rules decide applicability. Calculators calculate. Exceptions protect accuracy. Real drawings are the acceptance benchmark."*

Allowed Statuses: `WORKING`, `PARTIAL`, `EXPERIMENTAL`, `NOT IMPLEMENTED`

---

### Capability: Skirting Material & Finish Applicability (Audit Item 1)
- **Status:** `WORKING`
- **Evidence:** `SK-01` rule contains explicit `applies_when: skirting_finish_code: SK-01`. If finish schedule/evidence is absent, engine records measured boundary perimeter but never fabricates a material item. Generates `UNKNOWN_SKIRTING_FINISH` exception and leaves skirting material unclassified.
- **Known Limitation:** Requires explicit finish annotation or approved project mapping to select material.
- **End-to-End Test:** `tests/adversarial/test_phase1_materials_and_applicability.py::test_skirting_applicability_prevents_duplicate_quantities`

---

### Capability: Door Subtype Routing & Cardinality (Audit Items 2, 14, 15)
- **Status:** `WORKING`
- **Evidence:** Single leaf (`single_leaf`), double leaf (`double_leaf`), and glass (`glass`) rules specify exact semantic attributes. A double-leaf door cannot match a single-leaf rule. Mutual exclusive matching (`match_policy: exclusive`) prevents duplicate takeoff and flags `AMBIGUOUS_RULE_MATCH` if rules conflict. Unresolved doors produce `DR-UNKNOWN` with `REVIEW_REQUIRED`.
- **Known Limitation:** Unlabeled door blocks without swing geometry require manual classification.
- **End-to-End Test:** `tests/adversarial/test_phase1_materials_and_applicability.py::test_door_subtypes_route_to_distinct_boq_items`

---

### Capability: Drywall & Partition Wall Takeoff (Audit Item 3)
- **Status:** `WORKING`
- **Evidence:** API processes wall entities from DXF and PDF, converts to `WallSegment`, and invokes `wall.partition_area`. Computes `Length * Height - Opening Deductions`. Tested for gypsum (`PT-01`), glass (`PT-02`), unmapped partition (`PT-RAW`), missing height exception (`MISSING_WALL_HEIGHT`), and IS 1200 opening deductions.
- **Known Limitation:** Wall height must be provided via 3D/metadata or approved project assumption (`default_ceiling_height_m`).
- **End-to-End Test:** `tests/adversarial/test_partition_takeoff_e2e.py`

---

### Capability: Strict Calculator Registry & Zero Silent Fallback (Audit Items 4 & 18)
- **Status:** `WORKING`
- **Evidence:** Registered calculators declare `supported_entities` (`room`, `wall`, `opening`, etc.). If YAML references an unknown calculator, rule execution is blocked with `UNKNOWN_CALCULATOR` exception and zero quantity. Incompatible source entities fail profile schema validation at startup. Never substitutes another calculator automatically.
- **Known Limitation:** Custom calculators must be registered via `@CalculatorRegistry.register` before profile load.
- **End-to-End Test:** `tests/adversarial/test_audit_p0_fixes.py`

---

### Capability: Rule Schema Validation via Pydantic (Audit Item 5)
- **Status:** `WORKING`
- **Evidence:** `RuleProfileSchema` validates all YAML profiles on load. Enforces rule ID uniqueness, supported units (`sqm`, `m`, `rm`, `nos`, etc.), valid source entity types, and calculator existence. Malformed configurations fail immediately with `RuleValidationError`.
- **Known Limitation:** None.
- **End-to-End Test:** `tests/adversarial/test_audit_p0_fixes.py`

---

### Capability: Project Profile & Assumption Lineage in Door Detection (Audit Item 6)
- **Status:** `WORKING`
- **Evidence:** API passes `ProjectProfile` into `DoorDetector.process_blocks()`. When assumptions are enabled, dimensions are attributed with `width_source="PROJECT_ASSUMPTION"` and `height_source="PROJECT_ASSUMPTION"` and flagged `REVIEW_REQUIRED`. When assumptions are disabled, missing dimensions produce `MISSING_OPENING_WIDTH` / `MISSING_OPENING_HEIGHT` exceptions with null dimensions.
- **Known Limitation:** None.
- **End-to-End Test:** `tests/adversarial/test_partition_takeoff_e2e.py::test_partition_takeoff_end_to_end_with_assumed_height`

---

### Capability: Quantity Dependency Status Propagation (Audit Item 7)
- **Status:** `WORKING`
- **Evidence:** `propagate_dependency_status()` computes transitive status over dependency graphs. If a door width is unverified, downstream skirting and partition quantities inherit `REVIEW_REQUIRED`. If wall height is missing, partition status is `REVIEW_REQUIRED`. No downstream quantity remains `AUTO_MEASURED` if an input is unresolved.
- **Known Limitation:** None.
- **End-to-End Test:** `tests/adversarial/test_audit_p0_fixes.py`

---

### Capability: PDF Wall Intelligence & Filtering (Audit Item 8)
- **Status:** `PARTIAL`
- **Evidence:** `WallDetector` validates parallel segments (75mm–350mm thickness), filters sheet borders, title blocks, and short ticks. Connected vector lines form topology.
- **Known Limitation:** Highly complex multi-layer drawings with non-standard vector decorations require further parallel pair heuristics; currently relies on vector line snapping and wall candidate extraction.
- **End-to-End Test:** `tests/golden/test_golden_pdf.py`

---

### Capability: PDF Topology Confidence Scoring (Audit Item 9)
- **Status:** `WORKING`
- **Evidence:** `RoomBoundarySolver` scores polygon confidence based on wall-supported boundary ratio, minimum sensible area (rejection of furniture/cavity loops < 2.5 sqm), label ambiguity, and opening verification. Low-confidence room polygons receive `status=REVIEW_REQUIRED` and flag `LOW_CONFIDENCE_ROOM_POLYGON`.
- **Known Limitation:** Extreme architectural chamfers or non-orthogonal curved walls may reduce confidence score.
- **End-to-End Test:** `tests/adversarial/test_api_multipage_pdf.py`

---

### Capability: Truthful Benchmark Labelling & Metric Separation (Audit Items 10, 11, 12, 13)
- **Status:** `WORKING`
- **Evidence:** Test suite clearly separates `Generated File-Based Golden Benchmark` (`tests/golden_real_files/`) from `Field Golden Benchmark` (`tests/field_golden/`). Unmeasured metrics (Window Precision/Recall, live estimator review times) are marked `NOT MEASURED` in `BENCHMARK_REPORT.md` rather than claimed.
- **Known Limitation:** Field golden drawings will be populated as real anonymized client datasets are onboarded.
- **End-to-End Test:** `tests/golden_real_files/test_golden_real_drawings.py`

---

### Capability: Separation of Base Measurements from BOQ Items (Audit Item 16)
- **Status:** `WORKING`
- **Evidence:** `TakeoffSummary.base_measurements` records raw physical quantities (`total_floor_area_sqm`, `total_perimeter_m`, `total_wall_length_m`, `total_openings_count`) independently of material classification. Available via `/v1/drawings/{id}/process` and `/v1/drawings/{id}/quantities`.
- **Known Limitation:** None.
- **End-to-End Test:** `tests/adversarial/test_partition_takeoff_e2e.py`

---

### Capability: Generic Rule Runtime Acceptance (Audit Item 17)
- **Status:** `WORKING`
- **Evidence:** Novel trade profile with `DEMO-001` (room polygon area) and `DEMO-002` (wall linear length) executes purely from YAML configuration with ZERO changes to Python codebase.
- **Known Limitation:** None.
- **End-to-End Test:** `tests/adversarial/test_generic_rule_runtime_acceptance.py`

---

### Capability: Spatial Revision Engine via API (Audit Item 19)
- **Status:** `WORKING`
- **Evidence:** Geometric entities from every takeoff are persisted in `GEOMETRY_DB`. API `/v1/revisions/compare` passes persisted geometry to `RevisionDifferenceEngine.compare_takeoffs()`. Renamed spaces with identical geometry ($\text{IoU} \ge 0.95$) are classified as `MODIFIED` rather than inflating takeoff with `REMOVED + ADDED`.
- **Known Limitation:** Deformations below 50% IoU are reported as removal of baseline and addition of revised space.
- **End-to-End Test:** `tests/adversarial/test_api_spatial_revision.py`

---

### Capability: Local OCR / Local AI Fallback
- **Status:** `PARTIAL`
- **Evidence:** `PaddleOCRProvider` implemented in `vision/ocr/` with confidence scoring. Phase-1 prioritizes deterministic CAD vectors and PDF text streams; OCR is invoked for raster/hybrid fallbacks.
- **Known Limitation:** Scanned paper drawings requiring full raster vectorization scheduled for Phase 2.
- **End-to-End Test:** `tests/golden/test_golden_ocr_fusion.py`

---

### Capability: Scanned Raster Image Vectorization
- **Status:** `NOT IMPLEMENTED`
- **Evidence:** Pure raster drawings return explicit HTTP 400 error `RASTER_PROCESSING_NOT_SUPPORTED`.
- **Known Limitation:** Phase-2 scope.
- **End-to-End Test:** `tests/integration/test_api.py`

---

### Capability: Free LLM Integration & Diverse CAD Architecture Benchmark
- **Status:** `WORKING`
- **Evidence:** Free LLM architecture (`core/ai/`) integrates Google Gemini API (Free Tier), local offline Ollama (`llama3`/`qwen2.5`), and deterministic fallback with strict Pydantic schemas (`ClassifyLayerTask`, `ClassifyBlockTask`, `ClassifyAnnotationTask`). Tested across 5 diverse CAD architectural typologies (Residential 2BHK, Healthcare Clinic, Corporate Tech Suite, Retail Flagship Store, Industrial Warehouse Office) with unstandardized layer conventions and custom door blocks. 100% mathematical zero-hallucination takeoff verified.
- **Known Limitation:** AI is strictly constrained to semantic classification of ambiguous layers/blocks; geometric measurements and calculations remain 100% deterministic per Blueprint Section 56.
- **End-to-End Test:** `tests/adversarial/test_free_llm_cad_diversity.py`

