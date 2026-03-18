export const ISOCHRONE_RASTER_SOURCE_ID = "isochrones-raster";
export const ISOCHRONE_RASTER_LAYER_ID = "isochrones-raster-layer";
export const ORIGIN_SOURCE_ID = "origins";
export const ORIGIN_LAYER_ID = "origins-circle";
export const PATH_SOURCE_ID = "paths";
export const PATH_LINE_LAYER_ID = "paths-line";
export const PATH_POINT_LAYER_ID = "paths-point";

export const DEBUG_SOURCE_IDS = {
  origins: ORIGIN_SOURCE_ID,
  paths: PATH_SOURCE_ID,
  isochrones: ISOCHRONE_RASTER_SOURCE_ID
} as const;

export const DEBUG_LAYER_IDS = {
  origins: ORIGIN_LAYER_ID,
  paths: PATH_LINE_LAYER_ID,
  isochrones: ISOCHRONE_RASTER_LAYER_ID
} as const;
