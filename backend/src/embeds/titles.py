"""The Title of an embed: suggested once, from the journalist's first message."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

MAX_TITLE_LENGTH = 60

INSTRUCTIONS = (
    "Suggest a short title (2 to 6 words) for the interactive news embed a journalist is "
    "asking for below, in the language they write in. Reply with the title only: no quotes, "
    "no explanation."
)


async def suggest_title(model: BaseChatModel, first_message: str) -> str:
    """The model's suggestion, or the start of the message if the model can't give one."""
    try:
        reply = await model.ainvoke([SystemMessage(INSTRUCTIONS), HumanMessage(first_message)])
        title = _cleaned(reply.text)
    except Exception:  # The provider failed: a title is not worth failing the turn for.
        title = ""
    return title or _shortened(first_message)


def _cleaned(text: str) -> str:
    lines = text.strip().splitlines()
    first = lines[0] if lines else ""
    return _shortened(first.strip().strip("\"'*#`«»“”").strip())


def _shortened(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= MAX_TITLE_LENGTH:
        return text
    cut = text[: MAX_TITLE_LENGTH - 1].rsplit(" ", 1)[0]
    return f"{cut}…"
