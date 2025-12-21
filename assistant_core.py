import json
import random
from storage import load_progress, save_progress
from logic import *

from logic import today_str, get_yesterday, weekday_name
from storage import load_progress


WORDS_FILE = "words.json"

# =========================
def load_words():
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# =========================
def run_daily_flow(user_reply=None):
    words = load_words()
    p = load_progress()
    today_s = today_str()
    week = week_id()

    # ---------- MENSAJE INICIAL ----------
    day_name = weekday_name()
    if is_saturday() or is_sunday():
        intro = f"📅 {day_name}\n\n🧠 Repaso de toda la semana :D\n\n"
    else:
        intro = f"📅 {day_name}\n\n🎓 Bienvenida a tu examen\n\n"

    # ---------- NUEVO DÍA ----------
    if p["last_day"] != today_s:
        p["last_day"] = today_s

        # Crear examen (NO el primer día)
        if p["daily_history"]:
            p["current_exam"] = create_exam(p)

        # Palabras nuevas
        new_ids = get_new_words(words, p["used_words"])
        p["daily_history"][today_s] = new_ids
        p["used_words"].extend(new_ids)

        # Semana
        p["weekly_history"].setdefault(week, [])
        p["weekly_history"][week].extend(new_ids)

        save_progress(p)

        if "current_exam" in p:
            return intro + format_question(words, p)

        return intro + format_new_words(words, new_ids)

    # ---------- RESPUESTA A EXAMEN ----------
    if "current_exam" in p:
        return handle_exam_reply(words, p, user_reply)

    return "✅ Ya completaste todo por hoy"

# =========================
def create_exam(p):
    if is_sunday():
        exam_type = "written"
        pool = get_week_words(p) + p["failed_words"]
    elif is_saturday():
        exam_type = "mc"
        pool = get_week_words(p) + p["failed_words"]
    else:
        exam_type = "mc"
        pool = p["daily_history"].get(yesterday_str(), []) + p["failed_words"]

    pool = list(dict.fromkeys(pool))  # únicos

    return {
        "type": exam_type,
        "questions": pool,
        "index": 0,
        "score": 0
    }

# =========================
def format_question(words, p):
    exam = p["current_exam"]
    qid = exam["questions"][exam["index"]]

    # ---------- ESCRITO ----------
    if exam["type"] == "written":
        return f"✍️ ¿Cómo se dice '{words[qid]['spanish']}' en inglés?"

    # ---------- OPCIÓN MÚLTIPLE ----------
    # Generar opciones SOLO una vez
    if "options" not in exam:
        options = generate_options(words, qid)
        exam["options"] = options["choices"]
        exam["answer"] = options["correct"]
        save_progress(p)

    msg = f"❓ ¿Cómo se dice '{words[qid]['spanish']}'?\n\n"
    for k, v in exam["options"].items():
        msg += f"{k}) {v}\n"

    msg += "\n(Responde con A, B, C o D)"
    return msg

# =========================
def handle_exam_reply(words, p, reply):
    exam = p["current_exam"]
    qid = exam["questions"][exam["index"]]
    correct_word = words[qid]["english"].lower()

    feedback = ""

    # =========================
    # EXAMEN ESCRITO (DOMINGO)
    # =========================
    if exam["type"] == "written":
        user_answer = reply.strip().lower()

        if user_answer == correct_word:
            exam["score"] += 1
            feedback = "✅ Correcto\n\n"
        else:
            p["failed_words"].append(qid)
            feedback = f"❌ Incorrecto\n✔ Respuesta: {correct_word}\n\n"

    # =========================
    # OPCIÓN MÚLTIPLE (L–S)
    # =========================
    else:
        # Generar opciones NUEVAS por pregunta
        if "options" not in exam or "answer" not in exam:
            options = generate_options(words, qid)
            exam["options"] = options["choices"]
            exam["answer"] = options["correct"]

        user_choice = normalize_mc_reply(reply, exam["options"])

        # Respuesta inválida
        if user_choice is None:
            save_progress(p)
            return (
                "⚠️ Respuesta no válida.\n"
                "Responde con A, B, C o D (o la palabra).\n\n"
                + format_question(words, p)
            )

        if user_choice == exam["answer"]:
            exam["score"] += 1
            feedback = "✅ Correcto\n\n"
        else:
            p["failed_words"].append(qid)
            correct_letter = exam["answer"]
            correct_word = exam["options"][correct_letter]
            feedback = (
                f"❌ Incorrecto\n"
                f"✔ Respuesta: {correct_letter}) {correct_word}\n\n"
            )

    # =========================
    # AVANZAR EXAMEN
    # =========================
    exam["index"] += 1

    # 🔥 LIMPIAR OPCIONES PARA LA SIGUIENTE PREGUNTA
    exam.pop("options", None)
    exam.pop("answer", None)

    # ¿Terminó el examen?
    if exam["index"] >= len(exam["questions"]):
        today = today_str()

        # 🔥 GUARDAR RESULTADO DEL EXAMEN
        p.setdefault("exam_results", {})
        p["exam_results"][today] = exam["score"]

        del p["current_exam"]
        save_progress(p)

        return (
            feedback
            + "📝 Examen terminado\n\n"
            + format_new_words(
                words,
                p["daily_history"][today]
            )
        )


    save_progress(p)
    return feedback + format_question(words, p)


# =========================
def generate_options(words, correct_id):
    correct = words[correct_id]["english"]
    others = random.sample(
        [w["english"] for i, w in enumerate(words) if i != correct_id],
        3
    )
    choices = [correct] + others
    random.shuffle(choices)

    labels = ["A", "B", "C", "D"]
    mapping = dict(zip(labels, choices))

    return {
        "choices": mapping,
        "correct": next(k for k, v in mapping.items() if v == correct)
    }

# =========================
def normalize_mc_reply(reply, options):
    if not reply:
        return None

    r = reply.strip().lower()
    r = r.replace(")", "").replace(".", "")

    # letra
    if r and r[0] in ["a", "b", "c", "d"]:
        return r[0].upper()

    # palabra
    for letter, word in options.items():
        if r == word.lower():
            return letter

    return None

# =========================
def format_new_words(words, ids):
    msg = "📘 Palabras nuevas del día:\n\n"
    for i in ids:
        msg += f"- {words[i]['english']} → {words[i]['spanish']}\n"
    return msg



def generate_admin_report(words=None):
    p = load_progress()
    today = today_str()

    msg = f"📊 Reporte diario — {weekday_name(today)}\n\n"

    # =========================
    # EXAMEN DE HOY
    # =========================
    if today in p.get("exam_results", {}):
        score = p["exam_results"][today]
        total = len(p["daily_history"].get(today, []))
        msg += f"📝 Examen: ✅ ({score}/{total})\n"
    else:
        msg += "📝 Examen: ❌ NO realizado\n"

    # =========================
    # PALABRAS NUEVAS
    # =========================
    today_words = p["daily_history"].get(today, [])
    msg += f"📚 Palabras nuevas: {len(today_words)}\n"

    # =========================
    # ERRORES
    # =========================
    msg += f"❌ Palabras pendientes: {len(set(p.get('failed_words', [])))}\n"

    # =========================
    # RACHA
    # =========================
    streak = 0
    for day in sorted(p.get("exam_results", {}).keys(), reverse=True):
        streak += 1

    msg += f"🔥 Racha actual: {streak} días\n"

    return msg

def exam_completed_today(progress):
    today = today_str()
    return today in progress.get("exam_results", {})

