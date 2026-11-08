import os
import json
import time
from io import BytesIO
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder
from tools.db_tools import (
    save_mistake, add_word, get_stats,
    save_speaking_evaluation, load_chat_history, 
    save_chat_history, clear_chat_history, update_word_status,
    get_weak_topics, index_pdf_books, search_knowledge_base,
    get_syllabus, mark_topic_completed
)

load_dotenv()

st.set_page_config(
    page_title="Teacher Azam",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #131314; color: #E3E3E3; }
    [data-testid="stSidebar"] { background-color: #1E1F20; border-right: 1px solid #2D2F31; }
    .stButton>button {
        border-radius: 20px;
        border: 1px solid #3C4043;
        background-color: #282A2C;
        color: #E3E3E3;
        transition: all 0.2s ease;
    }
    .stButton>button:hover { background-color: #37393B; border-color: #8AB4F8; color: #FFFFFF; }
    div[data-testid="stMetricValue"] { font-size: 1.3rem !important; color: #8AB4F8 !important; }
    .flashcard {
        background: #1E1F20;
        border: 1px solid #3C4043;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

tool_map = {
    "save_mistake": save_mistake,
    "add_word": add_word,
    "save_speaking_evaluation": save_speaking_evaluation,
    "search_knowledge_base": search_knowledge_base
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "save_mistake",
            "description": "Foydalanuvchining xatosini, to'g'ri shakli va tushuntirishini saqlash.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incorrect": {"type": "string", "description": "Xato jumla."},
                    "correction": {"type": "string", "description": "To'g'ri shakli."},
                    "explanation": {"type": "string", "description": "Tushuntirish."},
                    "topic": {"type": "string", "description": "Mavzu nomi."}
                },
                "required": ["incorrect", "correction", "explanation", "topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_word",
            "description": "Lug'atga yangi so'z qo'shish.",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "So'z."},
                    "translation": {"type": "string", "description": "Tarjimasi."},
                    "example": {"type": "string", "description": "Misol."}
                },
                "required": ["word", "translation", "example"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Grammatika yoki IELTS kitoblari bazasidan aniq qoida va misollarni qidirish.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Qidirilayotgan grammatik mavzu."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_speaking_evaluation",
            "description": "IELTS Speaking baholash natijalarini saqlash.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fluency": {"type": "number", "description": "Fluency bali."},
                    "lexical": {"type": "number", "description": "Lexical bali."},
                    "grammar": {"type": "number", "description": "Grammar bali."},
                    "overall": {"type": "number", "description": "Overall Band."},
                    "feedback": {"type": "string", "description": "Xulosa."}
                },
                "required": ["fluency", "lexical", "grammar", "overall", "feedback"]
            }
        }
    }
]

system_instruction = """
You are Teacher Azam, an elite, highly detailed English Professor and IELTS Examiner teaching an Uzbek native speaker aiming for IELTS 6.5–7.0.

SIZNING USLUBINGIZ VA ASOSIY QOIDALARINGIZ:
1. QISQA YOZISH TAQIQLANADI. Mavzuni har bir mayda ikir-chikiri, nuqtalari, istisnolari va kontekstlari bilan to'liq tushuntiring.
2. HAR BIR DARSNI QUYIDAGI STANDART TUZILISH BO'YICHA TUSHUNTIRING:
   - 📌 1. Mavzuning Tub Ma'nosi va O'zbek tiliga qiyosi
   - 📐 2. Aniq Formulalar va Qoliplar (+, -, ?)
   - 💡 3. Barcha Ishlatilish Vaziyatlari (Cases) va namunalar
   - ⏳ 4. Signal So'zlar (Time Markers)
   - ⚠️ 5. Eng Ko'p Qilinadigan Xatolar (Common Traps)
   - 🎯 6. IELTS 6.5 - 7.0 Imtihonida qo'llash sirlari
   - ✍️ 7. Amaliy Topshiriq (Practice)
3. Foydalanuvchiga HECH QACHON JSON, kod bloki yoki texnik ma'lumotlarni matn sifatida ko'rsatmang.
4. Tushuntirish tili: Aniq, tushunarli o'zbek tilida, inglizcha atamalar bilan birga.
"""

def generate_voice(text: str):
    try:
        clean_text = text.replace("*", "").replace("#", "").split("To'g'ri javob")[0]
        tts = gTTS(text=clean_text[:350], lang="en", tld="co.uk")
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception:
        return None

def transcribe_audio(audio_bytes):
    try:
        audio_file = ("user_speech.wav", audio_bytes, "audio/wav")
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            language="en"
        )
        return transcription.text
    except Exception as e:
        st.error(f"Ovozni aniqlashda xatolik: {e}")
        return None

