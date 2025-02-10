import os
import logging
import sqlite3
import asyncio
import random
import requests
from transformers import pipeline
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Configurar logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Hardcoded values (para debugging)
TOKEN = "TU_BOT_TOKEN"
ALLOWED_CHAT_ID = 7012719413  # Reemplaza con tu chat ID

# Uso de variables de entorno (para producción)
# TOKEN = os.getenv("TOKEN")
# ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "0"))

# Conectar a la base de datos SQLite
def init_db():
    conn = sqlite3.connect("bullet_journal.db")
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
        completed INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect("bullet_journal.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, xp) VALUES (?, ?)", (user_id, 0))
    conn.commit()
    conn.close()

# Obtener misiones pendientes
def get_missions(user_id):
    conn = sqlite3.connect("bullet_journal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT mission FROM missions WHERE user_id = ? AND completed = 0", (user_id,))
    missions = cursor.fetchall()
    conn.close()
    return [m[0] for m in missions]

# Completar una misión y agregar XP
def complete_mission(user_id, mission):
    conn = sqlite3.connect("bullet_journal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM missions WHERE user_id = ? AND mission = ? AND completed = 0", (user_id, mission))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return False  # La misión no existe o ya está completada

    cursor.execute("UPDATE missions SET completed = 1 WHERE user_id = ? AND mission = ?", (user_id, mission))
    cursor.execute("UPDATE users SET xp = xp + 10 WHERE user_id = ?", (user_id,))  # +10 XP por misión completada
    conn.commit()
    conn.close()
    return True

# Comando de inicio
async def start(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    add_user(update.message.chat_id)
    await update.message.reply_text("¡Bienvenido a tu Bullet Journal Bot! 🎯")

# Agregar una misión
def add_mission(user_id, mission):
    conn = sqlite3.connect("bullet_journal.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO missions (user_id, mission, completed) VALUES (?, ?, ?)", (user_id, mission, 0))
    conn.commit()
    conn.close()

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

# Asignar una misión aleatoria
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

# Completar una misión
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

# Ver misiones pendientes
async def show_missions(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    
    user_id = update.message.chat_id
    missions = get_missions(user_id)
    if missions:
        await update.message.reply_text("📜 Tus misiones pendientes:\n" + "\n".join(missions))
    else:
        await update.message.reply_text("🎉 ¡No tienes misiones pendientes!")

# ✅ **IA con Hugging Face**
ai_pipeline = pipeline("text-generation", model="mistralai/Mistral-7B-v0.1")

def generate_ai_response(prompt):
    response = ai_pipeline(prompt, max_length=50, do_sample=True)
    return response[0]["generated_text"]

# Comando para motivación IA
async def motivate(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return

    prompt = "Dame un mensaje motivacional para alguien que está completando misiones de productividad."
    ai_response = generate_ai_response(prompt)
    await update.message.reply_text(f"🤖 IA dice: {ai_response}")

# Configurar el bot
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
