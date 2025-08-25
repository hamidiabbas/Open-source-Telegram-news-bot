import os
import requests
import feedparser
import asyncio
import schedule
import time
import logging
import html
import re
from colorama import init, Fore, Style
from dotenv import load_dotenv
from telegram import Bot
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

init(autoreset=True)
load_dotenv()

TG_TOKEN = os.getenv("TG_TOKEN")
CHANNEL = os.getenv("CHANNEL")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
POSTED_URLS_FILE = "posted_urls.txt"
LOG_FILE = "bot_errors.log"

logging.basicConfig(
    filename=LOG_FILE, 
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

CATEGORIES = {
    "technology": "#Tech",
    "science": "#Science",
    "ai": "#AI"
}

RSS_FEEDS = {
    "#Tech": [
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.feedburner.com/Techcrunch",
        "https://www.reddit.com/r/technology/.rss"
    ],
    "#AI": [
        "https://spectrum.ieee.org/rss/artificial-intelligence/fulltext",
        "https://venturebeat.com/category/ai/feed/",
        "https://www.reddit.com/r/artificial/.rss",
        "https://www.reddit.com/r/MachineLearning/.rss"
    ],
    "#Science": [
        "https://www.scientificamerican.com/feed/rss/",
        "https://www.reddit.com/r/science/.rss"
    ]
}

def extractive_summarize(text, sentences_count=2):
    """Generate a short extractive summary of input text."""
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary = summarizer(parser.document, sentences_count)
        return " ".join(str(sentence) for sentence in summary)
    except Exception as e:
        logging.error(f"Summary error: {e}")
        return text[:200]

def fetch_newsapi_news(category, hashtag):
    """Fetch news articles from NewsAPI."""
    if category == "ai":
        url = f'https://newsapi.org/v2/everything?q=artificial+intelligence&language=en&apiKey={NEWS_API_KEY}'
    else:
        url = f'https://newsapi.org/v2/top-headlines?category={category}&language=en&apiKey={NEWS_API_KEY}'
    try:
        resp = requests.get(url, timeout=10)
        articles = resp.json().get('articles', [])
        results = []
        for article in articles[:5]:
            results.append({
                "title": article.get('title', ''),
                "summary": article.get('description', '') or '',
                "url": article.get('url', ''),
                "img": article.get('urlToImage', ''),
                "hashtag": hashtag,
            })
        return results
    except Exception as e:
        logging.error(f"NewsAPI error for {category}: {e}")
        return []

def clean_reddit_markup(text):
    """Remove Reddit markdown links."""
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    return text

def fetch_rss_news(hashtag, url):
    """Fetch and process RSS news, including Reddit."""
    try:
        feed = feedparser.parse(url)
        results = []
        for entry in feed.entries[:4]:
            title = entry.title
            summary = entry.summary if hasattr(entry, 'summary') else ''
            link = entry.link
            img = ""
            if "media_content" in entry:
                img = entry['media_content'][0]['url']
            elif "media_thumbnail" in entry:
                img = entry['media_thumbnail'][0]['url']
            results.append({
                "title": title,
                "summary": summary,
                "url": link,
                "img": img,
                "hashtag": hashtag
            })
        return results
    except Exception as e:
        logging.error(f"RSS error for {url}: {e}")
        return []

def load_posted_urls():
    """Return a set of URLs already posted to avoid duplicates."""
    try:
        with open(POSTED_URLS_FILE, "r") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def save_posted_url(url):
    """Save a new successfully posted URL to .txt file."""
    with open(POSTED_URLS_FILE, "a") as f:
        f.write(url + "\n")

def clean_html_entities(text, max_length=200):
    """Clean and limit HTML for Telegram."""
    text = clean_reddit_markup(text)
    text = html.escape(text).replace('&lt;', '').replace('&gt;', '').replace('&amp;', '&')
    text = re.sub(r'[\r\n]+', ' ', text)
    return text[:max_length]

async def post_to_telegram():
    """Fetch, filter, summarize, and post news items."""
    if not TG_TOKEN or not CHANNEL or not NEWS_API_KEY:
        print(Fore.RED + "Missing credentials in .env! Exiting.")
        logging.error("Missing credentials in .env! Exiting.")
        return

    bot = Bot(token=TG_TOKEN)
    all_news = []
    for cat, hashtag in CATEGORIES.items():
        all_news += fetch_newsapi_news(cat, hashtag)
    for hashtag, urls in RSS_FEEDS.items():
        for rss_url in urls:
            all_news += fetch_rss_news(hashtag, rss_url)

    seen_urls = set()
    deduped_news = []
    for news in all_news:
        if news['url'] not in seen_urls:
            deduped_news.append(news)
            seen_urls.add(news['url'])
    already_posted = load_posted_urls()

    posted_this_run = 0

    for news in deduped_news[:20]:
        if news['url'] in already_posted:
            continue
        title = clean_html_entities(news['title'], 120)
        descr = clean_html_entities(news['summary'], 200)
        url = news['url']
        img = news['img']
        hashtag = news['hashtag']
        news_text = f"{title}. {descr}" if descr else title
        summary = clean_html_entities(extractive_summarize(news_text, sentences_count=2), 200)
        msg = (f"{hashtag} 📰\n"
               f"<b>{title}</b>\n"
               f"{summary}\n\n"
               f"<a href='{url}'>Read more</a>")
        try:
            if img and img.startswith('http'):
                try:
                    await bot.send_photo(chat_id=CHANNEL, photo=img, caption=msg, parse_mode='HTML')
                except Exception as e:
                    logging.error(f"Failed to send photo, fallback to text: {e}")
                    await bot.send_message(chat_id=CHANNEL, text=msg, parse_mode='HTML')
            else:
                await bot.send_message(chat_id=CHANNEL, text=msg, parse_mode='HTML')
            save_posted_url(news['url'])
            posted_this_run += 1
            await asyncio.sleep(3)
        except Exception as e:
            logging.error(f"Failed to send message: {e}")

    print(Fore.GREEN + f"Posted {posted_this_run} new stories this run! Checked {len(deduped_news)} unique stories.")

def job():
    asyncio.run(post_to_telegram())

if __name__ == "__main__":
    print(Fore.CYAN + "Starting Telegram News Bot...")
    asyncio.run(post_to_telegram())
    schedule.every(5).minutes.do(job)
    print(Fore.CYAN + "Bot scheduled. Will post automatically every 5 minutes!")
    while True:
        schedule.run_pending()
        time.sleep(60)
