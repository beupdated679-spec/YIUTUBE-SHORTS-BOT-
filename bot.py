import os
import json
import re
import subprocess
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

API_KEY = os.environ["AI_API_KEY"]
Path("output").mkdir(exist_ok=True)

def make_script(topic):
    prompt = (
        "Write an accurate, exciting 40-second YouTube Shorts narration "
        "about this science/technology topic: " + topic +
        ". Audience: United States. English. About 85 words. "
        "Return only the spoken narration, no title or stage directions."
    )
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-3.5-flash:generateContent?key=" + API_KEY,
        data=json.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode())
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

def main():
    config = json.loads(Path("config.json").read_text())
    with open("content_queue.json", encoding="utf-8") as f:
        queue = json.load(f)

    topic = queue["topic"]
    script = make_script(topic)
    Path("output/script.txt").write_text(script, encoding="utf-8")

    # Generate narration
    gTTS(text=script, lang="en", tld="com").save("output/voice.mp3")

    # Create a vertical science-themed background
    w, h = 720, 1280
    img = Image.new("RGB", (w, h), (8, 18, 48))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        c = int(15 + 35 * y / h)
        draw.line((0, y, w, y), fill=(5, c, 65 + c))
    for x in range(30, w, 90):
        for y in range(40, h, 100):
            draw.ellipse((x, y, x+3, y+3), fill=(100, 190, 255))

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48
        )
    except OSError:
        font = ImageFont.load_default()

    title = topic[:65]
    words = title.split()
    lines, line = [], ""
    for word in words:
        if len(line + " " + word) > 20:
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        lines.append(line)

    y = 470
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        draw.text(((w - (box[2]-box[0]))/2, y), line,
                  font=font, fill="white", stroke_width=2,
                  stroke_fill=(0, 0, 0))
        y += 65

    img.save("output/background.png")

    # Make simple timed captions from the narration
    sentences = re.split(r'(?<=[.!?])\s+', script)
    sentences = [s.strip() for s in sentences if s.strip()]
    duration = 40.0
    weights = [max(1, len(s.split())) for s in sentences]
    total = sum(weights)
    elapsed = 0.0

    def stamp(seconds):
        ms = int(seconds * 1000)
        hh, ms = divmod(ms, 3600000)
        mm, ms = divmod(ms, 60000)
        ss, ms = divmod(ms, 1000)
        return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"

    with open("output/captions.srt", "w", encoding="utf-8") as f:
        for i, sentence in enumerate(sentences, 1):
            end = elapsed + duration * weights[i-1] / total
            f.write(f"{i}\n{stamp(elapsed)} --> {stamp(end)}\n{sentence}\n\n")
            elapsed = end

    # Render the vertical MP4 with voice and captions
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "24",
        "-i", "output/background.png",
        "-i", "output/voice.mp3",
        "-vf", "subtitles=output/captions.srt:force_style='FontName=DejaVu Sans,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=140'",
        "-t", str(duration),
        "-r", "24", "-s", "720x1280",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        "output/science_short.mp4"
    ], check=True)

    print("Video created: output/science_short.mp4")

if __name__ == "__main__":
    main()
