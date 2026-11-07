import { useEffect, useState } from "react";

import { api, type Embed } from "./api";

export function MyEmbeds({ journalist }: { journalist: string }) {
  const [embeds, setEmbeds] = useState<Embed[] | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEmbeds(null);
    api.myEmbeds(journalist).then(setEmbeds, (e: Error) => setError(e.message));
  }, [journalist]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    try {
      const embed = await api.createEmbed(journalist, title.trim());
      window.location.hash = `#/embeds/${embed.id}`;
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <section className="card">
      <h2>My embeds</h2>
      <form className="row" onSubmit={create}>
        <input
          placeholder="Title, e.g. Electricity price calculator"
          value={title}
          maxLength={200}
          onChange={(e) => setTitle(e.target.value)}
        />
        <button type="submit" disabled={!title.trim()}>
          New embed
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      {embeds === null ? (
        <p className="hint">Loading…</p>
      ) : embeds.length === 0 ? (
        <p className="hint">You haven't made any embeds yet.</p>
      ) : (
        <ul className="embed-list">
          {embeds.map((embed) => (
            <li key={embed.id}>
              <a href={`#/embeds/${embed.id}`}>{embed.title}</a>
              <time dateTime={embed.created_at}>{new Date(embed.created_at).toLocaleString()}</time>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
