import os, requests, asyncio, schedule, time, logging, html, re, random, datetime, threading
import feedparser
from colorama import init, Fore
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes

init(autoreset=True)
load_dotenv()

TG_TOKEN = os.getenv("TG_TOKEN")
CHANNEL = os.getenv("CHANNEL")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
POSTED_URLS_FILE = "posted_urls.txt"
STORY_QUEUE_FILE = "story_queue.txt"
WATCHLIST_FILE = "watchlist.txt"
LOG_FILE = "bot_errors.log"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

RSS_FEEDS = {
    "#AI": [
        "https://openai.com/research/feed.xml",
        "https://ai.googleblog.com/feeds/posts/default",
        "https://venturebeat.com/category/ai/feed/",
        "https://www.nature.com/subjects/artificial-intelligence.rss",
        "https://spectrum.ieee.org/rss/ai-fulltext.xml",
        "https://www.technologyreview.com/feed/",
        "https://www.ft.com/artificial-intelligence?format=rss",
        "https://feeds.feedburner.com/wiredscience"
    ],
    "#StatsData": [
        "https://ourworldindata.org/rss",
        "https://www.visualcapitalist.com/feed/",
        "https://www.statista.com/rss",
        "https://www.weforum.org/agenda/rss.xml",
        "https://blog.oxfordeconomics.com/rss.xml",
        "https://www.imf.org/en/News/rss",
        "https://www.worldbank.org/en/news/all/rss",
        "https://tradingeconomics.com/rss/news.aspx",
        "https://www.oecd.org/newsRoom/rss.xml",
        "https://ec.europa.eu/eurostat/web/main/news/rss-feeds",
        "https://www.investopedia.com/feedbuilder/feed/getfeed/?feedName=rss_headline",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://www.brookings.edu/feed/",
        "https://www.pewresearch.org/feed/"
    ],
    "#Tech": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wsj.com/xml/rss/3_7455.xml",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://feeds.feedburner.com/TechCrunch/",
        "https://www.cnet.com/rss/all/",
        "https://www.bloomberg.com/feeds/podcasts/etf-report.xml",
        "https://www.zdnet.com/news/rss.xml",
        "https://www.reuters.com/rssFeed/technologyNews",
        "https://feeds.washingtonpost.com/rss/business/technology"
    ],
    "#World": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.reuters.com/tools/rss",
        "https://www.theguardian.com/world/rss",
        "https://feeds.washingtonpost.com/rss/world",
        "https://feeds.npr.org/1004/rss.xml",
        "https://www.economist.com/international/rss.xml",
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
        "https://apnews.com/rss/apf-topnews",
        "https://www.techmeme.com/feed.xml"
    ],
    "#Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.nytimes.com/services/xml/rss/nyt/Business.xml",
        "https://www.ft.com/?format=rss",
        "https://www.bloomberg.com/feed/podcast/etf-report.xml",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
        "https://www.economist.com/finance-and-economics/rss.xml",
        "https://www.wsj.com/xml/rss/3_7031.xml",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "https://www.reuters.com/finance/markets/rss"
    ],
    "#Science": [
        "https://www.nature.com/subjects/science.rss",
        "https://rss.sciam.com/ScientificAmerican-Global",
        "https://www.nytimes.com/services/xml/rss/nyt/Science.xml",
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://feeds.feedburner.com/DiscoverScienceNews",
        "https://www.sciencemag.org/rss/news_current.xml",
        "https://www.washingtonpost.com/rss/national/science"
    ],
    "#Economy": [
        "https://www.imf.org/en/News/rss",
        "https://www.worldbank.org/en/news/all/rss",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://www.economist.com/finance-and-economics/rss.xml",
        "https://www.ft.com/markets?format=rss",
        "https://www.marketwatch.com/rss/topstories",
        "https://www.nytimes.com/services/xml/rss/nyt/Economy.xml",
        "https://www.reuters.com/finance/markets/rss"
    ]
}

def clean_html_entities(text, max_length=350):
    soup = BeautifulSoup(text, "html.parser")
    clean_text = soup.get_text(separator=" ", strip=True)
    clean_text = html.escape(clean_text).replace('&lt;', '').replace('&gt;', '').replace('&amp;', '&')
    clean_text = re.sub(r'[\r\n]+', ' ', clean_text)
    return clean_text[:max_length]

