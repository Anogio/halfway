import type { IsochroneScalarGrid } from "@/lib/api";

const DEFAULT_UPSCALE = 8;
const DEFAULT_BLUR_RADIUS = 6;
const DEFAULT_BLUR_SIGMA = 2.4;
const DEFAULT_ALPHA = 0.54;
const MIN_VISIBLE_COVERAGE = 0.015;
const COMPONENT_FADE_START_CELLS = 2;
const COMPONENT_FADE_FULL_CELLS = 6;

const ISOCHRONE_COLOR_STOPS: Array<[number, [number, number, number]]> = [
  [0, [21, 48, 122]],
  [300, [18, 95, 181]],
  [600, [0, 141, 213]],
  [900, [0, 181, 180]],
  [1200, [117, 205, 58]],
  [1500, [236, 221, 68]],
  [1800, [250, 171, 56]],
  [2700, [230, 93, 66]],
  [3600, [174, 36, 69]]
];

export type ScalarGridSample = {
  lat: number;
  lon: number;
  timeS: number;
};

export type ScalarRasterOverlay = {
  imageUrl: string;
  coordinates: [[number, number], [number, number], [number, number], [number, number]];
};

export function findScalarGridMinimum(grid: IsochroneScalarGrid | null | undefined): ScalarGridSample | null {
  if (!grid) {
    return null;
  }

  let bestIdx = -1;
  let bestTimeS = Number.POSITIVE_INFINITY;
  for (let idx = 0; idx < grid.grid.values.length; idx += 1) {
    const value = grid.grid.values[idx];
    if (value === null || !Number.isFinite(value) || value >= bestTimeS) {
      continue;
    }
    bestIdx = idx;
    bestTimeS = value;
  }

  if (bestIdx < 0) {
    return null;
  }

  const rowOffset = Math.floor(bestIdx / grid.grid.col_count);
  const colOffset = bestIdx % grid.grid.col_count;
  const row = grid.grid.min_row + rowOffset;
  const col = grid.grid.min_col + colOffset;
  return {
    lat: Number((grid.topology.min_lat + row * grid.topology.lat_step).toFixed(5)),
    lon: Number((grid.topology.min_lon + col * grid.topology.lon_step).toFixed(5)),
    timeS: bestTimeS
  };
}

export function sampleScalarGridAtLngLat(
  grid: IsochroneScalarGrid | null | undefined,
  lng: number,
  lat: number
): ScalarGridSample | null {
  if (!grid) {
    return null;
  }

  const col = Math.floor((lng - grid.bounds.west) / grid.topology.lon_step);
  const row = Math.floor((lat - grid.bounds.south) / grid.topology.lat_step);
  if (row < 0 || col < 0 || row >= grid.grid.row_count || col >= grid.grid.col_count) {
    return null;
  }

  const timeS = grid.grid.values[row * grid.grid.col_count + col];
  if (timeS === null || !Number.isFinite(timeS)) {
    return null;
  }

  return {
    lat: Number(lat.toFixed(5)),
    lon: Number(lng.toFixed(5)),
    timeS
  };
}

export function buildScalarRasterOverlay(
  grid: IsochroneScalarGrid | null | undefined
): ScalarRasterOverlay | null {
  if (!grid || grid.grid.row_count <= 0 || grid.grid.col_count <= 0) {
    return null;
  }

  const width = grid.grid.col_count * DEFAULT_UPSCALE;
  const height = grid.grid.row_count * DEFAULT_UPSCALE;
  const denseValues = new Float32Array(width * height);
  const denseWeights = new Float32Array(width * height);
  const componentStrengths = buildComponentStrengths(grid);

  for (let y = 0; y < height; y += 1) {
    const sourceRow = mapDenseCoordinate(
      grid.grid.row_count,
      height,
      y,
      true
    );
    for (let x = 0; x < width; x += 1) {
      const sourceCol = mapDenseCoordinate(
        grid.grid.col_count,
        width,
        x,
        false
      );
      const sample = sampleInterpolatedGridValue(grid, componentStrengths, sourceRow, sourceCol);
      if (!sample) {
        continue;
      }
      const idx = y * width + x;
      denseValues[idx] = sample.timeS * sample.coverage;
      denseWeights[idx] = sample.coverage;
    }
  }

  const blurredValues = gaussianBlur(
    denseValues,
    width,
    height,
    DEFAULT_BLUR_RADIUS,
    DEFAULT_BLUR_SIGMA
  );
  const blurredWeights = gaussianBlur(
    denseWeights,
    width,
    height,
    DEFAULT_BLUR_RADIUS,
    DEFAULT_BLUR_SIGMA
  );
  const imageData = new ImageData(width, height);
  const rgba = imageData.data;
  for (let idx = 0; idx < blurredValues.length; idx += 1) {
    const weight = blurredWeights[idx];
    const base = idx * 4;
    if (weight <= MIN_VISIBLE_COVERAGE) {
      rgba[base + 3] = 0;
      continue;
    }

    const timeS = blurredValues[idx] / weight;
    const [r, g, b] = interpolateColor(timeS, grid.max_time_s);
    const coverage = Math.max(0, Math.min(weight, 1));
    const alpha = computeOverlayAlpha(timeS, grid.max_time_s, coverage);
    rgba[base] = r;
    rgba[base + 1] = g;
    rgba[base + 2] = b;
    rgba[base + 3] = Math.round(255 * alpha);
  }

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) {
    return null;
  }
  context.putImageData(imageData, 0, 0);

  return {
    imageUrl: canvas.toDataURL("image/png"),
    coordinates: [
      [grid.bounds.west, grid.bounds.north],
      [grid.bounds.east, grid.bounds.north],
      [grid.bounds.east, grid.bounds.south],
      [grid.bounds.west, grid.bounds.south]
    ]
  };
}

