import logging
import re
import warnings
import io
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Bypass warnings
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
def health(): return "Bot is Online", 200

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
    if not captured_cards:
        await context.bot.send_message(ADMIN_ID, "❌ <b>No cards in memory to export!</b>", parse_mode="HTML")
        return

    try:
        content = "\n".join(captured_cards)
        out_file = io.BytesIO(content.encode('utf-8'))
        out_file.name = FILE_NAME
        
        await context.bot.send_document(
            chat_id=ADMIN_ID,
            document=out_file,
            caption=f"🏴‍☠️ <b>DUMP EXPORT SUCCESS</b>\n━━━━━━━━━━━━━━\n🔥 Total: <code>{len(captured_cards)}</code>\n👤 Admin: @dex4dev",
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
    
    if not (update.effective_chat.id == SOURCE_GROUP_ID or update.effective_user.id == ADMIN_ID):
        return

    text = update.message.text or update.message.caption
    cc = extract_cc(text)
    
    if cc and cc not in unique_cards:
        unique_cards.add(cc)
        captured_cards.append(cc)
        
        if len(captured_cards) % 10 == 0:
            try:
                await context.bot.send_message(ADMIN_ID, f"📈 <b>Progress:</b> <code>{len(captured_cards)}/{limit_per_file}</code>", parse_mode="HTML")
            except: pass

        if len(captured_cards) >= limit_per_file:
            await send_captured_file(context)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(
        "<b>🏴‍☠️ PIRATE COLLECTOR v25.0</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📊 Stored: <code>{len(captured_cards)}</code>\n"
        f"🎯 Limit: <code>{limit_per_file}</code>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "<b>Available Commands:</b>\n"
        "/status - Show current progress\n"
        "/getfile - Export cards immediately\n"
        "/setlimit [num] - Change file limit\n"
        "/clear - Reset all data", 
        parse_mode="HTML"
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(
        f"📈 <b>Live Stats:</b>\n"
        f"Captured: <code>{len(captured_cards)}</code>\n"
        f"Target: <code>{limit_per_file}</code>\n"
        f"Unique Cards: <code>{len(unique_cards)}</code>", 
        parse_mode="HTML"
    )

async def set_limit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global limit_per_file
    if update.effective_user.id != ADMIN_ID: return
    try:
        limit_per_file = int(context.args[0])
        await update.message.reply_text(f"✅ <b>Limit updated:</b> <code>{limit_per_file}</code>", parse_mode="HTML")
    except:
        await update.message.reply_text("❌ <b>Format:</b> <code>/setlimit 200</code>", parse_mode="HTML")

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    captured_cards.clear()
    unique_cards.clear()
    await update.message.reply_text("🗑 <b>Memory Cleared Successfully!</b>", parse_mode="HTML")

# --- [ 🏁 INITIALIZATION ] ---

def main():
    threading.Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).job_queue(None).build()

    # Yahan saare handlers register kar diye hain
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(CommandHandler("getfile", lambda u, c: send_captured_file(c) if u.effective_user.id == ADMIN_ID else None))
    application.add_handler(CommandHandler("setlimit", set_limit_cmd))
    application.add_handler(CommandHandler("clear", clear_cmd))
    
    # Message Scraper (Text, Photo, Forwarded sab handle karega)
    application.add_handler(MessageHandler(filters.ALL, handle_incoming))

    print("--- BOT v25.0 FULLY FUNCTIONAL ---")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
