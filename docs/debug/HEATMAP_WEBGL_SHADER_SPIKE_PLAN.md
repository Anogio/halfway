# Heatmap WebGL Shader Spike Plan

## Goal

Try a local-only custom WebGL heatmap renderer that keeps the current scalar-grid API and interaction model, but stops baking the heatmap into a PNG image source.

The intent of the spike is:

- smoother pan/zoom behavior
- less CPU work during map movement
- a cleaner foundation for future visual tuning

## Scope

Keep unchanged:

- backend scalar-grid API
- hover and click hit-testing logic
- point/path overlays
- dock/search/onboarding UI

Replace:

- current `buildScalarRasterOverlay()` image-source path
- MapLibre image source/layer for the heatmap

With:

- a MapLibre custom WebGL layer
- a shader that colorizes a scalar-field texture directly in the map render loop

## Practical Architecture

### 1. Preprocess the scalar field once per update

Still do the heavy field preparation on the CPU when the scalar grid changes:

- dense upsampling
- component weighting / suppression
- gaussian blur on value and coverage

But stop converting that result into a canvas/PNG.

Instead, build a GPU-ready texture payload:

- red channel: normalized travel time
- alpha channel: normalized coverage / validity

This keeps the spike pragmatic while moving the actual rendering and compositing to WebGL.

### 2. Render via a MapLibre custom layer

Add a custom layer that:

- owns a shader program
- uploads the scalar texture once per update
- draws a quad over the scalar-grid bounds in mercator coordinates
- samples the scalar field in the fragment shader
- applies the color ramp and alpha curve in the shader

This should let the heatmap stay visually stable during pan/zoom without rebuilding image sources.

### 3. Keep overlays above the heatmap

Render order should remain:

- basemap
- WebGL heatmap layer
- paths
- origin markers
- labels/tooltips/popups

## Expected Benefits

- no raster rebuild on pan/zoom
- better responsiveness during navigation
- easier future experiments with alpha curves and color mapping

## Likely Limitations

- the blur is still CPU-side in this first spike
- WebGL layer lifecycle and context management add complexity
- some visual tuning may need another pass once the shader path is live

## Validation

1. Lint and typecheck
2. Local browser smoke test
3. Compare visually against the current raster version
4. Confirm that pan/zoom stays smooth and hover/click still work

## Success Criteria

The spike is good enough to keep locally if:

- the map no longer stutters from heatmap redraw work during pan/zoom
- the heatmap remains visually close to the current design
- interactions still behave correctly

If visuals regress too much, keep the spike as a technical branch for future work rather than treating it as production-ready.
