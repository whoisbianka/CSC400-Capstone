import os
from dotenv import load_dotenv
from google import genai

# Load the Gemini API key from .env
load_dotenv()

# Connect to Google Gemini
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Send our first message
response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents="Hello Gemini! I'm building a college major recommendation chatbot. Please introduce yourself in one sentence."
)

print("Gemini response:")
print(response.text)