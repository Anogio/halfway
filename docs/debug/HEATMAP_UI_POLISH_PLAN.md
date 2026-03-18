# Heatmap UI Polish Plan

## Goal

Improve overall readability and polish without changing the current frontend-raster architecture.

The two main themes are:

1. Make the vector basemap more helpful as an orientation tool in any city.
2. Make the left dock feel more integrated and less visually invasive, especially in empty and single-point states.
3. Preserve a strong mobile experience while making the desktop layout lighter and more map-first.

## Priorities

### 1. General Vector Basemap Tuning

Keep this city-agnostic.

Targets:

- stronger rivers, canals, and water hierarchy
- clearer parks and green areas
- better major-road hierarchy
- clearer rail corridors and station context
- more useful place/admin labels at medium zooms
- preserve heatmap-under-label layering
- preserve locale-aware label selection

This should improve orientation across all supported cities, not just Paris.

### 2. Dock Integration Pass

The dock currently feels too much like a solid white sheet sitting on top of the map.

Targets:

- reduce container visual weight
- keep strong readability while making the dock blend into the overall UI
- reduce empty-state dominance
- tighten card spacing and vertical rhythm
- make multi-point state the main reference state

Concrete ideas:

- softer panel background and border
- slightly stronger translucency / blur separation
- reduced padding in origin cards
- more compact path-detail typography and spacing
- more intentional scrolling behavior
- state-aware sizing so empty and single-point states do not occupy a full desktop column
- keep the mobile dock compact enough to preserve map context while staying easy to scroll and tap

Potential follow-up:

- default to one expanded card at a time when many origins are present
- keep other cards summarized until selected

### 3. Heatmap Alpha by Time

Reduce visual wash in outer slow-access zones.

Targets:

- vivid center
- lighter outskirts
- retain clear travel-time gradient

### 4. Heatmap Alpha by Zoom

Targets:

- zoomed out: calmer, more map readability
- zoomed in: slightly stronger heatmap and local detail

### 5. Minor Overlay Polish

Targets:

- path contrast above heatmap
- marker prominence
- popup hierarchy

### 6. Mobile Integrity Pass

Targets:

- preserve comfortable touch targets
- keep the bottom dock readable without crowding the map
- prevent search and dock layers from visually colliding on small screens
- verify that compact multi-point cards still scan well on phones

## Validation States

Design decisions should be checked in:

- empty state
- one-point state
- multi-point state
- desktop layout
- mobile layout
- French locale
- English locale
- zoomed-out overview
- zoomed-in local view

The multi-point state should be treated as the main evaluation state for the dock.

## Implementation Order

1. Dock integration pass
2. General vector basemap tuning
3. Heatmap alpha by time
4. Heatmap alpha by zoom
5. Mobile integrity pass
6. Minor overlay polish
7. Final headed-browser review
