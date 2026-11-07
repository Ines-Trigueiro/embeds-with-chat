import { useCallback, useEffect, useRef, useState } from "react";

import { api, forgetJournalist, storedJournalist, storeJournalist, type Embed } from "./api";
import { EmbedEditor } from "./EmbedEditor";
import { JournalistPrompt } from "./JournalistPrompt";
import { Sidebar } from "./Sidebar";

/** "#/embeds/<id>" opens an embed; anything else is a new, empty one. Survives a reload. */
function embedIdFromHash(): string | null {
  return /^#\/embeds\/([\w-]+)$/.exec(window.location.hash)?.[1] ?? null;
}

const COLLAPSED_KEY = "embeds.sidebarCollapsed";

function storedCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

export function App() {
  const [journalist, setJournalist] = useState(storedJournalist);
  const [embedId, setEmbedId] = useState(embedIdFromHash);
  const [embeds, setEmbeds] = useState<Embed[] | null>(null);
  const [collapsed, setCollapsed] = useState(storedCollapsed);
  const [drawerOpen, setDrawerOpen] = useState(false);
  // A new embed gets its id on the first message; the editor that created it stays mounted.
  const [editorKey, setEditorKey] = useState(0);
  const adopted = useRef<string | null>(null);

  useEffect(() => {
    const onHashChange = () => {
      const id = embedIdFromHash();
      setEmbedId(id);
      if (id === null || id !== adopted.current) setEditorKey((k) => k + 1);
      adopted.current = null;
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
  const update = useCallback((changes: Pick<Embed, "id"> & Partial<Embed>) => {
    setEmbeds((current) => current && current.map((e) => (e.id === changes.id ? { ...e, ...changes } : e)));
  }, []);

  const onCreated = useCallback(
    (embed: Embed) => {
      setEmbeds((current) => [embed, ...(current ?? []).filter((e) => e.id !== embed.id)]);
      adopted.current = embed.id;
      window.location.hash = `#/embeds/${embed.id}`;
    },
    [],
  );

  async function rename(id: string, title: string) {
    if (!journalist) return;
    try {
      update(await api.rename(journalist, id, title));
    } catch {
      // Keep the old title; the sidebar still shows it.
    }
  }

  function toggleCollapsed() {
    setCollapsed((c) => {
      try {
        localStorage.setItem(COLLAPSED_KEY, c ? "0" : "1");
      } catch {
        // Not remembered; still toggled.
      }
      return !c;
    });
  }

  if (!journalist) {
    return (
      <JournalistPrompt
        onSubmit={(name) => {
          storeJournalist(name);
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
          forgetJournalist();
          setJournalist(null);
          window.location.hash = "#/"; // The next journalist starts on a new embed, not this one.
        }}
        onNavigate={() => setDrawerOpen(false)}
      />
      <div className="scrim" onClick={() => setDrawerOpen(false)} />
      <main className="main">
        <EmbedEditor
          key={editorKey}
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
