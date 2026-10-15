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

    # Create five different vertical science scenes
    from PIL import Image, ImageDraw
    import math

    W, H = 720, 1280
    scenes = [
        ("SPACE EXPLORATION", "planet"),
        ("THE ATOM", "atom"),
        ("FUTURE TECHNOLOGY", "chip"),
        ("MYSTERIES OF SPACE", "stars"),
        ("SCIENCE CHANGES EVERYTHING", "waves"),
    ]

    colors = [
        (10, 20, 75), (20, 10, 65), (5, 45, 65),
        (25, 10, 75), (5, 30, 65)
    ]

    for i, (heading, kind) in enumerate(scenes):
        img = Image.new("RGB", (W, H), colors[i])
        d = ImageDraw.Draw(img)

        # Star field
        for x in range(35, W, 85):
            for y in range(60, H, 110):
                d.ellipse((x, y, x+4, y+4), fill=(170, 210, 255))

        cx, cy = W // 2, 570

        if kind == "planet":
            d.ellipse((cx-150, cy-150, cx+150, cy+150),
                      fill=(55, 120, 240), outline="white", width=4)
            d.ellipse((cx-220, cy-45, cx+220, cy+45),
                      outline=(255, 190, 100), width=12)

        elif kind == "atom":
            for angle in (0, 60, 120):
                d.ellipse((cx-170, cy-65, cx+170, cy+65),
                          outline=(80, 220, 255), width=5)
                # Rotate the ellipse for the next orbital direction
                # by drawing a simple angled orbital line.
                a = math.radians(angle)
                x1 = cx - int(170 * math.cos(a))
                y1 = cy - int(170 * math.sin(a))
                x2 = cx + int(170 * math.cos(a))
                y2 = cy + int(170 * math.sin(a))
                d.line((x1, y1, x2, y2), fill=(80, 220, 255), width=3)
            d.ellipse((cx-22, cy-22, cx+22, cy+22), fill="yellow")

        elif kind == "chip":
            d.rectangle((cx-120, cy-120, cx+120, cy+120),
                        fill=(20, 110, 140), outline="cyan", width=8)
            for k in range(-100, 101, 40):
                d.line((cx+k, cy-120, cx+k, cy-175), fill="cyan", width=8)
                d.line((cx+k, cy+120, cx+k, cy+175), fill="cyan", width=8)
                d.line((cx-120, cy+k, cx-175, cy+k), fill="cyan", width=8)
                d.line((cx+120, cy+k, cx+175, cy+k), fill="cyan", width=8)

        elif kind == "stars":
            for r in (70, 120, 170, 220):
                d.ellipse((cx-r, cy-r, cx+r, cy+r),
                          outline=(100, 130, 255), width=3)
            d.ellipse((cx-45, cy-45, cx+45, cy+45),
                      fill=(255, 190, 90))

        else:
            points = []
            for x in range(0, W, 5):
                y = cy + int(100 * math.sin(x / 35))
                points.append((x, y))
            d.line(points, fill=(70, 240, 255), width=8)
            points2 = [(x, y+90) for x, y in points]
            d.line(points2, fill=(255, 100, 220), width=5)

        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38
            )
        except OSError:
            font = ImageFont.load_default()

        d.text((35, 170), heading, font=font, fill="white",
               stroke_width=2, stroke_fill="black")
        img.save(f"output/scene{i+1}.png")

    # Captions from the generated narration
    sentences = re.split(r'(?<=[.!?])\s+', script)
    sentences = [s.strip() for s in sentences if s.strip()]
    weights = [max(1, len(s.split())) for s in sentences]
    total = sum(weights) or 1

    def stamp(seconds):
        ms = int(seconds * 1000)
        hh, ms = divmod(ms, 3600000)
        mm, ms = divmod(ms, 60000)
        ss, ms = divmod(ms, 1000)
        return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"

    elapsed = 0
    with open("output/captions.srt", "w", encoding="utf-8") as f:
        for i, sentence in enumerate(sentences, 1):
            end = elapsed + 40 * weights[i-1] / total
            f.write(
                f"{i}\n{stamp(elapsed)} --> {stamp(end)}\n"
                f"{sentence}\n\n"
            )
            elapsed = end

    # Join five scenes, add subtitles and narration
    inputs = []
    for i in range(1, 6):
        inputs += ["-loop", "1", "-framerate", "24",
                   "-t", "8", "-i", f"output/scene{i}.png"]
    inputs += ["-i", "output/voice.mp3"]

    filter_graph = (
        "[0:v][1:v][2:v][3:v][4:v]concat=n=5:v=1:a=0,"
        "subtitles=output/captions.srt:force_style="
        "'FontName=DejaVu Sans,FontSize=20,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=2,"
        "Alignment=2,MarginV=140'[v]"
    )

    subprocess.run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_graph,
        "-map", "[v]", "-map", "5:a",
        "-t", "40", "-r", "24",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        "output/science_short.mp4"
    ], check=True)

    print("Video created with five changing scenes!")

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
