import { expect, test } from "@playwright/test";

const ENGLISH_APP_ROUTE = "/?skipOnboarding=1&lang=en&city=paris_fr";
const ENGLISH_ROUTE_NO_CITY = "/?lang=en";

test.describe("Halfway app", () => {
  test("keeps the document pinned to the viewport through mobile onboarding", async ({ page }) => {
    await page.goto(ENGLISH_ROUTE_NO_CITY);

    await expect(page.getByRole("dialog", { name: "Choose your city" })).toBeVisible();

    const cityGateMetrics = await page.evaluate(() => {
      const scrollingElement = document.scrollingElement;
      const cityGateCard = document.querySelector(".city-gate-card")?.getBoundingClientRect();
      return {
        innerHeight: window.innerHeight,
        scrollHeight: scrollingElement?.scrollHeight ?? 0,
        cityGateTop: cityGateCard?.top ?? null,
        cityGateBottom: cityGateCard?.bottom ?? null
      };
    });

    expect(cityGateMetrics.scrollHeight).toBeLessThanOrEqual(cityGateMetrics.innerHeight + 1);
    expect(cityGateMetrics.cityGateTop).not.toBeNull();
    expect(cityGateMetrics.cityGateBottom).not.toBeNull();
    expect(cityGateMetrics.cityGateTop!).toBeGreaterThanOrEqual(0);
    expect(cityGateMetrics.cityGateBottom!).toBeLessThanOrEqual(cityGateMetrics.innerHeight);

    await page.getByTestId("city-gate-option-paris_fr").click();
    await expect(page.getByRole("dialog", { name: "Initialize meeting points" })).toBeVisible();

    const onboardingMetrics = await page.evaluate(() => {
      const scrollingElement = document.scrollingElement;
      const onboardingCard = document.querySelector(".onboarding-card")?.getBoundingClientRect();
      return {
        innerHeight: window.innerHeight,
        scrollHeight: scrollingElement?.scrollHeight ?? 0,
        onboardingTop: onboardingCard?.top ?? null,
        onboardingBottom: onboardingCard?.bottom ?? null
      };
    });

    expect(onboardingMetrics.scrollHeight).toBeLessThanOrEqual(onboardingMetrics.innerHeight + 1);
    expect(onboardingMetrics.onboardingTop).not.toBeNull();
    expect(onboardingMetrics.onboardingBottom).not.toBeNull();
    expect(onboardingMetrics.onboardingTop!).toBeGreaterThanOrEqual(0);
    expect(onboardingMetrics.onboardingBottom!).toBeLessThanOrEqual(onboardingMetrics.innerHeight);
  });

  test("shows city gate when no city preset is provided", async ({ page }) => {
    await page.goto(ENGLISH_ROUTE_NO_CITY);

    await expect(page.getByRole("dialog", { name: "Choose your city" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Halfway" })).toBeVisible();
    await expect(page.getByTestId("city-gate-option-paris_fr")).toBeVisible();
  });

  test("invalid city preset falls back to city gate", async ({ page }) => {
    await page.goto("/?skipOnboarding=1&lang=en&city=unknown");

    await expect(page.getByRole("dialog", { name: "Choose your city" })).toBeVisible();
    await expect(page.getByTestId("city-gate-option-paris_fr")).toBeVisible();
  });

  test("loads homepage with inspect dock and no controls panel", async ({ page }) => {
    await page.goto(ENGLISH_APP_ROUTE);

    await expect(page.getByLabel("Map controls")).toHaveCount(0);
    await expect(page.getByLabel("Heatmap legend")).toHaveCount(0);
    await expect(page.getByLabel("Map point details")).toHaveCount(1);
    await expect(page.getByTestId("city-toggle-button")).toBeVisible();
  });

  test("does not auto-compute heatmap before an origin is set", async ({ page }) => {
    await page.goto(ENGLISH_APP_ROUTE);

    await expect(page.getByText(/Isochrones updated\./i)).toHaveCount(0);

    const map = page.getByRole("img", { name: "Heatmap map with tiles and overlay" });
    await expect(map).toBeVisible();
    await expect(page.locator(".arrival-point-marker")).toHaveCount(0);
  });

  test("search-added points keep city in the label", async ({ page }) => {
    await page.route("**/geocode?*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          results: [
            {
              id: "rue-petit",
              label: "2 Rue Petit, Paris, France",
              lat: 48.89231,
              lon: 2.39127
            }
          ]
        })
      });
    });

    await page.goto(ENGLISH_APP_ROUTE);

    const searchInput = page.getByLabel("Add point by address");
    await searchInput.fill("rue petit");

    const option = page.getByRole("option", { name: "2 Rue Petit, Paris" });
    await expect(option).toBeVisible({ timeout: 10000 });
    await option.click();

    await expect(page.locator(".origin-item-title").first()).toHaveText("2 Rue Petit, Paris, France");
  });

  test("language toggle switches between English and French", async ({ page }) => {
    await page.goto(ENGLISH_APP_ROUTE);

    await expect(page.getByTestId("address-search-input")).toHaveAttribute("placeholder", "Add point by address");

    await page.getByTestId("language-toggle-button").click();
    await page.getByTestId("language-option-fr").click();

    await expect(page.getByTestId("address-search-input")).toHaveAttribute("placeholder", "Ajouter un point par adresse");
    await expect(page.locator("html")).toHaveAttribute("lang", "fr");

    await page.getByTestId("language-toggle-button").click();
    await page.getByTestId("language-option-en").click();

    await expect(page.getByTestId("address-search-input")).toHaveAttribute("placeholder", "Add point by address");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
  });

  test("refresh keeps French app name on screen and in the tab title", async ({ page }) => {
    await page.goto(ENGLISH_ROUTE_NO_CITY);

    await page.getByTestId("language-toggle-button").click();
    await page.getByTestId("language-option-fr").click();

    await expect(page.getByRole("heading", { name: "Halfway" })).toBeVisible();
    await expect(page).toHaveTitle("Halfway");

    await page.reload();

    await expect(page.getByRole("heading", { name: "Halfway" })).toBeVisible();
    await expect(page).toHaveTitle("Halfway");
  });
});
