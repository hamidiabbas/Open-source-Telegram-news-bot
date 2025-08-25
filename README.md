# Telegram AI Tech & Science News Bot

Automatically fetches, summarizes, and posts the latest tech, AI, and science news—plus hot Reddit posts—from top sources into your Telegram channel, every 5 minutes.

## Features

- Pulls news from NewsAPI, leading tech/AI/science sites (RSS), and Reddit subreddits
- Summarizes articles with lightweight, open-source extractive AI (Sumy)
- Automatically avoids duplicate posts
- Posts article images when available
- Emoji-rich, clean channel-ready captions
- Robust error logging (check `bot_errors.log`)
- Fast and free (no cloud LLM/API or credit card needed)

## Setup

### 1. Clone or Copy the Bot Files

Put `news_bot.py` and `requirements.txt` in your desired folder.

### 2. Install Requirements
python -m pip install -r requirements.txt

text

### 3. Set Your Secrets

Edit `news_bot.py` and fill in:

- `TG_TOKEN` - Your Telegram bot token (from BotFather)
- `CHANNEL` - Your channel username (e.g. `@geek_ai_news`) or numeric ID
- `NEWS_API_KEY` - [Get a free one here](https://newsapi.org/)

### 4. Run the Bot

python news_bot.py

text

The bot will:
- Post immediately on start
- Continue posting every 5 minutes

Leave it running in your terminal/console.

## Customizing

- **More Reddit/tech/science feeds:**  
  Add or remove RSS URLs in the `RSS_FEEDS` dictionary.
- **Schedule:**  
  Change the line `schedule.every(5).minutes.do(job)` to post at a different interval.
- **Summarization style:**  
  Tweak the sumy summarizer or try different methods (see code comments).

## Troubleshooting

- **Double posts?**  
  Make sure only one instance of the bot is running.

- **No posts?**  
  Check:
    - Your bot token, channel permissions (must be admin)
    - Internet/network restrictions for Telegram

- **Error logs:**  
  Check `bot_errors.log` in your project folder.

## License

MIT — Free for anyone to use, fork, and improve!

---

**Enjoy your hands-free news channel! Need upgrades, hosting/deployment tips, or more features? Open an issue or ask your assistant!**