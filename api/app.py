import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from gtts import gTTS
import speech_recognition as sr
import openai
from datetime import datetime

# --- CONFIGURATION ---
app = Flask(__name__)

# Secure: Load OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- DATABASE SETUP ---
DB_FILE = "chat_history.db"
TEXT_FILE = "chat_history.txt"  # text file to store chat history

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_input TEXT,
                    bot_response TEXT,
                    timestamp TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

# --- AI RESPONSE FUNCTION ---
def generate_response(user_input, language="English"):
    try:
        prompt = (f"You are a bilingual healthcare assistant. "
                  f"Answer in {language} (Sesotho or English) clearly about health, maternal, HIV/AIDS, or nutrition topics. "
                  f"User said: {user_input}")

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        message = response.choices[0].message.content
        return message
    except Exception as e:
        print("OpenAI API error:", e)
        return "Sorry, I couldn’t connect to the AI service."

# --- SAVE CHAT TO DATABASE ---
def save_chat(user_input, bot_response):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO chat (user_input, bot_response, timestamp) VALUES (?, ?, ?)",
              (user_input, bot_response, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# --- SAVE CHAT TO TEXT FILE ---
def save_chat_to_file(user_input, bot_response, language="English"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(TEXT_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] ({language}) You: {user_input}\n")
        f.write(f"[{timestamp}] ({language}) Bot: {bot_response}\n\n")

# --- ROUTES ---
@app.route("/")
def home():
    chat_history = ""
    if os.path.exists(TEXT_FILE):
        with open(TEXT_FILE, "r", encoding="utf-8") as f:
            chat_history = f.read()
    return render_template("index.html", chat_history=chat_history)

@app.route("/get", methods=["POST"])
def chat():
    user_input = request.form["msg"]
    language = request.form.get("language", "English")  # default to English

    response = generate_response(user_input, language)
    save_chat(user_input, response)
    save_chat_to_file(user_input, response, language)
    return jsonify({"response": response})

# --- VOICE INPUT ---
@app.route("/voice", methods=["POST"])
def voice_input():
    recognizer = sr.Recognizer()
    audio_file = request.files["audio"]
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio)
        return jsonify({"text": text})
    except:
        return jsonify({"text": "Sorry, I couldn’t understand the audio."})

# --- TEXT-TO-SPEECH ---
@app.route("/speak", methods=["POST"])
def speak():
    text = request.form["text"]
    language = request.form.get("language", "English")
    tts_lang = "en" if language.lower() == "english" else "st"  # 'st' = Sesotho

    tts = gTTS(text=text, lang=tts_lang)
    filename = f"static/voice_{datetime.now().timestamp()}.mp3"
    tts.save(filename)
    return jsonify({"audio_url": filename})

if __name__ == "__main__":
    # Important: For local testing only. Vercel runs Flask via serverless entry.
    app.run(debug=True)
