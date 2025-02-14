import os
import logging
import sqlite3
import random
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Configuración de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Variables de entorno y configuración
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Almacena tu token de forma segura en variables de entorno
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "0"))  # Configurable desde el entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Conectar a la base de datos SQLite
DB_FILE = "bullet_journal.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            xp INTEGER DEFAULT 0
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            user_id INTEGER,
            mission TEXT,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        conn.commit()

def execute_query(query, params=(), fetch_one=False, fetch_all=False):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        conn.commit()

def add_user(user_id):
    execute_query("INSERT OR IGNORE INTO users (user_id, xp) VALUES (?, ?)" ,(user_id, 0))

def get_missions(user_id):
    return [m[0] for m in execute_query("SELECT mission FROM missions WHERE user_id = ? AND completed = 0", (user_id,), fetch_all=True)]

def complete_mission(user_id, mission):
    mission_exists = execute_query("SELECT * FROM missions WHERE user_id = ? AND mission = ? AND completed = 0", (user_id, mission), fetch_one=True)
    if not mission_exists:
        return False
    execute_query("UPDATE missions SET completed = 1 WHERE user_id = ? AND mission = ?", (user_id, mission))
    execute_query("UPDATE users SET xp = xp + 10 WHERE user_id = ?", (user_id,))  # +10 XP
    return True

async def start(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    add_user(update.message.chat_id)
    await update.message.reply_text("¡Bienvenido a tu Bullet Journal Bot! 🎯")

def add_mission(user_id, mission):
    execute_query("INSERT INTO missions (user_id, mission, completed) VALUES (?, ?, 0)", (user_id, mission))

async def add_mission_command(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    mission = " ".join(context.args)
    if not mission:
        await update.message.reply_text("⚠️ Debes escribir una misión. Usa: /agregar_mision <nombre>")
        return
    add_mission(update.message.chat_id, mission)
    await update.message.reply_text(f"✅ Misión agregada: {mission}")

async def assign_random_mission(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    missions = [
        "📚 Leer 10 páginas de un libro",
        "🏃‍♂️ Hacer 10 minutos de ejercicio",
        "🧹 Limpiar tu escritorio",
        "🎯 Planear tu día de mañana",
        "💡 Aprender algo nuevo en 10 minutos"
    ]
    mission = random.choice(missions)
    add_mission(update.message.chat_id, mission)
    await update.message.reply_text(f"🎯 Nueva misión asignada: {mission}")

async def complete(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    mission = " ".join(context.args)
    if not mission:
        await update.message.reply_text("⚠️ Debes escribir el nombre de la misión que completaste. Usa: /completar <nombre>")
        return
    if complete_mission(update.message.chat_id, mission):
        await update.message.reply_text(f"✅ Has completado la misión: {mission}! +10 XP")
    else:
        await update.message.reply_text("⚠️ No encontré esa misión pendiente en tu lista.")

async def show_missions(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    missions = get_missions(update.message.chat_id)
    if missions:
        await update.message.reply_text("📜 Tus misiones pendientes:\n" + "\n".join(missions))
    else:
        await update.message.reply_text("🎉 ¡No tienes misiones pendientes!")

def generate_ai_response(prompt):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}]}
    response = requests.post(url, headers=headers, json=data)
    return response.json().get("choices", [{}])[0].get("message", {}).get("content", "No response.")

async def motivate(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    prompt = "Dame un mensaje motivacional para alguien que está completando misiones de productividad."
    ai_response = generate_ai_response(prompt)
    await update.message.reply_text(f"🤖 IA dice: {ai_response}")

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("agregar_mision", add_mission_command))
    app.add_handler(CommandHandler("mision", assign_random_mission))
    app.add_handler(CommandHandler("completar", complete))
    app.add_handler(CommandHandler("misiones", show_missions))
    app.add_handler(CommandHandler("motivacion", motivate))
    app.run_polling()

if __name__ == "__main__":
    main()
