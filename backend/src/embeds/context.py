"""What the model sees each turn.

The text of every earlier message, but the HTML of only the latest Version, attached
to the new request. Older HTML would cost tens of thousands of tokens and invite the
model to edit the wrong document; "make the buttons bigger" always means the latest.
Datasets are described (schema and a sample), never included in full (ADR 0002).
"""

import base64
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from embeds.datasets import DatasetAttachment, describe_for_model, without_dataset_contents
from embeds.images import ImageForModel
from embeds.store import Message, Version


def turn_context(
    system: str,
    conversation: list[Message],
    latest: Version | None,
    request: str,
    datasets: list[DatasetAttachment],
    images: list[ImageForModel],
) -> list[BaseMessage]:
    messages: list[BaseMessage] = [SystemMessage(system)]
    for message in conversation:
        if message.role == "journalist":
            messages.append(HumanMessage(message.text))
        else:
            messages.append(AIMessage(message.text))
    text = _request_with_context(request, latest, datasets, images)
    if not images:
        messages.append(HumanMessage(text))
        return messages
    # Vision input: the images themselves, after the text that says what each one is.
    content: list[str | dict[str, Any]] = [{"type": "text", "text": text}]
    for image in images:
        data = base64.b64encode(image.content).decode()
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:{image.media_type};base64,{data}"}}
        )
    messages.append(HumanMessage(content=content))
    return messages


def _request_with_context(
    request: str, latest: Version | None, datasets: list[DatasetAttachment], images: list[ImageForModel]
) -> str:
    parts = []
    if images:
        listed = "\n".join(f'- Image "{i.name}", at {i.url}' for i in images)
        parts.append(f"Images the journalist has attached, shown in this order:\n{listed}")
    if datasets:
        described = "\n".join(describe_for_model(d) for d in datasets)
        parts.append(f"Datasets the journalist has attached:\n{described}")
    if latest is not None:
        parts.append(
            f"The current version of the embed (version {latest.number}) is:\n\n"
            f"```html\n{without_dataset_contents(latest.html)}\n```\n\n"
            "Apply the journalist's request below to this version and reply with the whole "
            "updated document. If the request is only a question, answer it without HTML."
        )
    if not parts:
        return request
    return "\n\n".join([*parts, f"Journalist's request: {request}"])
