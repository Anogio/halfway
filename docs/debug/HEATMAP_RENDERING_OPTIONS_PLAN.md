# Heatmap Rendering Options Plan

## Goal

Get to a heatmap that feels close to the original visual quality:

- no white seams or holes between bands
- smoother, less grid-like boundaries
- strong, readable bucket colors
- readable basemap underneath
- acceptable backend and frontend performance

## Current Findings

### Baseline: current exact grid polygons

- Pros:
  - cheap to compute
  - stable polygons
  - simple frontend
- Cons:
  - visibly square cells
  - frontend-only smoothing creates seams

### Backend-only shared-boundary smoothing (option 1 attempt)

- Pros:
  - better than raw square cells
  - keeps polygon interaction model
- Cons:
  - still left visible holes in practice
  - noticeably slower than baseline
  - complex junctions stayed sharp by design

### First scalar-field backend prototype (early option 2 attempt)

- Approach tried:
  - refine the cell grid at `2x`
  - interpolate locally
  - polygonize fine cells again
- Result:
  - removed holes
  - improved shapes somewhat
  - still looked raster-derived
  - backend cost increased too much

Measured `/multi_isochrones` timing on the same Paris payload, 20 in-process samples:

- Baseline:
  - p50 `139.14 ms`
  - p95 `296.12 ms`
  - mean `296.67 ms`
- First backend scalar-field prototype:
  - p50 `635.57 ms`
  - p95 `665.95 ms`
  - mean `632.79 ms`

Conclusion:

- a pure backend fine-cell polygonization approach is probably not the right end state
- the two promising directions are:
  - frontend raster rendering
  - backend contour extraction from a smoothed scalar field

## Recommendation

Start with a frontend raster prototype built from exact per-cell times.

Reason:

- it is the fastest way to test whether a smoothed scalar-field rendering actually gives the desired visual feel
- it can shift most of the expensive visual processing to the client GPU
- it avoids committing immediately to a complex backend contour pipeline

Keep backend contour extraction as the stronger long-term fallback if we still need:

- true vector polygons
- exact bucket hover/click behavior
- deterministic geometry across clients

## Option A: Frontend Raster Rendering

## A.1 Objective

Render the heatmap as a smoothed raster field in the browser from exact per-cell travel times, not from pre-bucketed polygons.

The key idea is:

1. backend sends the exact scalar travel-time grid
2. frontend upsamples and smooths the field
3. frontend colors the smoothed field into time bands at render time
4. MapLibre displays the result as a raster overlay or custom WebGL layer

## A.2 Expected Benefits

- likely best visual quality for the least backend complexity
- likely better compute efficiency than backend contour generation
- easier to tune blur radius, opacity, and color treatment in the browser
- avoids polygon seam problems entirely

## A.3 Expected Tradeoffs

- output is no longer a true vector polygon layer
- hover/click is based on sampled scalar values, not polygon hit-testing
- cross-client rendering may vary slightly
- requires a custom rendering path in frontend

## A.4 Data Contract

Backend should expose a scalar grid payload of exact per-cell times, ideally without changing the existing production default path.

Suggested shape:

- `topology`
  - `min_lat`
  - `min_lon`
  - `lat_step`
  - `lon_step`
- `grid`
  - width / height or row/col bounds
  - flattened travel-time values
  - optional validity mask
- render metadata
  - `max_time_s`
  - optional default bucket size only for frontend labeling

Important:

- keep this behind an explicit request flag or alternate response mode
- do not make the default production path pay for debug/experimental raster data
- in raster mode, do not send heatmap polygons at all

## A.5 Rendering Pipeline

### Step 1. Build a scalar texture

- map each reachable grid cell to its travel-time value
- keep a separate validity mask for reachable/unreachable cells

### Step 2. Upsample on the client

- start with `4x` per coarse cell
- consider `8x` only if needed after a first visual pass

### Step 3. Smooth the field

- use a separable blur instead of a naive `15x15` box average
- first choice: Gaussian blur
- second choice: box blur if implementation is much simpler

Important masking rule:

- blur the value texture and the validity mask separately
- divide blurred-value by blurred-mask
- this avoids unreachable space washing out edges incorrectly

### Step 4. Map smoothed values to colors

- keep the original bucket color scheme
- start with discrete bucket color bands derived from the smoothed scalar values
- keep opacity tuned so the map remains readable

### Step 5. Render in MapLibre

Prefer one of these:

1. custom WebGL layer
2. raster/image source fed from an offscreen canvas

Do not start with vector tiles for this path.

Reason:

- vector tiles help deliver geometry efficiently once geometry exists
- they do not solve the smoothing or contour-generation problem
- this option is fundamentally raster-native

## A.6 Interaction Model

Phase 1:

- keep existing point/origin interactions
- use the raster only for visual rendering
- on click / hover, sample the smoothed scalar field at the cursor
- show exact or rounded travel time derived from the sampled value

Phase 2, if needed:

