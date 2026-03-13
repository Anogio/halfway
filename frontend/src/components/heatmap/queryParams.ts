function readQueryParam(name: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const params = new URLSearchParams(window.location.search);
  const value = params.get(name);
  if (value == null) {
    return null;
  }
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

export function isOnboardingSkippedByQuery(): boolean {
  return readQueryParam("skipOnboarding") === "1";
}

export function getCityPresetFromQuery(): string | null {
  return readQueryParam("city");
}

