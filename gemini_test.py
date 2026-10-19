import csv
import json
import os
import time
from pathlib import Path

import certifi
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault(
    "REQUESTS_CA_BUNDLE",
    os.environ["SSL_CERT_FILE"],
)

from google import genai
from google.genai import errors
from pydantic import ValidationError

from degree_path.chat_schemas import AdvisorTurn


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    configured_model = os.environ.get("GEMINI_MODEL")

    if not api_key or not configured_model:
        raise RuntimeError(
            "Set GEMINI_API_KEY and GEMINI_MODEL in .env."
        )

    model = configured_model.strip().removeprefix("models/")

    with (BASE_DIR / "tables" / "kwd_list.csv").open(
        newline="",
        encoding="utf-8",
    ) as file:
        catalog = [
            {
                "keyword_id": int(row["id"]),
                "keyword": row["keyword"],
            }
            for row in csv.DictReader(file)
        ]

    message = "I enjoy biology."

    context = {
        "keyword_catalog": catalog,
        "saved_keywords": [],
        "recent_messages": [],
        "latest_message": message,
    }

    prompt = (
        BASE_DIR / "degree_path" / "prompts" / "advisor.txt"
    ).read_text(encoding="utf-8")

    payload = json.dumps(context)

    print("API: Interactions")
    print("Model:", model)
    print("Keywords:", len(catalog))
    print("Context bytes:", len(payload.encode("utf-8")))
    print("Sending request…", flush=True)

    started = time.monotonic()

    try:
        with genai.Client(api_key=api_key) as client:
            interaction = client.interactions.create(
                model=model,
                input=payload,
                system_instruction=prompt,
                response_format=[
                    {
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": AdvisorTurn.model_json_schema(),
                    }
                ],
                store=False,
                timeout=90.0,
            )

        print("Status:", interaction.status)

        output = interaction.output_text

        if not output:
            raise ValueError(
                "The interaction returned no output text."
            )

        turn = AdvisorTurn.model_validate_json(output)

        allowed_ids = {
            item["keyword_id"] for item in catalog
        }

        addition_ids = [
            item.keyword_id
            for item in turn.keyword_additions
        ]

        if not set(addition_ids) <= allowed_ids:
            raise ValueError(
                "The response contains an unknown keyword ID."
            )

        if len(addition_ids) != len(set(addition_ids)):
            raise ValueError(
                "The response contains duplicate additions."
            )

        if turn.keyword_removals:
            raise ValueError(
                "There are no saved keywords to remove."
            )

        normalized_message = " ".join(
            message.casefold().split()
        )

        for addition in turn.keyword_additions:
            evidence = " ".join(
                addition.evidence.casefold().split()
            )

            if evidence not in normalized_message:
                raise ValueError(
                    "Evidence does not match the test message."
                )

        print("SUCCESS")
        print(turn.model_dump_json(indent=2))

    except errors.APIError as error:
        print("API error:", error.code, error.message)

    except ValidationError as error:
        print("Response schema validation failed:", error)

    except ValueError as error:
        print("Response validation failed:", error)

    finally:
        elapsed = time.monotonic() - started
        print(f"Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()