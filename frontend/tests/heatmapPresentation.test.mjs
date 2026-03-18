import assert from "node:assert/strict";
import test from "node:test";

import {
  buildDisplayPathSteps,
  formatDuration
} from "../src/lib/heatmapPresentation.mjs";

test("formatDuration formats minutes and hours", () => {
  assert.equal(formatDuration(600), "10 min");
  assert.equal(formatDuration(3600), "1h");
  assert.equal(formatDuration(3900), "1h 5m");
});

test("buildDisplayPathSteps groups consecutive rides on same line", () => {
  const steps = buildDisplayPathSteps({
    origin: { lat: 48.85, lon: 2.35 },
    destination: { lat: 48.86, lon: 2.36 },
    profile: "weekday_non_holiday",
    reachable: true,
    summary: {
      seed_count: 1,
      destination_candidate_count: 1,
      max_time_s: 3600
    },
    segments: [
      {
        type: "graph_edge",
        kind: "ride",
        seconds: 120,
        from_stop_name: "A",
        to_stop_name: "B",
        route_label: "9"
      },
      {
        type: "graph_edge",
        kind: "ride",
        seconds: 120,
        from_stop_name: "B",
        to_stop_name: "C",
        route_label: "9"
      },
      {
        type: "graph_edge",
        kind: "transfer_gtfs",
        seconds: 60
      }
    ],
    nodes: []
  });

  assert.equal(steps.length, 2);
  assert.match(steps[0].text, /Ride 9: A -> C/);
  assert.match(steps[1].text, /Transfer \(1 min\)/);
});
