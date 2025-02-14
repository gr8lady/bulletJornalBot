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
TOKEN = "7127008615:AAEDL_T7wl9L92x9276meCYY3LPb-0Yop4E"
ALLOWED_CHAT_ID = 7012719413  # Reemplaza con tu chat ID
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
            deadline TEXT DEFAULT NULL,
            FOREIGN KEY (mission_id) REFERENCES missions(id)
        )""")
        conn.commit()

# fin de la funcion de creacion de tablas

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
    /status - Ver el estado general de tu progreso
    /agregar_area <nombre> - Agregar una nueva área de vida
    /agregar_mision <Área> <Prioridad (Alta/Media/Baja)> <Nombre> - Agregar una misión
    /completar_mision <nombre> - Marcar una misión como completada
    /agregar_tarea <misión> <tarea> <días> - Agregar una tarea a una misión
    /completar_tarea <tarea> - Marcar una tarea como completada
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
# inicio funcion  de status de las misiones

async def status(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Obtener información del usuario
    cursor.execute("SELECT name, xp, class FROM profiles WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()

    # Obtener estado de las áreas (ciudades)
    cursor.execute("SELECT name, health FROM areas")
    areas = cursor.fetchall()

    # Obtener misiones activas
    cursor.execute("SELECT mission, completed FROM missions WHERE user_id = ? AND completed = 0", (user_id,))
    missions = cursor.fetchall()

    # Obtener tareas pendientes y zombies
    cursor.execute("SELECT task, status FROM tasks WHERE status IN ('pendiente', 'zombie')")
    tasks = cursor.fetchall()

    conn.close()

    # Construir la respuesta
    response = f"📜 **Estado General**\n"
    if profile:
        name, xp, user_class = profile
        response += f"👤 **{name}**\n🔹 XP: {xp}\n🏆 Clase: {user_class}\n\n"

    response += "🏙️ **Estado de Ciudades:**\n"
    for area_name, health in areas:
        response += f" - {area_name}: {health} ❤️\n"

    response += "\n🎯 **Misiones Activas:**\n"
    if missions:
        for mission, completed in missions:
            response += f" - {mission} {'✅' if completed else '❌'}\n"
    else:
        response += " - No hay misiones activas.\n"

    response += "\n📝 **Tareas Pendientes:**\n"
    if tasks:
        for task, status in tasks:
            emoji = "🧟" if status == "zombie" else "📌"
            response += f" - {emoji} {task}\n"
    else:
        response += " - No hay tareas pendientes.\n"

    await update.message.reply_text(response)
# fin de la funcion de status de las misiones

# Modificar la tabla de tareas para agregar el deadline
def update_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        ALTER TABLE tasks ADD COLUMN deadline TEXT DEFAULT NULL
        """)
        conn.commit()

# Función para agregar una tarea con deadline
async def add_task(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("⚠️ Uso: /agregar_tarea <misión> <tarea> <días para completar>")
        return

    mission_name, task_name, days = args[0], " ".join(args[1:-1]), int(args[-1])
    deadline = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM missions WHERE user_id = ? AND mission = ? AND completed = 0", (user_id, mission_name))
        mission = cursor.fetchone()
        if not mission:
            await update.message.reply_text("⚠️ No encontré esa misión activa.")
            return

        mission_id = mission[0]
        cursor.execute("INSERT INTO tasks (mission_id, task, deadline) VALUES (?, ?, ?)", (mission_id, task_name, deadline))
        conn.commit()

    await update.message.reply_text(f"✅ Tarea '{task_name}' agregada a '{mission_name}'. Fecha límite: {deadline}")

# Función para completar una tarea
async def complete_task(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    task_name = " ".join(context.args)
    if not task_name:
        await update.message.reply_text("⚠️ Uso: /completar_tarea <nombre>")
        return

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, xp FROM tasks WHERE task = ? AND status = 'pendiente'", (task_name,))
        task = cursor.fetchone()
        if not task:
            await update.message.reply_text("⚠️ No encontré esa tarea pendiente.")
            return

        task_id, xp = task
        cursor.execute("UPDATE tasks SET status = 'completado' WHERE id = ?", (task_id,))
        cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (xp, user_id))
        conn.commit()

    await update.message.reply_text(f"✅ Tarea '{task_name}' completada. +{xp} XP.")

# Función automática para actualizar tareas a 'zombie' si expiran
def update_task_status():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cursor.execute("UPDATE tasks SET status = 'zombie' WHERE deadline < ? AND status = 'pendiente'", (now,))
        conn.commit()

# Programar la revisión automática cada 24 horas
import threading
def schedule_task_update():
    update_task_status()
    threading.Timer(86400, schedule_task_update).start()

schedule_task_update()


if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("perfil", perfil))
    app.add_handler(CommandHandler("agregar_area", add_area))
    app.add_handler(CommandHandler("agregar_mision", add_mission))
    app.add_handler(CommandHandler("completar_mision", complete_mission))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("agregar_tarea", add_task))
    app.add_handler(CommandHandler("completar_tarea", complete_task))

    app.run_polling()
