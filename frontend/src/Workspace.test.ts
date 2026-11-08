import { describe, expect, it } from "vitest";

import type { ChatEvent, Embed, OpenedEmbed, Version } from "./api";
import { Workspace, type WorkspaceApi } from "./Workspace";

/**
 * One scripted turn: its events in order. An Error in the list is thrown there, mid-stream; a
 * Promise holds the stream there until it resolves.
 */
type ScriptedTurn = (ChatEvent | Error | Promise<void>)[];

/**
 * A fake API client whose turns are played back from a script, in order. `embed` is what opening
 * any embed returns, `others` what opening one of the others does; the list is the journalist's.
 */
function fakeApi(
  turns: ScriptedTurn[] = [],
  embed: Partial<OpenedEmbed> = {},
  { list = [], others = {} }: { list?: Embed[]; others?: Record<string, Partial<OpenedEmbed>> } = {},
) {
  const created: OpenedEmbed[] = [];
  const opened = (overrides: Partial<OpenedEmbed>): OpenedEmbed => ({
    id: "e1",
    title: null,
    created_at: "2026-01-01T00:00:00Z",
    embed_language: "nb",
    published: false,
    messages: [],
    attachments: [],
    versions: [],
    latest_version: null,
    progress_frame_url: "/progress",
    delivery: null,
    ...overrides,
  });
  async function* play(): AsyncGenerator<ChatEvent> {
    for (const step of turns.shift() ?? []) {
      if (step instanceof Error) throw step;
      if (step instanceof Promise) await step;
      else yield step;
    }
  }
  const api: WorkspaceApi = {
    myEmbeds: async () => list,
    openEmbed: async (_journalist, id) => opened({ ...embed, ...others[id], id }),
    createEmbed: async (_journalist, embed_language) => {
      const fresh = opened({ embed_language });
      created.push(fresh);
      return fresh;
    },
    sendMessage: () => play(),
    translate: () => play(),
    changeEmbed: async (_journalist, id, changes) => ({ ...opened({ ...embed, id }), ...changes }),
    publish: async (_journalist, id, number) => {
      const versions = (embed.versions ?? []).map((v) => (v.number === number ? { ...v, published: true } : v));
      return opened({ ...embed, id, published: true, versions, delivery: { snippet: "<script>", embed_url: "/e" } });
    },
    attach: async (_journalist, _id, file) => ({
      id: "a1",
      kind: "dataset",
      name: file.name,
      created_at: "2026-01-01T00:00:00Z",
      rows: 3,
      columns: [],
      url: null,
    }),
  };
  return { api, created };
}

function listed(id: string, title: string | null = null): Embed {
  return { id, title, created_at: "2026-01-01T00:00:00Z", embed_language: "nb", published: false };
}

function version(number: number): Version {
  return {
    number,
    created_at: "2026-01-01T00:00:00Z",
    preview_url: `/preview/${number}`,
    published: false,
    delivery: null,
    findings: [],
  };
}

/** The model's reply: the last turn in the Conversation. */
function reply(workspace: Workspace) {
  const last = workspace.getState().turns.at(-1);
  if (last?.kind !== "message") throw new Error("The last turn is not a message.");
  return last;
}