def get_perplexity_response(prompt, lang="en", source_url=None, model="sonar-pro"):
    api_key = PERPLEXITY_API_KEY
    if not api_key: return None
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if lang == "fa": prompt += "\nپاسخ را به زبان فارسی بنویس."
    if source_url: prompt += f"\nSource: {source_url}"
    data = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    try:
        resp = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=50)
        if resp.ok:
            result = resp.json()
            text = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()[:1800]
            return text
        else: return None
    except Exception: return None

def extract_sources(ai_text):
    if not ai_text: return []
    sources=[];found=False
    for line in ai_text.splitlines():
        if "source" in line.lower() or "منابع" in line: found=True;continue
        if found: sources += re.findall(r'(https?://\S+)', line)
    return [url.strip(" .),]") for url in sources]

def fetch_rss_news(hashtag, url, news_type):
    # ! NO DATE FILTER: Just fetch latest entries (will dedupe by posted_urls.txt)
    try:
        d = feedparser.parse(url)
        results = []
        for entry in d.entries[:3]:
            title = entry.title
            summary = getattr(entry, 'summary', '') or ''
            link = getattr(entry, 'link', '')
            results.append({'title': title, 'summary': summary, 'url': link, 'img': '', 'hashtag': hashtag})
        return results
    except Exception:
        return []

def fetch_trending_news_perplexity():
    prompt = "List today's top 7 breaking, major AI stories, then tech/business/world stories from the most professional/trusted sources. Output as: [headline] (url)."
    headlines = []
    ai_ans = get_perplexity_response(prompt)
    if ai_ans:
        for line in ai_ans.split("\n"):
            m = re.match(r"(.*?)\((https?://\S+)\)", line.strip())
            if m:
                title, url = m.group(1).strip(), m.group(2).strip(" )")
                headlines.append({"title": title, "url": url, "summary": "", "img": "", "hashtag": "#AI"})
    return headlines

def load_posted_urls():
    try:
        with open(POSTED_URLS_FILE, "r") as f: return set(line.strip() for line in f)
    except FileNotFoundError: return set()

def save_posted_url(url, keep_last=1500):
    with open(POSTED_URLS_FILE, "a") as f: f.write(url + "\n")
    try:
        with open(POSTED_URLS_FILE, "r") as f: lines=f.readlines()
        if len(lines) > keep_last:
            with open(POSTED_URLS_FILE, "w") as f: f.writelines(lines[-keep_last:])
    except: pass

def load_story_queue():
    if os.path.exists(STORY_QUEUE_FILE):
        with open(STORY_QUEUE_FILE, "r", encoding="utf-8") as f:
            lines=[line.strip() for line in f if line.strip()]
            return [eval(x) for x in lines]
    else: return []

def save_story_queue(queue):
    with open(STORY_QUEUE_FILE, "w", encoding="utf-8") as f:
        for item in queue: f.write(repr(item) + "\n")

def make_friendly_prompt(title, descr, lang):
    if lang == "fa":
        return ("تو یک بات خبری تلگرام هستی که همیشه خلاصه خبرها رو با لحن باهوش و ایموجی می‌نویسی. سعی کن جذاب و قابل فهم و کمی هم هوشمندانه باشه." f"خبر: {title} {descr}")
    return ("You're a world-class news bot. Summarize this for a professional audience in a witty, quick-but-expert, sometimes funny and emoji-rich way. End with sources. Journalism-style, not dry bot!\n" f"Story: {title} {descr}")

async def pin_message(bot, chat_id, message_id, only_if_not_already=True):
    try:
        chat = await bot.get_chat(chat_id)
        if not only_if_not_already or not getattr(chat, "pinned_message", None):
            await bot.pin_chat_message(chat_id=chat_id, message_id=message_id, disable_notification=True)
    except Exception as e: logging.error(f"Pin error: {e}")

