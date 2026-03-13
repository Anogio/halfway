import type { Locale } from "@/i18n/types";

export const DEFAULT_LOCALE: Locale = "en";
export const LOCALE_STORAGE_KEY = "commute.locale";
export const LOCALE_COOKIE_KEY = "commute.locale";

export function resolveLocale(value: string | null | undefined): Locale | null {
  if (!value) {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  if (normalized.startsWith("fr")) {
    return "fr";
  }
  if (normalized.startsWith("en")) {
    return "en";
  }
  return null;
}
