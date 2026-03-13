"use client";

import { useEffect } from "react";

const VIEWPORT_HEIGHT_CSS_VAR = "--app-viewport-height";

export function useViewportHeightCssVar() {
  useEffect(() => {
    const root = document.documentElement;

    const updateViewportHeight = () => {
      const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
      root.style.setProperty(VIEWPORT_HEIGHT_CSS_VAR, `${Math.round(viewportHeight)}px`);
    };

    updateViewportHeight();

    window.addEventListener("resize", updateViewportHeight);
    window.visualViewport?.addEventListener("resize", updateViewportHeight);
    window.visualViewport?.addEventListener("scroll", updateViewportHeight);

    return () => {
      window.removeEventListener("resize", updateViewportHeight);
      window.visualViewport?.removeEventListener("resize", updateViewportHeight);
      window.visualViewport?.removeEventListener("scroll", updateViewportHeight);
      root.style.removeProperty(VIEWPORT_HEIGHT_CSS_VAR);
    };
  }, []);
}
