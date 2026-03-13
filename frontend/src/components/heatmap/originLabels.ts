import type { OriginPoint } from "@/components/heatmap/types";

const INTERNAL_ORIGIN_LABEL_RE = /^origin-\d+$/i;

export function isInternalOriginLabel(label: string): boolean {
  return INTERNAL_ORIGIN_LABEL_RE.test(label);
}

export function shouldHideOriginLabel(origin: Pick<OriginPoint, "label" | "labelPending">): boolean {
  return Boolean(origin.labelPending) || isInternalOriginLabel(origin.label);
}