type InterpolatedGridSample = {
  timeS: number;
  coverage: number;
};

function mapDenseCoordinate(
  coarseCount: number,
  denseCount: number,
  denseIndex: number,
  invert: boolean
): number {
  if (coarseCount <= 1 || denseCount <= 1) {
    return 0;
  }
  const normalized = denseIndex / (denseCount - 1);
  const projected = normalized * (coarseCount - 1);
  return invert ? coarseCount - 1 - projected : projected;
}

function sampleInterpolatedGridValue(
  grid: IsochroneScalarGrid,
  componentStrengths: Float32Array,
  sourceRow: number,
  sourceCol: number
): InterpolatedGridSample | null {
  const row0 = Math.floor(sourceRow);
  const col0 = Math.floor(sourceCol);
  const row1 = Math.min(grid.grid.row_count - 1, row0 + 1);
  const col1 = Math.min(grid.grid.col_count - 1, col0 + 1);
  const rowMix = sourceRow - row0;
  const colMix = sourceCol - col0;

  const corners: Array<[number, number, number]> = [
    [row0, col0, (1 - rowMix) * (1 - colMix)],
    [row0, col1, (1 - rowMix) * colMix],
    [row1, col0, rowMix * (1 - colMix)],
    [row1, col1, rowMix * colMix]
  ];

  let weightedTime = 0;
  let totalWeight = 0;
  for (const [row, col, weight] of corners) {
    if (weight <= 0) {
      continue;
    }
    const value = grid.grid.values[row * grid.grid.col_count + col];
    if (value === null || !Number.isFinite(value)) {
      continue;
    }
    const componentStrength = componentStrengths[row * grid.grid.col_count + col] ?? 0;
    if (componentStrength <= 0) {
      continue;
    }
    const adjustedWeight = weight * componentStrength;
    weightedTime += value * adjustedWeight;
    totalWeight += adjustedWeight;
  }

  if (totalWeight <= 0) {
    return null;
  }
  return {
    timeS: weightedTime / totalWeight,
    coverage: totalWeight
  };
}

function buildComponentStrengths(grid: IsochroneScalarGrid): Float32Array {
  const { row_count: rowCount, col_count: colCount, values } = grid.grid;
  const strengths = new Float32Array(values.length);
  const visited = new Uint8Array(values.length);

  for (let startIdx = 0; startIdx < values.length; startIdx += 1) {
    const startValue = values[startIdx];
    if (visited[startIdx] === 1 || startValue === null || !Number.isFinite(startValue)) {
      continue;
    }

    const queue = [startIdx];
    visited[startIdx] = 1;
    const component: number[] = [];
    while (queue.length > 0) {
      const idx = queue.pop();
      if (idx === undefined) {
        continue;
      }
      component.push(idx);
      const row = Math.floor(idx / colCount);
      const col = idx % colCount;
      const neighbors = [
        [row - 1, col],
        [row + 1, col],
        [row, col - 1],
        [row, col + 1]
      ];

      for (const [nextRow, nextCol] of neighbors) {
        if (nextRow < 0 || nextCol < 0 || nextRow >= rowCount || nextCol >= colCount) {
          continue;
        }
        const nextIdx = nextRow * colCount + nextCol;
        if (visited[nextIdx] === 1) {
          continue;
        }
        const nextValue = values[nextIdx];
        if (nextValue === null || !Number.isFinite(nextValue)) {
          continue;
        }
        visited[nextIdx] = 1;
        queue.push(nextIdx);
      }
    }

    const strength = componentSizeStrength(component.length);
    for (const idx of component) {
      strengths[idx] = strength;
    }
  }

  return strengths;
}

