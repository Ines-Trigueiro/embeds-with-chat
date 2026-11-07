// Thin client for the editor API. Every request carries the journalist's name;
// there is no real authentication (see the README).

import type { Language } from "./i18n";

const JOURNALIST_KEY = "embeds.journalist";

export function storedJournalist(): string | null {
  try {
    return localStorage.getItem(JOURNALIST_KEY);
  } catch {
    return null;
  }
}

export function storeJournalist(name: string): void {
  try {
    localStorage.setItem(JOURNALIST_KEY, name);
  } catch {
    // Private mode: the name lives only for this page load.
  }
}

export function forgetJournalist(): void {
  try {
    localStorage.removeItem(JOURNALIST_KEY);
  } catch {
    // Nothing stored, nothing to forget.
  }
}

export interface Embed {
  id: string;
  title: string;
  created_at: string;
  embed_language: Language;
}

export interface Version {
  number: number;
  created_at: string;
  preview_url: string;
  published: boolean;
  /** Pinned to this version; only once it is published. */
  delivery: Delivery | null;
}

/** What the journalist pastes into an article. */
export interface Delivery {
  snippet: string;
  embed_url: string;
}

export interface Message {
  role: "journalist" | "model";
  text: string;
  version_number: number | null;
  /** Guides the model read for this reply. */
  guides: string[];
}

export interface OpenedEmbed extends Embed {
  messages: Message[];
  versions: Version[];
  latest_version: Version | null;
  progress_frame_url: string;
  /** Follows the newest published version; once one exists. */
  delivery: Delivery | null;
}

/** Server-sent events from one chat turn; see the backend's chat module. */
export type ChatEvent =
  | { event: "guide"; data: { name: string } }
  | { event: "text"; data: { delta: string } }
  | { event: "progress"; data: { html: string } }
  | { event: "version"; data: Version }
  | { event: "error"; data: { message: string } }
  | { event: "done"; data: { text: string } };

function headers(journalist: string): HeadersInit {
  // Browsers refuse non-Latin-1 header values, so the name travels URL-encoded.
  return { "Content-Type": "application/json", "X-Journalist": encodeURIComponent(journalist) };
}

async function call(journalist: string, path: string, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(path, {
    ...init,
    headers: { ...headers(journalist), ...init.headers },
  });
  if (!response.ok) {
    throw new Error(`${init.method ?? "GET"} ${path} failed: ${response.status}`);
  }
  return response;
}

async function request<T>(journalist: string, path: string, init: RequestInit = {}): Promise<T> {
  return (await (await call(journalist, path, init)).json()) as T;
}

/** Send a chat message and yield the reply's events as they stream in. */
async function* sendMessage(
  journalist: string,
  embedId: string,
  content: string,
  language: Language,
): AsyncGenerator<ChatEvent> {
  const response = await call(journalist, `/api/embeds/${embedId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content, language }),
  });
  if (!response.body) throw new Error("The reply could not be read.");

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += value;
    let end: number;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      let event = "message";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (data) yield { event, data: JSON.parse(data) } as ChatEvent;
    }
  }
}

export const api = {
  sendMessage,
  openEmbed: (journalist: string, embedId: string) =>
    request<OpenedEmbed>(journalist, `/api/embeds/${embedId}`),
  myEmbeds: (journalist: string) => request<Embed[]>(journalist, "/api/embeds"),
  createEmbed: (journalist: string, title: string, embed_language: Language) =>
    request<Embed>(journalist, "/api/embeds", {
      method: "POST",
      body: JSON.stringify({ title, embed_language }),
    }),
  publish: (journalist: string, embedId: string, number: number) =>
    request<OpenedEmbed>(journalist, `/api/embeds/${embedId}/versions/${number}/publish`, {
      method: "POST",
    }),
  setEmbedLanguage: (journalist: string, embedId: string, embed_language: Language) =>
    request<Embed>(journalist, `/api/embeds/${embedId}`, {
      method: "PATCH",
      body: JSON.stringify({ embed_language }),
    }),
};
