import os
import sqlite3
from datetime import datetime
from collections import Counter
from pypdf import PdfReader

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "memory", "database.db")
BOOKS_DIR = os.path.join(BASE_DIR, "books")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(BOOKS_DIR, exist_ok=True)

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# 20 bosqichli mukammal IELTS 6.5 - 7.0 Syllabus
MASTER_SYLLABUS = [
    # 1-Bosqich: Foundation & Fluency (A2 -> B1)
    (1, "Present Simple vs Present Continuous", "A2 Elementary", "Daily habits vs temporary actions (IELTS Speaking Part 1 foundation)"),
    (2, "Past Simple (Regular & Irregular)", "A2 Elementary", "Storytelling, past events, childhood memories (Part 1 & Cue Card)"),
    (3, "Past Continuous & Past Simple Interruption", "A2-B1", "Background actions ('I was studying when...') for fluent storytelling"),
    (4, "Present Perfect vs Past Simple", "B1 Intermediate", "Life achievements, experiences, recent trends without exact date"),
    (5, "Present Perfect Continuous", "B1 Intermediate", "Duration of ongoing actions ('I have been living in Tashkent for 2 years')"),
    (6, "Future Forms (Will, Going to, Present Continuous)", "B1 Intermediate", "Predictions, plans, and future arrangements in Speaking Part 1"),
    (7, "Articles (A, An, The & Zero Article)", "B1 Intermediate", "General vs specific noun references (Crucial for Grammar Range)"),
    (8, "Prepositions of Time, Place & Movement", "B1 Intermediate", "Accurate usage of in, at, on, through, towards without mother-tongue errors"),
    
    # 2-Bosqich: Expansion & Elaboration (B1 -> B2)
    (9, "Comparatives, Superlatives & Proportional ('The more... the more')", "B1-B2", "Comparing lifestyles, generations, and cities (Part 3 Goldmine)"),
    (10, "Modal Verbs for Speculation (Might, Could, Must, Can't)", "B2 Upper-Int", "Expressing degrees of certainty when answering abstract questions"),
    (11, "Zero, First & Second Conditionals", "B2 Upper-Int", "Hypothetical ideas ('If I had enough time, I would...')"),
    (12, "Third Conditional & Mixed Conditionals", "B2-C1 IELTS 7.0", "Regrets and past unreal conditions with present consequences"),
    (13, "Passive Voice (Simple & Continuous Forms)", "B2 Upper-Int", "Describing processes, environmental issues, and formal viewpoints"),
    (14, "Defining & Non-Defining Relative Clauses", "B2 Upper-Int", "Complex sentence building using who, which, where, whose"),
    
    # 3-Bosqich: Academic Precision & IELTS 7.0 Band Boosters (B2 -> C1)
    (15, "Gerunds vs Infinitives & Verb Patterns", "B2 Upper-Int", "Natural collocations ('avoid doing', 'manage to do', 'look forward to')"),
    (16, "Reported Speech & Indirect Questions", "B2 Upper-Int", "Polite phrasing and quoting experts or general opinion in Part 3"),
    (17, "Discourse Markers & High-Band Linking Words", "B2-C1 IELTS 7.0", "However, Furthermore, Consequently, In spite of, Whereas"),
    (18, "Cleft Sentences for Emphasis", "C1 Advanced", "'What impresses me most is...', 'It was my teacher who encouraged me...'"),
    (19, "Inversion for Strong Opinion & Variety", "C1 Advanced", "'Not only did it improve my confidence, but it also...', 'Rarely do people...'"),
    (20, "IELTS Speaking Part 3 Formula: Point + Reason + Example + Alternative", "C1 Advanced", "Mastering structured, coherent, 45-second academic responses")
]

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mistakes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incorrect TEXT NOT NULL,
        correction TEXT NOT NULL,
        explanation TEXT,
        topic TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vocabulary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT UNIQUE NOT NULL,
        translation TEXT NOT NULL,
        example TEXT,
        mastered BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS speaking_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fluency REAL,
        lexical REAL,
        grammar REAL,
        overall REAL,
        feedback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_base (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_title TEXT NOT NULL,
        page_num INTEGER,
        content TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS syllabus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_num INTEGER UNIQUE NOT NULL,
        title TEXT NOT NULL,
        level TEXT NOT NULL,
        core_rule TEXT NOT NULL,
        completed BOOLEAN DEFAULT 0
    )
    """)
    conn.commit()

    # Agar syllabus mavzulari 20 tadan kam bo'lsa, to'liq professional ro'yxatga yangilash
    cursor.execute("SELECT COUNT(*) FROM syllabus")
    if cursor.fetchone()[0] < len(MASTER_SYLLABUS):
        cursor.execute("DELETE FROM syllabus")
        cursor.executemany("""
            INSERT INTO syllabus (order_num, title, level, core_rule, completed)
            VALUES (?, ?, ?, ?, 0)
        """, MASTER_SYLLABUS)
        conn.commit()

    conn.close()

init_db()

def get_syllabus():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, order_num, title, level, core_rule, completed FROM syllabus ORDER BY order_num ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_topic_completed(topic_id: int, status: bool = True):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE syllabus SET completed = ? WHERE id = ?", (1 if status else 0, topic_id))
    conn.commit()
    conn.close()

def index_pdf_books():
    conn = get_connection()
    cursor = conn.cursor()
    pdf_files = [f for f in os.listdir(BOOKS_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files:
        conn.close()
        return "books/ papkasida PDF kitob topilmadi. Kitob tashlang!"

    total_chunks = 0
    for file_name in pdf_files:
        file_path = os.path.join(BOOKS_DIR, file_name)
        cursor.execute("SELECT COUNT(*) FROM knowledge_base WHERE book_title = ?", (file_name,))
        if cursor.fetchone()[0] > 0:
            continue
            
        reader = PdfReader(file_path)
        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and len(text.strip()) > 50:
                chunks = [text[i:i+800] for i in range(0, len(text), 700)]
                for chunk in chunks:
                    cursor.execute("""
                        INSERT INTO knowledge_base (book_title, page_num, content)
                        VALUES (?, ?, ?)
                    """, (file_name, page_idx + 1, chunk.strip()))
                    total_chunks += 1
                    
    conn.commit()
    conn.close()
    return f"Kitoblar bazaga kiritildi! Jami yangi bo'laklar: {total_chunks}"

def search_knowledge_base(query: str, limit: int = 3) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    keywords = [w.strip() for w in query.split() if len(w.strip()) > 3]
    if not keywords:
        keywords = [query]
    where_clauses = " OR ".join(["content LIKE ?" for _ in keywords[:3]])
    params = [f"%{k}%" for k in keywords[:3]]
    sql = f"SELECT book_title, page_num, content FROM knowledge_base WHERE {where_clauses} LIMIT {limit}"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "Kitoblar bazasidan ushbu mavzu bo'yicha ma'lumot topilmadi."
    results = [f"[{r['book_title']} - Sahifa {r['page_num']}]:\n{r['content']}" for r in rows]
    return "\n\n---\n\n".join(results)

def save_mistake(incorrect: str, correction: str, explanation: str, topic: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mistakes (incorrect, correction, explanation, topic)
        VALUES (?, ?, ?, ?)
    """, (incorrect, correction, explanation, topic))
    conn.commit()
    conn.close()
    return "Xato saqlandi."

