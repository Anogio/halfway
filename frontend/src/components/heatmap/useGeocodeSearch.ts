import { useEffect, useRef, useState } from "react";

import { fetchGeocode, type GeocodeResult } from "@/lib/api";
import { useI18n } from "@/i18n/useI18n";

export type GeocodeSearchState = {
  searchQuery: string;
  setSearchQuery: (value: string) => void;
  searchResults: GeocodeResult[];
  searchLoading: boolean;
  searchError: string | null;
  searchOpen: boolean;
  setSearchOpen: (value: boolean) => void;
  resetSearch: () => void;
};

export function useGeocodeSearch(activeCityId: string | null, minChars: number): GeocodeSearchState {
  const { messages } = useI18n();
  const geocodeRequestSeqRef = useRef(0);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<GeocodeResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);

  function resetSearch() {
    geocodeRequestSeqRef.current += 1;
    setSearchQuery("");
    setSearchLoading(false);
    setSearchError(null);
    setSearchResults([]);
    setSearchOpen(false);
  }

  useEffect(() => {
    if (!activeCityId) {
      geocodeRequestSeqRef.current += 1;
      setSearchLoading(false);
      setSearchError(null);
      setSearchResults([]);
      return;
    }

    const trimmedQuery = searchQuery.trim();
    if (trimmedQuery.length < minChars) {
      geocodeRequestSeqRef.current += 1;
      setSearchLoading(false);
      setSearchError(null);
      setSearchResults([]);
      return;
    }

    const requestSeq = geocodeRequestSeqRef.current + 1;
    geocodeRequestSeqRef.current = requestSeq;
    setSearchLoading(true);
    setSearchError(null);

    const timer = setTimeout(() => {
      void (async () => {
        try {
          const results = await fetchGeocode(activeCityId, trimmedQuery);
          if (geocodeRequestSeqRef.current !== requestSeq) {
            return;
          }
          setSearchResults(results);
          setSearchOpen(true);
        } catch (err) {
          if (geocodeRequestSeqRef.current !== requestSeq) {
            return;
          }
          const message = err instanceof Error ? err.message : messages.errors.unknownError;
          setSearchError(messages.errors.addressSearchFailed(message));
          setSearchResults([]);
        } finally {
          if (geocodeRequestSeqRef.current === requestSeq) {
            setSearchLoading(false);
          }
        }
      })();
    }, 300);

    return () => clearTimeout(timer);
  }, [activeCityId, messages.errors, minChars, searchQuery]);

  return {
    searchQuery,
    setSearchQuery,
    searchResults,
    searchLoading,
    searchError,
    searchOpen,
    setSearchOpen,
    resetSearch
  };
}