def get_clean_messages(history):
    cleaned = []
    for m in history:
        role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
        content = m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
        if role in ["system", "user", "assistant"] and isinstance(content, str) and content.strip():
            cleaned.append({"role": role, "content": content})
    return cleaned

def text_stream_generator(text: str):
    """Matnni so'zma-so'z oqizib chiqarish uchun xatosiz generator"""
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.015)

if "chat_history" not in st.session_state:
    saved = load_chat_history()
    cleaned_saved = get_clean_messages(saved)
    if cleaned_saved:
        st.session_state.chat_history = cleaned_saved
    else:
        st.session_state.chat_history = [
            {"role": "system", "content": system_instruction},
            {"role": "assistant", "content": "Salom! Men Teacher Azam — sizning shaxsiy IELTS ustozingizman. Qaysi mavzuni chuqur va to'liq o'rganamiz?"}
        ]

if "card_idx" not in st.session_state:
    st.session_state.card_idx = 0
if "show_card_answer" not in st.session_state:
    st.session_state.show_card_answer = False

# --- CHAP YON PANEL ---
with st.sidebar:
    st.markdown("### ✨ Teacher Azam")
    
    if st.button("➕ Yangi suhbat", use_container_width=True):
        clear_chat_history()
        st.session_state.chat_history = [
            {"role": "system", "content": system_instruction},
            {"role": "assistant", "content": "Yangi mashg'ulot boshlandi! Rejadan mavzu tanlang yoki savol bering."}
        ]
        save_chat_history(st.session_state.chat_history)
        st.rerun()

    st.divider()
    stats = get_stats()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Xatolar", stats["total_mistakes"])
        st.metric("Lug'at", stats["total_words"])
    with col2:
        st.metric("Kitoblar", f"{stats['total_books']} ta")
        st.metric("IELTS Band", f"{stats['average_score']}" if stats['average_score'] > 0 else "—")

    st.divider()
    st.markdown("**🎙️ Ovozli xabar**")
    audio_record = mic_recorder(
        start_prompt="🎙️ Gapirishni boshlash",
        stop_prompt="⏹️ To'xtatish va yuborish",
        key="sidebar_mic",
        use_container_width=True
    )

    # --- O'QUV DASTURI (SYLLABUS) ---
    st.divider()
    st.markdown("**🗺️ IELTS O'quv Rejasi (Syllabus)**")
    syllabus_topics = get_syllabus()
    completed_count = sum(1 for t in syllabus_topics if t["completed"])
    progress_val = completed_count / len(syllabus_topics) if syllabus_topics else 0.0
    st.progress(progress_val, text=f"Progress: {completed_count}/{len(syllabus_topics)} mavzu")

    with st.expander("📚 Mavzular ro'yxati (20 ta)", expanded=False):
        for top in syllabus_topics:
            icon = "✅" if top["completed"] else "⚪"
            st.markdown(f"**{top['order_num']}. {top['title']}** {icon}")
            st.caption(f"Daraja: `{top['level']}` | {top['core_rule']}")
            
            c_btn1, c_btn2 = st.columns([2, 1])
            with c_btn1:
                if st.button(f"📖 To'liq o'rganish", key=f"learn_{top['id']}", use_container_width=True):
                    prompt_learn = (
                        f"Teacher Azam, iltimos menga Syllabus bo'yicha '{top['title']}' ({top['level']}) mavzusini "
                        f"barcha ikir-chikiri, formulalari, hayotiy misollari, o'zbek tiliga qiyosi, keng tarqalgan xatolari va "
                        f"IELTS 6.5–7.0 imtihonida qo'llash sirlari bilan TO'LIQ va BATAFSIL tushuntirib bering. "
                        f"Oxirida mustahkamlash uchun 2 ta topshiriq bering."
                    )
                    st.session_state.chat_history.append({"role": "user", "content": f"'{top['title']}' mavzusini ikir-chikirigacha to'liq tushuntirib bering."})
                    with st.spinner("Keng qamrovli dars tayyorlanmoqda..."):
                        msgs = get_clean_messages(st.session_state.chat_history)
                        msgs.append({"role": "user", "content": prompt_learn})
                        res = client.chat.completions.create(model="openai/gpt-oss-120b", messages=msgs)
                        reply = res.choices[0].message.content
                        st.session_state.chat_history.append({"role": "assistant", "content": reply})
                        save_chat_history(get_clean_messages(st.session_state.chat_history))
                        st.rerun()
            with c_btn2:
                if not top["completed"]:
                    if st.button("Tugatdim", key=f"done_{top['id']}", use_container_width=True):
                        mark_topic_completed(top['id'], True)
                        st.rerun()
                else:
                    if st.button("Qaytarish", key=f"undone_{top['id']}", use_container_width=True):
                        mark_topic_completed(top['id'], False)
                        st.rerun()
            st.markdown("---")

    st.markdown("**📚 Kitoblar bazasi (RAG)**")
    if st.button("🔄 Kitoblarni bazaga yuklash", use_container_width=True):
        with st.spinner("Kitoblar bazaga kiritilmoqda..."):
            msg = index_pdf_books()
            st.success(msg)
            st.rerun()

    weak_topics = get_weak_topics(limit=3)
    if weak_topics:
        st.divider()
        st.markdown("**🔍 Eng zaif mavzularingiz**")
        for topic, count in weak_topics:
            st.caption(f"📌 **{topic}** — {count} ta xato")