async def post_news_with_ai(story, is_breaking=False):
    bot=Bot(token=TG_TOKEN)
    title=clean_html_entities(story['title'], 120)
    descr=clean_html_entities(story['summary'], 250)
    url=story['url']; img=story['img']; hashtag=story['hashtag']
    lang="fa" if random.random() < 0.3 else "en"
    prompt=make_friendly_prompt(title, descr, lang)
    ai_summary=get_perplexity_response(prompt, lang=lang, source_url=url)
    srcs=extract_sources(ai_summary)
    intro_choices=["🤖 AI News:", "🚀 Cool:", "🔥 Just In:", "👀 Trending:", "✨ Must-see:", "🥳 Editors' Pick:", "📈 Stats:"]
    intro=random.choice(intro_choices)
    msg=(f"{intro} <b>{title}</b>\n{hashtag}\n<a href='{url}'>Original</a>\n\n")
    if ai_summary:
        core=ai_summary.split("Sources:")[0] if "Sources:" in ai_summary else ai_summary
        msg += f"{core.strip()}\n"
    if srcs:
        msg+="\n<b>Sources:</b>\n"+'\n'.join([f"<a href='{link}'>{link}</a>" for link in srcs[:2]])
    msg_img=msg[:1000]
    try:
        sent=None
        if img and img.startswith('http'):
            sent=await bot.send_photo(chat_id=CHANNEL, photo=img, caption=msg_img, parse_mode='HTML')
        else:
            msg=msg[:4000]
            sent=await bot.send_message(chat_id=CHANNEL, text=msg, parse_mode='HTML')
        if is_breaking and sent: await pin_message(bot, CHANNEL, sent.message_id)
        save_posted_url(url)
        print(Fore.GREEN + f"Posted: {title}")
        await asyncio.sleep(3)
    except Exception as e: print(Fore.RED + f"Failed to send message: {e}")

async def fetch_all_feeds_async():
    loop = asyncio.get_event_loop()
    tasks = []
    for key, urls in RSS_FEEDS.items():
        for url in urls:
            news_type = key
            tasks.append(loop.run_in_executor(
                None, fetch_rss_news, key, url, news_type
            ))
    res = await asyncio.gather(*tasks)
    all_news = []
    for group in res:
        all_news += group
    return all_news

def build_daily_story_queue():
    print(Fore.CYAN + "[QUEUE] Building daily story queue...")
    all_news = asyncio.run(fetch_all_feeds_async())
    all_news += fetch_trending_news_perplexity()
    seen_urls = set()
    deduped_news = []
    already_posted = load_posted_urls()
    for news in all_news:
        if news['url'] not in seen_urls and news['url'] not in already_posted and news['url']:
            seen_urls.add(news['url'])
            deduped_news.append(news)
    random.shuffle(deduped_news)
    save_story_queue(deduped_news)
    print(Fore.CYAN + f"Queued {len(deduped_news)} stories for posting.")

async def post_from_queue():
    queue=load_story_queue()
    if not queue:
        print(Fore.YELLOW + "No stories in the queue right now.")
        build_daily_story_queue()
        queue = load_story_queue()
        if not queue:
            print(Fore.RED + "Still no stories after refill!")
            return
    story=queue.pop(0)
    save_story_queue(queue)
    await post_news_with_ai(story, is_breaking=False)

# ... Insert all the rest of the advanced cluster/spike, scheduled research, DM/chat, as before ...

def ai_entities_for_titles(news_list):
    joined = "\n• ".join([x['title'] for x in news_list])
    q = f"Extract main 1-3 keywords or named entities per line for these headlines:\n• {joined}\nReturn result as 'headline: entities'"
    raw = get_perplexity_response(q)
    entities = []
    for line in (raw or "").splitlines():
        ent = re.findall(r"\[(.*?)\]", line)
        if ent:
            for e in ent[0].split(","): entities.append(e.strip().lower())
    return set(entities)

def cluster_ai(news_list, min_count=3):
    clusters = []
    for i, news in enumerate(news_list):
        ent = ai_entities_for_titles([news])
        group = [news]
        for j, other in enumerate(news_list):
            if i==j: continue
            ents2 = ai_entities_for_titles([other])
            if ent & ents2: group.append(other)
        uniq_urls = set(x['url'] for x in group)
        if len(uniq_urls)>=min_count and all(g.get('url')!=news['url'] for g in clusters):
            clusters.append({"entity":",".join(ent), "news": group})
    seen = set(); uniq = []
    for c in clusters:
        idkey = tuple(sorted(n['url'] for n in c['news']))
        if idkey not in seen:
            seen.add(idkey)
            uniq.append(c)
    return uniq

