import { expect, test } from "@playwright/test";

const PATH_STATUS_RE = /Path total:|No path found within current max-time cap.|Path error:/i;
const ENGLISH_APP_ROUTE = "/?skipOnboarding=1&lang=en&city=paris_fr";

async function expectPathStatusVisible(inspectDialog: import("@playwright/test").Locator) {
  const statusMatches = inspectDialog.getByText(PATH_STATUS_RE);
  await expect(statusMatches.first()).toBeVisible({ timeout: 15000 });
}

async function clickMapAt(
  page: import("@playwright/test").Page,
  xFactor: number,
  yFactor: number
) {
  await page.waitForFunction(() => {
    const map = (window as Window & { __transitMap?: { getSize?: () => { x: number; y: number } } }).__transitMap;
    if (!map || typeof map.getSize !== "function") {
      return false;
    }
    const size = map.getSize();
    return Number.isFinite(size.x) && Number.isFinite(size.y) && size.x > 0 && size.y > 0;
  });
  await page.evaluate(([xFactorValue, yFactorValue]) => {
    const map = (window as Window & { __transitMap?: any }).__transitMap;
    if (!map) {
      throw new Error("transit map not ready");
    }
    const size = map.getSize();
    const containerX = Math.round(size.x * xFactorValue);
    const containerY = Math.round(Math.max(90, size.y * yFactorValue));
    const latlng = map.containerPointToLatLng([containerX, containerY]);
    map.fire("click", { latlng });
  }, [xFactor, yFactor] as const);
}

async function clickMapInFreeArea(page: import("@playwright/test").Page) {
  await clickMapAt(page, 0.52, 0.22);
}

async function mockReverseGeocode(
  page: import("@playwright/test").Page,
  labels: string[] = ["2 Rue Petit, Paris"]
) {
  let callIndex = 0;
  await page.route("**/reverse_geocode?*", async (route) => {
    const label = labels[Math.min(callIndex, labels.length - 1)];
    callIndex += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ label })
    });
  });
}

function arrivalTooltip(page: import("@playwright/test").Page, label: string) {
  return page.locator(".maplibregl-popup.arrival-point-tooltip-popup").filter({ hasText: label }).first();
}

