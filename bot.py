import json

def generate_metadata(topic):
    topic = topic.strip()

    if not topic:
        raise ValueError("Please provide a video topic.")

    title = f"Discover This Amazing Fact About {topic.title()}!"

    description = (
        f"Discover something interesting about {topic} "
        "in this YouTube Short!\n\n"
        f"What do you think about {topic}? Tell us in the comments."
    )

    hashtags = ["#Shorts", "#Facts", "#Science"]

    return {
        "title": title[:100],
        "description": description + "\n\n" + " ".join(hashtags),
        "hashtags": hashtags
    }

if __name__ == "__main__":
    result = generate_metadata("space")
    print(json.dumps(result, indent=2))
