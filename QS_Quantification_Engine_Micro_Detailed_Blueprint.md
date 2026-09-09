# QS Quantification Engine — Micro-Detailed Technical Blueprint

**Document Type:** Standalone Engine Blueprint  
**Purpose:** Read interior/construction drawings (PDF/DXF initially), understand measurable elements, and generate traceable QS quantities using deterministic geometry + free/local AI.  
**Integration:** Independent engine first; future integration with Construct-O-Genie through APIs.  
**Core Principle:** **AI interprets; deterministic code measures.**

---

# 1. Executive Summary

The engine is technically practical if it is built as a **hybrid system**, not as a “single AI model that reads a drawing and gives a BOQ.”

The correct architecture is:

```text
Drawing
  ↓
Input Classification
  ↓
Vector / Raster Parsing
  ↓
Geometry Extraction
  ↓
OCR + Symbol / Object Recognition
  ↓
Drawing Semantic Model
  ↓
QS Rule Engine
  ↓
Quantity Calculations
  ↓
Confidence + Exceptions
  ↓
Human Review
  ↓
Verified Measurement Output
```

The engine should not depend on OpenAI, Claude, Gemini or any paid API for routine processing.

Most calculations—area, perimeter, length, count, deductions, intersections, room boundaries—are normal geometry problems and should be calculated by code.

AI is useful only where the drawing contains ambiguity, such as:

- identifying whether a symbol is a door, window, chair, switch or sanitary fixture;
- understanding room names and annotations;
- classifying hatches or finishes;
- associating labels with nearby geometry;
- understanding inconsistent drawing conventions;
- interpreting notes where deterministic rules are insufficient.

The best commercial target is **machine-assisted QS**, not “100% autonomous QS.”

A realistic mature target is:

> **80–95% of repetitive takeoff automated on standardized vector drawings, with exceptions reviewed by a human.**

Accuracy will vary significantly with drawing quality and standardization.

---

# 2. What the Engine Is

The engine is a standalone **Drawing-to-Quantity Engine**.

It accepts drawings and outputs measurement data.

It is **not**:

- a BOQ costing system;
- a procurement system;
- a PO generator;
- a billing system;
- a full CAD editor;
- a generic chatbot.

Its responsibility ends at producing **traceable quantities and measurement evidence**.

Example output:

```text
Drawing: A-102 Rev-03
Floor: Ground Floor
Room: Conference Room 02

Item: Vitrified Tile Flooring
Quantity: 41.72 sqm
Measurement Method: Closed room polygon
Source Area: 41.72 sqm
Confidence: 98%
Status: Verified
```

Another example:

```text
Item: Gypsum Partition
Drawing: A-104 Rev-02
Wall Segment: W-018

Centreline Length: 12.840 m
Height: 2.700 m
Gross Area: 34.668 sqm
Opening Deduction: 2.835 sqm
Net Area: 31.833 sqm
Confidence: 93%
```

Every number must be explainable.

---

# 3. What Makes the Engine Practical

## 3.1 Easy Problems

These are highly practical:

- DXF line lengths;
- closed polygon areas;
- room areas;
- perimeter calculations;
- block counting;
- layer-based classification;
- door/window counts where blocks are standardized;
- annotation extraction;
- dimension parsing;
- basic wall length;
- hatch area;
- flooring quantities;
- false ceiling area;
- skirting perimeter;
- simple partitions.

These generally do not require LLMs.

---

## 3.2 Medium Problems

Practical, but need a mixture of AI and rules:

- identifying doors from non-standard symbols;
- detecting rooms where boundaries are incomplete;
- mapping text labels to rooms;
- identifying furniture symbols;
- differentiating wall types;
- reading dimension text on noisy PDFs;
- assigning hatches to finishes;
- recognizing electrical symbols;
- detecting sanitary fixtures;
- deriving elevation quantities.

---

## 3.3 Hard Problems

These should not be promised in MVP:

- arbitrary scanned hand-marked drawings;
- poorly rasterized PDFs;
- drawings without scale;
- inconsistent architectural conventions;
- complex joinery from elevations;
- hidden dimensions;
- construction intent not visible in drawing;
- multi-layer material assemblies from geometry alone;
- automatic interpretation of every consultant drawing;
- quantity decisions that require contractual/specification judgment.

For these cases the engine should produce an **exception**, not fabricate a quantity.

---

# 4. Input Types

## Priority 1 — DXF

Best MVP input.

Why:

- entities are already structured;
- exact coordinates exist;
- layers exist;
- blocks exist;
- text is structured;
- polylines can carry geometry;
- dimensions may be available as CAD entities.

Typical usable entities:

- LINE
- LWPOLYLINE
- POLYLINE
- ARC
- CIRCLE
- HATCH
- TEXT
- MTEXT
- INSERT / BLOCK
- DIMENSION
- SPLINE

Recommended parser:

- `ezdxf`

Important:

DWG should not be the first native target. The engine can initially require **DXF export** from CAD.

---

## Priority 2 — Vector PDF

Second-best input.

A vector PDF may contain:

- paths;
- lines;
- text;
- curves;
- clipping;
- vector hatches.

The challenge is that CAD semantics such as layers and blocks may be lost.

The engine must reconstruct topology from primitives.

---

## Priority 3 — Raster / Scanned PDF

Hardest.

Pipeline becomes:

```text
PDF Page
 ↓
Render at high DPI
 ↓
Image Cleanup
 ↓
Line Detection
 ↓
OCR
 ↓
Object Detection
 ↓
Geometry Reconstruction
```

This should be Phase 2/3, not Phase 1.

---

# 5. Core Design Principle

## AI must never be the final calculator.

Bad design:

```text
Upload drawing → Vision LLM → "Flooring = 1,842 sqft"
```

Why bad:

- difficult to audit;
- inconsistent;
- difficult to reproduce;
- hallucination risk;
- no geometric proof;
- model changes may change answers.

Correct design:

```text
AI:
"This polygon appears to be Room 12."

Geometry Engine:
Polygon area = 171.13 sqm

QS Rule:
Floor finish F-02 applies to Room 12

Output:
F-02 Flooring = 171.13 sqm
```

AI provides semantic interpretation.

Code provides measurement.

---

# 6. High-Level System Architecture

```text
┌──────────────────────────┐
│      File Intake API     │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Drawing Type Classifier  │
│ DXF / Vector / Raster    │
└────────────┬─────────────┘
             ↓
┌────────────────────────────────────┐
│ Parsing Layer                      │
│ DXF Parser / PDF Vector / Raster   │
└────────────┬───────────────────────┘
             ↓
┌──────────────────────────┐
│ Normalized Geometry      │
│ Coordinate Model         │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Drawing Intelligence     │
│ OCR / Detector / Rules   │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Semantic Drawing Graph   │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ QS Rule Engine           │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Quantity Calculator      │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Confidence + Exceptions  │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Human Review UI          │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Verified Output API      │
└──────────────────────────┘
```

