import os
import json
import boto3
import feedparser
from datetime import datetime
from dotenv import load_dotenv
import anthropic
import time

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
ses = boto3.client('ses', region_name=os.getenv('AWS_REGION'))

RSS_FEEDS = [
    {
        'name': 'AWS News',
        'url': 'https://aws.amazon.com/blogs/aws/feed/'
    },
    {
        'name': 'TechCrunch AI',
        'url': 'https://techcrunch.com/category/artificial-intelligence/feed/'
    },
    {
        'name': 'The Verge Tech',
        'url': 'https://www.theverge.com/rss/index.xml'
    }
]

def fetch_articles(feeds, max_per_feed=3):
    print("Fetching articles from RSS feeds...")
    all_articles = []

    for feed in feeds:
        print(f"  Fetching {feed['name']}...")
        try:
            parsed = feedparser.parse(feed['url'])
            for entry in parsed.entries[:max_per_feed]:
                all_articles.append({
                    'source': feed['name'],
                    'title': entry.get('title', 'No title'),
                    'summary': entry.get('summary', entry.get('description', ''))[:300],
                    'link': entry.get('link', ''),
                    'published': entry.get('published', 'Unknown')
                })
            print(f"  Got {min(max_per_feed, len(parsed.entries))} articles")
        except Exception as e:
            print(f"  Failed: {e}")

    print(f"\nTotal articles: {len(all_articles)}\n")
    return all_articles

def generate_newsletter(articles):
    print("Generating newsletter with Claude AI...")

    prompt = f"""
You are a tech newsletter editor writing for cloud engineers and solutions architects.

Create a compelling weekly newsletter from these articles.

Include:
1. NEWSLETTER HEADLINE (catchy and relevant)
2. EDITOR'S NOTE (2-3 sentences on the week's theme)
3. TOP STORY (most important article with 3 sentence summary)
4. QUICK HITS (3-4 other stories in one sentence each)
5. THIS WEEK IN AI (AI related highlights)
6. CLOSING THOUGHT (one actionable insight for cloud engineers)

ARTICLES:
{json.dumps(articles, indent=2)}

Write in an engaging conversational tone. Max 400 words.
    """

    for attempt in range(3):
        try:
            message = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(5)

    return "Newsletter generation unavailable"

def send_newsletter(newsletter_content, articles):
    message = f"""
THE CLOUD ENGINEER WEEKLY
=========================
{datetime.now().strftime('%B %d, %Y')}

{newsletter_content}

---
FULL ARTICLE LINKS:
{chr(10).join([f"- {a['source']}: {a['title']} -> {a['link']}" for a in articles])}

Unsubscribe | View in browser
The Cloud Engineer Weekly
    """

    try:
        ses.send_email(
            Source=os.getenv('YOUR_EMAIL'),
            Destination={'ToAddresses': [os.getenv('YOUR_EMAIL')]},
            Message={
                'Subject': {'Data': f"The Cloud Engineer Weekly — {datetime.now().strftime('%B %d %Y')}"},
                'Body': {'Text': {'Data': message}}
            }
        )
        print(f"\nNewsletter sent to {os.getenv('YOUR_EMAIL')}")
    except Exception as e:
        print(f"\nEmail failed: {e}")

def run():
    print("Newsletter Engine")
    print("=================\n")

    print("Step 1: Fetching articles...")
    articles = fetch_articles(RSS_FEEDS)

    print("Step 2: Generating newsletter with Claude AI...")
    newsletter = generate_newsletter(articles)

    print("\n" + "="*50)
    print("THE CLOUD ENGINEER WEEKLY")
    print("="*50 + "\n")
    print(newsletter)

    print("\nStep 3: Sending newsletter...")
    send_newsletter(newsletter, articles)

    report = {
        'timestamp': datetime.now().isoformat(),
        'articles_fetched': len(articles),
        'newsletter': newsletter
    }

    with open('newsletter_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print("Report saved to newsletter_report.json")
    print("\nNewsletter Engine complete!")

if __name__ == "__main__":
    run()