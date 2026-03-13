import { cookies } from "next/headers";
import type { Metadata } from "next";

import { I18nProvider } from "@/i18n/I18nProvider";
import { DEFAULT_LOCALE, LOCALE_COOKIE_KEY, resolveLocale } from "@/i18n/config";
import { enMessages } from "@/i18n/messages/en";
import { frMessages } from "@/i18n/messages/fr";

import HeatmapView from "@/components/HeatmapView";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function readSearchParam(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) {
    return value[0] ?? null;
  }
  return value ?? null;
}

async function getInitialLocale(searchParams: SearchParams) {
  const params = await searchParams;
  const queryLocale = resolveLocale(readSearchParam(params.lang));
  if (queryLocale) {
    return queryLocale;
  }

  const cookieStore = await cookies();
  return resolveLocale(cookieStore.get(LOCALE_COOKIE_KEY)?.value) ?? DEFAULT_LOCALE;
}

export async function generateMetadata({
  searchParams
}: {
  searchParams: SearchParams;
}): Promise<Metadata> {
  const locale = await getInitialLocale(searchParams);
  const messages = locale === "fr" ? frMessages : enMessages;
  return {
    title: messages.app.title,
    description: messages.app.description,
    openGraph: {
      type: "website",
      title: messages.app.title,
      description: messages.app.description,
      siteName: messages.app.siteName,
      images: [
        {
          url: "/logo-1024.png",
          width: 1024,
          height: 1024,
          alt: messages.app.description
        }
      ]
    },
    twitter: {
      card: "summary",
      title: messages.app.title,
      description: messages.app.description,
      images: ["/logo-1024.png"]
    }
  };
}

export default async function Home({
  searchParams
}: {
  searchParams: SearchParams;
}) {
  const initialLocale = await getInitialLocale(searchParams);

  return (
    <I18nProvider initialLocale={initialLocale}>
      <HeatmapView />
    </I18nProvider>
  );
}
