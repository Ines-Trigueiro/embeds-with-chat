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
  publish: {
    publish: "Publish version {{number}}",
    published: "Published",
    notYet: "Publish a version to get a snippet for the article.",
    heading: "Put it in an article",
    snippetLatest: "Snippet (always shows the newest published version)",
    urlLatest: "Embed URL (newest published version)",
    snippetPinned: "Snippet pinned to version {{number}}",
    urlPinned: "Embed URL for version {{number}}",
    copy: "Copy",
    copied: "Copied",
    testArticle: "Open in a test article ↗",
    testArticlePinned: "Open version {{number}} in a test article ↗",
  },
  quality: {
    ok: "Quality check: nothing to fix.",
    block: "Must fix:",
    warn: "Check:",
    cannotPublish: "This version can't be published until the problems are fixed. Ask the model to fix them.",
    confirm_one: "There is {{count}} warning for this version. Publish anyway?",
    confirm_other: "There are {{count}} warnings for this version. Publish anyway?",
    rules: {
      external_resource: "It loads or links to something outside the allowed list ({{detail}}). That will be blocked for readers.",
      cookie_access: "It tries to read cookies ({{detail}}).",
      page_access: "It tries to reach the article page around it ({{detail}}).",
      form_submission: "It has a form that sends data somewhere ({{detail}}).",
      redirect: "It tries to send readers to another page.",
      too_large: "It is too large ({{detail}}).",
      missing_alt: "{{detail}} image(s) have no alt text for screen readers.",
      missing_source: "No source line (\"Kilde:\" / \"Source:\") is visible.",
      missing_viewport: "It has no viewport setting, so it may look wrong on phones.",
    },
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
  publish: {
    publish: "Publiser versjon {{number}}",
    published: "Publisert",
    notYet: "Publiser en versjon for å få en kodesnutt til artikkelen.",
    heading: "Sett den inn i en artikkel",
    snippetLatest: "Kodesnutt (viser alltid nyeste publiserte versjon)",
    urlLatest: "Embed-URL (nyeste publiserte versjon)",
    snippetPinned: "Kodesnutt låst til versjon {{number}}",
    urlPinned: "Embed-URL for versjon {{number}}",
    copy: "Kopier",
    copied: "Kopiert",
    testArticle: "Åpne i en testartikkel ↗",
    testArticlePinned: "Åpne versjon {{number}} i en testartikkel ↗",
  },
  quality: {
    ok: "Kvalitetssjekk: ingenting å rette.",
    block: "Må rettes:",
    warn: "Sjekk:",
    cannotPublish: "Denne versjonen kan ikke publiseres før problemene er rettet. Be modellen rette dem.",
    confirm_one: "Det er {{count}} advarsel for denne versjonen. Publisere likevel?",
    confirm_other: "Det er {{count}} advarsler for denne versjonen. Publisere likevel?",
    rules: {
      external_resource: "Den laster eller lenker til noe utenfor den tillatte listen ({{detail}}). Det blir blokkert for leserne.",
      cookie_access: "Den prøver å lese informasjonskapsler ({{detail}}).",
      page_access: "Den prøver å nå artikkelsiden rundt seg ({{detail}}).",
      form_submission: "Den har et skjema som sender data et sted ({{detail}}).",
      redirect: "Den prøver å sende leserne til en annen side.",
      too_large: "Den er for stor ({{detail}}).",
      missing_alt: "{{detail}} bilde(r) mangler alternativ tekst for skjermlesere.",
      missing_source: "Ingen kildelinje («Kilde:») er synlig.",
      missing_viewport: "Den mangler viewport-innstilling, så den kan se feil ut på mobil.",
    },
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
  publish: {
    publish: "Udgiv version {{number}}",
    published: "Udgivet",
    notYet: "Udgiv en version for at få et kodestykke til artiklen.",
    heading: "Sæt det ind i en artikel",
    snippetLatest: "Kodestykke (viser altid nyeste udgivne version)",
    urlLatest: "Embed-URL (nyeste udgivne version)",
    snippetPinned: "Kodestykke låst til version {{number}}",
    urlPinned: "Embed-URL for version {{number}}",
    copy: "Kopiér",
    copied: "Kopieret",
    testArticle: "Åbn i en testartikel ↗",
    testArticlePinned: "Åbn version {{number}} i en testartikel ↗",
  },
  quality: {
    ok: "Kvalitetstjek: intet at rette.",
    block: "Skal rettes:",
    warn: "Tjek:",
    cannotPublish: "Denne version kan ikke udgives, før problemerne er rettet. Bed modellen rette dem.",
    confirm_one: "Der er {{count}} advarsel for denne version. Udgiv alligevel?",
    confirm_other: "Der er {{count}} advarsler for denne version. Udgiv alligevel?",
    rules: {
      external_resource: "Den indlæser eller linker til noget uden for den tilladte liste ({{detail}}). Det bliver blokeret for læserne.",
      cookie_access: "Den forsøger at læse cookies ({{detail}}).",
      page_access: "Den forsøger at nå artikelsiden omkring sig ({{detail}}).",
      form_submission: "Den har en formular, der sender data et sted hen ({{detail}}).",
      redirect: "Den forsøger at sende læserne til en anden side.",
      too_large: "Den er for stor ({{detail}}).",
      missing_alt: "{{detail}} billede(r) mangler alternativ tekst til skærmlæsere.",
      missing_source: "Ingen kildelinje («Kilde:») er synlig.",
      missing_viewport: "Den mangler viewport-indstilling, så den kan se forkert ud på mobil.",
    },
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
