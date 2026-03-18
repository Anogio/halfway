import type { MutableRefObject } from "react";

import type { CityMetadata, GeocodeResult, MultiPathItemResponse } from "@/lib/api";
import CityGateOverlay from "@/components/heatmap/CityGateOverlay";
import CityToggle from "@/components/heatmap/CityToggle";
import MapSearchBar from "@/components/heatmap/MapSearchBar";
import LanguageToggle from "@/components/heatmap/LanguageToggle";
import OnboardingOverlay from "@/components/heatmap/OnboardingOverlay";
import InspectDock from "@/components/heatmap/InspectDock";
import { MAX_ORIGINS, SEARCH_MIN_CHARS } from "@/components/heatmap/constants";
import type { CursorPosition, InspectCardState, OnboardingOrigin, OriginPoint, ToastState } from "@/components/heatmap/types";
import { useI18n } from "@/i18n/useI18n";

type HeatmapViewFrameProps = {
  mapRef: MutableRefObject<HTMLDivElement | null>;
  cities: CityMetadata[];
  activeCityId: string | null;
  onboardingOpen: boolean;
  citySelectionRequired: boolean;
  addModeActive: boolean;
  showCursorCrosshair: boolean;
  cursorPosition: CursorPosition | null;
  searchQuery: string;
  setSearchQuery: (value: string) => void;
  searchOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  searchLoading: boolean;
  searchError: string | null;
  searchResults: GeocodeResult[];
  mapSearchResultsDisabled: boolean;
  onboardingOrigins: OnboardingOrigin[];
  onboardingSubmitting: boolean;
  loading: boolean;
  metadataLoading: boolean;
  error: string | null;
  toast: ToastState | null;
  showInspectDock: boolean;
  inspectCard: InspectCardState | null;
  addModeBlocked: boolean;
  pathLoading: boolean;
  origins: OriginPoint[];
  pathError: string | null;
  pathByOriginId: Record<string, MultiPathItemResponse | null>;
  onSelectCity: (cityId: string) => void;
  onSelectAddressResult: (result: GeocodeResult) => Promise<void>;
  onRemoveOnboardingOrigin: (originId: string) => void;
  onConfirmOnboarding: () => Promise<void>;
  onCloseOnboarding: () => void;
  onStartAddOriginMode: () => void;
  onCancelAddOriginMode: () => void;
  onClearSelection: () => void;
  onRemoveOrigin: (originId: string) => Promise<void>;
};

export default function HeatmapViewFrame({
  mapRef,
  cities,
  activeCityId,
  onboardingOpen,
  citySelectionRequired,
  addModeActive,
  showCursorCrosshair,
  cursorPosition,
  searchQuery,
  setSearchQuery,
  searchOpen,
  setSearchOpen,
  searchLoading,
  searchError,
  searchResults,
  mapSearchResultsDisabled,
  onboardingOrigins,
  onboardingSubmitting,
  loading,
  metadataLoading,
  error,
  toast,
  showInspectDock,
  inspectCard,
  addModeBlocked,
  pathLoading,
  origins,
  pathError,
  pathByOriginId,
  onSelectCity,
  onSelectAddressResult,
  onRemoveOnboardingOrigin,
  onConfirmOnboarding,
  onCloseOnboarding,
  onStartAddOriginMode,
  onCancelAddOriginMode,
  onClearSelection,
  onRemoveOrigin
}: HeatmapViewFrameProps) {
  const { messages } = useI18n();

  return (
    <main
      className={`map-app${onboardingOpen ? " onboarding-active" : ""}${addModeActive ? " add-origin-pending" : ""}`}
    >
      <div className="top-right-controls">
        {!onboardingOpen && !citySelectionRequired && (
          <CityToggle cities={cities} activeCityId={activeCityId} onSelectCity={onSelectCity} />
        )}
        <LanguageToggle />
      </div>
      <div
        ref={mapRef}
        className="map-canvas-full"
        role="img"
        aria-label={messages.map.canvasAriaLabel}
      />
      {showCursorCrosshair && cursorPosition && (
        <div className="add-origin-crosshair" aria-hidden="true">
          <span className="add-origin-crosshair-line horizontal" style={{ top: `${cursorPosition.y}px` }} />
          <span className="add-origin-crosshair-line vertical" style={{ left: `${cursorPosition.x}px` }} />
        </div>
      )}

      {citySelectionRequired ? (
        <CityGateOverlay cities={cities} loading={loading || metadataLoading} onSelectCity={onSelectCity} />
      ) : onboardingOpen ? (
        <OnboardingOverlay
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          searchOpen={searchOpen}
          setSearchOpen={setSearchOpen}
          searchLoading={searchLoading}
          searchError={searchError}
          error={error}
          searchResults={searchResults}
          minChars={SEARCH_MIN_CHARS}
          onSelectAddressResult={(result) => void onSelectAddressResult(result)}
          onboardingOrigins={onboardingOrigins}
          maxOrigins={MAX_ORIGINS}
          onRemoveOnboardingOrigin={onRemoveOnboardingOrigin}
          onConfirmOnboarding={() => void onConfirmOnboarding()}
          confirmDisabled={onboardingOrigins.length === 0 || onboardingSubmitting || loading || metadataLoading}
          loading={onboardingSubmitting}
          onClose={onCloseOnboarding}
        />
      ) : (
        <div className="map-search-panel">
          <MapSearchBar
            containerClassName="map-search"
            query={searchQuery}
            setQuery={setSearchQuery}
            open={searchOpen}
            setOpen={setSearchOpen}
            loading={searchLoading}
            error={searchError}
            results={searchResults}
            minChars={SEARCH_MIN_CHARS}
            onSelectResult={(result) => void onSelectAddressResult(result)}
            resultsDisabled={mapSearchResultsDisabled}
          />
          <div className="map-search-actions">
            <button
              type="button"
              className={`map-search-action${addModeActive ? " secondary" : ""}`}
              onClick={addModeActive ? onCancelAddOriginMode : onStartAddOriginMode}
              disabled={addModeActive ? false : addModeBlocked}
            >
              {addModeActive ? messages.inspect.cancelPointPlacement : messages.inspect.addStartingPoint}
            </button>
            <button
              type="button"
              className="map-search-action secondary"
              onClick={onClearSelection}
              disabled={origins.length === 0 || loading || pathLoading}
            >
              {messages.inspect.clearSelection}
            </button>
          </div>
        </div>
      )}

      {loading && !onboardingOpen && !citySelectionRequired && (
        <div className="map-loading-indicator" role="status" aria-live="polite">
          <div className="map-loading-indicator-chip">
            <span className="app-loading-spinner" aria-hidden="true" />
            <span>{messages.map.loadingHeatmap}</span>
          </div>
        </div>
      )}

      {error && (
        <div className="inline-error" role="alert">
          {error}
        </div>
      )}

      {toast && (
        <div className={`toast toast-${toast.kind}`} role="status" aria-live="polite" data-testid="app-toast">
          {toast.text}
        </div>
      )}

      {showInspectDock && (
        <InspectDock
          inspectCard={inspectCard}
          addModeActive={addModeActive}
          loading={loading}
          pathLoading={pathLoading}
          origins={origins}
          pathError={pathError}
          pathByOriginId={pathByOriginId}
          onRemoveOrigin={(originId) => {
            void onRemoveOrigin(originId);
          }}
        />
      )}
    </main>
  );
}
