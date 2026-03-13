"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { CityMetadata } from "@/lib/api";
import { useI18n } from "@/i18n/useI18n";
import { getCityDisplay } from "@/lib/cities";

type CityToggleProps = {
  cities: CityMetadata[];
  activeCityId: string | null;
  onSelectCity: (cityId: string) => void;
};

export default function CityToggle({ cities, activeCityId, onSelectCity }: CityToggleProps) {
  const { messages } = useI18n();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  const activeCity = useMemo(
    () => (activeCityId ? cities.find((city) => city.id === activeCityId) ?? null : null),
    [activeCityId, cities]
  );
  const activeCityDisplay = activeCity ? getCityDisplay(activeCity, messages) : null;

  useEffect(() => {
    if (!open) {
      return;
    }

    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    window.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div className="city-switcher" ref={rootRef}>
      <button
        type="button"
        className="city-switcher-toggle"
        aria-label={messages.city.toggleAriaLabel}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        disabled={cities.length === 0}
        data-testid="city-toggle-button"
      >
        <span className="city-display-label">
          {activeCityDisplay ? (
            <>
              <span className="city-display-flag" aria-hidden="true">
                {activeCityDisplay.flag}
              </span>
              <span>{activeCityDisplay.name}</span>
            </>
          ) : (
            messages.city.unselectedLabel
          )}
        </span>
        <span className="sr-only">
          {messages.city.currentCityLabel(activeCityDisplay?.name ?? messages.city.unselectedLabel)}
        </span>
      </button>

      {open && (
        <div className="city-switcher-menu" role="menu" aria-label={messages.city.menuAriaLabel}>
          {cities.map((city) => {
            const isSelected = city.id === activeCityId;
            const cityDisplay = getCityDisplay(city, messages);
            return (
              <button
                key={city.id}
                type="button"
                role="menuitemradio"
                aria-checked={isSelected}
                className={`city-switcher-option${isSelected ? " selected" : ""}`}
                onClick={() => {
                  onSelectCity(city.id);
                  setOpen(false);
                }}
                data-testid={`city-option-${city.id}`}
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
  );
}