---

# 7. Module 1 — File Intake Engine

Responsibilities:

- accept files;
- calculate hash;
- create job;
- identify extension;
- verify file;
- preserve original;
- extract metadata;
- assign project/drawing/revision;
- prevent accidental duplicate processing.

Example metadata:

```json
{
  "drawing_id": "DRW-000147",
  "filename": "GF_LAYOUT_REV03.dxf",
  "drawing_number": "A-101",
  "revision": "03",
  "discipline": "architectural",
  "floor": "ground_floor",
  "source_type": "dxf"
}
```

---

# 8. Module 2 — Drawing Type Classifier

The system must decide:

```text
DXF
Vector PDF
Mixed PDF
Raster PDF
Image
Unsupported
```

For PDF:

1. inspect whether vector paths exist;
2. inspect embedded text;
3. inspect image coverage;
4. classify each page independently.

A PDF can contain:

- one vector page;
- one scanned page;
- one mixed page.

Do not classify only at file level.

---

# 9. Module 3 — Coordinate Normalization

Every input format must be converted to one internal coordinate system.

Recommended canonical units:

```text
millimetres
```

Internal geometry should use:

- X;
- Y;
- optional Z;
- drawing-space unit;
- physical unit;
- page transform;
- rotation.

Example:

```json
{
  "entity_id": "G-98421",
  "type": "polyline",
  "points_mm": [
    [0, 0],
    [4500, 0],
    [4500, 3200],
    [0, 3200]
  ]
}
```

Never calculate permanent quantities using screen pixels.

Pixels are only useful during raster analysis.

---

# 10. Module 4 — Scale Engine

Scale is critical.

Possible scale sources:

### DXF

Prefer model-space coordinates.

If drawing is properly authored, physical units can often be derived from CAD metadata/convention.

### PDF

Possible methods:

1. explicit scale note:
   `Scale 1:50`
2. dimension calibration:
   visible dimension = `3000`
3. user calibration:
   user selects two points and enters actual length.
4. sheet/view metadata if reliable.

Recommended hierarchy:

```text
Explicit CAD geometry
 > reliable dimension calibration
 > explicit drawing scale
 > manual calibration
 > AI guess (never final)
```

If scale cannot be established:

```text
status = SCALE_REQUIRED
```

No final quantity should be generated.

---

# 11. Module 5 — Vector Geometry Parser

For DXF extract:

```text
entity
layer
handle
block name
coordinates
linetype
color if useful
text
hatch pattern
dimension metadata
```

Store raw and normalized forms separately.

Example layer signal:

```text
A-WALL
A-DOOR
A-GLAZ
F-FURN
E-LIGHT
```

Do not assume all companies use the same naming convention.

Create a configurable **Layer Mapping Profile**.

Example:

```yaml
profile: client_xyz
mappings:
  A-WALL: wall
  PART-GYP: gypsum_partition
  FL-FIN: floor_finish
  DR: door
```

---

# 12. Module 6 — Raster Preprocessing

For scanned drawings use OpenCV-style processing.

Pipeline:

```text
Render page
 ↓
Deskew
 ↓
Grayscale
 ↓
Contrast normalization
 ↓
Adaptive threshold
 ↓
Noise removal
 ↓
Line preservation
 ↓
Optional tile segmentation
```

Do not run object detection on a massive page as one low-resolution image.

Better:

```text
Full page
 ↓
Create overlapping tiles
 ↓
Detect objects
 ↓
Transform tile coordinates back to page
 ↓
Deduplicate detections
```

---

# 13. Module 7 — OCR Engine

Recommended local OCR:

- PaddleOCR as primary candidate;
- Tesseract can remain fallback/benchmark.

OCR should extract:

```text
text
bounding box
rotation
confidence
page
coordinates
```

Important text categories:

- room names;
- dimensions;
- levels;
- material codes;
- door tags;
- window tags;
- notes;
- drawing title;
- scale;
- revision;
- grid labels.

Raw OCR text is not enough.

A post-processing stage must classify text.

Example:

```text
"3000"
```

could mean:

- dimension;
- room code;
- detail number.

So OCR output needs spatial context.

---

# 14. Module 8 — Dimension Understanding

Dimension reading is more than OCR.

Need to detect:

- extension lines;
- dimension line;
- arrowheads/ticks;
- numeric text;
- associated geometry.

Create object:

```json
{
  "type": "linear_dimension",
  "value_mm": 3000,
  "text_bbox": "...",
  "start_point": "...",
  "end_point": "...",
  "confidence": 0.96
}
```

Dimension associations can be used for:

- scale validation;
- geometry correction;
- wall width validation;
- opening size extraction.

---

# 15. Module 9 — Line / Wall Detection

For vector drawings:

- group near-parallel lines;
- detect wall pairs;
- determine wall thickness;
- construct centreline;
- join segments;
- identify intersections.

For raster:

possible techniques:

- Hough transforms;
- contour detection;
- skeletonization;
- learned line-segment detection;
- topology cleanup.

Internal wall object:

```json
{
  "wall_id": "W-104",
  "centerline_length_mm": 8540,
  "thickness_mm": 100,
  "start": [x1, y1],
  "end": [x2, y2],
  "classification": "partition",
  "confidence": 0.92
}
```

---

# 16. Module 10 — Room Boundary Detection

Goal:

convert floor plan into closed spatial regions.

Possible logic:

```text
wall lines
 + door gap handling
 + columns
 + room dividers
 → planar graph
 → closed faces
```

Then assign room name using nearest/internal text.

Example:

```json
{
  "room_id": "R-021",
  "name": "Conference Room",
  "polygon": "...",
  "gross_area_sqm": 38.21,
  "perimeter_m": 25.94
}
```

Room detection should support manual correction.

A user should be able to:

- merge rooms;
- split room;
- redraw boundary;
- rename room.

---

# 17. Module 11 — Door and Window Detection

Detection strategy priority:

### DXF

1. known block names;
2. layer;
3. geometry pattern;
4. AI detector.

### PDF

1. vector shape heuristics;
2. text/tag association;
3. local object detector.

Door object:

```json
{
  "opening_id": "D-018",
  "type": "door",
  "width_mm": 900,
  "height_mm": 2100,
  "host_wall": "W-104",
  "tag": "D1",
  "confidence": 0.97
}
```

Opening association is essential because wall finish and partition calculations need deductions.

---

# 18. Module 12 — Symbol Detection

Potential classes:

### Architectural

- door;
- window;
- column;
- staircase;
- sanitary fixture.

### Furniture

- workstation;
- chair;
- table;
- sofa;
- cabinet.

### Electrical

- light;
- switch;
- socket;
- data point;
- detector;
- speaker.