describe("Workspace", () => {
  it("creates a new Embed once when the first message is sent, names it and builds up the reply", async () => {
    const { api, created } = fakeApi([
      [
        { event: "title", data: { title: "Rent calculator" } },
        { event: "text", data: { delta: "Here is " } },
        { event: "text", data: { delta: "your calculator." } },
        { event: "done", data: { text: "Here is your calculator." } },
      ],
      [{ event: "done", data: { text: "Sure." } }],
    ]);
    const workspace = new Workspace(api, "Kari");
    const replySoFar: string[] = [];
    const stop = workspace.subscribe(() => {
      const last = workspace.getState().turns.at(-1);
      if (last?.kind === "message" && last.role === "model" && last.live) replySoFar.push(last.text);
    });

    await workspace.send("A rent calculator", "en");
    stop();
    expect(replySoFar).toContain("Here is ");
    expect(replySoFar).toContain("Here is your calculator.");
    await workspace.send("Make it blue", "en");

    expect(created).toHaveLength(1);
    const { embed, turns, streaming } = workspace.getState();
    expect(embed?.id).toBe("e1");
    expect(embed?.title).toBe("Rent calculator");
    expect(streaming).toBe(false);
    expect(turns.map((t) => t.kind === "message" && [t.role, t.text])).toEqual([
      ["journalist", "A rent calculator"],
      ["model", "Here is your calculator."],
      ["journalist", "Make it blue"],
      ["model", "Sure."],
    ]);
  });

  it("shows a Guide lookup before the text that follows it", async () => {
    const { api } = fakeApi([
      [
        { event: "guide", data: { name: "quiz" } },
        { event: "text", data: { delta: "A quiz." } },
        { event: "done", data: { text: "A quiz." } },
      ],
    ]);
    const workspace = new Workspace(api, "Kari");

    await workspace.send("A quiz", "en");

    expect(reply(workspace)).toMatchObject({ guides: ["quiz"], text: "A quiz.", live: false });
  });

  it("shows the new Version as soon as its version event arrives", async () => {
    const { api } = fakeApi([
      [
        { event: "progress", data: { html: "<p>Half" } },
        { event: "version", data: version(1) },
        { event: "done", data: { text: "Done." } },
      ],
    ]);
    const workspace = new Workspace(api, "Kari");
    const workInProgress: (string | null)[] = [];
    workspace.subscribe(() => workInProgress.push(workspace.getState().progressHtml));

    await workspace.send("A chart", "en");

    const { embed, shownNumber, progressHtml } = workspace.getState();
    expect(embed?.versions.map((v) => v.number)).toEqual([1]);
    expect(shownNumber).toBe(1);
    expect(reply(workspace).version_number).toBe(1);
    expect(workInProgress).toContain("<p>Half");
    expect(progressHtml).toBeNull();
  });

  it("shows an error on the turn, with what the model said before it", async () => {
    const { api } = fakeApi([
      [
        { event: "text", data: { delta: "Let me" } },
        { event: "error", data: { message: "The model is busy." } },
        { event: "done", data: { text: "Let me" } },
      ],
    ]);
    const workspace = new Workspace(api, "Kari");

    await workspace.send("A map", "en");

    expect(reply(workspace)).toMatchObject({ text: "Let me", error: "The model is busy.", live: false });
    expect(workspace.getState().streaming).toBe(false);
  });

  it("ends the turn with an error when the stream breaks off", async () => {
    const { api } = fakeApi([[{ event: "text", data: { delta: "Half a" } }, new Error("Network error")]]);
    const workspace = new Workspace(api, "Kari");

    await workspace.send("A map", "en");

    expect(reply(workspace)).toMatchObject({ text: "Half a", error: "Network error", live: false });
    expect(workspace.getState()).toMatchObject({ streaming: false, progressHtml: null });
  });

  describe("changing the Embed language once a Version exists", () => {
    const withVersion = { embed_language: "nb" as const, versions: [version(1)], latest_version: version(1) };

    /** The Translation marker: the last turn but one, before the model's reply. */
    function marker(workspace: Workspace) {
      const turn = workspace.getState().turns.at(-2);
      if (turn?.kind !== "translation") throw new Error("No Translation marker.");
      return turn;
    }

    it("asks for a Translation, which finishes with its Version and changes the Embed language", async () => {
      const { api } = fakeApi(
        [
          [
            { event: "version", data: version(2) },
            { event: "done", data: { text: "Translated." } },
          ],
        ],
        withVersion,
      );
      const workspace = new Workspace(api, "Kari");
      await workspace.open("e1");
      const whilePending: string[] = [];
      workspace.subscribe(() => {
        const { turns, embed } = workspace.getState();
        const turn = turns.at(-2);
        if (turn?.kind === "translation" && turn.state === "pending") whilePending.push(embed!.embed_language);
      });

      expect(await workspace.changeEmbedLanguage("en")).toBe("needs-translation");
      expect(workspace.getState().embed?.embed_language).toBe("nb");
      await workspace.translate("en", "en");

      expect(whilePending).toContain("nb");
      expect(marker(workspace)).toMatchObject({ language: "en", state: "finished", version_number: 2 });
      expect(workspace.getState()).toMatchObject({ shownNumber: 2, embed: { embed_language: "en" } });
    });

    it("marks a failed Translation and keeps the Embed language", async () => {
      const { api } = fakeApi(
        [
          [
            { event: "error", data: { message: "The model is busy." } },
            { event: "done", data: { text: "" } },
          ],
        ],
        withVersion,
      );
      const workspace = new Workspace(api, "Kari");
      await workspace.open("e1");

      await workspace.translate("en", "en");

      expect(marker(workspace)).toMatchObject({ language: "en", state: "failed", version_number: null });
      expect(workspace.getState()).toMatchObject({ shownNumber: 1, embed: { embed_language: "nb" } });
    });
  });

  it("changes the Embed language straight away while there is no Version", async () => {
    const { api } = fakeApi([], { embed_language: "nb" }, { list: [listed("e1")] });
    const workspace = new Workspace(api, "Kari");
    await workspace.loadEmbeds();
    await workspace.open("e1");

    expect(await workspace.changeEmbedLanguage("da")).toBe("changed");

    expect(workspace.getState().embed?.embed_language).toBe("da");
    expect(workspace.getState().embeds?.[0].embed_language).toBe("da");
  });

  it("creates a new Embed in the chosen Embed language before attaching a file to it", async () => {
    const { api, created } = fakeApi();
    const workspace = new Workspace(api, "Kari", "nb");
    await workspace.changeEmbedLanguage("en");

    await workspace.attach(new File(["a,b"], "rents.csv"));

    expect(created.map((e) => e.embed_language)).toEqual(["en"]);
    expect(workspace.getState()).toMatchObject({ attaching: false, attachError: null });
    expect(workspace.getState().embed?.attachments.map((a) => a.name)).toEqual(["rents.csv"]);
  });

  it("opens an Embed with its Conversation, a finished Translation and its latest Version shown", async () => {
    const { api } = fakeApi([], {
      versions: [version(1), version(2)],
      latest_version: version(2),
      messages: [
        { role: "journalist", kind: "message", text: "A quiz", version_number: null, guides: [] },
        { role: "model", kind: "message", text: "Here.", version_number: 1, guides: ["quiz"] },
        { role: "journalist", kind: "translation", text: "en", version_number: null, guides: [] },
        { role: "model", kind: "message", text: "Translated.", version_number: 2, guides: [] },
      ],
    });
    const workspace = new Workspace(api, "Kari");

    await workspace.open("e1");

    const { turns, shownNumber } = workspace.getState();
    expect(shownNumber).toBe(2);
    expect(turns[2]).toMatchObject({ kind: "translation", language: "en", state: "finished", version_number: 2 });
    expect(turns.every((t) => t.kind === "translation" || !t.live)).toBe(true);
  });

  it("loads the journalist's embeds", async () => {
    const { api } = fakeApi([], {}, { list: [listed("e1", "Rent calculator"), listed("e2", "Election map")] });
    const workspace = new Workspace(api, "Kari");
    expect(workspace.getState().embeds).toBeNull();

    await workspace.loadEmbeds();

    expect(workspace.getState().embeds?.map((e) => e.title)).toEqual(["Rent calculator", "Election map"]);
  });

  it("renames the open Embed in the list and the editor at once", async () => {
    const { api } = fakeApi([], { title: "Rent calculator" }, { list: [listed("e1", "Rent calculator"), listed("e2")] });
    const workspace = new Workspace(api, "Kari");
    await workspace.loadEmbeds();
    await workspace.open("e1");

    await workspace.rename("e1", "Rents in Oslo");

    const { embeds, embed } = workspace.getState();
    expect(embeds?.map((e) => e.title)).toEqual(["Rents in Oslo", null]);
    expect(embed?.title).toBe("Rents in Oslo");
  });

  it("publishes the Version on screen: the list shows the embed published and the Version is published", async () => {
    const versions = [version(1), version(2)];
    const { api } = fakeApi([], { versions, latest_version: version(2) }, { list: [listed("e1"), listed("e2")] });
    const workspace = new Workspace(api, "Kari");
    await workspace.loadEmbeds();
    await workspace.open("e1");

    await workspace.publish(2, false);

    const { embeds, embed } = workspace.getState();
    expect(embeds?.map((e) => e.published)).toEqual([true, false]);
    expect(embed?.versions.map((v) => v.published)).toEqual([false, true]);
    expect(embed?.delivery).not.toBeNull();
  });

  it("adds a new Embed to the top of the list on its first message, with its suggested Title", async () => {
    const { api } = fakeApi(
      [
        [
          { event: "title", data: { title: "Rent calculator" } },
          { event: "done", data: { text: "Here." } },
        ],
      ],
      {},
      { list: [listed("e0", "Election map")] },
    );
    const workspace = new Workspace(api, "Kari");
    await workspace.loadEmbeds();

    await workspace.send("A rent calculator", "en");

    const { embeds, openId } = workspace.getState();
    expect(embeds?.map((e) => [e.id, e.title])).toEqual([
      ["e1", "Rent calculator"],
      ["e0", "Election map"],
    ]);
    expect(openId).toBe("e1");
  });

  describe("opening another Embed", () => {
    const first = {
      versions: [version(1)],
      latest_version: version(1),
      messages: [
        { role: "journalist" as const, kind: "message" as const, text: "A quiz", version_number: null, guides: [] },
        { role: "model" as const, kind: "message" as const, text: "Here.", version_number: 1, guides: [] },
      ],
    };

    it("replaces the Conversation and Versions entirely", async () => {
      const { api } = fakeApi([], first, { others: { e2: { versions: [], latest_version: null, messages: [] } } });
      const workspace = new Workspace(api, "Kari");
      await workspace.open("e1");

      await workspace.open("e2");

      expect(workspace.getState()).toMatchObject({ openId: "e2", turns: [], shownNumber: null });
      expect(workspace.getState().embed).toMatchObject({ id: "e2", versions: [] });
    });

    it("keeps a late reply from the Embed it left out of the one it opened", async () => {
      let release = () => {};
      const held = new Promise<void>((resolve) => (release = resolve));
      const { api } = fakeApi(
        [
          [
            { event: "text", data: { delta: "Half" } },
            held,
            { event: "title", data: { title: "Quiz" } },
            { event: "version", data: version(2) },
            { event: "done", data: { text: "Done." } },
          ],
        ],
        first,
        { list: [listed("e1"), listed("e2", "Map")], others: { e2: { versions: [], latest_version: null, messages: [] } } },
      );
      const workspace = new Workspace(api, "Kari");
      await workspace.loadEmbeds();
      await workspace.open("e1");
      const sending = workspace.send("Make it blue", "en");

      await workspace.open("e2");
      release();
      await sending;

      const { embed, turns, shownNumber, streaming, embeds } = workspace.getState();
      expect(embed).toMatchObject({ id: "e2", title: null, versions: [] });
      expect({ turns, shownNumber, streaming }).toEqual({ turns: [], shownNumber: null, streaming: false });
      expect(embeds?.map((e) => e.title)).toEqual(["Quiz", "Map"]);
    });

    it("starts a new Embed with nothing of the one that was open", async () => {
      const { api } = fakeApi([], first);
      const workspace = new Workspace(api, "Kari");
      await workspace.open("e1");

      workspace.startNew("en");

      expect(workspace.getState()).toMatchObject({ openId: null, embed: null, turns: [], newEmbedLanguage: "en" });
    });
  });
});
