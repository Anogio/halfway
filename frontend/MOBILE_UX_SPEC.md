# Mobile UX Spec - Map-First Interaction

## Scope
Define mobile interaction for map exploration and origin changes without relying on hover.

This spec is for touch devices first. Desktop behavior can remain richer, but must not conflict.

## Product Intent
- Tapping the map should inspect travel time, not immediately mutate origin.
- Origin change must be explicit and intentional.
- Side panel is treated as debug tooling, not the final primary UX.

## Core Interaction Model
### Primary rule
- `Tap = inspect`
- `Set as origin` button = mutate origin

### User flow
1. User taps map.
2. App finds the tapped isochrone band (or nearest valid band).
3. App opens an anchored info tooltip/card.
4. Card shows travel-time info and an action button:
   - `Set as origin`
5. If user presses `Set as origin`:
   - Origin marker moves to tapped location.
   - Inputs update.
   - Recompute is triggered (or queued if manual mode is chosen later).

## UI Components
### A. Tap info card (map anchored)
- Appears near tap point.
- Content:
  - `Travel time: X-Y min`
  - Optional coordinate line (`lat, lon`, compact)
  - CTA button: `Set as origin`
  - Close affordance (`x` or dismiss on outside tap)

### B. Origin marker
- Remains visible at current origin.
- Does not move on inspect tap.
- Moves only after explicit confirm action.

### C. Debug side panel (non-final)
- Can remain present for now.
- Must not be required for primary touch flow.

## Interaction States
### Idle
- No info card open.
- Origin marker visible.

### Inspecting
- Info card open for last tap.
- Card updates if user taps another point.
- Previous card replaced by latest.

### Confirming origin change
- User taps `Set as origin`.
- UI shows transient loading state (`Updating…`).

### Updated
- Origin updated.
- Heatmap/isochrones refreshed.
- Success toast optional.

## Touch and Gesture Rules
- Single tap on polygon: open/update info card.
- Single tap outside card/polygon: close card.
- Map pan/zoom gestures should not open card accidentally.
- If tap lands on empty area:
  - Show `No travel-time data here` in card.
  - Keep `Set as origin` enabled so users can launch a new computation from any point.

## Edge Cases
- Very dense polygon overlaps:
  - Prefer topmost visible feature at tap point.
- Tap while request in flight:
  - Card can still open; CTA disabled until current request settles.
- Tap near map edge:
  - Card auto-positions to stay within viewport.
- No data response:
  - Card shows friendly fallback; no origin mutation.

## Accessibility
- Card must be keyboard-focusable for hybrid devices.
- Button label explicit: `Set as origin`.
- Minimum touch target 44x44 px.
- Color is not sole carrier of meaning; card text provides time range.

## Suggested Implementation Plan
1. Add mobile mode guard (`pointer: coarse`) for touch-first interaction.
2. Replace map-click direct mutation with inspect state.
3. Implement anchored card with CTA and dismiss behavior.
4. Wire `Set as origin` to existing origin update + recompute.
5. Keep desktop behavior unchanged initially; then unify if desired.
6. Add Playwright mobile viewport tests for tap flows.

## Acceptance Criteria
- Tapping map does not change origin by itself.
- User can inspect travel-time band on tap.
- User can explicitly set new origin from the card.
- Recompute occurs after explicit confirm.
- Works on small viewport without relying on side panel.

## Non-goals (for this phase)
- Final visual redesign of controls and layout.
- Full bottom-sheet navigation architecture.
- Multi-step onboarding/tutorial.
