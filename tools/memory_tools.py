import os
import json
from datetime import datetime
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_FILE = os.path.join(BASE_DIR, "memory", "memory.json")
CHAT_FILE = os.path.join(BASE_DIR, "memory", "chat_history.json")

def load_memory():
    if not os.path.exists(MEMORY_FILE) or os.path.getsize(MEMORY_FILE) == 0:
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        default_data = {
            "level": "Beginner",
            "mistakes": [],
            "vocabulary": [],
            "speaking_scores": [],
            "weak_areas": [],
            "statistics": {
                "total_lessons": 0,
                "total_tests": 0,
                "average_score": 0.0
            }
        }
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
        return default_data
    
    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
        if "speaking_scores" not in data:
            data["speaking_scores"] = []
        if "vocabulary" not in data:
            data["vocabulary"] = []
        if "mistakes" not in data:
            data["mistakes"] = []
        return data

def save_memory(data):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def load_chat_history():
    if not os.path.exists(CHAT_FILE) or os.path.getsize(CHAT_FILE) == 0:
        return []
    try:
        with open(CHAT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_chat_history(messages):
    os.makedirs(os.path.dirname(CHAT_FILE), exist_ok=True)
    serializable_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            serializable_messages.append(msg)
        else:
            serializable_messages.append({
                "role": getattr(msg, "role", "assistant"),
                "content": getattr(msg, "content", "")
            })
    with open(CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable_messages, f, indent=2, ensure_ascii=False)

def clear_chat_history():
    if os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

def save_mistake(incorrect: str, correction: str, explanation: str, topic: str) -> str:
    data = load_memory()
    data["mistakes"].append({
        "incorrect": incorrect,
        "correction": correction,
        "explanation": explanation,
        "topic": topic
    })
    if "statistics" in data:
        data["statistics"]["total_lessons"] = len(data["mistakes"])
    save_memory(data)
    return "Xato muvaffaqiyatli saqlandi."

def get_weak_topics(limit: int = 3):
    """Eng ko'p xato qilingan mavzularni hisoblash"""
    data = load_memory()
    mistakes = data.get("mistakes", [])
    if not mistakes:
        return []
    topics = [m.get("topic", "General Grammar") for m in mistakes if m.get("topic")]
    counts = Counter(topics)
    return counts.most_common(limit)

def add_word(word: str, translation: str, example: str) -> str:
    data = load_memory()
    exists = any(w.get("word", "").lower() == word.lower() for w in data["vocabulary"])
    if not exists:
        data["vocabulary"].append({
            "word": word,
            "translation": translation,
            "example": example,
            "mastered": False
        })
        save_memory(data)
        return "So'z lug'atga qo'shildi."
    return "Bu so'z allaqachon mavjud."

def update_word_status(word: str, mastered: bool):
    data = load_memory()
    for w in data.get("vocabulary", []):
        if w.get("word", "").lower() == word.lower():
            w["mastered"] = mastered
            break
    save_memory(data)

def save_speaking_evaluation(fluency: float, lexical: float, grammar: float, overall: float, feedback: str) -> str:
    data = load_memory()
    score_entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fluency": fluency,
        "lexical": lexical,
        "grammar": grammar,
        "overall": overall,
        "feedback": feedback
    }
    data["speaking_scores"].append(score_entry)
    
    all_scores = [s.get("overall", 0.0) for s in data["speaking_scores"] if s.get("overall")]
    if all_scores:
        data["statistics"]["average_score"] = round(sum(all_scores) / len(all_scores), 1)
        
    save_memory(data)
    return f"Speaking bahosi saqlandi! Overall Band: {overall}"

def get_progress() -> dict:
    data = load_memory()
    return {
        "total_mistakes": len(data.get("mistakes", [])),
        "total_words": len(data.get("vocabulary", [])),
        "speaking_attempts": len(data.get("speaking_scores", [])),
        "average_speaking_band": data.get("statistics", {}).get("average_score", 0.0),
        "level": data.get("level", "Beginner")
    }