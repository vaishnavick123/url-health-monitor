import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
API_TOKEN = os.getenv("API_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}"
}

CANDIDATE_LABELS = [
    "news",
    "shopping",
    "social media",
    "technology",
    "health",
    "education",
    "finance",
    "entertainment",
    "travel",
    "sports",
]

def classify_url(url_text: str) -> str:
    """
    Classify a URL (or associated text) into one of the candidate categories.
    Uses zero-shot classification from Hugging Face Inference API.
    """
    payload = {
        "inputs": url_text,
        "parameters": {
            "candidate_labels": CANDIDATE_LABELS
        }
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        # Get the label with the highest score
        top_label = result["labels"][0] if "labels" in result else "unknown"
        return top_label
    except Exception as e:
        print(f"Error classifying URL '{url_text}': {e}")
        return "unknown"
