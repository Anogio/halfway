import type { MultiPathItemResponse } from "@/lib/api";

export type InspectCardState = {
  lat: number;
  lon: number;
  minS: number | null;
  maxS: number | null;
};

export type OriginPoint = {
  id: string;
  label: string;
  labelPending?: boolean;
  lat: number;
  lon: number;
  color: string;
};

export type OnboardingOrigin = {
  id: string;
  label: string;
  lat: number;
  lon: number;
};

export type ToastState = {
  kind: "error";
  text: string;
};

export type CursorPosition = {
  x: number;
  y: number;
};

export type PathByOriginId = Record<string, MultiPathItemResponse | null>;
