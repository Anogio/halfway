import { useEffect, useId, useState } from "react";

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
  const detailsIdBase = useId();
  const [expandedOriginId, setExpandedOriginId] = useState<string | null>(null);
  const isCompactDock = origins.length <= 1;
  const canSwitchDetails = Boolean(inspectCard && origins.length > 1);

  useEffect(() => {
    if (!inspectCard || origins.length === 0) {
      setExpandedOriginId(null);
      return;
    }

    setExpandedOriginId((current) => {
      if (origins.length === 1) {
        return origins[0]?.id ?? null;
      }

      if (current && origins.some((origin) => origin.id === current)) {
        return current;
      }

      return origins[0]?.id ?? null;
    });
  }, [inspectCard, origins]);

  return (
    <section
      className={`inspect-card inspect-fixed${isCompactDock ? " is-compact" : ""}${origins.length === 0 ? " is-empty" : ""}${origins.length > 1 ? " has-multiple-origins" : ""}`}
      role="complementary"
      aria-label={messages.inspect.sectionAriaLabel}
    >
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
              const detailsId = `${detailsIdBase}-${origin.id}`;
              const displayLabel = origin.labelPending
                ? messages.status.loadingAddress
                : isInternalOriginLabel(origin.label)
                  ? messages.status.selectedPoint
                  : origin.label;
              const showDetails = Boolean(
                inspectCard && (canSwitchDetails ? expandedOriginId === origin.id : true)
              );
              const pathSummary =
                pathData && pathData.reachable
                  ? formatDuration(Number(pathData.summary.total_time_s ?? 0), messages.presentation.duration)
                  : pathData
                    ? messages.inspect.noPath
                    : null;

              return (
                <article
                  key={origin.id}
                  className={`origin-item${showDetails ? " is-expanded" : ""}${inspectCard && !showDetails ? " is-collapsed" : ""}`}
                >
                  <div className="origin-item-header">
                    {canSwitchDetails && !showDetails ? (
                      <button
                        type="button"
                        className={`origin-summary-btn${origin.labelPending ? " pending" : ""}`}
                        onClick={() => setExpandedOriginId(origin.id)}
                        aria-expanded="false"
                        aria-controls={detailsId}
                        aria-label={messages.inspect.showPathDetailsAriaLabel(displayLabel)}
                      >
                        <span className="origin-item-summary">
                          <span className="origin-swatch" style={{ backgroundColor: origin.color }} />
                          <span className="origin-item-main">
                            <span className={`origin-item-title${origin.labelPending ? " pending" : ""}`}>{displayLabel}</span>
                            {pathSummary && <span className="origin-item-travel-time">{pathSummary}</span>}
                          </span>
                        </span>
                        <span className="origin-chevron" aria-hidden="true">
                          ›
                        </span>
                      </button>
                    ) : (
                      <div
                        className={`origin-summary-btn is-static${origin.labelPending ? " pending" : ""}`}
                        {...(inspectCard ? { "aria-expanded": showDetails, "aria-controls": detailsId } : {})}
                      >
                        <span className="origin-item-summary">
                          <span className="origin-swatch" style={{ backgroundColor: origin.color }} />
                          <span className="origin-item-main">
                            <span className={`origin-item-title${origin.labelPending ? " pending" : ""}`}>{displayLabel}</span>
                            {pathSummary && <span className="origin-item-travel-time">{pathSummary}</span>}
                          </span>
                        </span>
                        {canSwitchDetails && (
                          <span className="origin-chevron expanded" aria-hidden="true">
                            ‹
                          </span>
                        )}
                      </div>
                    )}
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

                  {showDetails && (
                    <div
                      id={detailsId}
                      className="inspect-path-details"
                      aria-label={messages.inspect.pathDetailsAriaLabel(displayLabel)}
                    >
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
