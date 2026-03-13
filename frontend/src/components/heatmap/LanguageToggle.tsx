"use client";

import { useEffect, useRef, useState } from "react";

import { useI18n } from "@/i18n/useI18n";
import type { Locale } from "@/i18n/types";

const LANGUAGE_OPTIONS: Locale[] = ["en", "fr"];

export default function LanguageToggle() {
  const { locale, setLocale, messages } = useI18n();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

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
    <div className="language-switcher" ref={rootRef}>
      <button
        type="button"
        className="language-switcher-toggle"
        aria-label={messages.language.toggleAriaLabel}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        data-testid="language-toggle-button"
      >
        <span aria-hidden="true">{locale.toUpperCase()}</span>
        <span className="sr-only">{messages.language.currentLocaleLabel(locale)}</span>
      </button>

      {open && (
        <div className="language-switcher-menu" role="menu" aria-label={messages.language.menuAriaLabel}>
          {LANGUAGE_OPTIONS.map((option) => {
            const isSelected = option === locale;
            const optionLabel = option === "fr" ? messages.language.french : messages.language.english;

            return (
              <button
                key={option}
                type="button"
                role="menuitemradio"
                aria-checked={isSelected}
                className={`language-switcher-option${isSelected ? " selected" : ""}`}
                onClick={() => {
                  setLocale(option);
                  setOpen(false);
                }}
                data-testid={`language-option-${option}`}
              >
                {optionLabel}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
