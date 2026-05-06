import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ALLOWED_GROUP_ID = int(os.getenv("ALLOWED_GROUP_ID"))

groq_client = Groq(api_key=GROQ_API_KEY)

# Store messages in memory
message_store = []

async def store_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store every message with timestamp"""
    if update.effective_chat.id != ALLOWED_GROUP_ID:
        return
    message_store.append({
        "time": datetime.now(),
        "user": update.effective_user.first_name,
        "text": update.message.text or ""
    })

async def summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /summarize HH:MM HH:MM command"""
    if update.effective_chat.id != ALLOWED_GROUP_ID:
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Usage: /summarize HH:MM HH:MM\nExample: /summarize 14:00 16:00")
            return

        today = datetime.now().date()
        start_time = datetime.strptime(f"{today} {args[0]}", "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(f"{today} {args[1]}", "%Y-%m-%d %H:%M")

        # Filter messages in that time range
        filtered = [
            f"{m['user']}: {m['text']}"
            for m in message_store
            if start_time <= m['time'] <= end_time and m['text']
        ]

        if not filtered:
            await update.message.reply_text("No messages found in that time range!")
            return

        conversation = "\n".join(filtered)

        await update.message.reply_text("⏳ Summarizing...")

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": f"Summarize this Telegram group conversation clearly and concisely:\n\n{conversation}"
            }]
        )

        summary = response.choices[0].message.content
        await update.message.reply_text(f"📋 *Summary*\n\n{summary}", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, store_message))
    app.add_handler(CommandHandler("summarize", summarize))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()