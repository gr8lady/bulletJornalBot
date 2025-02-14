import os
import logging
import sqlite3
import random
import requests
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Configuración de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Variables de entorno y configuración
TOKEN = "712-----p4E"
ALLOWED_CHAT_ID = 70----13  # Reemplaza con tu chat ID
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Conectar a la base de datos SQLite
DB_FILE = "bullet_journal.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Tabla de usuarios
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            xp INTEGER DEFAULT 0
        )""")

        # Tabla de perfiles
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            name TEXT DEFAULT 'Humano Promedio',
            xp INTEGER DEFAULT 0,
            class TEXT DEFAULT 'Humano Promedio'
        )""")

        # Tabla de áreas de vida (Ciudades)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            health INTEGER DEFAULT 100
        )""")

        # Tabla de misiones
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            mission TEXT,
            area_id INTEGER,
            peso INTEGER DEFAULT 1, -- 1: Baja, 2: Media, 3: Alta
            completed INTEGER DEFAULT 0,
            deadline TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (area_id) REFERENCES areas(id)
        )""")

        # Tabla de tareas dentro de las misiones
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id INTEGER,
            task TEXT,
            xp INTEGER DEFAULT 10,
            status TEXT DEFAULT 'pendiente',
            FOREIGN KEY (mission_id) REFERENCES missions(id)
        )""")

        conn.commit()

# Función para agregar un área de vida (ciudad)
async def add_area(update: Update, context: CallbackContext):
    area_name = " ".join(context.args)
    if not area_name:
        await update.message.reply_text("⚠️ Debes escribir un nombre de área. Usa: /agregar_area <nombre>")
        return

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO areas (name) VALUES (?)", (area_name,))
        conn.commit()

    await update.message.reply_text(f"🏙️ Área '{area_name}' agregada.")

# Función para agregar una misión con área y peso
async def add_mission(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("⚠️ Uso: /agregar_mision <Área> <Prioridad (Alta/Media/Baja)> <Nombre>")
        return

    area_name, priority, mission_name = args[0], args[1].capitalize(), " ".join(args[2:])
    peso = {"Alta": 3, "Media": 2, "Baja": 1}.get(priority, 1)
    deadline = (datetime.datetime.now() + datetime.timedelta(days=2)).isoformat()

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM areas WHERE name = ?", (area_name,))
        area = cursor.fetchone()
        if not area:
            await update.message.reply_text("⚠️ No encontré esa área. Agrega una con /agregar_area <nombre>.")
            return
        area_id = area[0]
        cursor.execute("INSERT INTO missions (user_id, mission, area_id, peso, deadline) VALUES (?, ?, ?, ?, ?)",
                       (user_id, mission_name, area_id, peso, deadline))
        conn.commit()

    await update.message.reply_text(f"✅ Misión '{mission_name}' agregada en el área '{area_name}' (Prioridad: {priority}).")

# Función para completar una misión
async def complete_mission(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    mission_name = " ".join(context.args)
    if not mission_name:
        await update.message.reply_text("⚠️ Uso: /completar_mision <nombre>")
        return

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, peso, area_id FROM missions WHERE user_id = ? AND mission = ? AND completed = 0",
                       (user_id, mission_name))
        mission = cursor.fetchone()
        if not mission:
            await update.message.reply_text("⚠️ No encontré esa misión activa.")
            return

        mission_id, peso, area_id = mission
        cursor.execute("UPDATE missions SET completed = 1 WHERE id = ?", (mission_id,))
        cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (peso * 10, user_id))  # XP según peso
        cursor.execute("UPDATE areas SET health = health + ? WHERE id = ?", (peso * 5, area_id))  # Restaurar ciudad
        conn.commit()

    await update.message.reply_text(f"✅ Misión '{mission_name}' completada. +{peso * 10} XP.")

# Función de ayuda
async def help_command(update: Update, context: CallbackContext):
    help_text = """
    📜 **Comandos Disponibles:**
    /start - Iniciar y registrarte en el juego
    /perfil - Ver tu progreso y clase actual
    /agregar_area - Agregar una nueva área de vida
    /agregar_mision - Agregar una misión con área y prioridad
    /completar_mision - Marcar una misión como completada
    /help - Mostrar esta ayuda
    """
    await update.message.reply_text(help_text)

# fin de la funcion help text 


async def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        cursor.execute("INSERT OR IGNORE INTO profiles (user_id, name, xp, class) VALUES (?, 'Humano Promedio', 0, 'Humano Promedio')", (user_id,))
        conn.commit()

    await update.message.reply_text("🎯 ¡Bienvenido a Bullet Journal Quest! Tu aventura comienza como 'Humano Promedio'. Usa /perfil para ver tu estado.")

# Función para ver el perfil del usuario
async def perfil(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, xp, class FROM profiles WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    conn.close()

    if profile:
        name, xp, user_class = profile
        await update.message.reply_text(f"👤 **Perfil de {name}**\n🔹 XP: {xp}\n🏆 Clase: {user_class}")
    else:
        await update.message.reply_text("⚠️ No tienes un perfil aún. Usa /start para registrarte.")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("perfil", perfil))
    app.add_handler(CommandHandler("agregar_area", add_area))
    app.add_handler(CommandHandler("agregar_mision", add_mission))
    app.add_handler(CommandHandler("completar_mision", complete_mission))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