def add_word(word: str, translation: str, example: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO vocabulary (word, translation, example, mastered)
            VALUES (?, ?, ?, 0)
        """, (word.strip(), translation.strip(), example.strip()))
        conn.commit()
        return "So'z qo'shildi."
    except sqlite3.IntegrityError:
        return "Bu so'z mavjud."
    finally:
        conn.close()

def update_word_status(word: str, mastered: bool):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE vocabulary SET mastered = ? WHERE LOWER(word) = LOWER(?)", (1 if mastered else 0, word))
    conn.commit()
    conn.close()

def save_speaking_evaluation(fluency: float, lexical: float, grammar: float, overall: float, feedback: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO speaking_scores (fluency, lexical, grammar, overall, feedback)
        VALUES (?, ?, ?, ?, ?)
    """, (fluency, lexical, grammar, overall, feedback))
    conn.commit()
    conn.close()
    return f"Speaking bahosi saqlandi! Overall: {overall}"

def load_chat_history(limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat_history ORDER BY id ASC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in rows]

def save_chat_history(messages):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history")
    for msg in messages:
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "assistant")
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        if role and content:
            cursor.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def clear_chat_history():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()

def get_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM mistakes")
    total_mistakes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM vocabulary")
    total_words = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(overall) FROM speaking_scores")
    avg_score_row = cursor.fetchone()[0]
    avg_score = round(avg_score_row, 1) if avg_score_row else 0.0
    cursor.execute("SELECT word, translation, example, mastered FROM vocabulary ORDER BY id DESC")
    vocabulary = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT incorrect, correction, topic FROM mistakes ORDER BY id DESC LIMIT 5")
    recent_mistakes = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT COUNT(DISTINCT book_title) FROM knowledge_base")
    total_books = cursor.fetchone()[0]
    conn.close()
    
    return {
        "total_mistakes": total_mistakes,
        "total_words": total_words,
        "average_score": avg_score,
        "vocabulary": vocabulary,
        "recent_mistakes": recent_mistakes,
        "total_books": total_books
    }

def get_weak_topics(limit: int = 3):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT topic FROM mistakes WHERE topic IS NOT NULL AND topic != ''")
    topics = [row[0] for row in cursor.fetchall()]
    conn.close()
    if not topics:
        return []
    return Counter(topics).most_common(limit)