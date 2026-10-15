import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

def find_trending_topic():
    url = "https://trends.google.com/trending/rss?geo=US"
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        root = ET.fromstring(response.read())

    items = root.findall(".//item")
    if not items:
        raise RuntimeError("No trending topics found")

    return items[0].findtext("title", "Science and technology")

def main():
    config = json.loads(Path("config.json").read_text())
    topic = find_trending_topic()

    job = {
        "topic": topic,
        "niche": config["niche"],
        "audience": config["target_audience"],
        "language": config["video_language"],
        "status": "idea_ready"
    }

    Path("content_queue.json").write_text(
        json.dumps(job, indent=2)
    )
    print(json.dumps(job, indent=2))

if __name__ == "__main__":
    main()
