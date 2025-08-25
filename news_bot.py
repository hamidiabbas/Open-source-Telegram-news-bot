import os
import requests
import feedparser
import asyncio
import schedule
import time
import logging
import html
import re
import random
from colorama import init, Fore
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
STORY_QUEUE_FILE = "story_queue.txt"
LOG_FILE = "bot_errors.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

CATEGORIES = {
    "technology": "#Tech",
    "science": "#Science",
    "ai": "#AI",
    "world": "#World",
    "business": "#Business",
    "health": "#Health",
    "coding": "#Coding",
    "finance": "#Finance",
    "crypto": "#Crypto",
    "security": "#Security",
    "mobile": "#Mobile",
    "entertainment": "#Entertainment",
    "startup": "#Startup",
    "gaming": "#Gaming",
    "space": "#Space",
    "economy": "#Economy",
    "geopolitics": "#Geo"
}

RSS_FEEDS = {
    "#Tech": [
        "https://www.theverge.com/rss/index.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://www.techradar.com/rss",
        "http://feeds.arstechnica.com/arstechnica/index",
        "https://feeds.feedburner.com/TechCrunch/",
        "https://www.engadget.com/rss.xml",
        "https://feeds.wired.com/wired/index",
        "https://www.zdnet.com/news/rss.xml",
        "https://www.cnet.com/rss/all/",
        "https://www.digitaltrends.com/feed/",
        "https://www.pcworld.com/index.rss",
        "https://www.tomshardware.com/feeds/all",
        "http://feeds.makeuseof.com/Makeuseof",
        "https://www.reddit.com/r/technology/.rss",
        "https://www.reddit.com/r/gadgets/.rss"
    ],
    "#Science": [
        "https://www.sciencedaily.com/rss/top/science.xml",
        "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://feeds.feedburner.com/DiscoverSpace",
        "https://rss.sciam.com/ScientificAmerican-Global",
        "https://www.scientificamerican.com/feed/rss/",
        "https://physicsworld.com/feed/",
        "https://www.nature.com/subjects/science/rss"
    ],
    "#AI": [
        "https://venturebeat.com/category/ai/feed/",
        "https://www.reddit.com/r/artificial/.rss",
        "https://www.reddit.com/r/MachineLearning/.rss",
        "https://openai.com/research/feed.xml",
        "https://ai.googleblog.com/feeds/posts/default"
    ],
    "#World": [
        "http://feeds.bbci.co.uk/news/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.theguardian.com/world/rss",
        "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "https://www.reddit.com/r/worldnews/.rss"
    ],
    "#Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.ft.com/?format=rss",
        "https://www.bloomberg.com/feed/podcast/etf-report.xml",
        "https://www.reddit.com/r/business/.rss",
        "https://www.economist.com/the-world-this-week/rss.xml"
    ],
    "#Health": [
        "https://www.sciencedaily.com/rss/health_medicine.xml",
        "https://www.webmd.com/rss/news_breaking.xml",
        "https://www.reddit.com/r/health/.rss",
        "https://www.medicalnewstoday.com/rss",
        "https://www.nature.com/subjects/health/rss"
    ],
    "#Coding": [
        "https://news.ycombinator.com/rss",
        "https://www.reddit.com/r/programming/.rss",
        "https://feeds.feedburner.com/codinghorror/",
        "https://feeds.feedburner.com/oreilly/radar/atom",
        "https://dev.to/feed"
    ],
    "#Finance": [
        "https://www.investing.com/rss/news_285.rss",
        "https://www.marketwatch.com/rss/topstories",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.reddit.com/r/finance/.rss",
        "https://www.wsj.com/xml/rss/3_7031.xml"
    ],
    "#Crypto": [
        "https://cointelegraph.com/rss",
        "https://news.bitcoin.com/feed/",
        "https://www.reddit.com/r/CryptoCurrency/.rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cryptopotato.com/feed/"
    ],
    "#Security": [
        "https://threatpost.com/feed/",
        "https://www.securityweek.com/rss",
        "https://www.reddit.com/r/netsec/.rss",
        "https://feeds.feedburner.com/TheHackersNews",
        "https://krebsonsecurity.com/feed/"
    ],
    "#Mobile": [
        "https://www.androidcentral.com/rss",
        "https://9to5mac.com/feed/",
        "https://www.gsmarena.com/rss-news-reviews.php3",
        "https://www.macrumors.com/macrumors.xml",
        "https://www.reddit.com/r/apple/.rss"
    ],
    "#Entertainment": [
        "https://www.tmz.com/rss.xml",
        "https://www.hollywoodreporter.com/t/feed/rss.xml",
        "https://variety.com/feed/",
        "https://www.reddit.com/r/movies/.rss",
        "https://www.eonline.com/syndication/feeds/rssfeeds/topstories.xml"
    ],
    "#Startup": [
        "https://techcrunch.com/startups/feed/",
        "https://www.startupdaily.net/feed/",
        "https://venturebeat.com/category/startups/feed/",
        "https://www.reddit.com/r/startups/.rss",
        "https://feeds.feedburner.com/angelblog"
    ],
    "#Gaming": [
        "https://www.polygon.com/rss/index.xml",
        "https://www.gamespot.com/feeds/news/",
        "https://www.ign.com/feeds/all",
        "https://www.reddit.com/r/gaming/.rss",
        "https://feeds.feedburner.com/rockpapershotgun"
    ],
    "#Space": [
        "https://www.space.com/feeds/all",
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://www.reddit.com/r/space/.rss",
        "https://www.esa.int/rssfeed/Our_Activities/Space_Science",
        "https://www.skyandtelescope.com/astronomy-news/feed/"
    ],
    "#Economy": [
        "https://www.imf.org/en/News/rss",
        "https://www.worldbank.org/en/news/all/rss",
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://www.wsj.com/xml/rss/3_7031.xml",
        "https://www.marketwatch.com/rss/topstories",
        "https://www.economist.com/finance-and-economics/rss.xml",
        "https://www.federalreserve.gov/feeds/releases.htm",
        "https://www.reuters.com/business/finance/rss"
    ],
    "#Geo": [
        "https://www.rferl.org/api/zmgpqe$e_k",
        "https://www.atlanticcouncil.org/feed/",
        "https://foreignpolicy.com/feed/",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.bbc.com/news/world/rss.xml",
        "https://www.economist.com/international/rss.xml",
        "https://www.cfr.org/rss/global.xml",
        "https://www.realcleardefense.com/articles/atom.xml"
    ]
}

