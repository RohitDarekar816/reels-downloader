import requests
from urllib.parse import urlparse
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = '7713932198:AAEOth_zVrWRK0KCrIMCMDBuFbm1wfnYHaw'  # Replace with your actual bot token
WEBHOOK_URL = 'http://dev.cloudtix.in'  # Your API endpoint

def clean_instagram_url(url):
    """Remove query params and trailing slash from Instagram Reel URL."""
    parsed = urlparse(url)
    # Remove trailing slash from path if exists
    path = parsed.path.rstrip('/')
    # Rebuild the URL without query
    base_url = f"{parsed.scheme}://{parsed.netloc}{path}"
    print(f"{base_url}")
    return base_url

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if "instagram.com/reel/" in url:
        clean_url = clean_instagram_url(url)
        try:
            response = requests.post(WEBHOOK_URL, json={"reel_url": clean_url})
            if response.ok:
                await update.message.reply_text(f"✅ Sent: {clean_url}")
            else:
                await update.message.reply_text(f"❌ Server error: {response.status_code}")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to send: {str(e)}")
    else:
        await update.message.reply_text("⚠️ Please send a valid Instagram Reel URL.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()
