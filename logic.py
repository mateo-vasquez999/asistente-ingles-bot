import datetime
import random

# =========================
# MODO TEST
# =========================
TEST_MODE = False            # Cambia a False en producción        True
FAKE_TODAY = datetime.date(2025, 12, 17)

def _today():
    return FAKE_TODAY if TEST_MODE else datetime.date.today()

def today():
    return _today()

def today_str():
    return _today().isoformat()

def yesterday_str():
    return (_today() - datetime.timedelta(days=1)).isoformat()

def get_yesterday():
    return yesterday_str()

def week_id():
    d = _today()
    return f"{d.year}-W{d.isocalendar().week}"

def weekday_name(date_str=None):
    """
    Si no se pasa fecha, usa hoy.
    date_str: 'YYYY-MM-DD'
    """
    if date_str is None:
        d = _today()
    else:
        d = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    return d.strftime("%A")


def is_saturday():
    return _today().weekday() == 5

def is_sunday():
    return _today().weekday() == 6

def get_new_words(words, used, n=3):
    available = [i for i in range(len(words)) if i not in used]
    return random.sample(available, min(n, len(available)))

def get_week_words(progress):
    words = []
    for _, wids in progress.get("daily_history", {}).items():
        words.extend(wids)
    return list(set(words))
