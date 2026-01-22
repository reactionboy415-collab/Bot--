import logging
import re
import warnings
import io
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Bypass system warnings
warnings.filterwarnings("ignore")

# --- [ ⚙️ CONFIGURATION ] ---
BOT_TOKEN = "7963420197:AAGK-JSoXaxRNmRlszAQ3vLJf2DPz7i2r34"
ADMIN_ID = 7840042951
SOURCE_GROUP_ID = -1002666375873
FILE_NAME = "hq_dumps_by_@dex4dev.txt"
PORT = 10000 

# Memory State
captured_cards = []
unique_cards = set()
limit_per_file = 100

logging.basicConfig(level=logging.INFO)

# --- [ 🌐 RENDER PORT BINDING ] ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Pirate Bot is Active", 200

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- [ 🛠 ENGINE ] ---

def extract_cc(text):
    if not text: return None
    pattern = r"(\d{15,16}\|\d{2}\|\d{2,4}\|\d{3,4})"
    match = re.search(pattern, text)
    return match.group(1) if match else None

async def send_captured_file(context: ContextTypes.DEFAULT_TYPE):
    global captured_cards, unique_cards
    if not captured_cards: return

    try:
        content = "\n".join(captured_cards)
        out_file = io.BytesIO(content.encode('utf-8'))
        out_file.name = FILE_NAME
        
        await context.bot.send_document(
            chat_id=ADMIN_ID,
            document=out_file,
            caption=f"✅ <b>Collection Ready!</b>\n🔥 Total: <code>{len(captured_cards)}</code>\n👤 Admin: @dex4dev",
            parse_mode="HTML"
        )
        captured_cards = []
        unique_cards.clear()
    except Exception as e:
        logging.error(f"Upload failed: {e}")

# --- [ 🚀 HANDLERS ] ---

async def handle_incoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global captured_cards, unique_cards
    if not update.message: return
    
    if not (update.effective_chat.id == SOURCE_GROUP_ID or update.effective_user.id == ADMIN_ID):
        return

    text = update.message.text or update.message.caption
    cc = extract_cc(text)
    
    if cc and cc not in unique_cards:
        unique_cards.add(cc)
        captured_cards.append(cc)
        
        if len(captured_cards) % 10 == 0:
            try:
                await context.bot.send_message(ADMIN_ID, f"📈 Progress: <code>{len(captured_cards)}/{limit_per_file}</code>", parse_mode="HTML")
            except: pass

        if len(captured_cards) >= limit_per_file:
            await send_captured_file(context)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("🚀 <b>Pirate Collector v24.0 Live!</b>", parse_mode="HTML")

# --- [ 🏁 THE FIX ] ---

def main():
    # Start Web Server
    threading.Thread(target=run_flask, daemon=True).start()

    # The Correct Way: Use Builder but explicitly disable JobQueue and Persistence
    # This solves the TypeError and the startup crash
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .job_queue(None)      # Disables APScheduler/pytz requirement
        .persistence(None)    # Disables database requirement
        .build()
    )

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("getfile", lambda u, c: send_captured_file(c) if u.effective_user.id == ADMIN_ID else None))
    application.add_handler(MessageHandler(filters.ALL, handle_incoming))

    print("--- BOT RUNNING ON RENDER ---")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
