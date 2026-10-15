import os

API_KEY = os.environ.get("DEMO_API_KEY", "unset")


def summarize(text: str) -> str:
    return " ".join(text.split())[:280]