spiked_once = set()
async def process_spike_and_watch_alerts(bot, new_stories):
    if not new_stories: return
    clusters = cluster_ai(new_stories, min_count=3)
    for group in clusters:
        urls_key = ",".join(sorted([n['url'] for n in group['news']]))
        if urls_key in spiked_once: continue
        spiked_once.add(urls_key)
        ent = group["entity"]
        emj = random.choice(["📈","🔥","🚨","👀"])
        titles = [f"• {n['title']} (<a href='{n['url']}'>link</a>)" for n in group['news'][:5]]
        ai_trend = get_perplexity_response(
            f"Summarize in 1-2 lines, for Telegram users, what connects these headlines as a breaking trend: {', '.join([n['title'] for n in group['news'][:5]])}")
        msg = f"{emj} <b>AI Spike Alert:</b> <b>{ent}</b> trending ({len(group['news'])} new articles)\n"
        if ai_trend: msg += f"🤖 <i>{ai_trend.strip()}</i>\n"
        msg += "\n".join(titles)
        await bot.send_message(chat_id=CHANNEL, text=msg, parse_mode='HTML')

    wlist = []
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            wlist = [line.strip().lower() for line in f if line.strip()]
    for n in new_stories:
        combined = n["title"] + " " + n["summary"]
        for w in wlist:
            if w.lower() in combined.lower():
                k = n['url']+w
                if k in spiked_once: continue
                spiked_once.add(k)
                hi_title = re.sub(f"({w})", r"<u>\1</u>", n['title'], flags=re.I)
                emj = random.choice(["🔔","🚩","⭐","✨","🕵️"])
                msg = f"{emj} <b>Watchlist ALERT:</b> <b>{w}</b>\n<b>{hi_title}</b>\n<a href='{n['url']}'>[Story]</a>"
                quicksum = get_perplexity_response(f"Explain briefly why this headline matters: {n['title']}", model="sonar-pro")
                if quicksum: msg+= "\n🤖 " + quicksum
                await bot.send_message(chat_id=CHANNEL, text=msg, parse_mode='HTML')

async def real_time_monitor():
    bot = Bot(token=TG_TOKEN)
    print(Fore.LIGHTYELLOW_EX + "[RT DETECT] Real-time watch running...")
    seen_urls = load_posted_urls()
    seen_titles = set()
    while True:
        headlines = []
        for hashtag, urls in RSS_FEEDS.items():
            for url in urls:
                headlines += fetch_rss_news(hashtag, url, hashtag)
        headlines += fetch_trending_news_perplexity()
        new_stories = [s for s in headlines if s['url'] not in seen_urls and s['title'] not in seen_titles]
        if new_stories:
            await process_spike_and_watch_alerts(bot, new_stories)
            for s in new_stories:
                seen_urls.add(s['url'])
                seen_titles.add(s['title'])
        await asyncio.sleep(120)

def schedule_bot():
    schedule.every(5).minutes.do(lambda: asyncio.run(post_from_queue()))
    schedule.every().day.at("07:00").do(lambda: asyncio.run(scheduled_analysis_post("Daily Economic & Trading Deep Research", "Act as a top global trading and economic analyst. Write a detailed daily research report for traders: market trends, risks, central banks, geopolitical events, biggest moves in stocks/bonds/crypto, and emerging opportunities. Provide a several-paragraph analysis, use latest data, then a bullet list of actionable insights, and a markdown list of fresh sources.", "today", "economics/markets", "daily", model="sonar-deep-research")))
    schedule.every().monday.at("08:00").do(lambda: asyncio.run(scheduled_analysis_post("Weekly Economic Outlook", "Act as an expert economic analyst. Give a professional but easy to follow economic summary on global inflation, oil prices, central bank moves, and crypto events for the upcoming week. Use up-to-date data and cite sources. Bullet point main risks.", "this week", "economics", "weekly", model="sonar-deep-research")))
    schedule.every().wednesday.at("09:00").do(lambda: asyncio.run(scheduled_analysis_post("Academic Science Research Digest", "Summarize the three most important peer-reviewed science discoveries from the past week. Explain as for a general audience, with citations to the actual published papers.", "the past week", "science", "weekly", model="sonar-deep-research")))
    while True:
        schedule.run_pending()
        time.sleep(60)