### Plumbing

- WC;
- basin;
- sink;
- floor trap.

Use a local object detection model.

For a commercial product, choose frameworks/models only after confirming both:

- code license;
- pretrained model/weights license.

A permissive implementation option is to evaluate **PaddleDetection**-based models and export to ONNX where appropriate.

---

# 19. Module 13 — Custom Symbol Training

Generic object detectors will not understand every interior drawing symbol.

You will eventually need a custom dataset.

Recommended dataset structure:

```text
class
image crop
bounding box / polygon
drawing source
drawing style
discipline
company/template
```

Initial classes should be limited.

Example MVP:

```text
door
window
workstation
chair
light
switch
socket
wc
basin
```

Do not train 100 classes initially.

---

# 20. Module 14 — Hatch / Finish Detection

Vector DXF:

- HATCH entity;
- pattern;
- boundary;
- layer.

Vector PDF:

- identify repeated vector patterns;
- clipping region;
- nearby finish legend.

Raster:

- texture classification;
- local pattern descriptors;
- AI classification.

Output:

```json
{
  "finish_region_id": "F-120",
  "finish_code": "F-02",
  "polygon": "...",
  "area_sqm": 41.72,
  "confidence": 0.87
}
```

---

# 21. Module 15 — Legend Interpreter

Interior drawings frequently have legends.

Example:

```text
F-01 = Carpet
F-02 = 600 x 1200 Vitrified Tile
W-01 = Paint
W-02 = Laminate
```

The engine should detect structured legend tables.

Output:

```json
{
  "F-01": {
    "category": "floor_finish",
    "description": "Carpet"
  },
  "F-02": {
    "category": "floor_finish",
    "description": "600x1200 Vitrified Tile"
  }
}
```

Then semantic regions labelled F-02 can inherit material information.

---

# 22. Module 16 — Drawing Semantic Graph

This is the most important architecture layer.

Do not send raw lines directly to the QS calculator.

Create a normalized drawing model.

Example:

```text
Project
 └── Floor
      ├── Room
      │    ├── FloorFinish
      │    ├── CeilingFinish
      │    ├── Walls
      │    ├── Doors
      │    └── Furniture
      │
      ├── Wall
      │    ├── Openings
      │    └── Finish
      │
      └── Devices
```

This semantic graph becomes the **single source of truth**.

---

# 23. Module 17 — QS Rule Engine

Rules should not be hardcoded everywhere in Python.

Create configurable QS rules.

Example rule:

```yaml
id: flooring_area
applies_to: room
when:
  floor_finish: true
formula:
  quantity: net_floor_area
unit: sqm
```

Skirting:

```yaml
id: skirting
applies_to: room
formula:
  quantity: room_perimeter - total_door_width
unit: rm
```

Wall paint:

```yaml
id: wall_paint
applies_to: wall
formula:
  gross_area: wall_length * wall_height
  deduction: door_area + window_area
  quantity: gross_area - deduction
unit: sqm
```

Rule configuration allows the engine to support different QS practices without rewriting the application.

---

# 24. Measurement Rules — Examples

## Flooring

```text
Quantity = closed finish polygon area
```

or

```text
Quantity = room net floor area
```

---

## Skirting

```text
Quantity =
room perimeter
- door opening widths
- explicitly excluded segments
```

---

## Wall Finish

```text
Gross Wall Area =
wall length × applicable height

Net Wall Area =
gross wall area
- door area
- window area
- other deductible opening area
```

---

## Gypsum Partition

Possible conventions:

```text
Centreline length × height
```

or

```text
face area × number of payable faces
```

The engine must not assume one method globally.

Store rule profile.

---

## False Ceiling

```text
Ceiling Area =
ceiling finish boundary
```

Possible deduction rules:

- shafts;
- large openings;
- atriums;
- voids.

---

## Grid Ceiling

```text
Area = ceiling region area
```

Optionally:

```text
tile count ≈ area / module area
```

but purchase quantity should not be confused with measured quantity.

---

## Doors

```text
Count = valid unique door instances
```

Attributes:

- type;
- width;
- height;
- tag.

---

## Windows

Same principle.

---

## Electrical Points

```text
Quantity = unique symbol count
```

Deduplicate overlapping detections.

---

# 25. Rule Profiles

Different clients / companies may follow different measurement conventions.

Use profiles:

```text
Standard Interior Profile
Client ABC Profile
Company XYZ Profile
Project Specific Profile
```

Inheritance:

```text
System Default
  ↓
Company Rule
  ↓
Project Rule
  ↓
Manual Exception
```

The most specific valid rule wins.

---

# 26. Module 18 — Local AI Layer

Local AI means inference happens on your machine/server.

No paid API call is required for each drawing.

Recommended separation:

### OCR AI

PaddleOCR

### Object Detection AI

A commercially suitable open-source detector framework/model after license verification.

### Optional Local Language/Vision Model

Use through a local runtime such as Ollama only for ambiguous semantic tasks.

Example local-model task:

```text
Input:
Detected note:
"FULL HT GYP PARTITION WITH 12MM PLY SUPPORT"

Question:
Which internal category best matches this note?

Allowed output:
gypsum_partition_with_ply
```

Never ask:

```text
"Read this entire drawing and calculate all quantities."
```

---

# 27. Why Local AI Can Be “Free”

The following costs can be zero:

```text
OpenAI API cost = ₹0
Claude API cost = ₹0
Gemini API cost = ₹0
Per-token charge = ₹0
Per-drawing external inference charge = ₹0
```

because models are hosted locally.

But total cost is **not zero**.

You still have:

- development effort;
- computer/server;
- storage;
- electricity;
- optional GPU;
- model training;
- labeling;
- maintenance.

Correct commercial statement:

> **The engine can have near-zero marginal AI API cost by running open-source models locally.**

---

# 28. Recommended Licensing Strategy

Since this can become a commercial product:

Prefer:

- Apache-2.0 libraries;
- MIT libraries;
- BSD libraries;
- models whose weights explicitly permit intended commercial use.

Avoid making architecture dependent on a tool whose license creates unwanted obligations for your distribution/business model.

Maintain a file:

```text
THIRD_PARTY_LICENSES.md
```

Fields:

```text
dependency
version
license
source
commercial-use status
model-weight license
review date
```

---

# 29. Free/Local Stack — Candidate Components

## Geometry / CAD

```text
Python
ezdxf
Shapely
NumPy
```

## Image Processing

```text
OpenCV
Pillow
```

## OCR

```text
PaddleOCR
```

## Object Detection / AI

```text
PaddleDetection or another commercially suitable detector
ONNX Runtime for optimized local inference
```

## Optional Local LLM/VLM Runtime

```text
Ollama
```

## Backend

```text
FastAPI
Pydantic
SQLAlchemy
```

## Database

Start:

```text
PostgreSQL
```

