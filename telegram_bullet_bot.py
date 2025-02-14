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
TOKEN = "7127008615:AAEDL_T7wl9L92x9276meCYY3LPb-0Yop4E"
ALLOWED_CHAT_ID = 7012719413  # Reemplaza con tu chat ID
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Conectar a la base de datos SQLite
DB_FILE = "bullet_journal.db"

def init_db():
    with sqlite3.connect("bullet_journal.db") as conn:
        cursor = conn.cursor()

        # 📌 Tabla de usuarios (XP y referencia a misiones)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            xp INTEGER DEFAULT 0
        )
        """)

        # 📌 Tabla de misiones asignadas a los usuarios
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            user_id INTEGER,
            mission TEXT,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)

        # 📌 Tabla de perfiles para el sistema de roles
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            name TEXT DEFAULT 'Humano Promedio',
            xp INTEGER DEFAULT 0,
            class TEXT DEFAULT 'Humano Promedio'
        )
        """)
        conn.commit()


# 📌 2. Registrar Usuarios Nuevos con el Rango "Humano Promedio"
def register_user(user_id):
    conn = sqlite3.connect("bullet_journal.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO profiles (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# 📌 3. Comando `/perfil` para ver el progreso del usuario
async def perfil(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    conn = sqlite3.connect("bullet_journal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, xp, class FROM profiles WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    conn.close()

    if profile:
        name, xp, user_class = profile
        await update.message.reply_text(f"👤 **Perfil de {name}**\n🔹 XP: {xp}\n🏆 Clase: {user_class}")
    else:
        await update.message.reply_text("⚠️ No tienes un perfil aún. Usa /start para registrarte.")

# 📌 4. Comando `/set_nombre` para personalizar el nombre del usuario
async def set_nombre(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    new_name = " ".join(context.args)
    if not new_name:
        await update.message.reply_text("⚠️ Debes escribir un nombre. Usa: /set_nombre <nombre>")
        return
    
    conn = sqlite3.connect("bullet_journal.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE profiles SET name = ? WHERE user_id = ?", (new_name, user_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Tu nombre ha sido actualizado a: {new_name}")

# 📌 5. Agregar los comandos al bot
from telegram.ext import Application  #final de la funcion


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
    app.add_handler(CommandHandler("perfil", perfil))
    app.add_handler(CommandHandler("set_nombre", set_nombre))
    app.run_polling()

if __name__ == "__main__":
    main()
