"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { DEFAULT_LOCALE, LOCALE_COOKIE_KEY, LOCALE_STORAGE_KEY, resolveLocale } from "@/i18n/config";
import { enMessages } from "@/i18n/messages/en";
import { frMessages } from "@/i18n/messages/fr";
import type { Locale, Messages } from "@/i18n/types";

const LOCALES: Locale[] = ["en", "fr"];

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  messages: Messages;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({
  children,
  initialLocale
}: {
  children: ReactNode;
  initialLocale: Locale;
}) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);
  const messages = useMemo(() => (locale === "fr" ? frMessages : enMessages), [locale]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    document.cookie = `${LOCALE_COOKIE_KEY}=${locale}; path=/; max-age=31536000; samesite=lax`;
    document.documentElement.lang = locale;
    document.title = messages.app.title;
  }, [locale, messages]);

  const setLocale = useCallback((nextLocale: Locale) => {
    if (!LOCALES.includes(nextLocale)) {
      return;
    }
    const normalizedLocale = resolveLocale(nextLocale) ?? DEFAULT_LOCALE;
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("lang", normalizedLocale);
      window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
    }
    setLocaleState(normalizedLocale);
  }, []);

  const value = useMemo<I18nContextValue>(() => ({ locale, setLocale, messages }), [locale, messages, setLocale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18nContext(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18nContext must be used within I18nProvider");
  }
  return context;
}