Spatial geometry can use:

```text
PostGIS
```

if useful.

## Background Jobs

For standalone MVP:

```text
Redis + Celery/RQ
```

or a simpler internal worker initially.

---

# 30. Why ONNX Is Useful

Training framework and production runtime do not have to be the same.

Example:

```text
Train Detector
 ↓
Export model.onnx
 ↓
ONNX Runtime
 ↓
CPU/GPU Local Inference
```

Advantages:

- portable;
- CPU deployment possible;
- GPU optional;
- framework independence;
- local inference;
- easier future embedding into services.

---

# 31. Local Hardware Strategy

## Development Machine

Reasonable:

```text
Modern 8+ core CPU
32 GB RAM preferred
SSD
Optional NVIDIA GPU
```

GPU helps for:

- model training;
- larger object detectors;
- local vision-language models.

But geometry, OCR and smaller inference can often run CPU-side.

---

# 32. CPU-First MVP

Important business recommendation:

**Do not make GPU mandatory for MVP.**

Pipeline:

```text
DXF/vector first
geometry heavy
OCR limited
small detector
```

This allows:

- local workstation;
- cheap server;
- easier testing;
- low operational cost.

GPU acceleration can come later.

---

# 33. Confidence Engine

Every semantic conclusion needs confidence.

Example confidence sources:

```text
layer match = 0.99
known block name = 0.99
vector geometry match = 0.95
OCR = 0.91
detector = 0.83
LLM inference = 0.68
manual = 1.00
```

A combined confidence score can be calculated.

Example:

```text
Door detected from:
block = DR_900
layer = A-DOOR
geometry = swing arc

Confidence = 0.995
```

Another:

```text
Unknown raster symbol
detector says socket = 0.61

Result:
REVIEW_REQUIRED
```

---

# 34. Confidence Thresholds

Example:

```text
>= 0.95   auto-accept candidate
0.80–0.95 visible review
0.60–0.80 mandatory review
< 0.60    unresolved
```

Thresholds should be configurable by entity type.

A 90% confidence room label is different from a 90% confidence wall boundary.

---

# 35. Exception Engine

Exceptions are a feature, not a failure.

Possible exception types:

```text
SCALE_NOT_FOUND
ROOM_BOUNDARY_OPEN
UNKNOWN_SYMBOL
AMBIGUOUS_FINISH
MISSING_HEIGHT
MULTIPLE_LABEL_MATCH
DRAWING_CONFLICT
LOW_OCR_CONFIDENCE
UNSUPPORTED_ENTITY
DUPLICATE_OBJECT
REVISION_CONFLICT
```

Example:

```json
{
  "exception": "MISSING_HEIGHT",
  "entity": "W-102",
  "required_for": "wall_paint_quantity",
  "suggested_default": 2700,
  "status": "pending_review"
}
```

---

# 36. Human Review Interface

The reviewer should see the drawing.

Essential interactions:

### Select quantity

Click:

```text
Vitrified Tile — 41.72 sqm
```

Drawing highlights the exact polygon.

### Select wall

Shows:

```text
Length: 12.84 m
Height: 2.70 m
Door deduction: 1.89 sqm
Window deduction: 0.95 sqm
Net: 31.83 sqm
```

### User actions

```text
Accept
Edit
Reject
Reclassify
Split
Merge
Draw manually
Add assumption
```

---

# 37. Audit Trail

Every quantity must have lineage.

Example:

```json
{
  "quantity_id": "Q-887",
  "item": "wall_paint",
  "result": 31.833,
  "unit": "sqm",
  "source_drawing": "A-104",
  "revision": "02",
  "source_entities": [
    "W-104",
    "D-018",
    "WIN-022"
  ],
  "formula": "(12.84*2.7)-(0.9*2.1)-(1.2*0.79)",
  "rule_version": "QS-WALL-004-v3",
  "review_status": "verified",
  "reviewed_by": "user-id",
  "timestamp": "..."
}
```

This is essential for trust.

---

# 38. Revision Management

Never overwrite earlier measurement results.

Example:

```text
A-101 Rev-01
A-101 Rev-02
A-101 Rev-03
```

Each revision gets separate geometry.

Then a difference engine compares:

```text
added entities
removed entities
modified geometry
changed labels
changed quantities
```

Example output:

```text
Conference Room flooring
Rev-02: 41.72 sqm
Rev-03: 46.11 sqm
Delta: +4.39 sqm
```

---

# 39. Geometry Difference Engine

A simple comparison cannot rely only on entity IDs because export may recreate IDs.

Use spatial matching.

Potential logic:

```text
same type
+ proximity
+ shape similarity
+ dimension similarity
+ semantic label
```

Output classifications:

```text
UNCHANGED
MODIFIED
ADDED
REMOVED
UNCERTAIN_MATCH
```

---

# 40. Data Model — Key Tables

## projects

```text
id
name
created_at
```

## drawings

```text
id
project_id
drawing_number
revision
discipline
floor
source_file
source_type
status
```

## entities

```text
id
drawing_id
entity_type
geometry
layer
raw_metadata
confidence
```

## rooms

```text
id
drawing_id
name
geometry
area
perimeter
confidence
```

## walls

```text
id
drawing_id
geometry
length
thickness
height
type
confidence
```

## openings

```text
id
wall_id
opening_type
width
height
confidence
```

## finishes

```text
id
host_type
host_id
finish_code
geometry
confidence
```

## quantities

```text
id
drawing_id
rule_id
item_code
quantity
unit
formula
confidence
status
```

## exceptions

```text
id
drawing_id
entity_id
type
message
status
resolution
```

---

# 41. Units Engine

Never store only formatted quantities.

Store SI-normalized base values.

Example:

```text
length → mm
area → mm² internally or sqm canonical
volume → mm³ or m³ canonical
count → integer
```

UI can display:

```text
sqm
sqft
rm
rft
nos
cum
```

Conversion should be deterministic.

---

# 42. Rounding Engine

QS rounding should be separated from raw measurement.

Store:

```text
raw_quantity = 41.718394
display_quantity = 41.72
commercial_quantity = optional
```

Never lose raw precision.

---

# 43. Measurement Evidence

For each result, generate a visual overlay.

Example:

```text
Room polygon highlighted
Door deductions marked
Measured wall shown
Label linked
```

Potential output:

```text
measurement_overlay.png
```

This makes review dramatically easier.

---

# 44. PDF Measurement Sheet Output

Future output can include:

```text
Item
Room
Drawing
Formula
Quantity
Unit
Reference
Assumption
```

Example:

```text
Gypsum Partition
Meeting Room 03
A-104 Rev-02
12.840 × 2.700 - openings
31.833
sqm
W-104
Height assumed from general note GN-02
```

---

# 45. API Design

Standalone engine should expose APIs.

## Upload

```http
POST /v1/drawings
```

