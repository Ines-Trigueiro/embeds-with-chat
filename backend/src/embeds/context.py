"""What the model sees each turn.

The text of every earlier message, but the HTML of only the latest Version, attached
to the new request. Older HTML would cost tens of thousands of tokens and invite the
model to edit the wrong document; "make the buttons bigger" always means the latest.
"""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from embeds.store import Message, Version


def turn_context(
    system: str, conversation: list[Message], latest: Version | None, request: str
) -> list[BaseMessage]:
    messages: list[BaseMessage] = [SystemMessage(system)]
    for message in conversation:
        if message.role == "journalist":
            messages.append(HumanMessage(message.text))
        else:
            messages.append(AIMessage(message.text))
    messages.append(HumanMessage(_with_current_version(request, latest)))
    return messages


def _with_current_version(request: str, latest: Version | None) -> str:
    if latest is None:
        return request
    return (
        f"The current version of the embed (version {latest.number}) is:\n\n"
        f"```html\n{latest.html}\n```\n\n"
        "Apply the journalist's request below to this version and reply with the whole "
        "updated document. If the request is only a question, answer it without HTML.\n\n"
        f"Journalist's request: {request}"
    )
