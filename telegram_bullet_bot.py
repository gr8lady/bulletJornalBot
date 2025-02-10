import os
import logging
import sqlite3
import asyncio
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Configurar logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Hardcoded values (para debugging)
TOKEN = "7127008615:AAEDL_T7wl9L92x9276meCYY3LPb-0Yop4E"
ALLOWED_CHAT_ID = 7012719413  # Reemplaza con tu chat ID

# Uso de variables de entorno (descomentar para producción)
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

# Obtener nivel de usuario
def get_level(xp):
    if xp < 50:
        return "🟢 Novato"
    elif xp < 150:
        return "🔵 Aprendiz"
    elif xp < 300:
        return "🟣 Experto"
    else:
        return "🟠 Maestro"

# Comando para ver perfil de usuario
async def profile(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    
    user_id = update.message.chat_id
    conn = sqlite3.connect("bullet_journal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT xp FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    xp = result[0] if result else 0
    level = get_level(xp)
    await update.message.reply_text(f"🎖 Tu progreso:\n🔹 XP: {xp}\n🏆 Rango: {level}")

# Comando de inicio
async def start(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    add_user(update.message.chat_id)
    await update.message.reply_text("¡Bienvenido a tu Bullet Journal Bot! 🎯")

# Comando para agregar una misión
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

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("perfil", profile))
    app.add_handler(CommandHandler("agregar_mision", add_mission_command))
    app.add_handler(CommandHandler("mision", assign_random_mission))
    app.run_polling()

if __name__ == "__main__":
    main()