- optionally derive bucket labels from the sampled value for presentation only
- optionally add continuous-value tooltips if that feels better than bucket labels

Avoid reconstructing exact hover polygons in the raster path.

## A.7 Implementation Plan

1. Add a backend response mode for scalar grid payloads with exact per-cell times.
2. Keep current polygon response untouched for the default path.
3. Build a frontend experiment path that:
   - requests the scalar grid
   - uploads value + mask textures
   - renders a smoothed heatmap overlay
   - samples the smoothed field for inspect/click behavior
4. Tune:
   - upsample factor
   - blur radius
   - opacity
   - color mapping
5. Compare visuals side by side with the current polygon version.

## A.8 Performance Checks

Measure:

- backend response time before and after adding scalar-grid response mode
- client FPS while panning/zooming
- time-to-first-heatmap-render
- memory footprint for typical Paris view

Success target:

- backend median close to baseline polygon generation
- interactive map remains smooth on a typical laptop browser

## A.9 Done Criteria

- no visible holes
- visibly smoother heatmap than exact polygons
- colors feel at least as vivid as the original style
- streets remain readable
- no obvious frame drops in headed browser testing
- no heatmap polygons shipped in raster mode

## Option B: Backend Contour Extraction From Smoothed Scalar Field

## B.1 Objective

Generate proper polygon bands from a smoothed scalar field in the backend instead of smoothing already-polygonized buckets.

The key idea is:

1. compute the scalar travel-time grid
2. upsample it
3. smooth it
4. extract isobands / contours
5. send real polygons to the frontend

## B.2 Expected Benefits

- best long-term path for stable vector geometry
- preserves clean hover/click behavior on bucket bands
- frontend can stay simple
- likely best deterministic output across clients

## B.3 Expected Tradeoffs

- most complex implementation
- likely slower than the frontend raster path
- requires careful topology handling
- contour extraction needs stronger test coverage

## B.4 Backend Pipeline

### Step 1. Create a dense scalar raster

- start from the coarse cell travel-time grid
- upsample to `4x` first
- keep a validity mask

### Step 2. Smooth the scalar raster

- use a separable Gaussian blur or equivalent
- blur values and mask separately
- divide blurred-value by blurred-mask

### Step 3. Extract bucket bands

Use contour extraction rather than fine-cell re-polygonization.

Preferred approach:

- marching squares / isobands per bucket threshold range

Output:

- one or more polygons per bucket
- holes and disconnected islands preserved where meaningful

### Step 4. Simplify carefully

- apply light simplification only if needed
- do not reintroduce gaps between adjacent buckets

### Step 5. Send polygons to frontend

- frontend returns to one clean polygon fill layer
- keep the original color scheme

## B.5 Implementation Plan

1. Keep the current scalar-grid code path as input only.
2. Replace fine-cell polygonization with actual contour extraction.
3. Add tests for:
   - no seam gaps between adjacent bands
   - no self-intersections
   - disconnected islands
   - stable outer boundaries
4. Compare latency and geometry complexity against baseline.
5. Validate in headed browser on Paris examples.

## B.6 Performance Checks

Measure:

- p50 / p95 / mean / max for `/multi_isochrones`
- geometry size:
  - feature count
  - polygon count
  - ring point counts
- browser render cost for returned polygons

Success target:

- materially smoother visuals than baseline
- lower latency than the first backend scalar-field prototype
- no visible holes

## B.7 Done Criteria

- no seams between buckets
- visibly smoother than current exact polygons
- original color scheme preserved
- stable hover/click behavior still works
- backend cost remains acceptable for production

## Option Comparison

### Frontend raster

- Best for:
  - fastest visual experimentation
  - highest chance of GPU-assisted efficiency
  - purely visual heatmap quality
- Weakest at:
  - exact polygon interaction semantics
  - deterministic geometry

### Backend contour extraction

- Best for:
  - real vector bucket polygons
  - stable interaction model
  - cleaner long-term architecture if bucket geometry is product-critical
- Weakest at:
  - implementation complexity
  - backend compute cost

## Proposed Execution Order

1. Build the frontend raster prototype first, using exact per-cell times only.
2. Judge visual quality in a headed browser.
3. If the raster look is clearly better and interaction needs are modest:
   - continue iterating on frontend rendering
4. If exact polygons remain important:
   - use the backend contour extraction path as phase 2

## Validation Checklist

After each spike, verify:

- Paris center view
- dense central areas with many bucket transitions
- edge-of-scope areas
- single-origin and multi-origin cases
- zoomed-in street readability
- zoomed-out overall shape quality

Record for each run:

- screenshot(s)
- backend latency
- visual verdict
- whether seams, blockiness, or washout remain

## Immediate Next Step

Start the frontend raster spike with a minimal experiment:

1. expose scalar grid data from the backend behind an explicit non-default mode
2. render it in the frontend as a smoothed raster overlay
3. tune only:
   - upsample factor
   - blur radius
   - opacity
4. evaluate the result before investing in backend contour extraction
