import os
import telebot
from telebot import types
from googletrans import Translator
import whisper
from gtts import gTTS
from fpdf import FPDF
import subprocess

# Initialize bot and required libraries
bot = telebot.TeleBot("YOUR_TELEGRAM_TOKEN")
translator = Translator()
model = whisper.load_model("small")

# Store user settings
user_settings = {}

# Set default settings
def get_settings(user_id):
    return user_settings.get(user_id, {
        "output": "text",  # text, voice, pdf
        "language": "en"
    })

# Save user settings
def update_settings(user_id, key, value):
    if user_id not in user_settings:
        user_settings[user_id] = get_settings(user_id)
    user_settings[user_id][key] = value

# Languages list (top 30 languages)
languages = {
    "en": "🇬🇧 English",
    "zh-CN": "🇨🇳 Chinese (Simplified)",
    "hi": "🇮🇳 Hindi",
    "es": "🇪🇸 Spanish",
    "fr": "🇫🇷 French",
    "ar": "🇸🇦 Arabic",
    "bn": "🇧🇩 Bengali",
    "ru": "🇷🇺 Russian",
    "pt": "🇧🇷 Portuguese",
    "ur": "🇵🇰 Urdu",
    "id": "🇮🇩 Indonesian",
    "de": "🇩🇪 German",
    "ja": "🇯🇵 Japanese",
    "sw": "🇿🇦 Swahili",
    "mr": "🇮🇳 Marathi",
    "te": "🇮🇳 Telugu",
    "tr": "🇹🇷 Turkish",
    "ko": "🇰🇷 Korean",
    "vi": "🇻🇳 Vietnamese",
    "ta": "🇮🇳 Tamil",
    "ha": "🇳🇬 Hausa",
    "th": "🇹🇭 Thai",
    "gu": "🇮🇳 Gujarati",
    "pl": "🇵🇱 Polish",
    "uk": "🇺🇦 Ukrainian",
    "fa": "🇮🇷 Persian",
    "ml": "🇮🇳 Malayalam",
    "kn": "🇮🇳 Kannada",
    "or": "🇮🇳 Oriya",
    "pa": "🇮🇳 Punjabi"
}

# Show settings buttons
@bot.message_handler(commands=['settings'])
def settings_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Output format buttons (Text, Voice, PDF)
    output_btns = [
        types.InlineKeyboardButton("Text", callback_data="output_text"),
        types.InlineKeyboardButton("Voice", callback_data="output_voice"),
        types.InlineKeyboardButton("PDF", callback_data="output_pdf")
    ]
    
    # Language buttons (Top 30 languages)
    lang_btns = [types.InlineKeyboardButton(name, callback_data=f"lang_{lang_code}") for lang_code, name in languages.items()]
    
    markup.add(*output_btns)
    markup.add(*lang_btns)
    bot.send_message(message.chat.id, "Choose your settings:", reply_markup=markup)

# Handle callback from settings menu
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    if call.data.startswith("output_"):
        update_settings(user_id, "output", call.data.split("_")[1])
        bot.answer_callback_query(call.id, f"Output set to {call.data.split('_')[1]}")
    elif call.data.startswith("lang_"):
        lang_code = call.data.split("_")[1]
        update_settings(user_id, "language", lang_code)
        bot.answer_callback_query(call.id, f"Language set to {languages.get(lang_code)}")

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id

    # Check if the user has already received the welcome message
    if "welcome_sent" not in user_settings.get(user_id, {}):
        welcome_text = (
            "Welcome to the Voice Translator Bot! 🎉\n\n"
            "This bot allows you to send voice messages, text, or PDFs and get translations in your preferred language. "
            "You can also receive the translations in different formats: text, voice, or PDF.\n\n"
            "Use /settings to customize the output format and language.\n\n"
            "How to use:\n"
            "1. Send a voice message, and I'll transcribe and translate it.\n"
            "2. Send a text, and I'll translate it.\n"
            "3. Send a PDF, and I'll notify you (text extraction not supported yet).\n\n"
            "Ready to get started? Send me a voice message, text, or PDF!"
        )
        bot.send_message(message.chat.id, welcome_text)

        # Mark the welcome message as sent
        if user_id not in user_settings:
            user_settings[user_id] = {}
        user_settings[user_id]["welcome_sent"] = True
    else:
        # Optionally, you can send a different message if the user already received the welcome message
        bot.send_message(message.chat.id, "Welcome back! Ready to translate? Use /settings to customize.")

# Handle voice message
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    setting = get_settings(user_id)

    # Check if the message was already processed (prevent double responses)
    if message.message_id in user_settings.get(user_id, {}).get("processed_messages", []):
        return  # Ignore the message if it's already been processed
    
    # Mark the message as processed to avoid duplicates
    if "processed_messages" not in user_settings.get(user_id, {}):
        user_settings[user_id]["processed_messages"] = []
    user_settings[user_id]["processed_messages"].append(message.message_id)

    file_info = bot.get_file(message.voice.file_id)
    file = bot.download_file(file_info.file_path)

    with open("audio.ogg", "wb") as f:
        f.write(file)

    # Convert OGG to WAV using ffmpeg
    subprocess.run(['ffmpeg', '-i', 'audio.ogg', 'audio.wav', '-y'])

    # Transcribe the voice message using Whisper
    result = model.transcribe("audio.wav")
    original_text = result["text"]
    translated = translator.translate(original_text, dest=setting["language"]).text

    # Respond based on user settings (text, voice, or pdf)
    respond_by_setting(message, translated, setting)

# Handle text message
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    setting = get_settings(user_id)

    # Check if the message was already processed (prevent double responses)
    if message.message_id in user_settings.get(user_id, {}).get("processed_messages", []):
        return  # Ignore the message if it's already been processed
    
    # Mark the message as processed to avoid duplicates
    if "processed_messages" not in user_settings.get(user_id, {}):
        user_settings[user_id]["processed_messages"] = []
    user_settings[user_id]["processed_messages"].append(message.message_id)

    # Translate text based on user's language preference
    translated = translator.translate(message.text, dest=setting["language"]).text
    respond_by_setting(message, translated, setting)

# Handle PDF file
@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    user_id = message.from_user.id
    setting = get_settings(user_id)

    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)

    with open("input.pdf", "wb") as f:
        f.write(downloaded)

    # Notify the user that PDF processing is not supported (text extraction not implemented)
    bot.send_message(message.chat.id, "Received your PDF. (Text extraction not supported in this version)")

# Respond based on user settings (text, voice, or pdf)
def respond_by_setting(message, text, setting):
    if setting["output"] == "text":
        bot.reply_to(message, text)
    elif setting["output"] == "voice":
        tts = gTTS(text=text, lang=setting["language"])
        tts.save("output.mp3")
        with open("output.mp3", "rb") as v:
            bot.send_voice(message.chat.id, v)
    elif setting["output"] == "pdf":
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(190, 10, txt=text)
        pdf.output("output.pdf")
        with open("output.pdf", "rb") as p:
            bot.send_document(message.chat.id, p)

# Start the bot
bot.polling()