def extractive_summarize(text, sentences_count=2):
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary = summarizer(parser.document, sentences_count)
        return " ".join(str(sentence) for sentence in summary)
    except Exception as e:
        logging.error(f"Summary error: {e}")
        return text[:200]

def fetch_newsapi_news(category, hashtag):
    if category == "ai":
        url = f'https://newsapi.org/v2/everything?q=artificial+intelligence&language=en&apiKey={NEWS_API_KEY}'
    elif category == "geopolitics" or category == "geo":
        url = f"https://newsapi.org/v2/everything?q=geopolitics&language=en&apiKey={NEWS_API_KEY}"
    elif category == "economy":
        url = f"https://newsapi.org/v2/everything?q=economy&language=en&apiKey={NEWS_API_KEY}"
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
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    return text

def fetch_rss_news(hashtag, url):
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
    try:
        with open(POSTED_URLS_FILE, "r") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def save_posted_url(url, keep_last=1000):
    with open(POSTED_URLS_FILE, "a") as f:
        f.write(url + "\n")
    try:
        with open(POSTED_URLS_FILE, "r") as f:
            lines = f.readlines()
        if len(lines) > keep_last:
            with open(POSTED_URLS_FILE, "w") as f:
                f.writelines(lines[-keep_last:])
    except Exception:
        pass

from bs4 import BeautifulSoup

def clean_html_entities(text, max_length=200):
    # Remove Reddit markdown links first
    text = clean_reddit_markup(text)
    # Remove HTML tags and get visible text only
    soup = BeautifulSoup(text, "html.parser")
    clean_text = soup.get_text(separator=" ", strip=True)
    # Escape stray HTML entities for Telegram safety
    clean_text = html.escape(clean_text).replace('&lt;', '').replace('&gt;', '').replace('&amp;', '&')
    clean_text = re.sub(r'[\r\n]+', ' ', clean_text)
    return clean_text[:max_length]


########## STORY QUEUE FUNCTIONS ##########

