import logging
import sqlite3
import schedule
import time
import asyncio

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
except ModuleNotFoundError:
    print("Error: La biblioteca 'python-telegram-bot' no está instalada. Instálala con: pip install python-telegram-bot")
    exit()

# Configurar logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Configurar el chat permitido
ALLOWED_CHAT_ID = 7012719413  # Reemplaza con tu chat ID específico

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

# Agregar un usuario a la base de datos
def add_user(user_id):
    conn = sqlite3.connect("bullet_journal.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, xp) VALUES (?, ?)", (user_id, 0))
    conn.commit()
    conn.close()

# Agregar una misión
def add_mission(user_id, mission):
    conn = sqlite3.connect("bullet_journal.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO missions (user_id, mission, completed) VALUES (?, ?, ?)", (user_id, mission, 0))
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

# Completar una misión
def complete_mission(user_id, mission):
    conn = sqlite3.connect("bullet_journal.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE missions SET completed = 1 WHERE user_id = ? AND mission = ?", (user_id, mission))
    cursor.execute("UPDATE users SET xp = xp + 10 WHERE user_id = ?", (user_id,))  # 10 XP por misión completada
    conn.commit()
    conn.close()

# Comandos de Telegram
async def start(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    user_id = update.message.chat_id
    add_user(user_id)
    await update.message.reply_text("¡Bienvenido a tu Bullet Journal Bot! 🎯 Te asignaré misiones y llevaré un registro de tu XP.")

# Asignar misión diaria
async def daily_mission(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    user_id = update.message.chat_id
    mission = "Completar una tarea importante hoy 🏆"
    add_mission(user_id, mission)
    await update.message.reply_text(f"Tu misión de hoy: {mission}")

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

# Completar una misión
async def complete(update: Update, context: CallbackContext):
    if update.message.chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return
    user_id = update.message.chat_id
    mission = " ".join(context.args)
    complete_mission(user_id, mission)
    await update.message.reply_text(f"✅ Has completado la misión: {mission}! +10 XP")

# Configurar el bot
def main():
    init_db()
    TOKEN = "7127008615:AAEDL_T7wl9L92x9276meCYY3LPb-0Yop4E"
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mision", daily_mission))
    app.add_handler(CommandHandler("misiones", show_missions))
    app.add_handler(CommandHandler("completar", complete))
    
    app.run_polling()

if __name__ == "__main__":
    main()
