import os
import logging
import sqlite3
import random
from functools import wraps
from contextlib import contextmanager
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from transformers import pipeline

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "0"))

# Define missions once at the module level
MISSIONS = [
    "📚 Leer 10 páginas de un libro",
    "🏃‍♂️ Hacer 10 minutos de ejercicio",
    "🧹 Limpiar tu escritorio",
    "🎯 Planear tu día de mañana",
    "💡 Aprender algo nuevo en 10 minutos",
]

# Initialize AI pipeline
try:
    ai_pipeline = pipeline("text-generation", model="mistralai/Mistral-7B-v0.1")
except Exception as e:
    logger.error(f"Failed to initialize AI pipeline: {e}")
    ai_pipeline = None


# Decorator for restricted access
def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        if update.message.chat_id != ALLOWED_CHAT_ID:
            await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
            return
        return await func(update, context, *args, **kwargs)

    return wrapped


# Context manager for database connections
@contextmanager
def get_db_connection():
    conn = sqlite3.connect("bullet_journal.db")
    try:
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
    finally:
        conn.close()


# Initialize database
def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS missions (
                user_id INTEGER,
                mission TEXT,
                completed INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()


# Generate AI response
def generate_ai_response(prompt: str) -> str:
    if not ai_pipeline:
        return "Lo siento, el servicio de IA no está disponible en este momento."

    try:
        response = ai_pipeline(prompt, max_length=50, do_sample=True)
        return response[0]["generated_text"]
    except Exception as e:
        logger.error(f"AI pipeline error: {e}")
        return "Lo siento, no pude generar una respuesta en este momento."


# Add a mission to the database
def add_mission(user_id: int, mission: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO missions (user_id, mission, completed) VALUES (?, ?, ?)",
            (user_id, mission, 0),
        )
        conn.commit()
        logger.info(f"Mission added for user {user_id}: {mission}")


# Add a user to the database
def add_user(user_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, xp) VALUES (?, ?)", (user_id, 0)
        )
        conn.commit()
        logger.info(f"User added or updated: {user_id}")


# Get user's level based on XP
def get_level(xp: int) -> str:
    if xp < 50:
        return "🟢 Novato"
    elif xp < 150:
        return "🔵 Aprendiz"
    elif xp < 300:
        return "🟣 Experto"
    else:
        return "🟠 Maestro"


# Get user's pending missions
def get_missions(user_id: int) -> list[str]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT mission FROM missions WHERE user_id = ? AND completed = 0", (user_id,)
        )
        missions = cursor.fetchall()
        return [m[0] for m in missions]


# Complete a mission and add XP
def complete_mission(user_id: int, mission: str) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM missions WHERE user_id = ? AND mission = ? AND completed = 0",
            (user_id, mission),
        )
        result = cursor.fetchone()

        if not result:
            return False  # Mission not found or already completed

        cursor.execute(
            "UPDATE missions SET completed = 1 WHERE user_id = ? AND mission = ?",
            (user_id, mission),
        )
        cursor.execute("UPDATE users SET xp = xp + 10 WHERE user_id = ?", (user_id,))
        conn.commit()
        logger.info(f"Mission completed by user {user_id}: {mission}")
        return True


# Command handlers
@restricted
async def start(update: Update, context: CallbackContext):
    add_user(update.message.chat_id)
    await update.message.reply_text("¡Bienvenido a tu Bullet Journal Bot! �")


@restricted
async def motivate(update: Update, context: CallbackContext):
    prompt = "Dame un mensaje motivacional para alguien que está completando misiones de productividad."
    ai_response = generate_ai_response(prompt)
    await update.message.reply_text(f"🤖 IA dice: {ai_response}")


@restricted
async def assign_random_mission(update: Update, context: CallbackContext):
    mission = random.choice(MISSIONS)
    add_mission(update.message.chat_id, mission)
    await update.message.reply_text(f"🎯 Nueva misión asignada: {mission}")


@restricted
async def add_mission_command(update: Update, context: CallbackContext):
    mission = " ".join(context.args)
    if not mission:
        await update.message.reply_text("⚠️ Debes escribir una misión. Usa: /agregar_mision <nombre>")
        return

    add_mission(update.message.chat_id, mission)
    await update.message.reply_text(f"✅ Misión agregada: {mission}")


@restricted
async def daily_mission(update: Update, context: CallbackContext):
    mission = random.choice(MISSIONS)
    add_mission(update.message.chat_id, mission)
    await update.message.reply_text(f"Tu misión de hoy: {mission}")


@restricted
async def complete(update: Update, context: CallbackContext):
    mission = " ".join(context.args)
    if not mission:
        await update.message.reply_text("⚠️ Debes escribir el nombre de la misión que completaste. Usa: /completar <nombre>")
        return

    if complete_mission(update.message.chat_id, mission):
        await update.message.reply_text(f"✅ Has completado la misión: {mission}! +10 XP")
    else:
        await update.message.reply_text("⚠️ No encontré esa misión pendiente en tu lista.")


@restricted
async def show_missions(update: Update, context: CallbackContext):
    missions = get_missions(update.message.chat_id)
    if missions:
        await update.message.reply_text("📜 Tus misiones pendientes:\n" + "\n".join(missions))
    else:
        await update.message.reply_text("🎉 ¡No tienes misiones pendientes!")


@restricted
async def profile(update: Update, context: CallbackContext):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT xp FROM users WHERE user_id = ?", (update.message.chat_id,))
        result = cursor.fetchone()

    xp = result[0] if result else 0
    level = get_level(xp)
    await update.message.reply_text(f"🎖 Tu progreso:\n🔹 XP: {xp}\n🏆 Rango: {level}")


# Main function
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("perfil", profile))
    app.add_handler(CommandHandler("agregar_mision", add_mission_command))
    app.add_handler(CommandHandler("mision", assign_random_mission))
    app.add_handler(CommandHandler("completar", complete))
    app.add_handler(CommandHandler("misiones", show_missions))
    app.add_handler(CommandHandler("motivacion", motivate))
    app.run_polling()


if __name__ == "__main__":
    main()