def load_story_queue():
    if os.path.exists(STORY_QUEUE_FILE):
        with open(STORY_QUEUE_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            return [eval(x) for x in lines]
    else:
        return []

def save_story_queue(queue):
    with open(STORY_QUEUE_FILE, "w", encoding="utf-8") as f:
        for item in queue:
            f.write(repr(item) + "\n")

def reset_story_queue():
    if os.path.exists(STORY_QUEUE_FILE):
        os.remove(STORY_QUEUE_FILE)

async def pin_message(bot, chat_id, message_id, only_if_not_already=True):
    try:
        chat = await bot.get_chat(chat_id)
        if not only_if_not_already or not getattr(chat, "pinned_message", None):
            await bot.pin_chat_message(chat_id=chat_id, message_id=message_id, disable_notification=True)
    except Exception as e:
        logging.error(f"Pin error: {e}")

async def post_breaking_story(story):
    bot = Bot(token=TG_TOKEN)
    title = clean_html_entities(story['title'], 120)
    descr = clean_html_entities(story['summary'], 200)
    url = story['url']
    img = story['img']
    hashtag = story['hashtag']
    news_text = f"{title}. {descr}" if descr else title
    summary = clean_html_entities(extractive_summarize(news_text, sentences_count=2), 200)
    msg = (f"{hashtag} 📰\n"
           f"<b>{title}</b>\n"
           f"{summary}\n\n"
           f"<a href='{url}'>Read more</a>")
    try:
        if img and img.startswith('http'):
            sent = await bot.send_photo(chat_id=CHANNEL, photo=img, caption=msg, parse_mode='HTML')
            await pin_message(bot, CHANNEL, sent.message_id)
        else:
            sent = await bot.send_message(chat_id=CHANNEL, text=msg, parse_mode='HTML')
            await pin_message(bot, CHANNEL, sent.message_id)
        save_posted_url(story['url'])
        print(Fore.LIGHTRED_EX + f"(Breaking) Posted immediately: {title}")
        await asyncio.sleep(3)
    except Exception as e:
        logging.error(f"Failed to send breaking message: {e}")
        print(Fore.RED + f"Failed to send breaking message: {e}")

########## BUILD DAILY STORY QUEUE ##########

def build_daily_story_queue():
    bot_print = Fore.CYAN + "[QUEUE]"
    print(bot_print, "Building daily story queue...")
    all_news = []
    for cat, hashtag in CATEGORIES.items():
        all_news += fetch_newsapi_news(cat, hashtag)
    for hashtag, urls in RSS_FEEDS.items():
        for rss_url in urls:
            all_news += fetch_rss_news(hashtag, rss_url)
    seen_urls = set()
    deduped_news = []
    already_posted = load_posted_urls()
    for news in all_news:
        if news['url'] not in seen_urls and news['url'] not in already_posted:
            seen_urls.add(news['url'])
            is_breaking = ("breaking" in news['title'].lower()) or ("breaking" in news['summary'].lower())
            if is_breaking:
                asyncio.run(post_breaking_story(news))
            else:
                deduped_news.append(news)
    random.shuffle(deduped_news)
    save_story_queue(deduped_news)
    print(bot_print, f"Queued {len(deduped_news)} fresh stories for drip posting.")

########## POST FROM QUEUE ##########

async def post_from_queue():
    queue = load_story_queue()
    if not queue:
        print(Fore.YELLOW + "No stories in the queue right now.")
        return
    to_post = queue.pop(0)
    save_story_queue(queue)

    bot = Bot(token=TG_TOKEN)
    title = clean_html_entities(to_post['title'], 120)
    descr = clean_html_entities(to_post['summary'], 200)
    url = to_post['url']
    img = to_post['img']
    hashtag = to_post['hashtag']
    news_text = f"{title}. {descr}" if descr else title
    summary = clean_html_entities(extractive_summarize(news_text, sentences_count=2), 200)
    msg = (f"{hashtag} 📰\n"
           f"<b>{title}</b>\n"
           f"{summary}\n\n"
           f"<a href='{url}'>Read more</a>")
    is_breaking = ("breaking" in title.lower()) or ("breaking" in descr.lower())
    try:
        if img and img.startswith('http'):
            sent = await bot.send_photo(chat_id=CHANNEL, photo=img, caption=msg, parse_mode='HTML')
            if is_breaking:
                await pin_message(bot, CHANNEL, sent.message_id)
        else:
            sent = await bot.send_message(chat_id=CHANNEL, text=msg, parse_mode='HTML')
            if is_breaking:
                await pin_message(bot, CHANNEL, sent.message_id)
        save_posted_url(to_post['url'])
        print(Fore.GREEN + f"Posted: {title}")
        await asyncio.sleep(3)
    except Exception as e:
        logging.error(f"Failed to send message: {e}")
        print(Fore.RED + f"Failed to send message: {e}")

########## SCHEDULER ##########

def schedule_bot():
    # Rebuild story queue every 1 hour for faster breaking detection
    schedule.every().hour.at(":00").do(build_daily_story_queue)
    # OR, for less frequent, use every().day.at("00:00"), but hourly is good for breaking
    # schedule.every().day.at("00:00").do(build_daily_story_queue)

    # Post one story every 5 minutes (if available)
    schedule.every(5).minutes.do(lambda: asyncio.run(post_from_queue()))

    print(Fore.CYAN + "Bot scheduled: will refill queue every hour and post every 5 minutes!")
    while True:
        schedule.run_pending()
        time.sleep(60)

########## ENTRY ##########

if __name__ == "__main__":
    print(Fore.CYAN + "Starting Telegram News Bot...")
    build_daily_story_queue()  # Fill the queue immediately at startup
    asyncio.run(post_from_queue())  # Post first story right away (if any)
    schedule_bot()
