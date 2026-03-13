import { defineConfig, devices } from "@playwright/test";

const shouldManageWebServers = process.env.PW_SKIP_WEBSERVER !== "1";
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [
    ["list"],
    ["html", { outputFolder: "../output/playwright/html-report", open: "never" }]
  ],
  outputDir: "../output/playwright/test-results",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure"
  },
  webServer: shouldManageWebServers
    ? [
        {
          command:
            "cd ../backend && CORS_ALLOW_ORIGIN_REGEX='^http://(localhost|127\\.0\\.0\\.1):3000$' PYTHONPATH=src:shared/src UV_CACHE_DIR=.uv-cache uv run python -m transit_backend.api.server",
          url: "http://127.0.0.1:8000/health",
          timeout: 120_000,
          reuseExistingServer: true
        },
        {
          command: "npm run dev -- --hostname 127.0.0.1 --port 3000",
          url: "http://127.0.0.1:3000",
          timeout: 120_000,
          reuseExistingServer: true
        }
      ]
    : undefined,
  projects: [
    {
      name: "chromium",
      testIgnore: /.*-map\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] }
    },
    {
      name: "mobile-chromium",
      testIgnore: /.*-map\.spec\.ts/,
      use: { ...devices["Pixel 7"] }
    },
    {
      name: "map-chromium",
      testMatch: /.*-map\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        headless: process.env.CI === "true"
      }
    }
  ]
});
