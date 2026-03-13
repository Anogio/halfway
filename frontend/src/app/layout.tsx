import { cookies } from "next/headers";
import type { Metadata } from "next";
import "maplibre-gl/dist/maplibre-gl.css";

import { DEFAULT_LOCALE, LOCALE_COOKIE_KEY, resolveLocale } from "@/i18n/config";

import "./globals.css";

const metadataBase = process.env.NEXT_PUBLIC_SITE_URL
  ? new URL(process.env.NEXT_PUBLIC_SITE_URL)
  : undefined;

export const metadata: Metadata = {
  metadataBase,
  applicationName: "Halfway",
  icons: {
    icon: [
      { url: "/logo-mark.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon-512.png", type: "image/png", sizes: "512x512" }
    ],
    shortcut: [{ url: "/favicon.ico" }],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }]
  }
};

async function getCookieLocale() {
  const cookieStore = await cookies();
  return resolveLocale(cookieStore.get(LOCALE_COOKIE_KEY)?.value) ?? DEFAULT_LOCALE;
}

export default async function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getCookieLocale();

  return (
    <html lang={locale}>
      <body>{children}</body>
    </html>
  );
}
