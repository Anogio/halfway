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
  searchResults: GeocodeResult[];
  minChars: number;
  onSelectAddressResult: (result: GeocodeResult) => void;
  onboardingOrigins: OnboardingOrigin[];
  maxOrigins: number;
  onRemoveOnboardingOrigin: (originId: string) => void;
  onConfirmOnboarding: () => void;
  confirmDisabled: boolean;
  onClose: () => void;
};

export default function OnboardingOverlay({
  searchQuery,
  setSearchQuery,
  searchOpen,
  setSearchOpen,
  searchLoading,
  searchError,
  searchResults,
  minChars,
  onSelectAddressResult,
  onboardingOrigins,
  maxOrigins,
  onRemoveOnboardingOrigin,
  onConfirmOnboarding,
  confirmDisabled,
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
      <div className="onboarding-card">
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
                  >
                    {messages.onboarding.removeButton}
                  </button>
                </li>
              );
            })}
          </ul>
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
      </div>
    </section>
  );
}
