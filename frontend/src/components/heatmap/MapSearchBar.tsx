import type { GeocodeResult } from "@/lib/api";
import { useI18n } from "@/i18n/useI18n";

type MapSearchBarProps = {
  containerClassName: string;
  query: string;
  setQuery: (value: string) => void;
  open: boolean;
  setOpen: (value: boolean) => void;
  loading: boolean;
  error: string | null;
  results: GeocodeResult[];
  minChars: number;
  onSelectResult: (result: GeocodeResult) => void;
  resultsDisabled: boolean;
  disabled?: boolean;
};

export default function MapSearchBar({
  containerClassName,
  query,
  setQuery,
  open,
  setOpen,
  loading,
  error,
  results,
  minChars,
  onSelectResult,
  resultsDisabled,
  disabled = false
}: MapSearchBarProps) {
  const { messages } = useI18n();

  return (
    <section className={containerClassName} role="search" aria-label={messages.search.sectionAriaLabel}>
      <input
        type="text"
        className="map-search-input"
        placeholder={messages.search.inputPlaceholder}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          setTimeout(() => setOpen(false), 120);
        }}
        aria-label={messages.search.inputAriaLabel}
        autoComplete="off"
        disabled={disabled}
        data-testid="address-search-input"
      />
      {open && (
        <div className="map-search-dropdown" role="listbox" aria-label={messages.search.suggestionsAriaLabel}>
          {loading && <p className="map-search-status">{messages.search.searchingAddresses}</p>}
          {error && !loading && <p className="map-search-error">{error}</p>}
          {!loading && !error && query.trim().length >= minChars && results.length === 0 && (
            <p className="map-search-status">{messages.search.noResultFound}</p>
          )}
          {!loading &&
            !error &&
            results.map((result) => {
              return (
                <button
                  key={result.id}
                  type="button"
                  className="map-search-option"
                  role="option"
                  aria-selected="false"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => onSelectResult(result)}
                  disabled={resultsDisabled || disabled}
                >
                  <span className="map-search-option-label">{result.label}</span>
                </button>
              );
            })}
        </div>
      )}
    </section>
  );
}