## Start processing

```http
POST /v1/drawings/{id}/process
```

## Job status

```http
GET /v1/jobs/{id}
```

## Geometry

```http
GET /v1/drawings/{id}/entities
```

## Rooms

```http
GET /v1/drawings/{id}/rooms
```

## Quantities

```http
GET /v1/drawings/{id}/quantities
```

## Exceptions

```http
GET /v1/drawings/{id}/exceptions
```

## Resolve exception

```http
POST /v1/exceptions/{id}/resolve
```

## Verify quantity

```http
POST /v1/quantities/{id}/verify
```

## Export

```http
GET /v1/drawings/{id}/export
```

This lets Construct-O-Genie connect later without changing the engine core.

---

# 46. Job Pipeline

Do not make one giant `process_file()` function.

Use stages:

```text
INGESTED
 ↓
CLASSIFIED
 ↓
PARSED
 ↓
NORMALIZED
 ↓
OCR_COMPLETE
 ↓
GEOMETRY_COMPLETE
 ↓
SEMANTICS_COMPLETE
 ↓
QS_COMPLETE
 ↓
REVIEW_REQUIRED / VERIFIED
```

Each stage should be rerunnable.

---

# 47. Idempotency

If processing crashes after OCR, do not restart everything.

Save stage outputs.

Example:

```text
stage_01_metadata.json
stage_02_raw_geometry.json
stage_03_ocr.json
stage_04_semantic_graph.json
stage_05_quantities.json
```

Production version stores data primarily in DB/object storage, but stage files help debugging.

---

# 48. Suggested Repository Structure

```text
qs-engine/
│
├── apps/
│   ├── api/
│   └── worker/
│
├── core/
│   ├── geometry/
│   ├── units/
│   ├── confidence/
│   └── exceptions/
│
├── parsers/
│   ├── dxf/
│   ├── pdf_vector/
│   └── pdf_raster/
│
├── vision/
│   ├── preprocessing/
│   ├── ocr/
│   ├── detection/
│   └── hatch/
│
├── semantics/
│   ├── rooms/
│   ├── walls/
│   ├── openings/
│   ├── finishes/
│   └── symbols/
│
├── qs/
│   ├── rule_engine/
│   ├── formulas/
│   └── profiles/
│
├── revision/
│
├── review/
│
├── exports/
│
├── models/
│
├── tests/
│   ├── unit/
│   ├── fixtures/
│   ├── golden_drawings/
│   └── regression/
│
├── configs/
│
├── THIRD_PARTY_LICENSES.md
│
└── README.md
```

---

# 49. Golden Drawing Test System

This is essential.

Create 20–50 manually measured reference drawings.

For each drawing store:

```text
known room areas
known wall lengths
known door counts
known finish quantities
known partition quantities
```

Every new engine build runs against them.

Example:

```text
Expected Flooring = 187.42 sqm
Engine = 187.39 sqm
Error = -0.016%
PASS
```

---

# 50. Accuracy Metrics

Do not say only “accuracy 90%.”

Measure separately.

## Geometry Accuracy

```text
absolute length error
area percentage error
boundary IoU
```

## Object Detection

```text
precision
recall
mAP if relevant
```

## OCR

```text
character error rate
dimension recognition accuracy
```

## Quantity Accuracy

```text
abs(engine_qty - verified_qty) / verified_qty
```

## Review Burden

Very important commercial metric:

```text
manual corrections per drawing
review minutes per drawing
```

---

# 51. Practical MVP Accuracy Targets

For standardized DXF:

### Room Area

Target:

```text
>99% mathematical accuracy once correct boundary is known
```

### Block Count

```text
~100% if block naming is standardized
```

### Door Detection

```text
very high with blocks/layers
```

### Wall / Partition

High when layers and geometry are standardized.

### Raster Drawing

Significantly lower and drawing-dependent.

Hence product claims should be based on **supported drawing classes**, not generic “all drawings.”

---

# 52. Drawing Quality Score

Before processing, calculate a drawing quality score.

Signals:

```text
vector data exists?
text is native?
scale found?
layers available?
blocks available?
room boundaries closed?
OCR clarity?
```

Example:

```text
Drawing Quality: 92/100
Expected Automation Level: High
```

or

```text
Drawing Quality: 44/100
Expected Automation Level: Low
Manual calibration required
```

This prevents unrealistic expectations.

---

# 53. AI Fallback Strategy

AI should be called in layers.

```text
1. exact rules
2. layer/block mapping
3. geometry heuristic
4. OCR context
5. detector
6. local LLM/VLM
7. human
```

This hierarchy minimizes AI usage and maximizes reliability.

---

# 54. Why LLM Should Be Last, Not First

Example:

Layer:

```text
A-DOOR
```

Block:

```text
D1_900
```

Geometry:

```text
door swing
```

No reason to ask an LLM.

LLM/VLM is useful when:

```text
Layer = 0
Block = unnamed
Symbol unusual
Annotation ambiguous
```

---

# 55. Local LLM Task Contract

Every LLM call should have constrained output.

Bad:

```text
"What is this?"
```

Good:

```json
{
  "task": "classify_annotation",
  "allowed_labels": [
    "gypsum_partition",
    "glass_partition",
    "wall_finish",
    "unknown"
  ]
}
```

Response must validate against schema.

If output invalid:

```text
UNKNOWN
```

---

# 56. Never Let AI Invent Missing Dimensions

If wall height does not exist:

Bad:

```text
AI assumes 2700 mm silently
```

Correct:

```text
MISSING_HEIGHT
Suggested project default = 2700 mm
Requires approval
```

After user approval:

```text
assumption_source = manual
height = 2700
```

---

# 57. Project Assumption Registry

Store approved defaults.

Example:

```yaml
ceiling_height_mm: 2700
full_height_partition_mm: 3000
door_height_mm: 2100
skirting_height_mm: 100
```

But each must record:

```text
source
approved_by
date
scope
```

---

# 58. Rule Explainability

Every result needs plain-language explanation.

Example:

```text
Paint quantity is 87.32 sqm because:
- wall length = 18.40 m
- wall height = 2.70 m
- gross = 49.68 sqm per face
- 2 faces included
- door/window deductions = 12.04 sqm
```

This should be generated by deterministic templates, not necessarily LLM.

---

# 59. Initial Supported QS Categories

Do not begin with every trade.

Recommended MVP:

## Architecture

- room area;
- wall length;
- partition area;
- door count;
- window count.

## Finishes

- flooring;
- skirting;
- ceiling;
- wall finish.

## Basic Counts

- furniture blocks;
- electrical symbols where standardized.

---

# 60. Categories to Defer

Later:

- complex joinery;
- detailed MEP;
- duct quantities;
- pipe routing;
- cable lengths;
- reinforcement;
- formwork;
- structural steel;
- bespoke millwork;
- complex façade.

