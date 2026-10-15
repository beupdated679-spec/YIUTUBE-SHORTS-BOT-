import os
import json
import urllib.request
import time

def generate_metadata(topic):
    api_key = os.environ.get("AI_API_KEY")

    if not api_key:
        raise ValueError("AI_API_KEY secret is missing.")

    prompt = f"""
Create YouTube Shorts metadata for this topic: {topic}

Return ONLY valid JSON with these fields:
{{
  "title": "Catchy title under 100 characters",
  "description": "Engaging description",
  "hashtags": ["#Shorts", "#RelevantHashtag"]
}}
Use relevant hashtags. Do not invent facts.
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-3.8-flash:generateContent"
        f"?key={api_key}"
    )

    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    for attempt in range(3):
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        break
    except urllib.error.HTTPError as e:
        if e.code != 503 or attempt == 2:
            raise
        time.sleep(2 ** (attempt + 1))

    text = result["candidates"][0]["content"]["parts"][0]["text"]
    text = text.strip().removeprefix("```json").removesuffix("```").strip()

    return json.loads(text)

if __name__ == "__main__":
    metadata = generate_metadata("Amazing space facts")
    print(json.dumps(metadata, indent=2))
