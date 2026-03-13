import Image from "next/image";

import type { CityMetadata } from "@/lib/api";
import { useI18n } from "@/i18n/useI18n";
import { getCityDisplay } from "@/lib/cities";

type CityGateOverlayProps = {
  cities: CityMetadata[];
  loading: boolean;
  onSelectCity: (cityId: string) => void;
};

export default function CityGateOverlay({ cities, loading, onSelectCity }: CityGateOverlayProps) {
  const { messages } = useI18n();
  const cityLoadingPlaceholders = Array.from({ length: 3 }, (_, index) => index);

  return (
    <section
      className="city-gate-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={messages.city.gateDialogAriaLabel}
    >
      <div className={`city-gate-card${loading ? " is-loading" : ""}`} aria-busy={loading}>
        <div className="city-gate-intro">
          <div className="city-gate-brand">
            <Image
              src="/logo-mark.svg"
              alt=""
              className="city-gate-brand-mark"
              aria-hidden="true"
              width={46}
              height={46}
            />
            <div className="city-gate-title-group">
              <p className="city-gate-eyebrow">{messages.city.gateEyebrow}</p>
              <h1 className="city-gate-title">{messages.city.gateTitle}</h1>
            </div>
          </div>
          <p className="city-gate-description">{messages.city.gateDescription}</p>
        </div>

        {loading ? (
          <div className="city-gate-loading" role="status" aria-live="polite">
            <div className="city-gate-loading-head">
              <span className="city-gate-loading-dot" aria-hidden="true" />
              <p className="city-gate-loading-text">{messages.city.gateLoading}</p>
            </div>
            <div className="city-gate-skeleton-list" aria-hidden="true">
              {cityLoadingPlaceholders.map((placeholder) => (
                <div key={placeholder} className="city-gate-skeleton-option" />
              ))}
            </div>
          </div>
        ) : (
          <div className="city-gate-options" role="group" aria-label={messages.city.gateOptionsAriaLabel}>
            {cities.map((city) => {
              const cityDisplay = getCityDisplay(city, messages);
              return (
                <button
                  key={city.id}
                  type="button"
                  className="city-gate-option"
                  onClick={() => onSelectCity(city.id)}
                  disabled={loading}
                  data-testid={`city-gate-option-${city.id}`}
                >
                  <span className="city-display-label">
                    <span className="city-display-flag" aria-hidden="true">
                      {cityDisplay.flag}
                    </span>
                    <span>{cityDisplay.name}</span>
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
