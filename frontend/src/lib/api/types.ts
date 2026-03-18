export type IsochroneScalarGrid = {
  topology: {
    min_lat: number;
    min_lon: number;
    lat_step: number;
    lon_step: number;
  };
  grid: {
    min_row: number;
    min_col: number;
    row_count: number;
    col_count: number;
    values: Array<number | null>;
  };
  bounds: {
    west: number;
    south: number;
    east: number;
    north: number;
  };
  max_time_s: number;
};

export type IsochroneResponse = {
  origin: { lat: number; lon: number };
  profile: string;
  stats?: {
    seed_count: number;
    reachable_cells_compute_horizon: number;
    reachable_cells_render_horizon: number;
    reachable_cells: number;
    total_linked_cells: number;
    compute_max_time_s: number;
    render_max_time_s: number;
  };
  scalar_grid: IsochroneScalarGrid | null;
};

export type MultiOrigin = {
  id: string;
  lat: number;
  lon: number;
};

export type MultiIsochroneResponse = {
  origins: MultiOrigin[];
  profile: string;
  stats?: NonNullable<IsochroneResponse["stats"]> & {
    origin_count: number;
    origin_seed_counts: Record<string, number>;
  };
  scalar_grid: IsochroneScalarGrid | null;
};

export type PathSegment = {
  type: "walk_origin" | "graph_edge" | "walk_destination";
  kind: string;
  seconds: number;
  from_label?: string;
  to_label?: string;
  from_stop_name?: string;
  to_stop_name?: string;
  from_stop_id?: string;
  to_stop_id?: string;
  route_id?: string;
  route_label?: string;
};

export type PathSummary = {
  max_time_s: number;
  total_time_s?: number;
};

export type PathStats = {
  seed_count: number;
  destination_candidate_count: number;
  node_count?: number;
  segment_count?: number;
  origin_walk_s?: number;
  graph_time_s?: number;
  boarding_wait_s?: number;
  ride_runtime_s?: number;
  transfer_s?: number;
  destination_walk_s?: number;
};

export type PathResponse = {
  origin: { lat: number; lon: number };
  destination: { lat: number; lon: number };
  profile: string;
  reachable: boolean;
  summary: PathSummary;
  stats?: PathStats;
  segments: PathSegment[];
  nodes: {
    node_idx: number;
    stop_id: string;
    stop_name: string;
    lat: number;
    lon: number;
  }[];
};

export type MultiPathItemResponse = PathResponse & {
  origin_id: string;
};

export type MultiPathResponse = {
  destination: { lat: number; lon: number };
  profile: string;
  paths: MultiPathItemResponse[];
};

export type CityMetadata = {
  id: string;
  country_code: string;
  default_view: [number, number, number];
  bbox: [number, number, number, number];
};

export type MetadataResponse = {
  cities: CityMetadata[];
};

export type GeocodeResult = {
  id: string;
  label: string;
  lat: number;
  lon: number;
};

type GeocodeResponse = {
  results: GeocodeResult[];
};

type ReverseGeocodeResponse = {
  label: string;
};

export type {
  GeocodeResponse,
  ReverseGeocodeResponse
};
