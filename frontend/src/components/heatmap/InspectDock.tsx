import type { MultiPathItemResponse } from "@/lib/api";

import {
  buildDisplayPathSteps,
  formatDuration
} from "@/lib/heatmapPresentation.mjs";
import { isInternalOriginLabel } from "@/components/heatmap/originLabels";
import type { InspectCardState, OriginPoint } from "@/components/heatmap/types";
import { useI18n } from "@/i18n/useI18n";

type InspectDockProps = {
  inspectCard: InspectCardState | null;
  addModeActive: boolean;
  loading: boolean;
  pathLoading: boolean;
  origins: OriginPoint[];
  pathError: string | null;
  pathByOriginId: Record<string, MultiPathItemResponse | null>;
  onRemoveOrigin: (originId: string) => void;
};

export default function InspectDock({
  inspectCard,
  addModeActive,
  loading,
  pathLoading,
  origins,
  pathError,
  pathByOriginId,
  onRemoveOrigin
}: InspectDockProps) {
  const { messages } = useI18n();

  return (
    <section className="inspect-card inspect-fixed" role="complementary" aria-label={messages.inspect.sectionAriaLabel}>
      <div className="inspect-header">
        <h2 className="inspect-title">{messages.inspect.pointsHeading}</h2>
        {origins.length > 0 && <span className="inspect-count">{origins.length}</span>}
      </div>

      {addModeActive && (
        <p className="inspect-add-mode-hint">{messages.inspect.addModeHint}</p>
      )}

      {pathLoading && inspectCard && origins.length > 0 && (
        <p className="inspect-path-loading">{messages.inspect.computingPaths}</p>
      )}
      {pathError && (
        <p className="inspect-path-error">
          {messages.inspect.pathErrorPrefix}: {pathError}
        </p>
      )}

      {origins.length === 0 ? (
        <div className="inspect-empty-state">
          <p>{messages.inspect.emptyState}</p>
        </div>
      ) : (
        <>
          {!inspectCard && <p className="inspect-selection-hint">{messages.inspect.selectDestinationToComputePaths}</p>}
          <div className="origin-list" aria-label={messages.inspect.pointPathsListAriaLabel}>
            {origins.map((origin) => {
              const pathData = pathByOriginId[origin.id];
              const displayLabel = origin.labelPending
                ? messages.status.loadingAddress
                : isInternalOriginLabel(origin.label)
                  ? messages.status.selectedPoint
                  : origin.label;
              const pathSummary =
                pathData && pathData.reachable
                  ? formatDuration(Number(pathData.summary.total_time_s ?? 0), messages.presentation.duration)
                  : pathData
                    ? messages.inspect.noPath
                    : null;

              return (
                <article key={origin.id} className="origin-item">
                  <div className="origin-item-header">
                    <div className={`origin-item-summary${origin.labelPending ? " pending" : ""}`}>
                      <span className="origin-swatch" style={{ backgroundColor: origin.color }} />
                      <div className="origin-item-main">
                        <span className={`origin-item-title${origin.labelPending ? " pending" : ""}`}>{displayLabel}</span>
                        {pathSummary && <span className="origin-item-travel-time">{pathSummary}</span>}
                      </div>
                    </div>
                    <button
                      type="button"
                      className="origin-remove-btn"
                      aria-label={messages.inspect.removeOriginAriaLabel(displayLabel)}
                      onClick={() => onRemoveOrigin(origin.id)}
                      disabled={loading}
                    >
                      ×
                    </button>
                  </div>

                  {inspectCard && (
                    <div className="inspect-path-details" aria-label={messages.inspect.pathDetailsAriaLabel(displayLabel)}>
                      {!pathData ? (
                        <p>{messages.inspect.pathNotComputedYet}</p>
                      ) : pathData.reachable ? (
                        <>
                          <p>
                            {messages.inspect.pathTotalLabel}:{" "}
                            <strong>
                              {formatDuration(Number(pathData.summary.total_time_s ?? 0), messages.presentation.duration)}
                            </strong>
                          </p>
                          <ul>
                            {buildDisplayPathSteps(pathData, messages.presentation).map((step) => (
                              <li key={step.key}>
                                <span>{step.text}</span>
                              </li>
                            ))}
                          </ul>
                        </>
                      ) : (
                        <p>
                          <strong>{messages.inspect.noPathWithinMaxTime}</strong>
                        </p>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}