---

# 61. MVP Version 0 — Geometry Proof

Goal:

prove the measurement engine before AI.

Input:

```text
DXF only
```

Features:

- parse drawing;
- render geometry;
- select layer;
- line length;
- polyline area;
- closed room polygon;
- block count;
- unit conversion;
- overlay.

Success criteria:

> A QS can upload a clean DXF and verify that measured geometry matches CAD.

No AI required.

---

# 62. MVP Version 1 — Assisted QS

Add:

- layer mapping;
- room detection;
- native text;
- door/window block detection;
- QS rules;
- exception system;
- review UI.

Output:

- room-wise quantity sheet.

This already has commercial value if drawings are standardized.

---

# 63. MVP Version 2 — Local AI

Add:

- OCR;
- object detection;
- unknown symbol classification;
- finish recognition;
- confidence engine.

Now PDF support becomes stronger.

---

# 64. MVP Version 3 — Raster Intelligence

Add:

- raster line reconstruction;
- tiled object detection;
- advanced OCR;
- boundary repair suggestions;
- manual calibration.

---

# 65. MVP Version 4 — Drawing Set Intelligence

Interpret several drawings together.

Example:

```text
Layout
+
Flooring plan
+
RCP
+
Elevations
```

Resolve entities across sheets.

Example:

Conference Room exists across:

```text
A-101
A-121
A-131
```

Semantic graph links them.

---

# 66. Cross-Drawing Entity Resolution

Need a stable internal room identity.

Example:

```text
room_uuid = R-PROJECT-021
```

Linked source representations:

```text
A-101 → Conference Room
A-121 → Conf. Room
A-131 → CR-02
```

Matching signals:

- location;
- room number;
- text similarity;
- adjacency;
- dimensions.

---

# 67. Version 5 — Specification Intelligence

Optional input:

```text
material schedule
finish schedule
specification
legend
```

Engine maps geometry to richer item definitions.

Example:

```text
F-02
→ 600x1200 vitrified tile
→ approved make xyz
→ measured in sqm
```

Still quantity engine—not costing engine.

---

# 68. Deployment Options

## Option A — Desktop / Local Workstation

Pros:

- drawings never leave office;
- zero external inference charges;
- easier privacy;
- no cloud GPU.

Cons:

- machine-dependent performance;
- installation/update complexity.

---

## Option B — Company's Own Local Server

Best long-term option for internal organization.

```text
browser UI
 ↓
LAN/API
 ↓
local server
```

Advantages:

- centralized;
- models downloaded once;
- no external drawing upload;
- multi-user.

---

## Option C — Cloud Server

Still no per-token API, but compute cost applies.

Useful when engine becomes SaaS.

---

# 69. Recommended Initial Deployment

For prototype:

```text
Windows/Linux development workstation
+
Dockerized backend
+
browser review UI
```

Keep core engine platform-independent.

---

# 70. Security

Drawings can contain confidential layouts.

Recommended:

- process locally where possible;
- no automatic external AI calls;
- encrypt stored project files;
- hash files;
- role-based access later;
- logs must not expose drawing contents unnecessarily.

A major product advantage can be:

> **AI processing stays on your infrastructure.**

---

# 71. Performance Strategy

A drawing should not rerun all models for every query.

Cache:

```text
OCR output
geometry
detector results
semantic graph
quantities
```

Only recompute affected downstream stages.

Example:

User changes wall height.

Do not rerun OCR.

Only:

```text
QS rules → quantities
```

---

# 72. Spatial Indexing

Large drawings can contain thousands of entities.

Use spatial indexing.

Examples:

- R-tree;
- STRtree;
- database spatial index.

This speeds up:

```text
nearest text
point-in-polygon
nearby wall
opening association
entity overlap
```

---

# 73. Geometry Tolerances

CAD geometry is rarely mathematically perfect.

Need tolerance profile:

```text
endpoint_snap_mm = 3
parallel_angle_tolerance_deg = 1
room_gap_close_mm = 20
duplicate_distance_mm = 2
```

These values must be configurable.

---

# 74. Topology Repair

Common issue:

wall endpoints do not exactly touch.

Engine can suggest:

```text
Gap = 4.2 mm
Likely closure
```

Auto-fix only below safe tolerance.

Large gaps require review.

---

# 75. Duplicate Detection

PDF exports may generate overlapping lines.

If not removed:

- wall lengths can double;
- hatch geometry can duplicate;
- counts can inflate.

Need geometric duplicate detection:

```text
same endpoints
same orientation
same approximate geometry
```

---

# 76. Text-to-Geometry Association

Example room label:

```text
MEETING ROOM
```

Assign by:

1. text centroid inside room polygon;
2. nearest valid room;
3. semantic alignment;
4. confidence.

If two candidate rooms:

```text
AMBIGUOUS_LABEL
```

---

# 77. Door-to-Wall Association

Door must know host wall.

Logic:

```text
door centre
→ nearest wall segment
→ orientation compatibility
→ wall gap
→ attach
```

This enables proper deductions.

---

# 78. Finish-to-Room Association

If hatch lies inside room:

```text
intersection_area / hatch_area
```

If > threshold, assign.

If hatch spans rooms:

- split by room boundaries;
- create room-specific measurements.

---

# 79. Height Resolution Strategy

Sources ordered:

```text
explicit local note
> elevation annotation
> room/partition schedule
> project default
> manual
```

Never blindly use one global height.

---

# 80. Quantity Status Model

Every quantity:

```text
DRAFT
AUTO_MEASURED
REVIEW_REQUIRED
VERIFIED
REJECTED
SUPERSEDED
```

Only `VERIFIED` quantity should be treated as final exported QS quantity if strict mode is enabled.

---

# 81. Manual Override Policy

Never overwrite machine result destructively.

Store:

```text
machine_quantity
manual_quantity
final_quantity
reason
```

Example:

```text
machine = 41.72
manual = 42.05
reason = niche included manually
```

This data becomes valuable training feedback.

---

# 82. Feedback Learning Loop

Every correction becomes training/evaluation data.

Example:

```text
AI classification:
chair

Reviewer:
workstation

Store correction.
```

Later retrain custom detector/classifier.

Thus the engine becomes better using its own reviewed drawings without paid API usage.

---

# 83. Dataset Governance

Do not automatically train on every client drawing without policy.

Need flags:

```text
may_use_for_training = yes/no
anonymized = yes/no
```

Separate:

- production project data;
- approved training dataset.

---

# 84. Model Registry

Maintain:

```text
model_name
version
classes
training_dataset_version
metrics
license
deployment_date
checksum
```

Example:

```text
symbol-detector-v4.onnx
```

If quantity behavior changes, you can trace model version.

---

# 85. Rule Registry

Same for rules:

