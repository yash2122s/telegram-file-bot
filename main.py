
import os
import logging
import base64
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Get the token from Replit Secrets
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# --- Temporary "Database" ---
# This dictionary will store our file references.
# For a real bot, you should use a proper database like SQLite.
file_database = {}
file_counter = 0
# -----------------------------

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# This function now handles receiving files and creating deep links
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global file_counter
    if not update.message:
        return

    file_id = None
    file_type = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    elif update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    else:
        return

    # 1. Create a unique key for the file
    file_counter += 1
    file_key = f"file_{file_counter}"

    # 2. Store the file_id and its type in our database
    file_database[file_key] = {"id": file_id, "type": file_type}

    # 3. Base64 encode the key to use in the URL
    encoded_key = base64.urlsafe_b64encode(file_key.encode()).decode()

    # 4. Get the bot's username to build the link
    bot_username = (await context.bot.get_me()).username

    # 5. Create the deep link and send it back
    deep_link = f"https://t.me/{bot_username}?start={encoded_key}"
    await update.message.reply_text(
        f"✅ Deep link generated!\n\nShare this link to give others access to the file:\n{deep_link}"
    )

# This function now handles users clicking the deep link
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            # 1. Decode the key from the link
            encoded_key = context.args[0]
            decoded_key = base64.urlsafe_b64decode(encoded_key).decode()

            # 2. Look up the file in our database
            file_data = file_database.get(decoded_key)

            if file_data:
                # 3. Send the correct file type based on the stored info
                file_id = file_data["id"]
                file_type = file_data["type"]

                await update.message.reply_text("Sending you the file...")
                if file_type == "photo":
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=file_id)
                elif file_type == "document":
                    await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id)
                elif file_type == "video":
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=file_id)
            else:
                await update.message.reply_text("Sorry, this link is invalid or has expired.")
        
        except Exception as e:
            logger.error(f"Error processing deep link: {e}")
            await update.message.reply_text("This link appears to be broken.")
    else:
        # Normal /start command
        await update.message.reply_text("Hello! Send me a file to generate a shareable deep link.")

# Main function to run the bot
def main():
    if not TELEGRAM_BOT_TOKEN:
        print("!!! ERROR: TELEGRAM_BOT_TOKEN not found. !!!")
        return

    print("Bot is starting with deep link logic...")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL | filters.VIDEO, file_handler))

    application.run_polling()

if __name__ == '__main__':
    main()
