# Manual Sanity Checklist

Use this checklist after offline rebuilds or routing refactors.

## 1) Paris center quick check
- Open app at default view.
- Set origin near Hotel de Ville (`48.8566, 2.3522`).
- Confirm reachable area covers central arrondissements within `< 30 min`.
- Confirm distant suburbs are still visible but clipped to max color when above max-time.

## 2) Edge-of-scope check
- Pan near west edge (Boulogne) and east edge (Vincennes).
- Click several points and verify tooltip can always `Set as origin`.
- Compute multi-path from at least one edge point and inspect ride/transfer sequence for plausibility.

## 3) Unreachable/long-trip behavior
- Pick a far point near outer Ile-de-France edge.
- Confirm app still renders a value (max-color when above max-time), not a missing polygon gap.

## 4) Path display sanity
- Trigger a path with one metro/tram ride and one transfer.
- Confirm no `0 min` steps are shown.
- Confirm consecutive rides on same line are grouped into one step.
- Confirm transfer labels are compact (`Transfer (X min)`).

## 5) Mobile behavior
- In mobile viewport, tap map point to open inspect dock.
- Confirm map tap does not immediately move origin.
- Confirm dock action `Set as origin` works on first computation (cold start).

## 6) Backend spot-check
- Call `/heatmap` and `/multi_isochrones` for `48.8566,2.3522` with `city=paris`.
- Sanity-check a few point values against known Paris intuition:
  - Nearby center points should be low-minute values.
  - Peripheral points should generally be higher and often clipped at max-time.
