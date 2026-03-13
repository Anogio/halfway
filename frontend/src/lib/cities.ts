import type { CityMetadata } from "@/lib/api";
import type { Messages } from "@/i18n/types";

export type CityDisplay = {
  flag: string;
  name: string;
};

export function getCityDisplay(city: CityMetadata, messages: Messages): CityDisplay {
  return {
    flag: countryCodeToFlag(city.country_code),
    name: messages.city.localizedName(city.id),
  };
}

function countryCodeToFlag(countryCode: string): string {
  const normalizedCountryCode = countryCode.trim().toUpperCase();
  if (!/^[A-Z]{2}$/.test(normalizedCountryCode)) {
    return "";
  }

  return String.fromCodePoint(
    ...normalizedCountryCode.split("").map((letter) => 127397 + letter.charCodeAt(0))
  );
}
