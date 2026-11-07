// UI and chat language (nb/da/en). The embed's own language is a separate setting per embed.
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

export const LANGUAGES = ["nb", "da", "en"] as const;
export type Language = (typeof LANGUAGES)[number];

export const LANGUAGE_NAMES: Record<Language, string> = { nb: "Norsk", da: "Dansk", en: "English" };

const en = {
  app: { title: "Embeds with chat", switchJournalist: "Switch journalist", language: "Language" },
  prompt: {
    yourName: "Your name",
    hint: "No password: your name only keeps your embeds apart from others'.",
    continue: "Continue",
  },
  myEmbeds: {
    heading: "My embeds",
    titlePlaceholder: "Title, e.g. Electricity price calculator",
    create: "New embed",
    loading: "Loading…",
    empty: "You haven't made any embeds yet.",
  },
  editor: {
    loading: "Loading…",
    placeholder: "Describe what you want, or what to change…",
    send: "Send",
    readingGuide: "Reading guide: {{name}}…",
    version: "Version {{number}}",
    noVersion: "No version yet",
    showing: "Showing",
    latest: "(latest)",
    previewSize: "Preview size",
    mobile: "Mobile",
    desktop: "Desktop",
    embedLanguage: "Embed language",
    embedLanguageHint: "The language readers see. Applies from the next reply.",
  },
  preview: {
    empty: "Describe the embed you want in the chat, and it appears here.",
    writing: "Writing…",
    frameTitle: "Embed preview",
  },
  guides: { quiz: "quiz", calculator: "calculator", chart: "chart", map: "map", timeline: "timeline" },
};

type Translations = typeof en;

const nb: Translations = {
  app: { title: "Embeds med chat", switchJournalist: "Bytt journalist", language: "Språk" },
  prompt: {
    yourName: "Navnet ditt",
    hint: "Ingen passord: navnet holder bare embedene dine adskilt fra andres.",
    continue: "Fortsett",
  },
  myEmbeds: {
    heading: "Mine embeds",
    titlePlaceholder: "Tittel, f.eks. Strømpriskalkulator",
    create: "Ny embed",
    loading: "Laster …",
    empty: "Du har ikke laget noen embeds ennå.",
  },
  editor: {
    loading: "Laster …",
    placeholder: "Beskriv hva du vil ha, eller hva som skal endres …",
    send: "Send",
    readingGuide: "Leser veiledning: {{name}} …",
    version: "Versjon {{number}}",
    noVersion: "Ingen versjon ennå",
    showing: "Viser",
    latest: "(nyeste)",
    previewSize: "Forhåndsvisningsstørrelse",
    mobile: "Mobil",
    desktop: "Desktop",
    embedLanguage: "Språk i embeden",
    embedLanguageHint: "Språket leserne ser. Gjelder fra neste svar.",
  },
  preview: {
    empty: "Beskriv embeden du vil ha i chatten, så dukker den opp her.",
    writing: "Skriver …",
    frameTitle: "Forhåndsvisning av embeden",
  },
  guides: { quiz: "quiz", calculator: "kalkulator", chart: "graf", map: "kart", timeline: "tidslinje" },
};

const da: Translations = {
  app: { title: "Embeds med chat", switchJournalist: "Skift journalist", language: "Sprog" },
  prompt: {
    yourName: "Dit navn",
    hint: "Ingen adgangskode: dit navn holder kun dine embeds adskilt fra andres.",
    continue: "Fortsæt",
  },
  myEmbeds: {
    heading: "Mine embeds",
    titlePlaceholder: "Titel, fx Elprisberegner",
    create: "Ny embed",
    loading: "Indlæser …",
    empty: "Du har ikke lavet nogen embeds endnu.",
  },
  editor: {
    loading: "Indlæser …",
    placeholder: "Beskriv hvad du vil have, eller hvad der skal ændres …",
    send: "Send",
    readingGuide: "Læser vejledning: {{name}} …",
    version: "Version {{number}}",
    noVersion: "Ingen version endnu",
    showing: "Viser",
    latest: "(nyeste)",
    previewSize: "Størrelse på forhåndsvisning",
    mobile: "Mobil",
    desktop: "Desktop",
    embedLanguage: "Sprog i embeddet",
    embedLanguageHint: "Det sprog læserne ser. Gælder fra næste svar.",
  },
  preview: {
    empty: "Beskriv det embed, du vil have, i chatten, så dukker det op her.",
    writing: "Skriver …",
    frameTitle: "Forhåndsvisning af embeddet",
  },
  guides: { quiz: "quiz", calculator: "beregner", chart: "graf", map: "kort", timeline: "tidslinje" },
};

const STORAGE_KEY = "embeds.language";

function storedLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && (LANGUAGES as readonly string[]).includes(stored)) return stored as Language;
  } catch {
    // No storage: fall through to the default.
  }
  return "nb";
}

export function currentLanguage(): Language {
  return (LANGUAGES as readonly string[]).includes(i18n.language) ? (i18n.language as Language) : "nb";
}

export function changeLanguage(language: Language): void {
  try {
    localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Not remembered, but still switched for this page load.
  }
  void i18n.changeLanguage(language);
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, nb: { translation: nb }, da: { translation: da } },
  lng: storedLanguage(),
  fallbackLng: "en",
  interpolation: { escapeValue: false }, // React escapes already.
});

i18n.on("languageChanged", (language) => {
  document.documentElement.lang = language;
});
document.documentElement.lang = i18n.language;