function componentSizeStrength(size: number): number {
  if (size <= COMPONENT_FADE_START_CELLS) {
    return 0.18;
  }
  if (size >= COMPONENT_FADE_FULL_CELLS) {
    return 1;
  }
  const t =
    (size - COMPONENT_FADE_START_CELLS) /
    (COMPONENT_FADE_FULL_CELLS - COMPONENT_FADE_START_CELLS);
  return 0.18 + smoothstep(t) * 0.82;
}

function computeOverlayAlpha(
  timeS: number,
  maxTimeS: number,
  coverage: number
): number {
  const coverageAlpha = DEFAULT_ALPHA * Math.pow(coverage, 0.92);
  const normalizedTime = clamp(timeS / Math.max(maxTimeS, 1), 0, 1);
  const outerFade = 1 - 0.46 * smoothstep(Math.pow(normalizedTime, 0.84));
  return clamp(coverageAlpha * outerFade, 0, 0.76);
}

function smoothstep(value: number): number {
  const t = clamp(value, 0, 1);
  return t * t * (3 - 2 * t);
}

function gaussianBlur(
  values: Float32Array,
  width: number,
  height: number,
  radius: number,
  sigma: number
): Float32Array {
  if (radius <= 0) {
    return values.slice();
  }
  const kernel = buildGaussianKernel(radius, sigma);
  const horizontalPass = convolveHorizontal(values, width, height, kernel, radius);
  return convolveVertical(horizontalPass, width, height, kernel, radius);
}

function buildGaussianKernel(radius: number, sigma: number): Float32Array {
  const kernel = new Float32Array(radius * 2 + 1);
  let sum = 0;
  for (let idx = -radius; idx <= radius; idx += 1) {
    const value = Math.exp(-(idx * idx) / (2 * sigma * sigma));
    kernel[idx + radius] = value;
    sum += value;
  }
  if (sum > 0) {
    for (let idx = 0; idx < kernel.length; idx += 1) {
      kernel[idx] /= sum;
    }
  }
  return kernel;
}

function convolveHorizontal(
  values: Float32Array,
  width: number,
  height: number,
  kernel: Float32Array,
  radius: number
): Float32Array {
  const output = new Float32Array(width * height);
  for (let row = 0; row < height; row += 1) {
    const rowOffset = row * width;
    for (let col = 0; col < width; col += 1) {
      let sum = 0;
      for (let offset = -radius; offset <= radius; offset += 1) {
        const sampleCol = clamp(col + offset, 0, width - 1);
        sum += values[rowOffset + sampleCol] * kernel[offset + radius];
      }
      output[rowOffset + col] = sum;
    }
  }
  return output;
}

function convolveVertical(
  values: Float32Array,
  width: number,
  height: number,
  kernel: Float32Array,
  radius: number
): Float32Array {
  const output = new Float32Array(width * height);
  for (let row = 0; row < height; row += 1) {
    for (let col = 0; col < width; col += 1) {
      let sum = 0;
      for (let offset = -radius; offset <= radius; offset += 1) {
        const sampleRow = clamp(row + offset, 0, height - 1);
        sum += values[sampleRow * width + col] * kernel[offset + radius];
      }
      output[row * width + col] = sum;
    }
  }
  return output;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function interpolateColor(timeS: number, maxTimeS: number): [number, number, number] {
  const clamped = Math.max(0, Math.min(timeS, maxTimeS));
  for (let idx = 0; idx < ISOCHRONE_COLOR_STOPS.length - 1; idx += 1) {
    const [startTime, startColor] = ISOCHRONE_COLOR_STOPS[idx];
    const [endTime, endColor] = ISOCHRONE_COLOR_STOPS[idx + 1];
    if (clamped > endTime) {
      continue;
    }
    const span = endTime - startTime || 1;
    const t = Math.max(0, Math.min(1, (clamped - startTime) / span));
    return [
      Math.round(startColor[0] + (endColor[0] - startColor[0]) * t),
      Math.round(startColor[1] + (endColor[1] - startColor[1]) * t),
      Math.round(startColor[2] + (endColor[2] - startColor[2]) * t)
    ];
  }
  return ISOCHRONE_COLOR_STOPS[ISOCHRONE_COLOR_STOPS.length - 1][1];
}
