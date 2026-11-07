# Work log

Notes on how I steered the coding assistant (Claude Code) during this assignment.

## 1. Design interview (before any code)

I had the assistant interview me in rounds about the design, with a recommended answer for every question, before any code was written. The output was `GLOSSARY.md` and three ADRs in `docs/adr/`.

Where I overrode its recommendations:
- **Frontend**: it recommended server-rendered Jinja templates with a little JS, to keep me in Python. I chose a React + TypeScript SPA.
- **Scope**: it recommended doing the core first, then building extensions in priority order and cutting what didn't fit the time. I chose to build all three: streaming, attachments and quality checks.
- **Manual editing**: I rejected it outright, because journalists should not touch code.
- **Images**: it recommended images only as content in the embed. I want them as content and as a visual reference for the model.
- **Language**: it proposed a Norwegian UI. I asked for a nb/da/en switch. The assistant then separated the journalist's chat language from the embed's language, and I accepted that.
- **Model**: Claude is the default, but any LangChain-supported model can be selected through an env var.

Where it pushed back on me:
- It warned that the combined scope (SPA + LangChain + streaming + attachments + quality checks) is large for 4–6 hours. I kept the scope.
- It asked me to clarify "skills". They became **Guides**: markdown best-practice files the model loads through a tool, named that way to avoid confusion with Claude Code skills.
- It pointed out that pinning versions in the snippet changes what "publish" means. The result: only explicitly published versions reach readers.
