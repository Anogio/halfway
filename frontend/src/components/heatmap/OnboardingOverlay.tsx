import Image from "next/image";

import type { GeocodeResult } from "@/lib/api";

import { isInternalOriginLabel } from "@/components/heatmap/originLabels";
import type { OnboardingOrigin } from "@/components/heatmap/types";
import MapSearchBar from "@/components/heatmap/MapSearchBar";
import { useI18n } from "@/i18n/useI18n";

type OnboardingOverlayProps = {
  searchQuery: string;
  setSearchQuery: (value: string) => void;
  searchOpen: boolean;
  setSearchOpen: (value: boolean) => void;
  searchLoading: boolean;
  searchError: string | null;
  error: string | null;
  searchResults: GeocodeResult[];
  minChars: number;
  onSelectAddressResult: (result: GeocodeResult) => void;
  onboardingOrigins: OnboardingOrigin[];
  maxOrigins: number;
  onRemoveOnboardingOrigin: (originId: string) => void;
  onConfirmOnboarding: () => void;
  confirmDisabled: boolean;
  loading: boolean;
  onClose: () => void;
};

export default function OnboardingOverlay({
  searchQuery,
  setSearchQuery,
  searchOpen,
  setSearchOpen,
  searchLoading,
  searchError,
  error,
  searchResults,
  minChars,
  onSelectAddressResult,
  onboardingOrigins,
  maxOrigins,
  onRemoveOnboardingOrigin,
  onConfirmOnboarding,
  confirmDisabled,
  loading,
  onClose
}: OnboardingOverlayProps) {
  const { messages } = useI18n();

  return (
    <section
      className="onboarding-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={messages.onboarding.dialogAriaLabel}
    >
      <div className={`onboarding-card${loading ? " is-loading" : ""}`} aria-busy={loading}>
        <div className="onboarding-header">
          <div className="onboarding-brand">
            <Image
              src="/logo-mark.svg"
              alt=""
              className="onboarding-brand-mark"
              aria-hidden="true"
              width={50}
              height={50}
            />
            <h1 className="onboarding-title">{messages.onboarding.title}</h1>
          </div>
          <button
            type="button"
            className="onboarding-close"
            onClick={onClose}
            aria-label={messages.onboarding.closeAriaLabel}
            disabled={loading}
          >
            ×
          </button>
        </div>
        <p className="onboarding-description">{messages.onboarding.description}</p>

        <MapSearchBar
          containerClassName="onboarding-search"
          query={searchQuery}
          setQuery={setSearchQuery}
          open={searchOpen}
          setOpen={setSearchOpen}
          loading={searchLoading}
          error={searchError}
          results={searchResults}
          minChars={minChars}
          onSelectResult={onSelectAddressResult}
          resultsDisabled={onboardingOrigins.length >= maxOrigins}
          disabled={loading}
        />

        <p className="onboarding-origin-count">{messages.onboarding.selectedPoints(onboardingOrigins.length, maxOrigins)}</p>

        {onboardingOrigins.length === 0 ? (
          <p className="onboarding-empty">{messages.onboarding.noPointSelectedYet}</p>
        ) : (
          <ul className="onboarding-origin-list" aria-label={messages.onboarding.selectedStartingPointsAriaLabel}>
            {onboardingOrigins.map((origin) => {
              const displayLabel = isInternalOriginLabel(origin.label) ? messages.status.selectedPoint : origin.label;

              return (
                <li key={origin.id} className="onboarding-origin-item">
                  <span className="onboarding-origin-label">{displayLabel}</span>
                  <button
                    type="button"
                    className="onboarding-origin-remove"
                    onClick={() => onRemoveOnboardingOrigin(origin.id)}
                    aria-label={messages.onboarding.removeOriginAriaLabel(displayLabel)}
                    disabled={loading}
                  >
                    {messages.onboarding.removeButton}
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {error && !loading && (
          <div className="onboarding-error" role="alert">
            {error}
          </div>
        )}

        <div className="onboarding-actions">
          <button
            type="button"
            className="onboarding-confirm"
            onClick={onConfirmOnboarding}
            disabled={confirmDisabled}
          >
            {messages.onboarding.confirmAndStartMap}
          </button>
        </div>

        {loading && (
          <div className="onboarding-loading-veil" role="status" aria-live="polite">
            <div className="onboarding-loading-panel">
              <span className="app-loading-spinner" aria-hidden="true" />
              <p className="onboarding-loading-title">{messages.onboarding.loadingTitle}</p>
              <p className="onboarding-loading-description">{messages.onboarding.loadingDescription}</p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