def generate_new_prompt(meta_instruction, focus_period="this week", domain="economics"):
    meta = (f"Act as an experienced prompt engineer for Sonar. Write a perfect prompt for {domain} analysis on {focus_period}. "
            f"INSTRUCTION: {meta_instruction}. Return only the prompt I should use.")
    suggestion = get_perplexity_response(meta)
    print(Fore.LIGHTBLUE_EX + "[PROMPT SUGGESTED BY AI]", suggestion)
    return suggestion.strip() if suggestion else meta_instruction

async def scheduled_analysis_post(title, prompt_template, focus_period, domain, interval, model="sonar-deep-research", monthly=False, target_day=1):
    if monthly and datetime.datetime.utcnow().day != target_day: return
    meta_instruction=prompt_template
    prompt=generate_new_prompt(meta_instruction, focus_period, domain)
    ai_output=get_perplexity_response(prompt, model=model)
    post_body = f"🧠 <b>{title} ({focus_period})</b>\n\n"
    post_body += f"<i>Prompt used:</i> <code>{html.escape(prompt)}</code>\n\n"
    if ai_output:  post_body += ai_output[:3800]
    else: post_body += "Could not retrieve AI answer at this time."
    bot=Bot(token=TG_TOKEN)
    await bot.send_message(chat_id=CHANNEL, text=post_body, parse_mode='HTML')
    print(Fore.LIGHTMAGENTA_EX + f"[{interval.upper()} ANALYSIS POSTED] {title[:60]}")

async def ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text=update.message.text.strip()
    if text.startswith("/ask"):
        q=text.split(" ",1)[1] if " " in text else ""
        if not q: await update.message.reply_text("Send your question after /ask!"); return
        prompt=f"Summarize and fact-check: {q}\nCite sources."
        ai_ans=get_perplexity_response(prompt)
        srcs=extract_sources(ai_ans)
        msg=""
        if ai_ans: msg += html.escape(ai_ans.split("Sources:")[0]) + "\n"
        if srcs: msg += "<b>Sources:</b>\n"+'\n'.join([f"<a href='{u}'>{u}</a>" for u in srcs[:5]])
        await update.message.reply_text(msg or "No answer.", parse_mode='HTML')
    elif text.startswith("/quiz"):
        t = "Give a quick news quiz. Show question, then say 'Answer:' after one new line."
        resp = get_perplexity_response(t)
        if resp:
            qst, _, ans = resp.partition('Answer:')
            await update.message.reply_text(f"🧩 <b>Quiz:</b> {html.escape(qst.strip())}", parse_mode='HTML')
            await asyncio.sleep(2)
            await update.message.reply_text(f"💡 <b>Answer:</b> {html.escape(ans.strip())}", parse_mode='HTML')
        else:
            await update.message.reply_text("I couldn't come up with a quiz right now! Try again?")

def telegram_command_server():
    application=Application.builder().token(TG_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), ai_message))
    application.add_handler(CommandHandler("ask", ai_message))
    application.add_handler(CommandHandler("quiz", ai_message))
    print(Fore.MAGENTA + "Telegram AI command server active! (DM /ask, /quiz)")
    application.run_polling()

def schedule_news_job():
    build_daily_story_queue()
    asyncio.run(post_from_queue())
    schedule_bot()

async def main():
    print(Fore.CYAN + "Starting all-in-one bot: posts every 5min, all feeds, no date limits!")
    
    # Start scheduling in background thread
    news_thread = threading.Thread(target=schedule_news_job, daemon=True)
    news_thread.start()
    
    # Start real-time monitoring
    asyncio.create_task(real_time_monitor())
    
    # Run telegram server (this will keep the program alive)
    telegram_command_server()

if __name__ == "__main__":
    asyncio.run(main())
