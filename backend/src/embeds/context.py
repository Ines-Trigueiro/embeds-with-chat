"""What the model sees each turn.

The text of every earlier message, but the HTML of only the latest Version, attached
to the new request. Older HTML would cost tens of thousands of tokens and invite the
model to edit the wrong document; "make the buttons bigger" always means the latest.
Datasets are described (schema and a sample), never included in full (ADR 0002).
"""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from embeds.datasets import ParsedDataset, describe_for_model, without_dataset_contents
from embeds.store import Message, Version

Datasets = dict[str, tuple[str, ParsedDataset]]  # id -> (file name, dataset)


def turn_context(
    system: str,
    conversation: list[Message],
    latest: Version | None,
    request: str,
    datasets: Datasets | None = None,
) -> list[BaseMessage]:
    messages: list[BaseMessage] = [SystemMessage(system)]
    for message in conversation:
        if message.role == "journalist":
            messages.append(HumanMessage(message.text))
        else:
            messages.append(AIMessage(message.text))
    messages.append(HumanMessage(_request_with_context(request, latest, datasets or {})))
    return messages


def _request_with_context(request: str, latest: Version | None, datasets: Datasets) -> str:
    parts = []
    if datasets:
        described = "\n".join(
            describe_for_model(dataset_id, name, dataset)
            for dataset_id, (name, dataset) in datasets.items()
        )
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