# --- MARKAZIY CHAT ---
for idx, msg in enumerate(st.session_state.chat_history):
    role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
    content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
    
    if role == "user" and content:
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(content)
    elif role == "assistant" and content:
        with st.chat_message("assistant", avatar="✨"):
            st.markdown(content)
            if idx == len(st.session_state.chat_history) - 1:
                audio_fp = generate_voice(content)
                if audio_fp:
                    st.audio(audio_fp, format="audio/mp3")

# --- PASTKI KIRITISH MAYDONI ---
final_user_input = None

if audio_record and "bytes" in audio_record and len(audio_record["bytes"]) > 0:
    with st.spinner("Ovozingiz tinglanmoqda..."):
        transcribed = transcribe_audio(audio_record["bytes"])
        if transcribed and len(transcribed.strip()) > 0:
            final_user_input = transcribed

user_typed_input = st.chat_input("Teacher Azam bilan gaplashing...")
if user_typed_input:
    final_user_input = user_typed_input

if final_user_input:
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(final_user_input)
    st.session_state.chat_history.append({"role": "user", "content": final_user_input})

    with st.chat_message("assistant", avatar="✨"):
        clean_history = get_clean_messages(st.session_state.chat_history)
        
        # 1-bosqich: Funksiyalarni bajarish
        init_res = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=clean_history,
            tools=tools,
            tool_choice="auto"
        )
        res_msg = init_res.choices[0].message

        # Agar model funksiya chaqirsa
        if res_msg.tool_calls:
            temp_history = list(clean_history)
            temp_history.append(res_msg)
            for tool_call in res_msg.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                func_to_call = tool_map.get(func_name)
                
                if func_to_call:
                    try:
                        func_result = func_to_call(**func_args)
                    except TypeError:
                        if func_name == "save_mistake":
                            func_result = func_to_call(
                                incorrect=func_args.get("incorrect") or func_args.get("mistake", ""),
                                correction=func_args.get("correction", ""),
                                explanation=func_args.get("explanation") or func_args.get("rule", ""),
                                topic=func_args.get("topic", "General Grammar")
                            )
                        elif func_name == "add_word":
                            func_result = func_to_call(
                                word=func_args.get("word", ""),
                                translation=func_args.get("translation") or func_args.get("uzbek_translation", ""),
                                example=func_args.get("example", "")
                            )
                        elif func_name == "search_knowledge_base":
                            func_result = func_to_call(query=func_args.get("query", ""))
                        else:
                            func_result = {"error": "Mos kelmadi"}
                else:
                    func_result = {"error": "Funksiya topilmadi"}

                temp_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": json.dumps(func_result) if isinstance(func_result, dict) else str(func_result)
                })

            # Yakuniy javobni olish (tools parametri bilan birga uzatiladi, shunda xatolik bermaydi)
            final_res = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=temp_history,
                tools=tools,
                tool_choice="auto"
            )
            raw_reply = final_res.choices[0].message.content or "Tushundim!"
            full_reply = st.write_stream(text_stream_generator(raw_reply))
            st.session_state.chat_history.append({"role": "assistant", "content": full_reply})
            save_chat_history(get_clean_messages(st.session_state.chat_history))
            st.rerun()

        else:
            # Agar oddiy javob bo'lsa, olingan javobni to'g'ridan-to'g'ri chiroyli oqizish
            raw_reply = res_msg.content or "Javob tayyorlanmadi."
            full_reply = st.write_stream(text_stream_generator(raw_reply))
            st.session_state.chat_history.append({"role": "assistant", "content": full_reply})
            save_chat_history(get_clean_messages(st.session_state.chat_history))
            st.rerun()