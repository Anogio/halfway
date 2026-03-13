export type TransitMapDebugHandle = {
  getSize: () => { x: number; y: number };
  containerPointToLatLng: (point: [number, number]) => { lat: number; lng: number };
  fire: (type: "click", payload: { latlng: { lat: number; lng: number } }) => void;
  getSourceFeatureCount?: (sourceName: "origins" | "paths" | "isochrones") => number | null;
  getRenderedFeatureCount?: (
    layerName: "origins" | "paths" | "isochrones",
    point?: [number, number]
  ) => number | null;
  getInspectDebug?: () => {
    inspectCard: { lat: number; lon: number; minS: number | null; maxS: number | null } | null;
    inspectAddressLabel: string | null;
    markerAttached: boolean;
    popupAttached: boolean;
  };
};
