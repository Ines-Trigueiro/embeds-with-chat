// The journalist's embeds, the open one and its Conversation, with no React: the app, sidebar
// and editor subscribe and only render. Every rule lives here, so it can be tested with a fake
// API client.

import type { api, ChatEvent, Embed, Message, OpenedEmbed } from "./api";
import type { Language } from "./i18n";

/** The part of the API client the Workspace uses; tests pass a fake one. */
export type WorkspaceApi = Pick<
  typeof api,
  "myEmbeds" | "openEmbed" | "createEmbed" | "sendMessage" | "translate" | "changeEmbed" | "publish" | "attach"
>;

/** A message in the Conversation, the journalist's or the model's. */
export interface MessageTurn {
  kind: "message";
  role: Message["role"];
  text: string;
  guides: string[];
  version_number: number | null;
  error: string | null;
  /** The model's reply arriving right now. */
  live: boolean;
}

/** A Translation in the Conversation: the journalist typed nothing, so it's a marker. */
export interface TranslationMarker {
  kind: "translation";
  language: Language;
  /** Pending while its reply arrives; finished once its Version exists. */
  state: "pending" | "finished" | "failed";
  version_number: number | null;
}

export type Turn = MessageTurn | TranslationMarker;

export interface WorkspaceState {
  /** The journalist's embeds, newest first, as the sidebar lists them; null while loading. */
  embeds: Embed[] | null;
  /** The embed open (or opening); null for a new embed until it is created. */
  openId: string | null;
  /** Null while it opens, and for a new embed until the journalist first sends or attaches something. */
  embed: OpenedEmbed | null;
  /** The Embed language a new embed will be created in. */
  newEmbedLanguage: Language;
  loadError: string | null;
  turns: Turn[];
  /** The Version on screen. */
  shownNumber: number | null;
  /** The Work in progress: shown in the preview while a reply streams, never stored. */
  progressHtml: string | null;
  /** Whether a turn is streaming. */
  streaming: boolean;
  attaching: boolean;
  attachError: string | null;
}

export class Workspace {
  private state: WorkspaceState;
  private listeners = new Set<() => void>();
  private creating: Promise<OpenedEmbed> | null = null;
  /** Counts the embeds opened: work started on one embed must not land in the next. */
  private visit = 0;

  constructor(
    private readonly api: WorkspaceApi,
    private readonly journalist: string,
    newEmbedLanguage: Language = "nb",
  ) {
    this.state = { embeds: null, ...nothingOpen(null, newEmbedLanguage) };
  }

  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  getState = () => this.state;

  async loadEmbeds() {
    try {
      this.set({ embeds: await this.api.myEmbeds(this.journalist) });
    } catch {
      this.set({ embeds: [] });
    }
  }

  /** Open an existing embed, replacing whatever was open. */
  async open(embedId: string) {
    const isCurrent = this.replace(embedId, this.state.newEmbedLanguage);
    try {
      const opened = await this.api.openEmbed(this.journalist, embedId);
      const shownNumber = opened.latest_version?.number ?? null;
      if (isCurrent()) this.set({ embed: opened, turns: fromMessages(opened.messages), shownNumber });
    } catch (e) {
      if (isCurrent()) this.set({ loadError: (e as Error).message });
    }
  }

  /** Start a new, empty embed, created when the journalist first sends or attaches something. */
  startNew(newEmbedLanguage: Language) {
    this.replace(null, newEmbedLanguage);
  }

  /** Send the journalist's message; the reply streams into the Conversation. */
  async send(content: string, chatLanguage: Language) {
    await this.runTurn(journalistTurn(content), (id) =>
      this.api.sendMessage(this.journalist, id, content, chatLanguage),
    );
  }

  /**
   * A plain change while there is no Version yet. Once one exists it must be a Translation
   * (ADR 0004), which costs a model call and a Version, so the journalist is asked first.
   */
  async changeEmbedLanguage(language: Language): Promise<"changed" | "needs-translation"> {
    const { embed } = this.state;
    if (!embed) {
      this.set({ newEmbedLanguage: language });
      return "changed";
    }
    if (embed.versions.length > 0) return "needs-translation";
    const { embed_language } = await this.api.changeEmbed(this.journalist, embed.id, { embed_language: language });
    this.update({ id: embed.id, embed_language });
    return "changed";
  }

  /** Translate the current Version; the Embed language changes once the translated Version exists. */
  async translate(language: Language, chatLanguage: Language) {
    const marker: TranslationMarker = { kind: "translation", language, state: "pending", version_number: null };
    await this.runTurn(marker, (id) => this.api.translate(this.journalist, id, language, chatLanguage));
  }

  async attach(file: File) {
    const isCurrent = this.isCurrent();
    this.set({ attaching: true, attachError: null });
    try {
      const { id } = await this.ensureEmbed();
      const attachment = await this.api.attach(this.journalist, id, file);
      const { embed } = this.state;
      if (isCurrent()) this.set({ embed: { ...embed!, attachments: [...embed!.attachments, attachment] } });
    } catch (e) {
      if (isCurrent()) this.set({ attachError: (e as Error).message });
    } finally {
      if (isCurrent()) this.set({ attaching: false });
    }
  }

  show(number: number) {
    this.set({ shownNumber: number });
  }

  /** Publish a Version of the open embed; throws the server's reason (a blocker, unaccepted warnings). */
  async publish(number: number, acceptWarnings: boolean) {
    const isCurrent = this.isCurrent();
    const updated = await this.api.publish(this.journalist, this.state.embed!.id, number, acceptWarnings);
    if (isCurrent()) this.set({ embed: updated });
    this.update({ id: updated.id, published: true });
  }

