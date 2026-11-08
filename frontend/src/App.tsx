import { useEffect, useState } from "react";

import { api, type Embed } from "./api";
import { EmbedEditor } from "./EmbedEditor";
import { JournalistPrompt } from "./JournalistPrompt";
import { Sidebar } from "./Sidebar";
import { readStored, writeStored } from "./storage";

/** "#/embeds/<id>" opens an embed; anything else is a new, empty one. Survives a reload. */
function embedIdFromHash(): string | null {
  return /^#\/embeds\/([\w-]+)$/.exec(window.location.hash)?.[1] ?? null;
}

const JOURNALIST_KEY = "embeds.journalist";
const COLLAPSED_KEY = "embeds.sidebarCollapsed";

export function App() {
  const [journalist, setJournalist] = useState(() => readStored(JOURNALIST_KEY));
  const [embedId, setEmbedId] = useState(embedIdFromHash);
  const [embeds, setEmbeds] = useState<Embed[] | null>(null);
  const [collapsed, setCollapsed] = useState(() => readStored(COLLAPSED_KEY) === "1");
  const [drawerOpen, setDrawerOpen] = useState(false);
  // Each navigation opens a fresh editor. Creating an embed isn't one: see `onCreated`.
  const [visit, setVisit] = useState(0);

  useEffect(() => {
    const onHashChange = () => {
      setEmbedId(embedIdFromHash());
      setVisit((v) => v + 1);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    if (!journalist) return;
    setEmbeds(null);
    api.myEmbeds(journalist).then(setEmbeds, () => setEmbeds([]));
  }, [journalist]);

  /** Update an embed in the sidebar: a new Title, published, … */
  function update(changes: Pick<Embed, "id"> & Partial<Embed>) {
    setEmbeds((current) => current && current.map((e) => (e.id === changes.id ? { ...e, ...changes } : e)));
  }

  /** The editor that created the embed stays on screen, mid-reply: no hashchange, no new visit. */
  function onCreated(embed: Embed) {
    setEmbeds((current) => [embed, ...(current ?? []).filter((e) => e.id !== embed.id)]);
    setEmbedId(embed.id);
    history.replaceState(null, "", `#/embeds/${embed.id}`);
  }

  async function rename(id: string, title: string) {
    if (!journalist) return;
    try {
      update(await api.changeEmbed(journalist, id, { title }));
    } catch {
      // Keep the old title; the sidebar still shows it.
    }
  }

  function toggleCollapsed() {
    writeStored(COLLAPSED_KEY, collapsed ? "0" : "1");
    setCollapsed(!collapsed);
  }

  if (!journalist) {
    return (
      <JournalistPrompt
        onSubmit={(name) => {
          writeStored(JOURNALIST_KEY, name);
          setJournalist(name);
        }}
      />
    );
  }

  const current = embeds?.find((e) => e.id === embedId) ?? null;
  return (
    <div className={`app${drawerOpen ? " drawer-open" : ""}`}>
      <Sidebar
        journalist={journalist}
        embeds={embeds}
        currentId={embedId}
        collapsed={collapsed && !drawerOpen}
        onToggle={() => (drawerOpen ? setDrawerOpen(false) : toggleCollapsed())}
        onRename={rename}
        onSwitchJournalist={() => {
          writeStored(JOURNALIST_KEY, null);
          setJournalist(null);
          window.location.hash = "#/"; // The next journalist starts on a new embed, not this one.
        }}
        onNavigate={() => setDrawerOpen(false)}
      />
      <div className="scrim" onClick={() => setDrawerOpen(false)} />
      <main className="main">
        <EmbedEditor
          key={visit}
          journalist={journalist}
          embedId={embedId}
          title={current?.title ?? null}
          onOpenSidebar={() => setDrawerOpen(true)}
          onCreated={onCreated}
          onChanged={update}
          onRename={(title) => embedId && rename(embedId, title)}
        />
      </main>
    </div>
  );
}