test.describe("Halfway map flows", () => {
  test("city selector switch resets state and reopens onboarding", async ({ page }) => {
    await page.route("**/metadata", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          cities: [
            {
              id: "paris",
              label: "Paris",
              default_view: [48.8566, 2.3522, 12],
              bbox: [1.149856, 47.961079, 3.560668, 49.459332]
            },
            {
              id: "london",
              label: "London",
              default_view: [51.5074, -0.1278, 11],
              bbox: [-0.5103, 51.2868, 0.334, 51.6923]
            }
          ]
        })
      });
    });
    await mockReverseGeocode(page);

    await page.goto("/?lang=en&city=paris");

    await page.getByRole("button", { name: "Close onboarding" }).click();
    const inspectDialog = page.getByLabel("Map point details");
    const addPointButton = page.getByRole("button", { name: "Add point by clicking" });
    await clickMapInFreeArea(page);
    await addPointButton.click();
    await clickMapInFreeArea(page);
    await expect(page.getByLabel("Point paths list")).toBeVisible();

    await page.getByTestId("city-toggle-button").click();
    await page.getByTestId("city-option-london").click();

    await expect(page.getByRole("dialog", { name: "Initialize meeting points" })).toBeVisible();
    await expect(page.getByLabel("Point paths list")).toHaveCount(0);
    await expect(page).toHaveURL(/city=paris/);
  });

  test("sends city on all backend spatial/geocoding calls", async ({ page }) => {
    const geocodeCities = new Set<string>();
    const reverseGeocodeCities = new Set<string>();
    const multiIsoCities = new Set<string>();
    const multiPathCities = new Set<string>();

    await page.route("**/geocode?*", async (route) => {
      const url = new URL(route.request().url());
      const city = url.searchParams.get("city");
      if (city) {
        geocodeCities.add(city);
      }
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

    await page.route("**/reverse_geocode?*", async (route) => {
      const url = new URL(route.request().url());
      const city = url.searchParams.get("city");
      if (city) {
        reverseGeocodeCities.add(city);
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ label: "2 Rue Petit, Paris" })
      });
    });

    await page.route("**/multi_isochrones", async (route) => {
      const body = route.request().postDataJSON() as { city?: unknown };
      if (typeof body.city === "string") {
        multiIsoCities.add(body.city);
      }
      await route.continue();
    });

    await page.route("**/multi_path", async (route) => {
      const body = route.request().postDataJSON() as { city?: unknown };
      if (typeof body.city === "string") {
        multiPathCities.add(body.city);
      }
      await route.continue();
    });

    await page.goto(ENGLISH_APP_ROUTE);

    const searchInput = page.getByLabel("Add point by address");
    await searchInput.fill("rue petit");
    const option = page.getByRole("option", { name: "2 Rue Petit, Paris" });
    await expect(option).toBeVisible({ timeout: 10000 });
    await option.click();
    await expect(page.getByLabel("Point paths list")).toBeVisible();

    await clickMapInFreeArea(page);
    const inspectDialog = page.getByLabel("Map point details");
    await expectPathStatusVisible(inspectDialog);

    expect([...geocodeCities].length).toBeGreaterThan(0);
    expect([...reverseGeocodeCities].length).toBeGreaterThan(0);
    expect([...multiIsoCities].length).toBeGreaterThan(0);
    expect([...multiPathCities].length).toBeGreaterThan(0);

    const expectedCity = [...geocodeCities][0];
    expect(expectedCity).toBeTruthy();
    expect([...geocodeCities]).toEqual([expectedCity]);
    expect([...reverseGeocodeCities]).toEqual([expectedCity]);
    expect([...multiIsoCities]).toEqual([expectedCity]);
    expect([...multiPathCities]).toEqual([expectedCity]);
  });

  test("clicking map shows destination tooltip and can add an origin", async ({ page }) => {
    await mockReverseGeocode(page, [
      "Destination Clicked, Paris",
      "2 Rue Petit, Paris",
      "Best Meeting Point, Paris"
    ]);
    await page.goto(ENGLISH_APP_ROUTE);

    await clickMapInFreeArea(page);

    const inspectDialog = page.getByLabel("Map point details");
    await expect(inspectDialog).toBeVisible();
    await expect(arrivalTooltip(page, "Destination Clicked, Paris")).toBeVisible();
    await expect(page.locator(".inspect-origin-quick-action-btn")).toHaveCount(0);
    await expect(inspectDialog.getByRole("button", { name: "Compute path" })).toHaveCount(0);

    const addOriginButton = page.getByRole("button", { name: "Add point by clicking" });
    await expect(addOriginButton).toBeEnabled();
    await addOriginButton.click();
    await expect(page.getByRole("button", { name: "Cancel adding point" })).toBeVisible();
    await clickMapInFreeArea(page);
    await expect(page.getByLabel("Point paths list")).toBeVisible();
    await expect(page.locator(".origin-item-title").first()).toHaveText(/Loading address|2 Rue Petit, Paris/i);
    await expect(arrivalTooltip(page, "Best Meeting Point, Paris")).toBeVisible();
    await expectPathStatusVisible(inspectDialog);
    await expect(page.locator(".arrival-point-marker")).toHaveCount(1);
  });

  test("floating plus quick action is not rendered", async ({ page }) => {
    await page.goto(ENGLISH_APP_ROUTE);

    await clickMapInFreeArea(page);
    await expect(page.locator(".inspect-origin-quick-action-btn")).toHaveCount(0);
  });

  test("with an origin set, clicking another point auto-computes a path", async ({ page }) => {
    await mockReverseGeocode(page);
    await page.goto(ENGLISH_APP_ROUTE);
    const inspectDialog = page.getByLabel("Map point details");
    const addPointButton = page.getByRole("button", { name: "Add point by clicking" });

    await clickMapInFreeArea(page);
    await addPointButton.click();
    await clickMapInFreeArea(page);
    await expect(page.getByLabel("Point paths list")).toBeVisible();

    await clickMapInFreeArea(page);
    await expectPathStatusVisible(inspectDialog);
  });

  test("adding and removing points keeps best destination auto-selected", async ({ page }) => {
    await mockReverseGeocode(page, [
      "Destination A, Paris",
      "2 Rue Petit, Paris",
      "Meeting A, Paris",
      "Destination B, Paris",
      "4 Avenue de Flandre, Paris",
      "Meeting B, Paris"
    ]);
    await page.goto(ENGLISH_APP_ROUTE);
    const inspectDialog = page.getByLabel("Map point details");
    const addPointButton = page.getByRole("button", { name: "Add point by clicking" });

    await clickMapInFreeArea(page);
    await addPointButton.click();
    await clickMapInFreeArea(page);
    await expectPathStatusVisible(inspectDialog);
    await expect(page.locator(".arrival-point-marker")).toHaveCount(1);

    await addPointButton.click();
    await clickMapInFreeArea(page);
    await expectPathStatusVisible(inspectDialog);
    await expect(page.locator(".arrival-point-marker")).toHaveCount(1);

    await inspectDialog.locator(".origin-remove-btn").nth(1).click();
    await expectPathStatusVisible(inspectDialog);
    await expect(page.locator(".arrival-point-marker")).toHaveCount(1);
  });

  test("dock can clear selection back to empty state", async ({ page }) => {
    await mockReverseGeocode(page);
    await page.goto(ENGLISH_APP_ROUTE);

    await clickMapInFreeArea(page);
    const inspectDialog = page.getByLabel("Map point details");
    await page.getByRole("button", { name: "Add point by clicking" }).click();
    await clickMapInFreeArea(page);
    await expect(page.getByLabel("Point paths list")).toBeVisible();

    const clearSelectionButton = page.getByRole("button", { name: "Clear all points" });
    await expect(clearSelectionButton).toBeEnabled({ timeout: 15000 });
    await clearSelectionButton.click();
    await expect(page.getByLabel("Map point details")).toBeVisible();
    await expect(page.getByLabel("Point paths list")).toHaveCount(0);
    await expect(inspectDialog.getByText("Add some points first.")).toBeVisible();
  });
});
