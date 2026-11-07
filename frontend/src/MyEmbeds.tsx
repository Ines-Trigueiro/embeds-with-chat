import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type Embed } from "./api";
import { currentLanguage } from "./i18n";

export function MyEmbeds({ journalist }: { journalist: string }) {
  const { t, i18n } = useTranslation();
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
      // A new embed is written in the journalist's language unless they change it.
      const embed = await api.createEmbed(journalist, title.trim(), currentLanguage());
      window.location.hash = `#/embeds/${embed.id}`;
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <section className="card">
      <h2>{t("myEmbeds.heading")}</h2>
      <form className="row" onSubmit={create}>
        <input
          placeholder={t("myEmbeds.titlePlaceholder")}
          value={title}
          maxLength={200}
          onChange={(e) => setTitle(e.target.value)}
        />
        <button type="submit" disabled={!title.trim()}>
          {t("myEmbeds.create")}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      {embeds === null ? (
        <p className="hint">{t("myEmbeds.loading")}</p>
      ) : embeds.length === 0 ? (
        <p className="hint">{t("myEmbeds.empty")}</p>
      ) : (
        <ul className="embed-list">
          {embeds.map((embed) => (
            <li key={embed.id}>
              <a href={`#/embeds/${embed.id}`}>{embed.title}</a>
              <time dateTime={embed.created_at}>{new Date(embed.created_at).toLocaleString(i18n.language)}</time>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
