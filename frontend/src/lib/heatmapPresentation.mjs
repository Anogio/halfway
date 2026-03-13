export const SMOOTHING_ITERATIONS = 1;

export function bucketLabel(minS, maxS, formatter) {
  const minM = Math.floor(minS / 60);
  const maxM = Math.ceil(maxS / 60);
  if (typeof formatter === "function") {
    return formatter(minM, maxM);
  }
  return `${minM}-${maxM} min`;
}

export function formatDuration(seconds, durationFormatterSet) {
  const formatters = {
    minutes: (mins) => `${mins} min`,
    hours: (hours) => `${hours}h`,
    hoursMinutes: (hours, mins) => `${hours}h ${mins}m`,
    ...(durationFormatterSet ?? {})
  };

  const mins = Math.round(seconds / 60);
  if (mins < 60) {
    return formatters.minutes(mins);
  }
  const hours = Math.floor(mins / 60);
  const rem = mins % 60;
  return rem === 0 ? formatters.hours(hours) : formatters.hoursMinutes(hours, rem);
}

export function buildDisplayPathSteps(pathData, presentationMessages) {
  const messages = {
    unlabeledLine: "unlabeled",
    unknownStop: "unknown",
    firstStop: "first stop",
    lastStop: "last stop",
    rideStep: (lineLabel, from, to, duration) => `Ride ${lineLabel}: ${from} -> ${to} (${duration})`,
    walkStep: (toLabel, duration) => `Walk to ${toLabel} (${duration})`,
    walkDestinationStep: (fromLabel, duration) => `Walk to destination from ${fromLabel} (${duration})`,
    transferStep: (duration) => `Transfer (${duration})`,
    duration: {
      minutes: (mins) => `${mins} min`,
      hours: (hours) => `${hours}h`,
      hoursMinutes: (hours, mins) => `${hours}h ${mins}m`
    },
    ...(presentationMessages ?? {})
  };
  messages.duration = {
    minutes: (mins) => `${mins} min`,
    hours: (hours) => `${hours}h`,
    hoursMinutes: (hours, mins) => `${hours}h ${mins}m`,
    ...(presentationMessages?.duration ?? {})
  };

  if (!pathData.reachable) {
    return [];
  }

  const steps = [];
  let currentRide = null;

  const flushRide = () => {
    if (!currentRide) {
      return;
    }
    const lineLabel = currentRide.line || messages.unlabeledLine;
    steps.push({
      key: `ride-${lineLabel}-${currentRide.from}-${currentRide.to}-${currentRide.seconds}`,
      text: messages.rideStep(
        lineLabel,
        currentRide.from,
        currentRide.to,
        formatDuration(currentRide.seconds, messages.duration)
      )
    });
    currentRide = null;
  };

  for (const segment of pathData.segments) {
    if (Math.round(Number(segment.seconds) / 60) <= 0) {
      continue;
    }

    if (segment.type === "graph_edge" && segment.kind === "ride") {
      const line = (segment.route_label || segment.route_id || "").trim();
      const from = segment.from_stop_name || segment.from_label || messages.unknownStop;
      const to = segment.to_stop_name || segment.to_label || messages.unknownStop;
      if (currentRide && currentRide.line === line && line) {
        currentRide.to = to;
        currentRide.seconds += Number(segment.seconds);
      } else {
        flushRide();
        currentRide = {
          line,
          from,
          to,
          seconds: Number(segment.seconds)
        };
      }
      continue;
    }

    flushRide();

    if (segment.type === "walk_origin") {
      steps.push({
        key: `walk-origin-${segment.to_label}-${segment.seconds}`,
        text: messages.walkStep(
          segment.to_label ?? messages.firstStop,
          formatDuration(Number(segment.seconds), messages.duration)
        )
      });
      continue;
    }

    if (segment.type === "walk_destination") {
      steps.push({
        key: `walk-destination-${segment.from_label}-${segment.seconds}`,
        text: messages.walkDestinationStep(
          segment.from_label ?? messages.lastStop,
          formatDuration(Number(segment.seconds), messages.duration)
        )
      });
      continue;
    }

    if (segment.type === "graph_edge") {
      steps.push({
        key: `transfer-${segment.kind}-${segment.from_stop_id}-${segment.to_stop_id}-${segment.seconds}`,
        text: messages.transferStep(formatDuration(Number(segment.seconds), messages.duration))
      });
    }
  }

  flushRide();
  return steps;
}

export function smoothFeatureCollection(data) {
  const featureCollection = data?.feature_collection;
  if (!featureCollection) {
    return null;
  }
  return {
    ...featureCollection,
    features: featureCollection.features.map((feature) => ({
      ...feature,
      geometry: {
        ...feature.geometry,
        coordinates: feature.geometry.coordinates.map((polygon) =>
          polygon.map((ring) => smoothRing(ring, SMOOTHING_ITERATIONS))
        )
      }
    }))
  };
}

function smoothRing(ring, iterations) {
  if (iterations <= 0 || ring.length < 4) {
    return ring;
  }

  let current = ring;
  for (let iter = 0; iter < iterations; iter += 1) {
    current = chaikin(current);
  }
  return current;
}

function chaikin(ring) {
  if (ring.length < 4) {
    return ring;
  }

  const last = ring[ring.length - 1];
  const first = ring[0];
  const isClosed = last[0] === first[0] && last[1] === first[1];
  const pts = isClosed ? ring.slice(0, -1) : ring.slice();
  if (pts.length < 3) {
    return ring;
  }

  const next = [];
  for (let i = 0; i < pts.length; i += 1) {
    const p0 = pts[i];
    const p1 = pts[(i + 1) % pts.length];
    next.push([0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1]]);
    next.push([0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1]]);
  }
  next.push(next[0]);
  return next;
}
