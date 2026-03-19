import type { IsochroneScalarGrid } from "@/lib/api";

const DEFAULT_UPSCALE = 8;
const DEFAULT_ALPHA = 0.54;
const COMPONENT_FADE_START_CELLS = 2;
const COMPONENT_FADE_FULL_CELLS = 6;
const MAX_GPU_RENDER_DIMENSION = 1600;

export const HEATMAP_BASE_ALPHA = DEFAULT_ALPHA;
export const HEATMAP_MIN_VISIBLE_COVERAGE = 0.015;

export const ISOCHRONE_COLOR_STOPS: Array<[number, [number, number, number]]> = [
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

export type ScalarFieldTexture = {
  width: number;
  height: number;
  renderWidth: number;
  renderHeight: number;
  maxTimeS: number;
  bounds: IsochroneScalarGrid["bounds"];
  pixels: Uint8Array;
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

export function buildScalarFieldTexture(
  grid: IsochroneScalarGrid | null | undefined
): ScalarFieldTexture | null {
  if (!grid || grid.grid.row_count <= 0 || grid.grid.col_count <= 0) {
    return null;
  }

  const { row_count: rowCount, col_count: colCount, values } = grid.grid;
  const componentStrengths = buildComponentStrengths(grid);
  const pixels = new Uint8Array(rowCount * colCount * 4);

  for (let row = 0; row < rowCount; row += 1) {
    for (let col = 0; col < colCount; col += 1) {
      const sourceIdx = row * colCount + col;
      const targetRow = rowCount - 1 - row;
      const targetIdx = (targetRow * colCount + col) * 4;
      const value = values[sourceIdx];
      const coverage = clamp(componentStrengths[sourceIdx] ?? 0, 0, 1);
      if (value === null || !Number.isFinite(value) || coverage <= 0) {
        pixels[targetIdx + 3] = 255;
        continue;
      }

      const normalizedTime = clamp(value / Math.max(grid.max_time_s, 1), 0, 1);
      const weightedTime = normalizedTime * coverage;
      pixels[targetIdx] = Math.round(weightedTime * 255);
      pixels[targetIdx + 1] = Math.round(coverage * 255);
      pixels[targetIdx + 2] = 0;
      pixels[targetIdx + 3] = 255;
    }
  }

  const [renderWidth, renderHeight] = computeGpuRenderSize(colCount, rowCount);
  return {
    width: colCount,
    height: rowCount,
    renderWidth,
    renderHeight,
    maxTimeS: grid.max_time_s,
    bounds: grid.bounds,
    pixels
  };
}

function computeGpuRenderSize(width: number, height: number): [number, number] {
  const scaledWidth = Math.max(1, width * DEFAULT_UPSCALE);
  const scaledHeight = Math.max(1, height * DEFAULT_UPSCALE);
  const maxDimension = Math.max(scaledWidth, scaledHeight);
  if (maxDimension <= MAX_GPU_RENDER_DIMENSION) {
    return [scaledWidth, scaledHeight];
  }
  const scale = MAX_GPU_RENDER_DIMENSION / maxDimension;
  return [
    Math.max(1, Math.round(scaledWidth * scale)),
    Math.max(1, Math.round(scaledHeight * scale))
  ];
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

function smoothstep(value: number): number {
  const t = clamp(value, 0, 1);
  return t * t * (3 - 2 * t);
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
