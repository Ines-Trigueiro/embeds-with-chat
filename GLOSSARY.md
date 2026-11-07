# Embeds with chat

A tool where a journalist describes an interactive element in a chat with a model, previews it, and publishes it for embedding in a news article.

## People

**Journalist**:
The person who creates embeds by chatting with the model. Not assumed to be a developer and never edits code directly.
_Avoid_: User, author, editor

**Reader**:
A member of the public viewing an article that contains a published embed.
_Avoid_: Visitor, end user

## Embeds

**Embed**:
An interactive element (calculator, quiz, map, chart) that a journalist works on over a chat, owned by one journalist and listed under "My embeds".
_Avoid_: Widget, component, interactive, project

**Version**:
One immutable HTML document of an embed, produced by a single model reply. An embed has an ordered history of versions.
_Avoid_: Revision, draft, snapshot

**Embed language**:
The language readers see an embed's text in, chosen per embed. Independent of the language the journalist chats in.
_Avoid_: Locale, content language

**Work in progress**:
The HTML the model has written so far, while its reply is still streaming. Shown in the preview, but never stored and never a version.
_Avoid_: Draft, partial, preview

**Conversation**:
The ordered messages between the journalist and the model for one embed.
_Avoid_: Thread, session, history

**Published version**:
A version the journalist has explicitly approved for readers. Only published versions are reachable by readers; all other versions are private to the journalist.
_Avoid_: Live version, release

**Publish**:
The journalist's act of making one version a published version, after it passes the quality check.
_Avoid_: Deploy, release, go live

**Quality check**:
The set of rules a version is checked against before it may be published. A violation either blocks publishing or is shown to the journalist as a warning they may override.
_Avoid_: Validation, lint, review

**Guide**:
Best-practice instructions for the model about one kind of embed (for example quiz or map). The model chooses which guides to consult; a base guide always applies.
_Avoid_: Skill, template, recipe

**Attachment**:
A file the journalist adds to an embed's conversation: either a dataset or an image.
_Avoid_: Upload, file

**Dataset**:
A spreadsheet attachment whose rows are carried into a version verbatim, never retyped by the model.
_Avoid_: Data file, table, spreadsheet

**Image**:
An image attachment, used either as content shown inside the embed or as a visual reference for the model.
_Avoid_: Picture, asset

**Article page**:
A page outside this tool that hosts a published embed for readers.
_Avoid_: Host page, parent page

## Delivery

**Editor origin**:
The address the journalist uses to chat, preview and publish. Never serves embeds to readers.
_Avoid_: App, frontend, editor (alone, it reads as a person)

**Embed origin**:
The separate address that serves embeds, both to the preview and to readers. Kept apart from the editor origin so an embed can never act with the editor's privileges.
_Avoid_: CDN, embed server

**Snippet**:
The HTML the journalist pastes into an article to display an embed.
_Avoid_: Embed code, script tag

**Embed URL**:
A stable public address that serves an embed on its own.
_Avoid_: Link, share URL
