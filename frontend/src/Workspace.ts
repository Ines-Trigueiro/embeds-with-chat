// The open embed and its Conversation, with no React: the editor subscribes and only renders.
// Every rule of a chat turn lives here, so it can be tested with a fake API client.

import type { api, ChatEvent, Embed, Message, OpenedEmbed } from "./api";
import type { Language } from "./i18n";

/** The part of the API client the Workspace uses; tests pass a fake one. */
export type WorkspaceApi = Pick<
  typeof api,
  "openEmbed" | "createEmbed" | "sendMessage" | "translate" | "changeEmbed" | "attach"
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
  /** Null for a new embed until the journalist first sends or attaches something. */
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

/**
 * Embed metadata the sidebar also shows. Until the Workspace holds the embed list too, these
 * tell App about it.
 */
export interface MetadataListener {
  created?: (embed: Embed) => void;
  changed?: (changes: Pick<Embed, "id"> & Partial<Embed>) => void;
}

export class Workspace {
  private state: WorkspaceState;
  private listeners = new Set<() => void>();
  private creating: Promise<OpenedEmbed> | null = null;

  constructor(
    private readonly api: WorkspaceApi,
    private readonly journalist: string,
    newEmbedLanguage: Language = "nb",
    private readonly metadata: MetadataListener = {},
  ) {
    this.state = {
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

  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  getState = () => this.state;

  /** Open an existing embed, replacing whatever was open. */
  async open(embedId: string) {
    try {
      const opened = await this.api.openEmbed(this.journalist, embedId);
      const shownNumber = opened.latest_version?.number ?? null;
      this.set({ embed: opened, turns: fromMessages(opened.messages), shownNumber });
    } catch (e) {
      this.set({ loadError: (e as Error).message });
    }
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
    const changed = await this.api.changeEmbed(this.journalist, embed.id, { embed_language: language });
    this.set({ embed: { ...this.state.embed!, embed_language: changed.embed_language } });
    return "changed";
  }

  /** Translate the current Version; the Embed language changes once the translated Version exists. */
  async translate(language: Language, chatLanguage: Language) {
    const marker: TranslationMarker = { kind: "translation", language, state: "pending", version_number: null };
    await this.runTurn(marker, (id) => this.api.translate(this.journalist, id, language, chatLanguage));
  }

  async attach(file: File) {
    this.set({ attaching: true, attachError: null });
    try {
      const { id } = await this.ensureEmbed();
      const attachment = await this.api.attach(this.journalist, id, file);
      const embed = this.state.embed!;
      this.set({ embed: { ...embed, attachments: [...embed.attachments, attachment] } });
    } catch (e) {
      this.set({ attachError: (e as Error).message });
    } finally {
      this.set({ attaching: false });
    }
  }

  show(number: number) {
    this.set({ shownNumber: number });
  }

  /** The publish dialog published a Version; this is the embed as the server now has it. */
  published(updated: OpenedEmbed) {
    this.set({ embed: updated });
    this.metadata.changed?.({ id: updated.id, published: true });
  }

  private set(changes: Partial<WorkspaceState>) {
    this.state = { ...this.state, ...changes };
    this.listeners.forEach((listener) => listener());
  }

  /** The embed to work on, creating it (once) first if this is a new one. */
  private ensureEmbed(): Promise<OpenedEmbed> {
    if (this.state.embed) return Promise.resolve(this.state.embed);
    this.creating ??= this.api.createEmbed(this.journalist, this.state.newEmbedLanguage).then((created) => {
      this.set({ embed: created });
      this.metadata.created?.(created);
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
    const reply: MessageTurn = { ...journalistTurn(""), role: "model", live: true };
    this.set({ streaming: true, turns: [...this.state.turns, asked, reply] });
    try {
      const { id } = await this.ensureEmbed();
      for await (const event of start(id)) this.handle(event);
    } catch (e) {
      // A dropped connection: the turn ends, with the reason on it.
      this.updateReply(() => ({ error: (e as Error).message }));
    } finally {
      this.updateReply(() => ({ live: false }));
      if (asked.kind === "translation") {
        this.updateTurn<TranslationMarker>(2, (m) => (m.state === "pending" ? { state: "failed" } : {}));
      }
      this.set({ progressHtml: null, streaming: false });
    }
  }

  /** What each chat event does: the one place that says so. */
  private handle({ event, data }: ChatEvent) {
    const embed = this.state.embed!;
    if (event === "title") {
      this.set({ embed: { ...embed, title: data.title } });
      this.metadata.changed?.({ id: embed.id, title: data.title });
    } else if (event === "guide") this.updateReply((t) => ({ guides: [...t.guides, data.name] }));
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
