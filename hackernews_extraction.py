import argparse
import requests
import json
import os

def fetch_top_stories(api_base_url, num_stories):
    """
    Fetch the top story IDs from HackerNews.
    """
    url = f"{api_base_url}/v0/topstories.json"
    response = requests.get(url)
    response.raise_for_status()
    story_ids = response.json()
    return story_ids[:num_stories]

def fetch_story_details(api_base_url, story_id):
    """
    Fetch details for a specific story ID from HackerNews.
    """
    url = f"{api_base_url}/v0/item/{story_id}.json"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def save_to_bucket(data, bucket_path, filename):
    """
    Save JSON data to the specified bucket path.
    """
    os.makedirs(bucket_path, exist_ok=True)
    file_path = os.path.join(bucket_path, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Saved {filename} to {bucket_path}")

def main():
    # Argument parser
    parser = argparse.ArgumentParser(description="Extract top stories from HackerNews.")
    parser.add_argument(
        "--num_stories",
        type=int,
        default=50,
        help="Number of top stories to fetch (default: 50).",
    )
    parser.add_argument(
        "--bucket_path",
        type=str,
        default="./raw",
        help="Path to the bucket for storing raw data (default: ./raw).",
    )
    args = parser.parse_args()

    # HackerNews API base URL
    api_base_url = "https://hacker-news.firebaseio.com"

    try:
        # Fetch top stories
        print(f"Fetching the top {args.num_stories} stories...")
        story_ids = fetch_top_stories(api_base_url, args.num_stories)

        # Fetch details for each story
        for idx, story_id in enumerate(story_ids, start=1):
            print(f"Fetching details for story ID {story_id} ({idx}/{len(story_ids)})...")
            story_details = fetch_story_details(api_base_url, story_id)

            # Save the story details in the raw bucket
            filename = f"story_{story_id}.json"
            save_to_bucket(story_details, args.bucket_path, filename)

        print("Extraction completed successfully!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
