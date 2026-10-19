"""Interpret one chat turn without reading or writing the database."""

import json
import os
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import ValidationError

from .chat_schemas import (
    AdvisorTurn,
    GeminiAdvisorTurn,
    KeywordAddition,
)

class InvalidAdvisorResponse(ValueError):
    """Gemini returned an unusable response; do not save any changes."""


def _keyword_rows(rows, name):
    """Accept explicit keyword_id/keyword dictionaries, not SELECT * rows."""
    if not isinstance(rows, list):
        raise ValueError(f"{name} must be a list of keyword dictionaries.")
    cleaned = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{name} must contain dictionaries.")
        keyword_id, label = row.get("keyword_id"), row.get("keyword")
        if type(keyword_id) is not int or keyword_id <= 0:
            raise ValueError(f"{name} contains an invalid keyword_id.")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"{name} contains an empty keyword label.")
        if keyword_id in seen:
            raise ValueError(f"{name} contains a duplicate keyword_id.")
        seen.add(keyword_id)
        cleaned.append({"keyword_id": keyword_id, "keyword": label.strip()})
    return cleaned


def interpret_message(
    message,
    keyword_catalog,
    saved_keywords,
    recent_messages,
    *,
    client=None,
    model=None,
):
    """Return an AdvisorTurn proposing changes, without applying them.

    Keyword lists use {"keyword_id": 7, "keyword": "Biology"} dictionaries.
    History uses {"role": "user" or "assistant", "content": "..."} entries
    and must exclude the latest message. Configuration must already be loaded.
    Pass a reusable client from Flask, or let this function open/close one.
    Provider/network exceptions propagate for the caller to handle separately.
    """
    if not isinstance(message, str) or not 1 <= len(message.strip()) <= 4000:
        raise ValueError("Message must contain between 1 and 4000 characters.")
    message = message.strip()
    catalog = _keyword_rows(keyword_catalog, "keyword_catalog")
    saved = _keyword_rows(saved_keywords, "saved_keywords")
    allowed = {row["keyword_id"]: row["keyword"] for row in catalog}
    keyword_ids = {
    row["keyword"]: row["keyword_id"]
        for row in catalog
    }
    if len(keyword_ids) != len(catalog):
        raise ValueError(
            "Keyword names must be unique to translate names into IDs."
        )

    saved_ids = {row["keyword_id"] for row in saved}
    if any(allowed.get(row["keyword_id"]) != row["keyword"] for row in saved):
        raise ValueError("Saved keywords must match the supplied catalog.")

    if not isinstance(recent_messages, list):
        raise ValueError("recent_messages must be a list.")
    history = []
    for entry in recent_messages[-20:]:
        if not isinstance(entry, dict) or entry.get("role") not in ("user", "assistant"):
            raise ValueError("History entries need a user or assistant role.")
        content = entry.get("content")
        if not isinstance(content, str) or not 1 <= len(content.strip()) <= 4000:
            raise ValueError("History content must contain 1 to 4000 characters.")
        history.append({"role": entry["role"], "content": content.strip()})

    model = model or os.environ.get("GEMINI_MODEL")
    if not model or not model.strip():
        raise ValueError("Set GEMINI_MODEL to a model available to your project.")
    prompt = (Path(__file__).parent / "prompts" / "advisor.txt").read_text(
        encoding="utf-8"
    )
    context = {
        "keyword_catalog": [row["keyword"] for row in catalog],
        "saved_keywords": [row["keyword"] for row in saved],
        "recent_messages": history,
        "latest_message": message,
    }

    config = types.GenerateContentConfig(
        system_instruction=prompt,
        response_mime_type="application/json",
        response_json_schema=GeminiAdvisorTurn.model_json_schema(),
    )

    context_json = json.dumps(
        context,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    print(
        f"Gemini request: model={model}, "
        f"catalog_keywords={len(catalog)}, "
        f"saved_keywords={len(saved)}, "
        f"history_messages={len(history)}, "
        f"context_bytes={len(context_json.encode('utf-8'))}",
        flush=True,
    )

    arguments = dict(
        model=model,
        contents=context_json,
        config=config,
    )
    if client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Set GEMINI_API_KEY before calling Gemini.")
        with genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
            timeout=90000,
            retry_options=types.HttpRetryOptions(
                attempts=3,
                initial_delay=2.0,
                max_delay=8.0,
                exp_base=2.0,
                jitter=1.0,
                http_status_codes=[503, 504],
            ),
        ),
        ) as owned_client:
            response = owned_client.models.generate_content(**arguments)
    else:
        response = client.models.generate_content(**arguments)

    if not response.text:
        raise InvalidAdvisorResponse(
            "Gemini returned no text; try again."
        )

    try:
        gemini_turn = GeminiAdvisorTurn.model_validate_json(
            response.text
        )
    except ValidationError as error:
        raise InvalidAdvisorResponse(
            "Gemini returned an invalid response structure."
        ) from error

    addition_names = [
        item.keyword
        for item in gemini_turn.keyword_additions
    ]
    removal_names = gemini_turn.keyword_removals

    # Reject names that do not exactly match a catalog entry.
    selected_names = set(addition_names) | set(removal_names)

    if not selected_names <= keyword_ids.keys():
        raise InvalidAdvisorResponse(
            "Gemini returned an unknown keyword."
        )

    # Reject repeated changes.
    if (
        len(set(addition_names)) != len(addition_names)
        or len(set(removal_names)) != len(removal_names)
    ):
        raise InvalidAdvisorResponse(
            "Gemini returned duplicate keyword changes."
        )

    # A keyword cannot be added and removed in the same turn.
    if set(addition_names) & set(removal_names):
        raise InvalidAdvisorResponse(
            "Gemini both added and removed the same keyword."
        )

    removal_ids = [
        keyword_ids[name]
        for name in removal_names
    ]

    if not set(removal_ids) <= saved_ids:
        raise InvalidAdvisorResponse(
            "Gemini removed a keyword that was not saved."
        )

    # Check that evidence comes from the user's latest message.
    normalized_message = " ".join(message.casefold().split())

    for item in gemini_turn.keyword_additions:
        normalized_evidence = " ".join(
            item.evidence.casefold().split()
        )

        if normalized_evidence not in normalized_message:
            raise InvalidAdvisorResponse(
                "Keyword evidence was not in the latest message."
            )

    # Convert the Gemini response to the application's existing format.
    return AdvisorTurn(
        reply=gemini_turn.reply,
        keyword_additions=[
            KeywordAddition(
                keyword_id=keyword_ids[item.keyword],
                evidence=item.evidence,
            )
            for item in gemini_turn.keyword_additions
        ],
        keyword_removals=removal_ids,
        major_mentions=gemini_turn.major_mentions,
    )
