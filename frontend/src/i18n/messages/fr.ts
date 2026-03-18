import type { Messages } from "@/i18n/types";

export const frMessages: Messages = {
  app: {
    title: "Halfway",
    siteName: "Halfway",
    description: "Comparez les trajets et repérez le lieu le plus simple pour vous retrouver."
  },
  language: {
    toggleAriaLabel: "Changer la langue",
    menuAriaLabel: "Options de langue",
    currentLocaleLabel: (localeCode: string) => `Langue actuelle : ${localeCode.toUpperCase()}`,
    english: "Anglais",
    french: "Français"
  },
  city: {
    toggleAriaLabel: "Changer de ville",
    menuAriaLabel: "Options de ville",
    currentCityLabel: (cityLabel: string) => `Ville actuelle : ${cityLabel}`,
    localizedName: (cityId: string) => {
      switch (cityId) {
        case "london_uk":
          return "Londres";
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
    unselectedLabel: "VILLE",
    gateDialogAriaLabel: "Choisir votre ville",
    gateEyebrow: "On se retrouve où ?",
    gateTitle: "Halfway",
    gateDescription: "Comparez les trajets et repérez le lieu le plus simple pour vous retrouver.",
    gateLoading: "Chargement des villes...",
    gateOptionsAriaLabel: "Villes disponibles"
  },
  map: {
    canvasAriaLabel: "Carte avec tuiles et superposition",
    loadingHeatmap: "Mise à jour de la carte..."
  },
  search: {
    sectionAriaLabel: "Recherche d'adresse",
    inputPlaceholder: "Ajouter un point par adresse",
    inputAriaLabel: "Ajouter un point par adresse",
    suggestionsAriaLabel: "Suggestions d'adresses",
    searchingAddresses: "Recherche d'adresses...",
    noResultFound: "Aucun résultat."
  },
  onboarding: {
    dialogAriaLabel: "Initialiser les points de départ",
    title: "Halfway",
    closeAriaLabel: "Fermer l'accueil",
    description: "Recherchez et ajoutez chaque point de départ. Vous pourrez en ajouter d'autres plus tard.",
    selectedPoints: (selected: number, max: number) => `Points sélectionnés : ${selected}/${max}`,
    selectedStartingPointsAriaLabel: "Points de départ sélectionnés",
    noPointSelectedYet: "Aucun point sélectionné pour le moment.",
    removeOriginAriaLabel: (originLabel: string) => `Retirer ${originLabel}`,
    removeButton: "Retirer",
    confirmAndStartMap: "Trouver un point de rencontre",
    loadingTitle: "Recherche du meilleur point de rencontre..."
  },
  inspect: {
    sectionAriaLabel: "Détails du point sur la carte",
    pointsHeading: "Points",
    cancelPointPlacement: "Annuler l'ajout du point",
    addStartingPoint: "Ajouter un point en cliquant",
    clearSelection: "Effacer tous les points",
    emptyState: "Ajoutez d'abord des points.",
    addModeHint: "Mode création de point actif. Cliquez n'importe où sur la carte pour ajouter un point de départ.",
    computingPaths: "Calcul des trajets...",
    pathErrorPrefix: "Erreur de trajet",
    pointPathsListAriaLabel: "Liste des trajets par point",
    noPath: "Aucun trajet",
    removeOriginAriaLabel: (originLabel: string) => `Retirer ${originLabel}`,
    pathDetailsAriaLabel: (originLabel: string) => `Détails du trajet pour ${originLabel}`,
    showPathDetailsAriaLabel: (originLabel: string) => `Afficher les détails du trajet pour ${originLabel}`,
    selectDestinationToComputePaths: "Sélectionnez une destination sur la carte pour calculer les trajets.",
    pathNotComputedYet: "Trajet pas encore calculé pour ce point.",
    pathTotalLabel: "Durée totale",
    noPathWithinMaxTime: "Aucun trajet trouvé dans la limite de temps actuelle."
  },
  errors: {
    unknownError: "Erreur inconnue",
    metadataLoadFailed: (message: string) => `Échec du chargement des métadonnées : ${message}`,
    addressSearchFailed: (message: string) => `Échec de la recherche d'adresse : ${message}`
  },
  status: {
    loadingAddress: "Chargement de l'adresse...",
    selectedPoint: "Point sélectionné"
  },
  toasts: {
    pointLimitReached: (maxOrigins: number) => `Limite de points atteinte (${maxOrigins}).`,
    pointAdded: (originLabel: string) => `${originLabel} ajouté.`,
    clickMapToAddPoint: "Cliquez sur la carte pour ajouter un point de départ.",
    pointCreationCanceled: "Création du point annulée.",
    allPointsRemoved: "Tous les points ont été retirés.",
    pointRemoved: "Point retiré.",
    selectionCleared: "Sélection effacée.",
    pointAlreadySelected: "Point déjà sélectionné.",
    pointsInitialized: (count: number) => `${count} points initialisés.`,
    computingMeetingIsochrone: "Calcul de l'isochrone de rencontre...",
    isochroneUpdated: "Isochrone mis à jour.",
    failedToFetchIsochrones: "Échec de la récupération des isochrones."
  },
  presentation: {
    bucketLabel: (minMinutes: number, maxMinutes: number) => `${minMinutes}-${maxMinutes} min`,
    duration: {
      minutes: (minutes: number) => `${minutes} min`,
      hours: (hours: number) => `${hours} h`,
      hoursMinutes: (hours: number, minutes: number) => `${hours} h ${minutes} min`
    },
    unlabeledLine: "sans libellé",
    unknownStop: "inconnu",
    firstStop: "premier arrêt",
    lastStop: "dernier arrêt",
    rideStep: (lineLabel: string, from: string, to: string, duration: string) =>
      `Ligne ${lineLabel} : ${from} -> ${to} (${duration})`,
    walkStep: (toLabel: string, duration: string) => `Marcher jusqu'à ${toLabel} (${duration})`,
    walkDestinationStep: (fromLabel: string, duration: string) =>
      `Marcher vers la destination depuis ${fromLabel} (${duration})`,
    transferStep: (duration: string) => `Correspondance (${duration})`
  }
};