  /** A new Title from the sidebar or the editor header. */
  async rename(embedId: string, title: string) {
    try {
      this.update(await this.api.changeEmbed(this.journalist, embedId, { title }));
    } catch {
      // Keep the old Title; both places still show it.
    }
  }

  /** Change an embed in the list and, if it's open, the open embed: one change, shown in both. */
  private update({ id, ...changes }: Pick<Embed, "id"> & Partial<Embed>) {
    const { embeds, embed } = this.state;
    this.set({
      embeds: embeds && embeds.map((e) => (e.id === id ? { ...e, ...changes } : e)),
      embed: embed?.id === id ? { ...embed, ...changes } : embed,
    });
  }

  private set(changes: Partial<WorkspaceState>) {
    this.state = { ...this.state, ...changes };
    this.listeners.forEach((listener) => listener());
  }

  /** Whether the embed open now is still the one open when this was called. */
  private isCurrent() {
    const visit = this.visit;
    return () => visit === this.visit;
  }

  /** Nothing of the embed open before stays; what's still arriving for it is dropped. */
  private replace(openId: string | null, newEmbedLanguage: Language) {
    this.visit++;
    this.creating = null;
    this.set(nothingOpen(openId, newEmbedLanguage));
    return this.isCurrent();
  }

  /** The embed to work on, creating it (once) first if this is a new one. */
  private ensureEmbed(): Promise<OpenedEmbed> {
    if (this.state.embed) return Promise.resolve(this.state.embed);
    const isCurrent = this.isCurrent();
    this.creating ??= this.api.createEmbed(this.journalist, this.state.newEmbedLanguage).then((created) => {
      const { id, title, created_at, embed_language, published } = created;
      const listed = { id, title, created_at, embed_language, published };
      this.set({ embeds: [listed, ...(this.state.embeds ?? [])] });
      if (isCurrent()) this.set({ openId: id, embed: created });
      return created;
    });
    return this.creating;
  }

  /** During a turn the Conversation ends with what was asked, then the model's reply. */
  private updateTurn<T extends Turn>(fromEnd: 1 | 2, update: (turn: T) => Partial<T>) {
    const turns = [...this.state.turns];
    const turn = turns.at(-fromEnd) as T;
    turns[turns.length - fromEnd] = { ...turn, ...update(turn) };
    this.set({ turns });
  }

  private updateReply(update: (turn: MessageTurn) => Partial<MessageTurn>) {
    this.updateTurn(1, update);
  }

  private async runTurn(asked: Turn, start: (embedId: string) => AsyncIterable<ChatEvent>) {
    const isCurrent = this.isCurrent();
    const reply: MessageTurn = { ...journalistTurn(""), role: "model", live: true };
    this.set({ streaming: true, turns: [...this.state.turns, asked, reply] });
    try {
      const { id } = await this.ensureEmbed();
      for await (const event of start(id)) {
        if (isCurrent()) this.handle(event);
        // The journalist left this embed: what changed about it still shows, in the list.
        else if (event.event === "title") this.update({ id, title: event.data.title });
        else if (event.event === "version" && asked.kind === "translation") {
          this.update({ id, embed_language: asked.language });
        }
      }
    } catch (e) {
      // A dropped connection: the turn ends, with the reason on it.
      if (isCurrent()) this.updateReply(() => ({ error: (e as Error).message }));
    } finally {
      if (isCurrent()) {
        this.updateReply(() => ({ live: false }));
        if (asked.kind === "translation") {
          this.updateTurn<TranslationMarker>(2, (m) => (m.state === "pending" ? { state: "failed" } : {}));
        }
        this.set({ progressHtml: null, streaming: false });
      }
    }
  }

  /** What each chat event does: the one place that says so. */
  private handle({ event, data }: ChatEvent) {
    const embed = this.state.embed!;
    if (event === "title") this.update({ id: embed.id, title: data.title });
    else if (event === "guide") this.updateReply((t) => ({ guides: [...t.guides, data.name] }));
    else if (event === "text") this.updateReply((t) => ({ text: t.text + data.delta }));
    else if (event === "progress") this.set({ progressHtml: data.html });
    else if (event === "version") {
      const asked = this.state.turns.at(-2);
      // A Translation's Embed language only becomes true once its Version exists (ADR 0004).
      const language = asked?.kind === "translation" ? asked.language : embed.embed_language;
      this.set({
        embed: { ...embed, embed_language: language, versions: [...embed.versions, data] },
        shownNumber: data.number,
      });
      this.updateReply(() => ({ version_number: data.number }));
      if (asked?.kind === "translation") {
        this.updateTurn<TranslationMarker>(2, () => ({ state: "finished", version_number: data.number }));
      }
    } else if (event === "error") this.updateReply(() => ({ error: data.message }));
    else if (event === "done") this.updateReply(() => ({ text: data.text }));
  }
}

/** The state of one open embed, before anything of it has loaded. */
function nothingOpen(openId: string | null, newEmbedLanguage: Language): Omit<WorkspaceState, "embeds"> {
  return {
    openId,
    embed: null,
    newEmbedLanguage,
    loadError: null,
    turns: [],
    shownNumber: null,
    progressHtml: null,
    streaming: false,
    attaching: false,
    attachError: null,
  };
}

function journalistTurn(text: string): MessageTurn {
  return { kind: "message", role: "journalist", text, guides: [], version_number: null, error: null, live: false };
}

/** The stored Conversation: a Translation marker finished if the reply after it made a Version. */
function fromMessages(messages: Message[]): Turn[] {
  return messages.map((m, i) => {
    if (m.kind === "message") return { ...m, kind: "message", error: null, live: false };
    const made = messages[i + 1]?.version_number ?? null;
    return {
      kind: "translation",
      language: m.text as Language,
      state: made === null ? "failed" : "finished",
      version_number: made,
    };
  });
}
