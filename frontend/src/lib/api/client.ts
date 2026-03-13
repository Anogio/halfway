import type {
  GeocodeResponse,
  GeocodeResult,
  MetadataResponse,
  MultiIsochroneResponse,
  MultiOrigin,
  MultiPathResponse,
  ReverseGeocodeResponse
} from "@/lib/api/types";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";
const ROUTING_DEBUG_STATS = process.env.NEXT_PUBLIC_ROUTING_DEBUG_STATS === "1";

type RoutingRequestOptions = {
  debug?: boolean;
};

function normalizeCity(city: string): string {
  const normalized = city.trim();
  if (!normalized) {
    throw new Error("city is required");
  }
  return normalized;
}

async function fetchJson<T>(
  pathOrUrl: string,
  init: RequestInit,
  errorPrefix: string
): Promise<T> {
  const response = await fetch(pathOrUrl, init);
  if (!response.ok) {
    throw new Error(`${errorPrefix} failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchMetadata(): Promise<MetadataResponse> {
  return fetchJson<MetadataResponse>(`${BACKEND_URL}/metadata`, { method: "GET" }, "Metadata request");
}

export async function fetchMultiIsochrones(
  city: string,
  origins: MultiOrigin[],
  options: RoutingRequestOptions = {}
): Promise<MultiIsochroneResponse> {
  const cityId = normalizeCity(city);
  return fetchJson<MultiIsochroneResponse>(
    `${BACKEND_URL}/multi_isochrones`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ city: cityId, origins, debug: options.debug ?? ROUTING_DEBUG_STATS })
    },
    "Multi-isochrone request"
  );
}

export async function fetchMultiPath(
  city: string,
  origins: MultiOrigin[],
  destinationLat: number,
  destinationLon: number,
  options: RoutingRequestOptions = {}
): Promise<MultiPathResponse> {
  const cityId = normalizeCity(city);
  return fetchJson<MultiPathResponse>(
    `${BACKEND_URL}/multi_path`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        city: cityId,
        origins,
        debug: options.debug ?? ROUTING_DEBUG_STATS,
        destination: {
          lat: destinationLat,
          lon: destinationLon
        }
      })
    },
    "Multi-path request"
  );
}

export async function fetchGeocode(city: string, query: string): Promise<GeocodeResult[]> {
  const normalized = query.trim();
  if (normalized.length < 3) {
    return [];
  }
  const cityId = normalizeCity(city);

  const url = new URL(`${BACKEND_URL}/geocode`);
  url.searchParams.set("city", cityId);
  url.searchParams.set("q", normalized);

  const payload = await fetchJson<GeocodeResponse>(url.toString(), { method: "GET" }, "Geocode request");
  if (!Array.isArray(payload.results)) {
    return [];
  }
  return payload.results;
}

export async function fetchReverseGeocode(
  city: string,
  lat: number,
  lon: number,
  signal?: AbortSignal
): Promise<string | null> {
  const cityId = normalizeCity(city);
  const url = new URL(`${BACKEND_URL}/reverse_geocode`);
  url.searchParams.set("city", cityId);
  url.searchParams.set("lat", lat.toFixed(5));
  url.searchParams.set("lon", lon.toFixed(5));

  const payload = await fetchJson<ReverseGeocodeResponse>(
    url.toString(),
    { method: "GET", signal },
    "Reverse geocode request"
  );

  if (typeof payload.label !== "string") {
    return null;
  }
  const normalizedLabel = payload.label.trim();
  return normalizedLabel || null;
}