```text
QS-FLOOR-001-v1
QS-SKIRT-001-v3
QS-WALL-004-v2
```

Never silently edit a rule already used in a verified project.

New rule = new version.

---

# 86. Deterministic Reproducibility

Given:

```text
same file
same model version
same rule version
same assumptions
```

the engine should produce the same result.

This is a major design requirement.

---

# 87. Logging

Log stages, not sensitive content.

Example:

```text
job_id
drawing_id
stage
duration
result_count
warning_count
model_version
```

Avoid dumping full OCR/drawing text into generic logs.

---

# 88. Error Handling

Possible errors:

```text
corrupt file
unsupported DXF version
PDF render failure
OCR failure
out-of-memory
geometry invalid
model unavailable
```

Each needs user-friendly status.

Never return a fake zero quantity after processing failure.

---

# 89. Output Formats

MVP:

```text
JSON
CSV
Excel
```

Later:

```text
annotated PDF
measurement sheet
API payload
```

Example JSON:

```json
{
  "drawing": "A-101",
  "revision": "03",
  "quantities": [
    {
      "item": "flooring",
      "room": "Conference Room",
      "quantity": 41.72,
      "unit": "sqm",
      "confidence": 0.98
    }
  ]
}
```

---

# 90. What “AI-Free Cost” Architecture Looks Like

```text
                     INTERNET
                        X
                        X
                        X

Drawing
  ↓
Local Parser
  ↓
Local OpenCV
  ↓
Local OCR
  ↓
Local Detector
  ↓
Local Optional LLM
  ↓
Local Geometry/QS Engine
  ↓
Result
```

Normal operations require no external AI provider.

---

# 91. Optional Paid Fallback — Future Only

If desired later:

```text
confidence < threshold
AND
user allows external AI
→ optional paid API
```

But engine must work without this.

Default:

```text
external_ai_enabled = false
```

---

# 92. Practicality Assessment

## DXF + Standard Layers

**Practicality: 9/10**

Very strong candidate.

---

## Vector PDF

**Practicality: 8/10**

Strong, but reconstructing CAD semantics adds work.

---

## Clean Raster PDF

**Practicality: 6–7/10**

Useful with human review.

---

## Poor Scan / Hand Markup

**Practicality: 3–5/10**

Do not make strong automatic claims.

---

# 93. Most Important Product Insight

The winning system is not:

> “AI replaces QS.”

It is:

> **“A QS reviews machine-generated measurements instead of manually tracing every drawing.”**

That converts hours of repetitive takeoff into exception review.

---

# 94. What Will Actually Take Development Time

Not area calculation.

Hard work:

1. geometry normalization;
2. drawing inconsistency;
3. room topology;
4. symbol datasets;
5. semantic linking;
6. review UX;
7. revision comparison;
8. rule configuration;
9. auditability;
10. regression testing.

This is where engineering effort should go.

---

# 95. Recommended Build Order

```text
STEP 1
DXF parser

STEP 2
geometry viewer

STEP 3
measure line / polygon / block

STEP 4
room boundary engine

STEP 5
layer/block mapping

STEP 6
QS rule engine

STEP 7
measurement evidence + review

STEP 8
vector PDF

STEP 9
OCR

STEP 10
local symbol detection

STEP 11
raster reconstruction

STEP 12
optional local LLM/VLM

STEP 13
revision intelligence
```

Do not start with the LLM.

---

# 96. Phase 1 Definition

### Supported

- DXF;
- room polygons;
- walls;
- doors from known blocks/layers;
- native text;
- flooring;
- perimeter;
- skirting;
- partition;
- ceiling where geometry exists;
- counts.

### Not Supported

- arbitrary scans;
- unknown symbols;
- complex elevations;
- MEP takeoff;
- automatic material specification inference.

Phase 1 should prove the business value.

---

# 97. Phase 1 Acceptance Criteria

A Phase 1 release passes only if:

1. DXF renders correctly.
2. Units are calibrated.
3. User can click an entity and see its source.
4. Room areas match reference CAD measurements.
5. Block counts match manually verified counts.
6. Quantities show formula.
7. Quantity source can be highlighted.
8. Reviewer can override.
9. All overrides are auditable.
10. Export contains drawing/revision reference.

---

# 98. Phase 2 Acceptance Criteria

Vector PDF:

1. scale calibration works;
2. native PDF text extracted;
3. major wall/room geometry reconstructed;
4. OCR handles raster text fallback;
5. door/window detection reaches agreed benchmark;
6. low-confidence cases are surfaced;
7. engine never silently guesses missing scale.

---

# 99. Phase 3 Acceptance Criteria

Raster:

1. deskew stable;
2. OCR benchmark achieved;
3. line reconstruction benchmark achieved;
4. tiled detector stable;
5. processing time acceptable;
6. manual calibration available;
7. review burden measured.

---

# 100. Suggested Prototype Screens

## Screen 1 — Upload

```text
Upload Drawing
Drawing No.
Revision
Floor
Discipline
```

## Screen 2 — Processing

```text
Parsing
Geometry
OCR
Recognition
QS Rules
```

## Screen 3 — Drawing Review

Left:

```text
drawing canvas
```

Right:

```text
rooms
walls
openings
finishes
exceptions
```

## Screen 4 — Quantities

```text
Item | Location | Qty | Unit | Confidence | Status
```

## Screen 5 — Evidence

```text
formula + highlighted geometry
```

---

# 101. Suggested Technology Boundary

The geometry domain should not import web/UI logic.

Example:

```text
core.geometry
```

must be independently testable.

Similarly:

```text
qs.rule_engine
```

must work on semantic objects without knowing PDF or DXF implementation details.

This prevents technical debt.

---

# 102. Testing Strategy

## Unit Tests

```text
distance
area
intersection
offset
unit conversion
rounding
```

## Parser Tests

known DXF fixtures.

## Semantic Tests

```text
room + label
door + wall
finish + room
```

## QS Rule Tests

exact formula inputs/outputs.

## Golden Drawing Regression

real-world drawings.

---

# 103. Example Complete Processing Trace

Input:

```text
A-101_GroundFloor_Rev03.dxf
```

### Parse

```text
14,842 entities
```

### Classify

```text
Walls: 684
Door blocks: 42
Text: 389
Hatches: 114
Other: ...
```

### Rooms

```text
37 candidate closed spaces
35 auto-accepted
2 review required
```

### Room Label

```text
Conference Room
confidence 0.99
```

### Geometry

```text
area = 41.718 sqm
perimeter = 26.122 m
```

### Door

```text
D1 width = 0.900 m
```

### QS rules

Floor:

```text
41.718 sqm
```

Skirting:

```text
26.122 - 0.900 = 25.222 rm
```

### Output

```text
Flooring: 41.72 sqm
Skirting: 25.22 rm
```

### Evidence

Room boundary and door opening highlighted.

No LLM required.

