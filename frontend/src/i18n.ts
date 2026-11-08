// UI and chat language (nb/da/en). The embed's own language is a separate setting per embed.
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

export const LANGUAGES = ["nb", "da", "en"] as const;
export type Language = (typeof LANGUAGES)[number];

export const LANGUAGE_NAMES: Record<Language, string> = { nb: "Norsk", da: "Dansk", en: "English" };

const en = {
  app: { title: "Embeds with chat", switchJournalist: "Switch journalist", language: "Language" },
  prompt: {
    tagline: "Describe an interactive element, see it come to life, and put it in your article.",
    yourName: "Your name",
    namePlaceholder: "e.g. Kari Nordmann",
    hint: "No password: your name only keeps your embeds apart from others'.",
    continue: "Continue",
  },
  sidebar: {
    heading: "My embeds",
    new: "New embed",
    search: "Search embeds",
    loading: "Loading…",
    empty: "No embeds yet.",
    noMatch: "No embeds match.",
    rename: "Rename",
    collapse: "Hide sidebar",
    expand: "Show sidebar",
    open: "Open the list of embeds",
  },
  editor: {
    emptyHeading: "What do you want to make?",
    suggestions: {
      quiz: "A quiz with five questions about …",
      calculator: "A calculator that shows how much …",
      chart: "A chart from the spreadsheet I attach",
      map: "A map that marks …",
    },
    placeholder: "Describe what you want, or what to change…",
    send: "Send",
    readingGuide: "Reading guide: {{name}}…",
    thinking: "Thinking…",
    translatedTo: "Translated to {{language}}",
    translatingTo: "Translating to {{language}}…",
    notTranslatedTo: "Not translated to {{language}}",
    translate: {
      title: "Translate to {{language}}?",
      body: "The model rewrites the text readers see in version {{number}} into {{language}}, as a new version {{next}}. The data stays exactly as it is.",
      confirm: "Translate",
    },
    writing: "Building the embed…",
    version: "Version {{number}}",
    noVersion: "No version yet",
    showing: "Version on screen",
    latest: "(latest)",
    previewSize: "Preview size",
    mobile: "Mobile",
    desktop: "Desktop",
    panes: "Show",
    pane: { chat: "Chat", preview: "Preview" },
    embedLanguage: "Embed language",
    embedLanguageHint: "The language readers see. Changing it translates the current version.",
  },
  preview: {
    empty: "Describe the embed you want in the chat, and it appears here.",
    writing: "Writing…",
    frameTitle: "Embed preview",
  },
  publish: {
    publish: "Publish version {{number}}",
    published: "Published",
    getSnippet: "Get embed code",
    dialogTitle: "Publish version {{number}}",
    codeTitle: "Put it in your article",
    blocked: "This version can't be published yet. Ask the model in the chat to fix this:",
    warnings: "Have a look at these before you publish:",
    acceptWarnings: "I've checked these, and want to publish anyway",
    ready: "The quality check found nothing to fix.",
    cancel: "Cancel",
    confirm: "Publish",
    publishing: "Publishing…",
    justPublished: "Version {{number}} is published.",
    copySnippet: "Copy embed code",
    copied: "Copied!",
    copy: "Copy",
    step1: "Copy the embed code with the button above.",
    step2: "In your article, add an HTML or embed block, and paste the code into it.",
    step3: "Preview the article: the embed shows up where you pasted the code.",
    updates: "Already in an article? It updates by itself when you publish a new version. No need to paste again.",
    testArticle: "See how it looks in an article",
    advanced: "Advanced",
    pinnedHint: "Code that keeps showing version {{number}}, even if you publish changes later:",
    pinnedSnippet: "Embed code for version {{number}} only",
    urlPinned: "Link to version {{number}} on its own",
    urlLatest: "Link to the embed on its own (newest published version)",
    notPublishedPinned: "Publish the version on screen to get code that keeps showing exactly that version.",
    close: "Close",
  },
  quality: {
    chipOk: "Quality check passed",
    chipBlock: "{{count}} must be fixed",
    chipWarn: "{{count}} to check",
    block: "Must fix:",
    warn: "Check:",
    cannotPublish: "This version can't be published until the problems are fixed. Ask the model to fix them.",
    rules: {
      external_resource: "It loads something from outside the allowed list ({{detail}}). That will be blocked for readers.",
      link: "It has a link ({{detail}}), but links can't open from an embed. Write the source as text instead.",
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
  attachments: {
    heading: "Attachments",
    attach: "Attach a spreadsheet (.csv, .xlsx) or an image",
    rows_one: "{{count}} row",
    rows_other: "{{count}} rows",
  },
  languages: { nb: "Norwegian", da: "Danish", en: "English" },
  guides: { quiz: "quiz", calculator: "calculator", chart: "chart", map: "map", timeline: "timeline" },
};

type Translations = typeof en;

const nb: Translations = {
  app: { title: "Embeds med chat", switchJournalist: "Bytt journalist", language: "Språk" },
  prompt: {
    tagline: "Beskriv et interaktivt element, se det ta form, og sett det inn i artikkelen din.",
    yourName: "Navnet ditt",
    namePlaceholder: "f.eks. Kari Nordmann",
    hint: "Ingen passord: navnet holder bare embedene dine adskilt fra andres.",
    continue: "Fortsett",
  },
  sidebar: {
    heading: "Mine embeds",
    new: "Ny embed",
    search: "Søk i embeds",
    loading: "Laster …",
    empty: "Ingen embeds ennå.",
    noMatch: "Ingen embeds passer.",
    rename: "Gi nytt navn",
    collapse: "Skjul sidepanelet",
    expand: "Vis sidepanelet",
    open: "Åpne listen over embeds",
  },
  editor: {
    emptyHeading: "Hva vil du lage?",
    suggestions: {
      quiz: "En quiz med fem spørsmål om …",
      calculator: "En kalkulator som viser hvor mye …",
      chart: "En graf fra regnearket jeg legger ved",
      map: "Et kart som viser …",
    },
    placeholder: "Beskriv hva du vil ha, eller hva som skal endres …",
    send: "Send",
    readingGuide: "Leser veiledning: {{name}} …",
    thinking: "Tenker …",
    translatedTo: "Oversatt til {{language}}",
    translatingTo: "Oversetter til {{language}} …",
    notTranslatedTo: "Ikke oversatt til {{language}}",
    translate: {
      title: "Oversette til {{language}}?",
      body: "Modellen skriver om teksten leserne ser i versjon {{number}} til {{language}}, som en ny versjon {{next}}. Dataene forblir nøyaktig som de er.",
      confirm: "Oversett",
    },
    writing: "Bygger embeden …",
    version: "Versjon {{number}}",
    noVersion: "Ingen versjon ennå",
    showing: "Versjon som vises",
    latest: "(nyeste)",
    previewSize: "Forhåndsvisningsstørrelse",
    mobile: "Mobil",
    desktop: "Desktop",
    panes: "Vis",
    pane: { chat: "Chat", preview: "Forhåndsvisning" },
    embedLanguage: "Språk i embeden",
    embedLanguageHint: "Språket leserne ser. Endrer du det, oversettes gjeldende versjon.",
  },
  preview: {
    empty: "Beskriv embeden du vil ha i chatten, så dukker den opp her.",
    writing: "Skriver …",
    frameTitle: "Forhåndsvisning av embeden",
  },
  publish: {
    publish: "Publiser versjon {{number}}",
    published: "Publisert",
    getSnippet: "Hent embedkode",
    dialogTitle: "Publiser versjon {{number}}",
    codeTitle: "Sett den inn i artikkelen",
    blocked: "Denne versjonen kan ikke publiseres ennå. Be modellen i chatten rette dette:",
    warnings: "Ta en titt på dette før du publiserer:",
    acceptWarnings: "Jeg har sjekket dette og vil publisere likevel",
    ready: "Kvalitetssjekken fant ingenting å rette.",
    cancel: "Avbryt",
    confirm: "Publiser",
    publishing: "Publiserer …",
    justPublished: "Versjon {{number}} er publisert.",
    copySnippet: "Kopier embedkoden",
    copied: "Kopiert!",
    copy: "Kopier",
    step1: "Kopier embedkoden med knappen over.",
    step2: "Legg til en HTML- eller embed-blokk i artikkelen, og lim inn koden der.",
    step3: "Forhåndsvis artikkelen: embeden vises der du limte inn koden.",
    updates: "Ligger den allerede i en artikkel? Den oppdateres av seg selv når du publiserer en ny versjon. Du trenger ikke lime inn på nytt.",
    testArticle: "Se hvordan den ser ut i en artikkel",
    advanced: "Avansert",
    pinnedHint: "Kode som fortsetter å vise versjon {{number}}, selv om du publiserer endringer senere:",
    pinnedSnippet: "Embedkode for bare versjon {{number}}",
    urlPinned: "Lenke til versjon {{number}} alene",
    urlLatest: "Lenke til embeden alene (nyeste publiserte versjon)",
    notPublishedPinned: "Publiser versjonen du ser for å få kode som alltid viser akkurat den versjonen.",
    close: "Lukk",
  },
  quality: {
    chipOk: "Kvalitetssjekk bestått",
    chipBlock: "{{count}} må rettes",
    chipWarn: "{{count}} å sjekke",
    block: "Må rettes:",
    warn: "Sjekk:",
    cannotPublish: "Denne versjonen kan ikke publiseres før problemene er rettet. Be modellen rette dem.",
    rules: {
      external_resource: "Den laster noe utenfor den tillatte listen ({{detail}}). Det blir blokkert for leserne.",
      link: "Den har en lenke ({{detail}}), men lenker kan ikke åpnes fra en embed. Skriv kilden som tekst i stedet.",
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
  attachments: {
    heading: "Vedlegg",
    attach: "Legg ved et regneark (.csv, .xlsx) eller et bilde",
    rows_one: "{{count}} rad",
    rows_other: "{{count}} rader",
  },
  languages: { nb: "norsk", da: "dansk", en: "engelsk" },
  guides: { quiz: "quiz", calculator: "kalkulator", chart: "graf", map: "kart", timeline: "tidslinje" },
};

const da: Translations = {
  app: { title: "Embeds med chat", switchJournalist: "Skift journalist", language: "Sprog" },
  prompt: {
    tagline: "Beskriv et interaktivt element, se det tage form, og sæt det ind i din artikel.",
    yourName: "Dit navn",
    namePlaceholder: "fx Mette Jensen",
    hint: "Ingen adgangskode: dit navn holder kun dine embeds adskilt fra andres.",
    continue: "Fortsæt",
  },
  sidebar: {
    heading: "Mine embeds",
    new: "Nyt embed",
    search: "Søg i embeds",
    loading: "Indlæser …",
    empty: "Ingen embeds endnu.",
    noMatch: "Ingen embeds passer.",
    rename: "Omdøb",
    collapse: "Skjul sidepanelet",
    expand: "Vis sidepanelet",
    open: "Åbn listen over embeds",
  },
  editor: {
    emptyHeading: "Hvad vil du lave?",
    suggestions: {
      quiz: "En quiz med fem spørgsmål om …",
      calculator: "En beregner, der viser hvor meget …",
      chart: "En graf fra det regneark, jeg vedhæfter",
      map: "Et kort, der viser …",
    },
    placeholder: "Beskriv hvad du vil have, eller hvad der skal ændres …",
    send: "Send",
    readingGuide: "Læser vejledning: {{name}} …",
    thinking: "Tænker …",
    translatedTo: "Oversat til {{language}}",
    translatingTo: "Oversætter til {{language}} …",
    notTranslatedTo: "Ikke oversat til {{language}}",
    translate: {
      title: "Oversætte til {{language}}?",
      body: "Modellen omskriver den tekst, læserne ser i version {{number}}, til {{language}} som en ny version {{next}}. Dataene forbliver præcis, som de er.",
      confirm: "Oversæt",
    },
    writing: "Bygger embeddet …",
    version: "Version {{number}}",
    noVersion: "Ingen version endnu",
    showing: "Version, der vises",
    latest: "(nyeste)",
    previewSize: "Størrelse på forhåndsvisning",
    mobile: "Mobil",
    desktop: "Desktop",
    panes: "Vis",
    pane: { chat: "Chat", preview: "Forhåndsvisning" },
    embedLanguage: "Sprog i embeddet",
    embedLanguageHint: "Det sprog, læserne ser. Ændrer du det, oversættes den nuværende version.",
  },
  preview: {
    empty: "Beskriv det embed, du vil have, i chatten, så dukker det op her.",
    writing: "Skriver …",
    frameTitle: "Forhåndsvisning af embeddet",
  },
  publish: {
    publish: "Udgiv version {{number}}",
    published: "Udgivet",
    getSnippet: "Hent embedkode",
    dialogTitle: "Udgiv version {{number}}",
    codeTitle: "Sæt det ind i artiklen",
    blocked: "Denne version kan ikke udgives endnu. Bed modellen i chatten rette dette:",
    warnings: "Kig på dette, før du udgiver:",
    acceptWarnings: "Jeg har tjekket dette og vil udgive alligevel",
    ready: "Kvalitetstjekket fandt intet at rette.",
    cancel: "Annullér",
    confirm: "Udgiv",
    publishing: "Udgiver …",
    justPublished: "Version {{number}} er udgivet.",
    copySnippet: "Kopiér embedkoden",
    copied: "Kopieret!",
    copy: "Kopiér",
    step1: "Kopiér embedkoden med knappen ovenfor.",
    step2: "Tilføj en HTML- eller embed-blok i artiklen, og indsæt koden der.",
    step3: "Forhåndsvis artiklen: embeddet vises, hvor du indsatte koden.",
    updates: "Ligger det allerede i en artikel? Det opdateres af sig selv, når du udgiver en ny version. Du behøver ikke indsætte igen.",
    testArticle: "Se hvordan det ser ud i en artikel",
    advanced: "Avanceret",
    pinnedHint: "Kode, der bliver ved med at vise version {{number}}, selv hvis du udgiver ændringer senere:",
    pinnedSnippet: "Embedkode kun for version {{number}}",
    urlPinned: "Link til version {{number}} alene",
    urlLatest: "Link til embeddet alene (nyeste udgivne version)",
    notPublishedPinned: "Udgiv den version, du ser, for at få kode, der altid viser præcis den version.",
    close: "Luk",
  },
  quality: {
    chipOk: "Kvalitetstjek bestået",
    chipBlock: "{{count}} skal rettes",
    chipWarn: "{{count}} at tjekke",
    block: "Skal rettes:",
    warn: "Tjek:",
    cannotPublish: "Denne version kan ikke udgives, før problemerne er rettet. Bed modellen rette dem.",
    rules: {
      external_resource: "Den indlæser noget uden for den tilladte liste ({{detail}}). Det bliver blokeret for læserne.",
      link: "Den har et link ({{detail}}), men links kan ikke åbnes fra et embed. Skriv kilden som tekst i stedet.",
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
  attachments: {
    heading: "Vedhæftninger",
    attach: "Vedhæft et regneark (.csv, .xlsx) eller et billede",
    rows_one: "{{count}} række",
    rows_other: "{{count}} rækker",
  },
  languages: { nb: "norsk", da: "dansk", en: "engelsk" },
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
