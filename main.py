import os
import telebot
from telebot import types
from googletrans import Translator
import whisper
from gtts import gTTS
from fpdf import FPDF
import subprocess
from dotenv import load_dotenv
import warnings

# Whisper CPU warning suppression
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")

# Load token from .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

translator = Translator()
model = whisper.load_model("small")
user_settings = {}


def get_settings(user_id):
    if user_id not in user_settings:
        user_settings[user_id] = {
            "output": "text",
            "language": "en",
            "welcome_sent": False,
            "processed_messages": []
        }
    return user_settings[user_id]


def update_settings(user_id, key, value):
    settings = get_settings(user_id)
    settings[key] = value


languages = {
    "en": "🇬🇧 English", "zh-CN": "🇨🇳 Chinese", "hi": "🇮🇳 Hindi", "es": "🇪🇸 Spanish", "fr": "🇫🇷 French",
    "ar": "🇸🇦 Arabic", "bn": "🇧🇩 Bengali", "ru": "🇷🇺 Russian", "pt": "🇧🇷 Portuguese", "ur": "🇵🇰 Urdu",
    "id": "🇮🇩 Indonesian", "de": "🇩🇪 German", "ja": "🇯🇵 Japanese", "sw": "🇿🇦 Swahili", "mr": "🇮🇳 Marathi",
    "te": "🇮🇳 Telugu", "tr": "🇹🇷 Turkish", "ko": "🇰🇷 Korean", "vi": "🇻🇳 Vietnamese", "ta": "🇮🇳 Tamil",
    "ha": "🇳🇬 Hausa", "th": "🇹🇭 Thai", "gu": "🇮🇳 Gujarati", "pl": "🇵🇱 Polish", "uk": "🇺🇦 Ukrainian",
    "fa": "🇮🇷 Persian", "ml": "🇮🇳 Malayalam", "kn": "🇮🇳 Kannada", "or": "🇮🇳 Oriya", "pa": "🇮🇳 Punjabi"
}


@bot.message_handler(commands=['settings'])
def settings_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Text 📝", callback_data="output_text"),
        types.InlineKeyboardButton("Voice 🔊", callback_data="output_voice"),
        types.InlineKeyboardButton("PDF 📄", callback_data="output_pdf")
    )
    temp_row = []
    for code, name in languages.items():
        temp_row.append(types.InlineKeyboardButton(name, callback_data=f"lang_{code}"))
        if len(temp_row) == 2:
            markup.add(*temp_row)
            temp_row = []
    if temp_row:
        markup.add(*temp_row)

    bot.send_message(message.chat.id, "Choose your settings:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data

    if data.startswith("output_"):
        output = data.split("_")[1]
        update_settings(user_id, "output", output)
        bot.answer_callback_query(call.id, f"Output format set to {output.capitalize()}")
    elif data.startswith("lang_"):
        lang_code = data.split("_")[1]
        update_settings(user_id, "language", lang_code)
        bot.answer_callback_query(call.id, f"Language set to {languages.get(lang_code, lang_code)}")


@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    settings = get_settings(user_id)

    if not settings.get("welcome_sent", False):
        bot.send_message(message.chat.id,
                         "🎉 Welcome to the Voice Translator Bot!\n\n"
                         "Send me a voice message, text, or PDF and get it translated!\n\n"
                         "✅ Use /settings to choose:\n• Output format: Text, Voice, PDF\n• Language: Top 30 supported\n\n"
                         "Let’s go! 🚀")
        settings["welcome_sent"] = True
    else:
        bot.send_message(message.chat.id,
                         "Welcome back to Al Voice Translator! 🎉\n\n"
                         "Easily translate your voice messages, texts, and PDFs into 30+ languages right here in Telegram.\n"
                         "Use the /settings command to customize output format (text, voice, PDF) and language.\n\n"
                         "Visit our website for more info:\n"
                         "https://aksel588.github.io/Al-Voice-Translator-web/\n\n"
                         "Let’s keep breaking language barriers together! 🌍🚀")


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    settings = get_settings(user_id)

    if message.message_id in settings["processed_messages"]:
        return
    settings["processed_messages"].append(message.message_id)

    try:
        bot.send_chat_action(message.chat.id, 'typing')
        file_info = bot.get_file(message.voice.file_id)
        file = bot.download_file(file_info.file_path)

        with open("audio.ogg", "wb") as f:
            f.write(file)

        subprocess.run(
            ['ffmpeg', '-loglevel', 'error', '-i', 'audio.ogg', 'audio.wav', '-y'],
            check=True
        )

        result = model.transcribe("audio.wav")
        original_text = result["text"]
        translated = translator.translate(original_text, dest=settings["language"]).text

        respond_by_setting(message, translated, settings)

    except Exception as e:
        bot.reply_to(message, f"❌ Failed to process voice: {e}")
    finally:
        for f in ["audio.ogg", "audio.wav"]:
            if os.path.exists(f):
                os.remove(f)


@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    settings = get_settings(user_id)

    if message.message_id in settings["processed_messages"]:
        return
    settings["processed_messages"].append(message.message_id)

    try:
        bot.send_chat_action(message.chat.id, 'typing')
        translated = translator.translate(message.text, dest=settings["language"]).text
        respond_by_setting(message, translated, settings)
    except Exception as e:
        bot.reply_to(message, f"❌ Translation failed: {e}")


@bot.message_handler(content_types=['audio'])
def handle_audio(message):
    bot.reply_to(message, "ℹ️ Please use the voice (mic) message feature for translations.")


@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    bot.reply_to(message, "📄 PDF received. Text extraction coming soon! 🚀")


def respond_by_setting(message, text, setting):
    try:
        if setting["output"] == "text":
            bot.reply_to(message, text)
        elif setting["output"] == "voice":
            tts = gTTS(text=text, lang=setting["language"])
            tts.save("output.mp3")
            with open("output.mp3", "rb") as v:
                bot.send_voice(message.chat.id, v)
            os.remove("output.mp3")
        elif setting["output"] == "pdf":
            pdf = FPDF()
            pdf.add_page()
            pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)  # Unicode font to support multiple languages
            pdf.set_font("DejaVu", size=12)
            pdf.multi_cell(190, 10, txt=text[:10000])
            pdf.output("output.pdf")
            with open("output.pdf", "rb") as p:
                bot.send_document(message.chat.id, p)
            os.remove("output.pdf")
    except Exception as e:
        bot.reply_to(message, f"❌ Error responding: {e}")


bot.polling()
