import { useEffect, useState, useSyncExternalStore } from "react";

import { api } from "./api";
import { EmbedEditor } from "./EmbedEditor";
import { currentLanguage } from "./i18n";
import { JournalistPrompt } from "./JournalistPrompt";
import { Sidebar } from "./Sidebar";
import { readStored, writeStored } from "./storage";
import { Workspace } from "./Workspace";

/** "#/embeds/<id>" opens an embed; anything else is a new, empty one. Survives a reload. */
function embedIdFromHash(): string | null {
  return /^#\/embeds\/([\w-]+)$/.exec(window.location.hash)?.[1] ?? null;
}

const JOURNALIST_KEY = "embeds.journalist";
const COLLAPSED_KEY = "embeds.sidebarCollapsed";

export function App() {
  const [journalist, setJournalist] = useState(() => readStored(JOURNALIST_KEY));

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
  return (
    <Desk
      key={journalist}
      journalist={journalist}
      onSwitchJournalist={() => {
        writeStored(JOURNALIST_KEY, null);
        setJournalist(null);
        window.location.hash = "#/"; // The next journalist starts on a new embed, not this one.
      }}
    />
  );
}

/** One journalist's sidebar and editor, both showing the one Workspace. */
function Desk({ journalist, onSwitchJournalist }: { journalist: string; onSwitchJournalist: () => void }) {
  const [workspace] = useState(() => new Workspace(api, journalist, currentLanguage()));
  const { openId } = useSyncExternalStore(workspace.subscribe, workspace.getState);
  const [collapsed, setCollapsed] = useState(() => readStored(COLLAPSED_KEY) === "1");
  const [drawerOpen, setDrawerOpen] = useState(false);
  // Each navigation gives the editor fresh UI state. Creating an embed isn't one: no hashchange.
  const [visit, setVisit] = useState(0);

  useEffect(() => {
    workspace.loadEmbeds();
    const openFromHash = () => {
      const id = embedIdFromHash();
      if (id) workspace.open(id);
      else workspace.startNew(currentLanguage());
      setVisit((v) => v + 1);
    };
    openFromHash();
    window.addEventListener("hashchange", openFromHash);
    return () => window.removeEventListener("hashchange", openFromHash);
  }, [workspace]);

  useEffect(() => {
    // A new embed was just created: give it its address, without reopening it mid-reply.
    if (openId && openId !== embedIdFromHash()) history.replaceState(null, "", `#/embeds/${openId}`);
  }, [openId]);

  function toggleCollapsed() {
    writeStored(COLLAPSED_KEY, collapsed ? "0" : "1");
    setCollapsed(!collapsed);
  }

  return (
    <div className={`app${drawerOpen ? " drawer-open" : ""}`}>
      <Sidebar
        journalist={journalist}
        workspace={workspace}
        collapsed={collapsed && !drawerOpen}
        onToggle={() => (drawerOpen ? setDrawerOpen(false) : toggleCollapsed())}
        onSwitchJournalist={onSwitchJournalist}
        onNavigate={() => setDrawerOpen(false)}
      />
      <div className="scrim" onClick={() => setDrawerOpen(false)} />
      <main className="main">
        <EmbedEditor key={visit} workspace={workspace} onOpenSidebar={() => setDrawerOpen(true)} />
      </main>
    </div>
  );
}
