"use client";

import { useMemo } from "react";

import { smoothFeatureCollection } from "@/lib/heatmapPresentation.mjs";
import HeatmapViewFrame from "@/components/heatmap/HeatmapViewFrame";
import { useHeatmapController } from "@/components/heatmap/useHeatmapController";
import { useMapLibreMap } from "@/components/heatmap/useMapLibreMap";
import { useViewportHeightCssVar } from "@/components/heatmap/useViewportHeightCssVar";
import { useI18n } from "@/i18n/useI18n";

export default function HeatmapView() {
  const { messages } = useI18n();
  const controller = useHeatmapController();
  useViewportHeightCssVar();

  const displayFeatureCollection = useMemo(
    () => smoothFeatureCollection(controller.data),
    [controller.data]
  );

  const { mapRef } = useMapLibreMap({
    defaultView: controller.defaultView,
    maxBoundsBbox: controller.mapBbox,
    displayFeatureCollection,
    bucketLabelFormatter: messages.presentation.bucketLabel,
    origins: controller.origins,
    pathByOriginId: controller.pathByOriginId,
    inspectCard: controller.inspectCard,
    inspectAddressLabel: controller.inspectAddressLabel,
    onMapPointClick: controller.onMapPointClick
  });

  return (
    <HeatmapViewFrame
      mapRef={mapRef}
      cities={controller.cities}
      activeCityId={controller.activeCityId}
      onboardingOpen={controller.onboardingOpen}
      citySelectionRequired={controller.citySelectionRequired}
      addModeActive={controller.addModeActive}
      showCursorCrosshair={controller.showCursorCrosshair}
      cursorPosition={controller.cursorPosition}
      searchQuery={controller.searchQuery}
      setSearchQuery={controller.setSearchQuery}
      searchOpen={controller.searchOpen}
      setSearchOpen={controller.setSearchOpen}
      searchLoading={controller.searchLoading}
      searchError={controller.searchError}
      searchResults={controller.searchResults}
      mapSearchResultsDisabled={controller.mapSearchResultsDisabled}
      onboardingOrigins={controller.onboardingOrigins}
      loading={controller.loading}
      metadataLoading={controller.metadataLoading}
      error={controller.error}
      toast={controller.toast}
      showInspectDock={controller.showInspectDock}
      inspectCard={controller.inspectCard}
      addModeBlocked={controller.addModeBlocked}
      pathLoading={controller.pathLoading}
      origins={controller.origins}
      pathError={controller.pathError}
      pathByOriginId={controller.pathByOriginId}
      onSelectCity={controller.onSelectCity}
      onSelectAddressResult={controller.onSelectAddressResult}
      onRemoveOnboardingOrigin={controller.onRemoveOnboardingOrigin}
      onConfirmOnboarding={controller.onConfirmOnboarding}
      onCloseOnboarding={controller.onCloseOnboarding}
      onStartAddOriginMode={controller.onStartAddOriginMode}
      onCancelAddOriginMode={controller.onCancelAddOriginMode}
      onClearSelection={controller.onClearSelection}
      onRemoveOrigin={controller.onRemoveOrigin}
    />
  );
}
