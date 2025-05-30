from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
)
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
from flask import Flask
import threading

# User state dictionary
user_states = {}

# /start command
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "👋 Welcome to Gujarati Learning Bot!\nSend me any sentence in English, and I'll give you the Gujarati translation + pronunciation."
    )

# /help command
def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "📌 Just send an English sentence.\nI’ll translate it into Gujarati and send audio.\n\nYou can rate the translation as ✅ Correct or ❌ Wrong."
    )

# Unified message handler for both translation and correction
def handle_message(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    state = user_states.get(chat_id)

    # If user is providing correction
    if state and state.get("awaiting_correction"):
        if update.message.voice:
            file = update.message.voice.get_file()
            filename = f"correction_{chat_id}.ogg"
            file.download(filename)
            correction = f"[Audio Correction File: {filename}]"
        else:
            correction = update.message.text or "[Empty correction]"

        # Save feedback
        with open("feedback_log.txt", "a", encoding="utf-8") as f:
            f.write(
                f"\n📝 Feedback:\nOriginal: {state['original']}\nBot Translation: {state['translation']}\nUser Correction: {correction}\n{'-'*40}\n"
            )

        update.message.reply_text("✅ Your correction has been saved. You can now send a new English sentence!")
        user_states[chat_id]["awaiting_correction"] = False

        # Clean up audio file if present
        if update.message.voice:
            os.remove(filename)
        return

    # Proceed with translation
    user_text = update.message.text
    if not user_text:
        update.message.reply_text("⚠️ Please send text to translate.")
        return

    gu_text = GoogleTranslator(source='auto', target='gu').translate(user_text)

    # Save state
    user_states[chat_id] = {
        "original": user_text,
        "translation": gu_text,
        "awaiting_correction": False
    }

    # Send translation and audio
    update.message.reply_text(f"Gujarati: {gu_text}\nPronunciation: Pronunciation not available with this method")
    tts = gTTS(text=gu_text, lang='gu')
    audio_file = f"pronunciation_{chat_id}.mp3"
    tts.save(audio_file)
    with open(audio_file, 'rb') as audio:
        update.message.reply_audio(audio)
    os.remove(audio_file)

    # Feedback buttons
    buttons = [[
        InlineKeyboardButton("✅ Correct", callback_data='correct'),
        InlineKeyboardButton("❌ Wrong", callback_data='wrong')
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    update.message.reply_text("Was this translation correct?", reply_markup=reply_markup)

# Feedback button handler
def feedback_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat.id
    query.answer()

    if query.data == "correct":
        query.edit_message_text("✅ Thanks! I'm glad it helped. Send the next English sentence.")
    elif query.data == "wrong":
        user_states[chat_id]["awaiting_correction"] = True
        query.edit_message_text("❌ Oh! Please send the correct translation (text or audio).")

# Flask server (for Replit or keep-alive service)
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()

# Main function
def main():
    from dotenv import load_dotenv
    load_dotenv()
    token = os.getenv("BOT_TOKEN")

    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CallbackQueryHandler(feedback_handler))
    dp.add_handler(MessageHandler(Filters.text | Filters.voice, handle_message))

    keep_alive()
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

