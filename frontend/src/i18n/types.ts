export type Locale = "en" | "fr";

export type DurationFormatterSet = {
  minutes: (minutes: number) => string;
  hours: (hours: number) => string;
  hoursMinutes: (hours: number, minutes: number) => string;
};

export type Messages = {
  app: {
    title: string;
    siteName: string;
    description: string;
  };
  language: {
    toggleAriaLabel: string;
    menuAriaLabel: string;
    currentLocaleLabel: (localeCode: string) => string;
    english: string;
    french: string;
  };
  city: {
    toggleAriaLabel: string;
    menuAriaLabel: string;
    currentCityLabel: (cityLabel: string) => string;
    localizedName: (cityId: string) => string;
    unselectedLabel: string;
    gateDialogAriaLabel: string;
    gateEyebrow: string;
    gateTitle: string;
    gateDescription: string;
    gateLoading: string;
    gateOptionsAriaLabel: string;
  };
  map: {
    canvasAriaLabel: string;
    loadingHeatmap: string;
  };
  search: {
    sectionAriaLabel: string;
    inputPlaceholder: string;
    inputAriaLabel: string;
    suggestionsAriaLabel: string;
    searchingAddresses: string;
    noResultFound: string;
  };
  onboarding: {
    dialogAriaLabel: string;
    title: string;
    closeAriaLabel: string;
    description: string;
    selectedPoints: (selected: number, max: number) => string;
    selectedStartingPointsAriaLabel: string;
    noPointSelectedYet: string;
    removeOriginAriaLabel: (originLabel: string) => string;
    removeButton: string;
    confirmAndStartMap: string;
    loadingTitle: string;
  };
  inspect: {
    sectionAriaLabel: string;
    pointsHeading: string;
    cancelPointPlacement: string;
    addStartingPoint: string;
    clearSelection: string;
    emptyState: string;
    addModeHint: string;
    computingPaths: string;
    pathErrorPrefix: string;
    pointPathsListAriaLabel: string;
    noPath: string;
    removeOriginAriaLabel: (originLabel: string) => string;
    pathDetailsAriaLabel: (originLabel: string) => string;
    selectDestinationToComputePaths: string;
    pathNotComputedYet: string;
    pathTotalLabel: string;
    noPathWithinMaxTime: string;
  };
  errors: {
    unknownError: string;
    metadataLoadFailed: (message: string) => string;
    addressSearchFailed: (message: string) => string;
  };
  status: {
    loadingAddress: string;
    selectedPoint: string;
  };
  toasts: {
    pointLimitReached: (maxOrigins: number) => string;
    pointAdded: (originLabel: string) => string;
    clickMapToAddPoint: string;
    pointCreationCanceled: string;
    allPointsRemoved: string;
    pointRemoved: string;
    selectionCleared: string;
    pointAlreadySelected: string;
    pointsInitialized: (count: number) => string;
    computingMeetingIsochrone: string;
    isochroneUpdated: string;
    failedToFetchIsochrones: string;
  };
  presentation: {
    bucketLabel: (minMinutes: number, maxMinutes: number) => string;
    duration: DurationFormatterSet;
    unlabeledLine: string;
    unknownStop: string;
    firstStop: string;
    lastStop: string;
    rideStep: (lineLabel: string, from: string, to: string, duration: string) => string;
    walkStep: (toLabel: string, duration: string) => string;
    walkDestinationStep: (fromLabel: string, duration: string) => string;
    transferStep: (duration: string) => string;
  };
};
