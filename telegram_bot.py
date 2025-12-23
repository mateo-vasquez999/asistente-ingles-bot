from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from datetime import time
import pytz

from assistant_core import run_daily_flow
from storage import load_progress

from assistant_core import run_daily_flow, generate_admin_report, exam_completed_today
from logic import today_str

import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_TELEGRAM_ID"))
STUDENT_TELEGRAM_ID = int(os.environ.get("STUDENT_TELEGRAM_ID"))


# =========================
# ZONA HORARIA
# =========================
LOCAL_TZ = pytz.timezone("America/Bogota")


async def admin_daily_report(context: ContextTypes.DEFAULT_TYPE):
    report = generate_admin_report(None)
    await context.bot.send_message(
        chat_id=ADMIN_TELEGRAM_ID,
        text=report
    )


async def remind_exam(context):
    p = load_progress()

    if exam_completed_today(p):
        return  # ya terminó, no molestar

    msg = run_daily_flow(None)

    await context.bot.send_message(
        chat_id=STUDENT_TELEGRAM_ID,
        text="⏰ Recordatorio\nAún no has terminado tu examen de hoy 📚"
    )

    await context.bot.send_message(
        chat_id=STUDENT_TELEGRAM_ID,
        text=msg
    )

async def admin_alert_no_exam(context):
    p = load_progress()

    if exam_completed_today(p):
        return

    await context.bot.send_message(
        chat_id=ADMIN_TELEGRAM_ID,
        text=(
            "🚨 ALERTA\n\n"
            "❌ Hoy NO se completó el examen\n"
            "⚠️ Se enviaron recordatorios sin respuesta"
        )
    )



# =========================
# TECLADO OPCIÓN MÚLTIPLE
# =========================
def mc_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("A", callback_data="A"),
            InlineKeyboardButton("B", callback_data="B"),
        ],
        [
            InlineKeyboardButton("C", callback_data="C"),
            InlineKeyboardButton("D", callback_data="D"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# =========================
# HANDLERS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id == STUDENT_TELEGRAM_ID:
        msg = run_daily_flow("")
        if "(Responde con A, B, C o D)" in msg:
            await update.message.reply_text(msg, reply_markup=mc_keyboard())
        else:
            await update.message.reply_text(msg)

    elif chat_id == ADMIN_TELEGRAM_ID:
        await update.message.reply_text(
            "👋 Admin conectado\n\n"
            "Comandos disponibles:\n"
            "/status\n"
            "/errores"
        )

    else:
        await update.message.reply_text("❌ Usuario no autorizado")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    # -------------------------
    # STUDENT
    # -------------------------
    if chat_id == STUDENT_TELEGRAM_ID:
        reply = run_daily_flow(text)

        if "(Responde con A, B, C o D)" in reply:
            await update.message.reply_text(
                reply,
                reply_markup=mc_keyboard()
            )
        else:
            await update.message.reply_text(reply)

    # -------------------------
    # ADMIN
    # -------------------------
    elif chat_id == ADMIN_TELEGRAM_ID:
        await update.message.reply_text("Usa /status o /errores")

    else:
        await update.message.reply_text("❌ Usuario no autorizado")


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data  # "A", "B", "C" o "D"
    reply = run_daily_flow(choice)

    if "(Responde con A, B, C o D)" in reply:
        await query.message.reply_text(
            reply,
            reply_markup=mc_keyboard()
        )
    else:
        await query.message.reply_text(reply)

# =========================
# ADMIN COMMANDS
# =========================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = load_progress()
    last_day = max(p["daily_history"]) if p["daily_history"] else "—"

    await update.message.reply_text(
        "📊 Estado general\n\n"
        f"📅 Último día estudiado: {last_day}\n"
        f"📝 Exámenes realizados: {len(p['exam_results'])}\n"
        f"❌ Palabras pendientes: {len(p['failed_words'])}"
    )


async def errores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = load_progress()

    if not p["failed_words"]:
        await update.message.reply_text("🎉 No hay palabras falladas")
        return

    msg = "❌ Palabras falladas:\n"
    msg += "\n".join(f"- {wid}" for wid in p["failed_words"])
    await update.message.reply_text(msg)

# =========================
# MENSAJE AUTOMÁTICO DIARIO
# =========================

async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    msg = run_daily_flow("")

    if "(Responde con A, B, C o D)" in msg:
        await context.bot.send_message(
            chat_id=STUDENT_TELEGRAM_ID,
            text=msg,
            reply_markup=mc_keyboard()
        )
    else:
        await context.bot.send_message(
            chat_id=STUDENT_TELEGRAM_ID,
            text=msg
        )

# =========================
# MAIN
# =========================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # =========================
    # COMANDOS
    # =========================
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("errores", errores))

    # =========================
    # BOTONES (A–D)
    # =========================
    app.add_handler(CallbackQueryHandler(handle_button))

    # =========================
    # MENSAJES TEXTO
    # =========================
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # =========================
    # ⏰ SCHEDULER DIARIO
    # =========================

    # 📚 Examen inicial — 1:00 PM
    app.job_queue.run_daily(
        daily_job,
        time=time(hour=16, minute=57, tzinfo=LOCAL_TZ),
        days=(0, 1, 2, 3, 4, 5, 6)
    )

    # ⏰ Recordatorio 1 — 4:00 PM
    app.job_queue.run_daily(
        remind_exam,
        time=time(hour=16, minute=19, tzinfo=LOCAL_TZ),
        days=(0, 1, 2, 3, 4, 5, 6)
    )

    # ⏰ Recordatorio 2 — 7:00 PM
    app.job_queue.run_daily(
        remind_exam,
        time=time(hour=19, minute=20, tzinfo=LOCAL_TZ),
        days=(0, 1, 2, 3, 4, 5, 6)
    )

    # 🚨 ALERTA PARA TI — 10:00 PM
    app.job_queue.run_daily(
        admin_alert_no_exam,
        time=time(hour=20, minute=21, tzinfo=LOCAL_TZ),
        days=(0, 1, 2, 3, 4, 5, 6)
    )

    # 📊 REPORTE DIARIO — 10:10 PM
    app.job_queue.run_daily(
        admin_daily_report,
        time=time(hour=20, minute=42, tzinfo=LOCAL_TZ),
        days=(0, 1, 2, 3, 4, 5, 6)
    )

    print("🤖 Bot de Telegram corriendo...")
    app.run_polling()


if __name__ == "__main__":
    main()
