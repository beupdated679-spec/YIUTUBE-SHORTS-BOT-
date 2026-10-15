import os
import random
import requests
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from gtts import gTTS
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips
)

# ---------------- SETTINGS ----------------

WIDTH = 1080
HEIGHT = 1920
DURATION = 30
SEGMENT_SECONDS = 3
FPS = 24

OUTPUT_DIR = Path("output")
ASSET_DIR = Path("assets")
OUTPUT_DIR.mkdir(exist_ok=True)
ASSET_DIR.mkdir(exist_ok=True)

OUTPUT_VIDEO = OUTPUT_DIR / "science_short.mp4"

# Add your Pexels API key in GitHub Codespaces Secrets.
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# Change these for each new video.
TOPIC = "Why does space look black?"
SCRIPT = (
    "Have you ever wondered why space looks black? "
    "The Sun produces enormous amounts of light, but space "
    "is almost empty. On Earth, the atmosphere scatters sunlight "
    "across the sky. In space, there is very little matter to "
    "scatter that light toward your eyes. That is why the sky "
    "between the stars looks dark. Stars are still shining, "
    "but the universe is incredibly vast. Did you know that? "
    "Tell us what science mystery we should explain next."
)

# Ten visual searches, one for every 3-second segment.
VISUAL_QUERIES = [
    "planet earth from space",
    "stars galaxy deep space",
    "sun glowing in space",
    "astronaut floating in space",
    "milky way galaxy",
    "earth atmosphere from orbit",
    "colorful nebula space",
    "distant stars universe",
    "planet surface from orbit",
    "deep space telescope"
]

BACKGROUND_COLORS = [
    (10, 20, 65),
    (40, 10, 75),
    (100, 25, 20),
    (5, 50, 85),
    (35, 10, 60),
    (5, 65, 75),
    (80, 15, 55),
    (15, 30, 90),
    (65, 35, 10),
    (5, 15, 45)
]

# ------------------------------------------


def get_pexels_image(query, index):
    """Download a relevant photo from Pexels when available."""

    if not PEXELS_API_KEY:
        return None

    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 5},
            timeout=20
        )
        response.raise_for_status()
        photos = response.json().get("photos", [])

        if not photos:
            return None

        photo = photos[index % len(photos)]
        image_url = photo["src"]["portrait"]

        image_response = requests.get(image_url, timeout=25)
        image_response.raise_for_status()

        return Image.open(
            BytesIO(image_response.content)
        ).convert("RGB")

    except (requests.RequestException, ValueError, KeyError) as error:
        print(f"Image download failed for '{query}': {error}")
        return None


def make_background(query, index):
    """Prepare a vertical image with a changing color overlay."""

    image = get_pexels_image(query, index)

    if image is None:
        # Reliable offline fallback: create a space-like background.
        image = Image.new(
            "RGB",
            (WIDTH, HEIGHT),
            BACKGROUND_COLORS[index]
        )
        draw = ImageDraw.Draw(image)

        random.seed(index + 100)
        for _ in range(220):
            x = random.randint(0, WIDTH - 1)
            y = random.randint(0, HEIGHT - 1)
            radius = random.randint(1, 4)
            draw.ellipse(
                (x, y, x + radius, y + radius),
                fill=(220, 225, 255)
            )

        # Add a soft colored planet.
        px = random.randint(200, WIDTH - 200)
        py = random.randint(350, HEIGHT - 500)
        radius = random.randint(100, 240)
        draw.ellipse(
            (px - radius, py - radius, px + radius, py + radius),
            fill=BACKGROUND_COLORS[index]
        )

    # Crop to fill the entire vertical frame.
    image_ratio = image.width / image.height
    target_ratio = WIDTH / HEIGHT

    if image_ratio > target_ratio:
        new_width = int(image.height * target_ratio)
        left = (image.width - new_width) // 2
        image = image.crop(
            (left, 0, left + new_width, image.height)
        )
    else:
        new_height = int(image.width / target_ratio)
        top = (image.height - new_height) // 2
        image = image.crop(
            (0, top, image.width, top + new_height)
        )

    image = image.resize((WIDTH, HEIGHT))

    # Apply the segment's distinct color tint.
    tint = Image.new(
        "RGB", image.size, BACKGROUND_COLORS[index]
    )
    image = Image.blend(image, tint, 0.28)
    image = ImageEnhance.Contrast(image).enhance(1.15)

    # Darken the image so white captions remain readable.
    image = ImageEnhance.Brightness(image).enhance(0.70)

    path = ASSET_DIR / f"background_{index + 1:02d}.jpg"
    image.save(path, quality=90)
    return str(path)


def make_caption_image(text, index):
    """Create a transparent caption overlay."""

    overlay = Image.new(
        "RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0)
    )
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            54
        )
    except OSError:
        font = ImageFont.load_default()

    words = text.split()
    lines = []
    line = ""

    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] > 900:
            if line:
                lines.append(line)
            line = word
        else:
            line = candidate

    if line:
        lines.append(line)

    line_height = 72
    total_height = len(lines) * line_height
    y = int(HEIGHT * 0.68 - total_height / 2)

    for line in lines:
        box = draw.textbbox((0, 0), line, font=font, stroke_width=2)
        text_width = box[2] - box[0]
        x = (WIDTH - text_width) // 2

        draw.text(
            (x, y),
            line,
            font=font,
            fill="white",
            stroke_width=3,
            stroke_fill="black"
        )
        y += line_height

    path = ASSET_DIR / f"caption_{index + 1:02d}.png"
    overlay.save(path)
    return str(path)


def main():
    print("Creating 30-second science Short...")

    print("Generating voice...")
    voice_path = OUTPUT_DIR / "voice.mp3"
    gTTS(text=SCRIPT, lang="en", slow=False).save(str(voice_path))

    audio = AudioFileClip(str(voice_path))

    # Divide narration into ten timed caption sections.
    words = SCRIPT.split()
    segment_words = []

    for i in range(10):
        start = round(i * len(words) / 10)
        end = round((i + 1) * len(words) / 10)
        segment_words.append(" ".join(words[start:end]))

    clips = []

    for i, query in enumerate(VISUAL_QUERIES):
        print(f"Preparing visual {i + 1}/10...")

        background_path = make_background(query, i)
        caption_path = make_caption_image(segment_words[i], i)

        background = (
            ImageClip(background_path)
            .set_duration(SEGMENT_SECONDS)
        )

        caption = (
            ImageClip(caption_path, transparent=True)
            .set_duration(SEGMENT_SECONDS)
        )

        segment = concatenate_videoclips(
            [background, caption],
            method="compose"
        ).set_duration(SEGMENT_SECONDS)

        clips.append(segment)

    print("Combining visuals and narration...")

    video = concatenate_videoclips(clips, method="compose")
    video = video.set_duration(DURATION)

    # Trim long narration or pad short narration with silence.
    if audio.duration >= DURATION:
        audio = audio.subclip(0, DURATION)
    else:
        from moviepy.audio.AudioClip import AudioClip

        silence_duration = DURATION - audio.duration
        silence = AudioClip(
            lambda t: 0,
            duration=silence_duration,
            fps=44100
        )
        from moviepy.audio.AudioClip import concatenate_audioclips
        audio = concatenate_audioclips([audio, silence])

    video = video.set_audio(audio)

    video.write_videofile(
        str(OUTPUT_VIDEO),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=2
    )

    video.close()
    audio.close()

    print(f"SUCCESS! Your video is saved at: {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
