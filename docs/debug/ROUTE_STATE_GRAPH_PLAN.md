# Route-State Graph Plan

## Goal

Make boarding, waiting, ride continuation, and line transfers explicit in the
graph so Dijkstra prices them correctly without becoming route-aware itself.

## Core Principle

Keep Dijkstra unchanged. Encode transit state in graph nodes and edges.

## Target Node Model

Use a layered graph with:

1. Physical access nodes
2. Onboard route-stop nodes
3. Explicit transfer connectors between physical nodes

### 1. Physical access nodes

These represent places a rider can stand or walk to:

- GTFS stop/platform nodes where available
- Parent-station or hub-level connectors where needed

They are used for:

- origin seeding
- destination access
- transfer walking
- explicit and synthetic transfer topology

### 2. Onboard route-stop nodes

Create one onboard node per:

- `(physical_node_idx, route_id, direction_id)`

These represent:

- "you are boarded on this route at this stop"

### 3. Transfer connectors

These remain edges between physical nodes:

- `pathways.txt`
- `transfers.txt`
- synthetic hub transfers
- spatial fallback transfers

## Edge Model

### A. Access walking

Runtime and grid connect the user or cell to physical access nodes only.

### B. Boarding edges

- `physical_stop -> onboard(stop, route, direction)`

Cost:

- expected wait for the boarded route at that stop

### C. Ride continuation edges

- `onboard(stop_a, route, direction) -> onboard(stop_b, route, direction)`

Cost:

- in-vehicle runtime only

No repeated wait while staying on the same line.

### D. Alighting edges

- `onboard(stop, route, direction) -> physical_stop`

Cost:

- usually `0`

### E. Transfer movement edges

- `physical_stop_a -> physical_stop_b`

Cost:

- pathway / corridor / platform-change / fallback movement time

This is where transfer walking is paid.

## Important Topology Requirement

Route-state nodes alone are not enough.

If multiple lines share one coarse physical node, then:

- alight from line A to shared physical node
- board line B from shared physical node

only charges wait and not station movement.

So the physical layer must be sufficiently granular:

- separate platform or boarding-area nodes where a transfer movement exists

If GTFS already provides that granularity, use it directly.
If not, synthesize it from parent-station/pathway structure where possible.

## Correct Fare-Free / Time-Free Behavior

Initial boarding should pay:

- access walk
- wait

Staying on the same line should pay:

- runtime only

Transferring should pay:

- alight
- transfer movement
- new wait

Exactly once each.

## Graph Construction Migration

### Step 1. Preserve physical stop layer

Keep the current physical stop nodes for:

- seeds
- destination access
- grid links
- transfer topology

### Step 2. Add onboard nodes

Create onboard nodes keyed by:

- physical node
- route
- direction

Store:

- `physical_node_idx`
- `route_id`
- `direction_id`

### Step 3. Move ride edges to onboard layer

Current ride edges are:

- physical stop -> physical stop

They should become:

- onboard(route, stop_a) -> onboard(route, stop_b)

Cost:

- runtime only

### Step 4. Add boarding edges

For every onboard node:

- physical -> onboard

Cost:

- expected wait

### Step 5. Add alight edges

For every onboard node:

- onboard -> physical

Cost:

- `0`

### Step 6. Keep transfer movement on physical layer

Keep current transfer edges between physical nodes:

- explicit pathways
- explicit transfers
- synthetic hub transfers
- spatial fallback transfers

### Step 7. Export richer node metadata

Each node needs:

- `node_kind`
- `physical_node_idx` for onboard nodes
- `route_id`
- `direction_id`
- physical stop metadata

## Runtime / Payload Changes

Dijkstra can stay unchanged.

Path reconstruction must understand node kinds so API payloads show:

- walk to station
- ride line X
- transfer
- ride line Y
- walk to destination

and hide onboard/physical bookkeeping transitions.

## Why Naive Node Splitting Is Not Enough

Blindly splitting every multi-line node and assigning a flat transfer penalty
would be wrong because:

- first boarding would be over-penalized
- connections could be double-penalized
- wait and transfer movement would be mixed together

The correct model separates:

- boarding wait
- in-vehicle runtime
- transfer movement

## Expected Benefits

- no free same-node line changes
- no repeated wait while staying on one line
- transfer costs affect Dijkstra directly
- better route realism in large hubs

## Expected Costs

- larger graph
- more complex graph build
- more complex path payload reconstruction
- artifact schema changes
