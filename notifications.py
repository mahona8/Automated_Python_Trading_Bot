import os
import requests
from dotenv import load_dotenv

load_dotenv()

NTFY_TOPIC = os.getenv("NTFY_TOPIC")


def send_failure_notification(message):
    url = f"https://ntfy.sh/{NTFY_TOPIC}"

    requests.post(
        url,
        data=message.encode("utf-8"),
        headers={
            "Title": "Trading Program Failure",
            "Priority": "urgent",
        },
        timeout=10,
    )