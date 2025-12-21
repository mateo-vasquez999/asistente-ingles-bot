import json
import os

FILE = "progress.json"

def load_progress():
    if not os.path.exists(FILE):
        return {
            "last_day": None,
            "daily_history": {},      # fecha -> [word_ids]
            "weekly_history": {},     # semana -> [word_ids]
            "used_words": [],
            "failed_words": [],
            "exam_results": {}
        }
    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_progress(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
