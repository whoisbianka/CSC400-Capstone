import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load the Gemini API key from the .env file
load_dotenv()

# Initialize Google Gemini
client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

MODEL_NAME = "gemini-3.5-flash-lite"


def ask_gemini(question, history=None):
    """
    Send a student's question to Google Gemini
    and return the AI-generated response.

    Previous conversation messages can be included
    so Gemini understands follow-up answers.
    """

    # Validate the student's question
    if not isinstance(question, str) or not question.strip():
        return "Please enter a question about college majors or careers."

    contents = []

    # Include previous conversation messages
    if history:
        for message in history[-12:]:

            if not isinstance(message, dict):
                continue

            role = message.get("role")
            text = message.get("text")

            # Only accept valid conversation roles
            if role not in ("user", "model"):
                continue

            # Skip empty or invalid messages
            if not isinstance(text, str) or not text.strip():
                continue

            contents.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part.from_text(
                            text=text[:2000]
                        )
                    ]
                )
            )

    # Add the student's newest question
    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=question.strip()
                )
            ]
        )
    )

    # Send the conversation to Google Gemini
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
        config={
            "system_instruction": (
                "You are Degree Path Explorer, a helpful AI college "
                "and career exploration assistant. Your audience includes "
                "high school juniors, seniors, and first-year college "
                "students. Help students explore majors based on their "
                "interests, strengths, and career goals. "
                "Remember and build on previous conversation messages. "
                "Do not repeatedly ask questions already answered. "
                "Ask useful follow-up questions when needed. "
                "Keep responses friendly, clear, and concise. "
                "Do not invent college tuition, admissions statistics, "
                "or program availability. "
                "Do not ask for sensitive personal information."
            )
        }
    )

    # Return Gemini's answer
    return response.text or "Gemini did not return a response."
