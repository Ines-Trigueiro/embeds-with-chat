// The browser's localStorage, which can be missing or full (private mode): then nothing
// is remembered, and the app still works for this page load.

export function readStored(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

/** Remember `value` under `key`, or forget it with null. */
export function writeStored(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    // Not remembered.
  }
}
