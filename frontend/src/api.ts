// Thin client for the editor API. Every request carries the journalist's name;
// there is no real authentication (see the README).

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
}

async function request<T>(journalist: string, path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", "X-Journalist": journalist, ...init.headers },
  });
  if (!response.ok) {
    throw new Error(`${init.method ?? "GET"} ${path} failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export const api = {
  myEmbeds: (journalist: string) => request<Embed[]>(journalist, "/api/embeds"),
  createEmbed: (journalist: string, title: string) =>
    request<Embed>(journalist, "/api/embeds", { method: "POST", body: JSON.stringify({ title }) }),
};
