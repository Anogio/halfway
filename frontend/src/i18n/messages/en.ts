import type { Messages } from "@/i18n/types";

export const enMessages: Messages = {
  app: {
    title: "Halfway",
    siteName: "Halfway",
    description: "Compare trips across the city and spot the easiest place to meet."
  },
  language: {
    toggleAriaLabel: "Change language",
    menuAriaLabel: "Language options",
    currentLocaleLabel: (localeCode: string) => `Current language: ${localeCode.toUpperCase()}`,
    english: "English",
    french: "French"
  },
  city: {
    toggleAriaLabel: "Change city",
    menuAriaLabel: "City options",
    currentCityLabel: (cityLabel: string) => `Current city: ${cityLabel}`,
    localizedName: (cityId: string) => {
      switch (cityId) {
        case "london_uk":
          return "London";
        case "grenoble_fr":
          return "Grenoble";
        case "madrid_es":
          return "Madrid";
        case "paris_fr":
          return "Paris";
        default:
          return cityId;
      }
    },
    unselectedLabel: "CITY",
    gateDialogAriaLabel: "Choose your city",
    gateEyebrow: "Meet halfway.",
    gateTitle: "Halfway",
    gateDescription: "Compare trips across the city and spot the easiest place to meet.",
    gateLoading: "Loading cities...",
    gateOptionsAriaLabel: "Available cities"
  },
  map: {
    canvasAriaLabel: "Heatmap map with tiles and overlay",
    loadingHeatmap: "Updating heatmap..."
  },
  search: {
    sectionAriaLabel: "Address search",
    inputPlaceholder: "Add point by address",
    inputAriaLabel: "Add point by address",
    suggestionsAriaLabel: "Address suggestions",
    searchingAddresses: "Searching addresses...",
    noResultFound: "No result found."
  },
  onboarding: {
    dialogAriaLabel: "Initialize meeting points",
    title: "Halfway",
    closeAriaLabel: "Close onboarding",
    description: "Search and add each starting point. You can still add new points later.",
    selectedPoints: (selected: number, max: number) => `Selected points: ${selected}/${max}`,
    selectedStartingPointsAriaLabel: "Selected starting points",
    noPointSelectedYet: "No point selected yet.",
    removeOriginAriaLabel: (originLabel: string) => `Remove ${originLabel}`,
    removeButton: "Remove",
    confirmAndStartMap: "Find a meeting point",
    loadingTitle: "Finding the best meeting point..."
  },
  inspect: {
    sectionAriaLabel: "Map point details",
    pointsHeading: "Points",
    cancelPointPlacement: "Cancel adding point",
    addStartingPoint: "Add point by clicking",
    clearSelection: "Clear all points",
    emptyState: "Add some points first.",
    addModeHint: "Point creation mode enabled. Click anywhere on the map to add a starting point.",
    computingPaths: "Computing paths...",
    pathErrorPrefix: "Path error",
    pointPathsListAriaLabel: "Point paths list",
    noPath: "No path",
    removeOriginAriaLabel: (originLabel: string) => `Remove ${originLabel}`,
    pathDetailsAriaLabel: (originLabel: string) => `${originLabel} path details`,
    selectDestinationToComputePaths: "Select a destination on the map to compute paths.",
    pathNotComputedYet: "Path not computed yet for this point.",
    pathTotalLabel: "Path total",
    noPathWithinMaxTime: "No path found within current max-time cap."
  },
  errors: {
    unknownError: "Unknown error",
    metadataLoadFailed: (message: string) => `Failed to load metadata: ${message}`,
    addressSearchFailed: (message: string) => `Address search failed: ${message}`
  },
  status: {
    loadingAddress: "Loading address...",
    selectedPoint: "Selected point"
  },
  toasts: {
    pointLimitReached: (maxOrigins: number) => `Point limit reached (${maxOrigins}).`,
    pointAdded: (originLabel: string) => `${originLabel} added.`,
    clickMapToAddPoint: "Click on the map to add a starting point.",
    pointCreationCanceled: "Point creation canceled.",
    allPointsRemoved: "All points removed.",
    pointRemoved: "Point removed.",
    selectionCleared: "Selection cleared.",
    pointAlreadySelected: "Point already selected.",
    pointsInitialized: (count: number) => `${count} points initialized.`,
    computingMeetingIsochrone: "Computing meeting isochrone...",
    isochroneUpdated: "Isochrone updated.",
    failedToFetchIsochrones: "Failed to fetch isochrones."
  },
  presentation: {
    bucketLabel: (minMinutes: number, maxMinutes: number) => `${minMinutes}-${maxMinutes} min`,
    duration: {
      minutes: (minutes: number) => `${minutes} min`,
      hours: (hours: number) => `${hours}h`,
      hoursMinutes: (hours: number, minutes: number) => `${hours}h ${minutes}m`
    },
    unlabeledLine: "unlabeled",
    unknownStop: "unknown",
    firstStop: "first stop",
    lastStop: "last stop",
    rideStep: (lineLabel: string, from: string, to: string, duration: string) =>
      `Ride ${lineLabel}: ${from} -> ${to} (${duration})`,
    walkStep: (toLabel: string, duration: string) => `Walk to ${toLabel} (${duration})`,
    walkDestinationStep: (fromLabel: string, duration: string) =>
      `Walk to destination from ${fromLabel} (${duration})`,
    transferStep: (duration: string) => `Transfer (${duration})`
  }
};