---

# 104. Example AI-Assisted Trace

Input:

Vector/raster PDF contains unfamiliar symbol.

Detector:

```text
door probability = 0.72
window probability = 0.18
unknown = 0.10
```

Nearby OCR:

```text
D3
900 x 2100
```

Geometry:

```text
wall opening = ~900 mm
swing-like arc present
```

Fusion engine:

```text
door confidence = 0.94
```

Quantity engine counts:

```text
Door D3 = 1 No.
```

The AI did not calculate the count.

It helped establish the semantic identity.

---

# 105. Confidence Fusion

Possible conceptual formula:

```text
confidence =
w1 × geometry_signal
+ w2 × layer_signal
+ w3 × block_signal
+ w4 × OCR_signal
+ w5 × detector_signal
```

Weights vary by entity.

For DXF doors:

block/layer may dominate.

For raster doors:

detector + geometry may dominate.

---

# 106. No Single Model Dependency

Architecture should allow:

```text
OCR Provider Interface
Detector Provider Interface
LLM Provider Interface
```

Example:

```python
class OCREngine:
    def recognize(self, image):
        ...
```

Then implementation can change without changing QS logic.

---

# 107. Local AI Model Download Strategy

Model files are stored locally:

```text
/models/ocr/
/models/detector/
/models/optional_llm/
```

Use checksums.

Do not automatically update production models.

Model upgrade must pass golden-drawing tests.

---

# 108. AI Cost Control

If all core models run locally:

```text
per-drawing token cost = ₹0
per-drawing paid AI API = ₹0
```

Operating cost becomes mainly compute.

For low volume, an existing workstation can be enough for development/prototype.

For large SaaS usage, compute is not free—local models merely change the cost structure from API fees to infrastructure.

---

# 109. Commercial Risk to Avoid

Do not advertise:

```text
"100% accurate AI QS"
```

Better:

```text
"Automated drawing takeoff with traceable measurements and human verification."
```

This is both more credible and easier to engineer.

---

# 110. Strongest Initial Use Case

The best first customer/use case:

> Interior contractor with repeatable CAD standards and recurring flooring, partitions, ceiling, doors and finish takeoffs.

Why?

Because standardization dramatically improves automation.

---

# 111. Standardization Profiles

The engine can learn/configure organization-specific profiles.

Example:

```text
Profile: Luxeworx Standard
```

Contains:

```text
layer mappings
block mappings
units
height defaults
finish code pattern
door tag pattern
QS rules
confidence thresholds
```

Then repeat projects become increasingly automated.

---

# 112. The Actual “Jugaad”

The cheap architecture is not “use a free ChatGPT replacement.”

The actual engineering shortcut is:

```text
Use CAD/vector structure wherever available
→ use rules
→ use geometry
→ use OCR
→ use small local detector
→ use LLM only for rare ambiguity
```

This reduces:

- compute;
- hallucination;
- training requirement;
- API cost;
- latency.

---

# 113. When AI Is Completely Unnecessary

Example DXF:

```text
Layer = FLOOR_F02
Closed polyline area = 62.4 sqm
```

Quantity:

```text
F02 = 62.4 sqm
```

AI adds no value.

---

# 114. When AI Is Valuable

Example PDF:

```text
Unknown hatch
Nearby note:
"12MM WOODEN LAMINATE FLOORING"
```

AI/OCR can map the annotation to finish category.

Geometry still calculates area.

---

# 115. When Human Is Required

Example:

```text
Drawing shows wall.
No height.
No elevation.
No general note.
```

The correct engine behavior:

```text
Quantity incomplete.
Height required.
```

Not:

```text
Assume 2700 automatically.
```

---

# 116. Long-Term Moat

The strongest moat will not be the base AI model.

It will be:

1. interior-specific drawing normalization;
2. proprietary reviewed symbol dataset;
3. QS measurement rules;
4. drawing revision intelligence;
5. exception handling;
6. organization-specific profiles;
7. audit history;
8. review feedback dataset.

Generic LLM companies can provide models, but they do not automatically provide this domain system.

---

# 117. Final Recommended Architecture

```text
                    ┌──────────────────┐
                    │   Drawing File   │
                    └────────┬─────────┘
                             ↓
                ┌──────────────────────────┐
                │ Input / Scale / Revision │
                └────────────┬─────────────┘
                             ↓
           ┌──────────────────────────────────┐
           │ Vector Parser / Raster Processor │
           └───────────────┬──────────────────┘
                           ↓
                ┌─────────────────────┐
                │ Geometry Repository │
                └──────────┬──────────┘
                           ↓
        ┌────────────────────────────────────────┐
        │ Semantic Intelligence                  │
        │ Rules + OCR + Detector + Optional LLM │
        └──────────────────┬─────────────────────┘
                           ↓
                ┌─────────────────────┐
                │ Drawing Graph       │
                └──────────┬──────────┘
                           ↓
                ┌─────────────────────┐
                │ QS Rule Engine      │
                └──────────┬──────────┘
                           ↓
                ┌─────────────────────┐
                │ Quantity Calculator │
                └──────────┬──────────┘
                           ↓
             ┌────────────────────────────┐
             │ Confidence / Exceptions    │
             └─────────────┬──────────────┘
                           ↓
                   ┌──────────────┐
                   │ QS Review UI │
                   └──────┬───────┘
                          ↓
                  ┌───────────────┐
                  │ Verified Qty  │
                  └──────┬────────┘
                         ↓
                JSON / Excel / API
```

---

# 118. Final Recommendation

Build this as a **deterministic QS geometry engine with local AI assistance**.

Do not build it as an LLM application.

Initial priority:

```text
DXF
→ geometry
→ rooms
→ walls
→ openings
→ flooring / ceiling / partition / skirting
→ audit/review
```

Then add:

```text
vector PDF
→ OCR
→ symbol detection
→ raster PDF
→ optional local LLM
```

The engine is commercially practical if the first promise is narrow:

> **“Upload a standardized interior drawing and obtain traceable machine-generated takeoff quantities that a QS can quickly verify.”**

That is achievable.

The eventual goal can be broader, but reliability must grow trade-by-trade and drawing-type-by-drawing-type.

---

# 119. Non-Negotiable Design Rules

1. **AI interprets; code calculates.**
2. **No quantity without source geometry.**
3. **No silent assumptions.**
4. **Every AI result has confidence.**
5. **Every low-confidence result can enter review.**
6. **Every manual correction is preserved.**
7. **Drawing revisions never overwrite history.**
8. **Model/rule versions are traceable.**
9. **Core engine does not require a paid AI API.**
10. **Accuracy claims are scoped by supported drawing type.**

---

# 120. One-Line Product Definition

> **A local-first QS takeoff engine that converts construction/interior drawings into auditable, reviewable quantities using deterministic geometry and selective open-source AI.**

