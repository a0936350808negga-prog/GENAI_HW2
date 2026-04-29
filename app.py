import streamlit as st
import sqlite3
import google.generativeai as genai
from PIL import Image
import uuid
from datetime import datetime

# ----------------- 0. API 金鑰設定 -----------------
GOOGLE_API_KEY = "AIzaSyA_9-I-uB_164tphzMM51xnF0MwU_205ps"
genai.configure(api_key=GOOGLE_API_KEY)

# ----------------- 1. 工具定義區 (Tool Use) -----------------
def calculate_protein_needs(weight_kg: float, phase: str) -> str:
    """計算每日建議蛋白質攝取量。phase: 'bulking', 'cutting', or 'maintenance'."""
    if phase == 'cutting':
        protein = weight_kg * 2.5
    elif phase == 'bulking':
        protein = weight_kg * 1.8
    else:
        protein = weight_kg * 2.0
    return f"根據外部系統精確計算，體重 {weight_kg}kg 在 {phase} 階段的建議蛋白質攝取量為 {protein} 克。"

# ----------------- 2. AI 大腦設定與路由區 -----------------
model_flash = genai.GenerativeModel('gemini-2.5-flash', tools=[calculate_protein_needs])
model_pro = genai.GenerativeModel('gemini-2.5-flash', tools=[calculate_protein_needs]) 

def auto_route_model(prompt, has_image=False):
    if has_image:
        return model_flash, "Gemini-2.5-Flash (視覺處理)"
    complex_keywords = ["計算", "蛋白質", "備賽", "證明", "奧林匹亞"]
    if any(keyword in prompt for keyword in complex_keywords) or len(prompt) > 200:
        return model_pro, "Gemini-2.5-Pro (深度推論與工具使用)"
    return model_flash, "Gemini-2.5-Flash (快速回應)"

# ----------------- 3. 多重聊天室資料庫區 (大升級) -----------------
DB_FILE = "long_term_memory.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 建立「聊天室列表」的資料表
    c.execute('''CREATE TABLE IF NOT EXISTS chat_sessions 
                 (session_id TEXT PRIMARY KEY, title TEXT, created_at TIMESTAMP)''')
    # 建立「對話內容」的資料表 (加上 session_id 作為關聯)
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT)''')
    conn.commit()
    conn.close()

def get_all_sessions():
    """取得所有聊天室列表"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT session_id, title FROM chat_sessions ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1]} for r in rows]

def create_new_session():
    """建立一個全新的聊天室"""
    session_id = str(uuid.uuid4())
    title = f"新聊天室 ({datetime.now().strftime('%H:%M')})"
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO chat_sessions (session_id, title, created_at) VALUES (?, ?, ?)", 
              (session_id, title, datetime.now()))
    conn.commit()
    conn.close()
    return session_id

def rename_session(session_id, new_title):
    """(選擇性) 根據使用者的第一句話自動重新命名聊天室"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE chat_sessions SET title = ? WHERE session_id = ?", (new_title[:15], session_id))
    conn.commit()
    conn.close()

def save_message(session_id, role, content):
    """儲存特定聊天室的訊息"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)", 
              (session_id, role, content))
    conn.commit()
    conn.close()

def load_history(session_id):
    """讀取特定聊天室的歷史對話"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY id ASC", (session_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

# ----------------- 4. 前端網頁介面 (側邊欄與對話管理) -----------------
st.set_page_config(page_title="AI Agent V4", page_icon="🚀")
st.title("🚀 全能 AI Agent 助理 (多開聊天室版)")

init_db()

# --- 聊天室狀態管理邏輯 ---
if "current_session_id" not in st.session_state:
    sessions = get_all_sessions()
    if not sessions:
        # 如果是第一次用，自動開一個新房間
        st.session_state.current_session_id = create_new_session()
    else:
        # 否則載入最新的一個房間
        st.session_state.current_session_id = sessions[0]["id"]
    # 載入該房間的對話
    st.session_state.messages = load_history(st.session_state.current_session_id)

with st.sidebar:
    st.header("💬 聊天室管理")
    
    # 新增聊天室按鈕
    if st.button("➕ 新增聊天室", use_container_width=True):
        new_id = create_new_session()
        st.session_state.current_session_id = new_id
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("---")
    
    # 顯示歷史聊天紀錄列表 (使用 Radio Button 模擬選單)
    sessions = get_all_sessions()
    if sessions:
        session_options = {s["title"]: s["id"] for s in sessions}
        # 找出目前選中的標題
        current_title = next((title for title, sid in session_options.items() if sid == st.session_state.current_session_id), list(session_options.keys())[0])
        
        selected_title = st.radio("歷史紀錄", list(session_options.keys()), index=list(session_options.keys()).index(current_title))
        
        # 如果使用者切換了聊天室，更新 ID 並重新讀取對話
        if session_options[selected_title] != st.session_state.current_session_id:
            st.session_state.current_session_id = session_options[selected_title]
            st.session_state.messages = load_history(st.session_state.current_session_id)
            st.rerun()

    st.markdown("---")
    st.subheader("🖼️ 多模態視覺輸入")
    uploaded_file = st.file_uploader("上傳圖片", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="已準備好圖片", use_container_width=True)

# --- 主聊天視窗 ---
# 確保每次切換都能載入正確的歷史對話
if "messages" not in st.session_state or len(st.session_state.messages) == 0:
    st.session_state.messages = load_history(st.session_state.current_session_id)
    if not st.session_state.messages:
        opening_msg = "歡迎來到新聊天室！我們今天聊點什麼？"
        save_message(st.session_state.current_session_id, "assistant", opening_msg)
        st.session_state.messages.append({"role": "assistant", "content": opening_msg})

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("請輸入訊息..."):
    # 如果是這個聊天室的第一句話，用它來幫聊天室重新命名
    if len(st.session_state.messages) <= 1:
        rename_session(st.session_state.current_session_id, prompt)
        
    with st.chat_message("user"):
        st.markdown(prompt)
    save_message(st.session_state.current_session_id, "user", prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    has_img = uploaded_file is not None
    active_model, model_name = auto_route_model(prompt, has_img)
    
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown(f"*(啟動中... 模型：{model_name})*")
        
        try:
            # 準備歷史記憶格式
            gemini_history = []
            for m in st.session_state.messages[:-1]: # 不包含剛輸入的 prompt
                api_role = "model" if m["role"] == "assistant" else "user"
                gemini_history.append({"role": api_role, "parts": [m["content"]]})

            chat = active_model.start_chat(
                history=gemini_history,
                enable_automatic_function_calling=True
            )
            
            contents = [prompt]
            if has_img:
                img = Image.open(uploaded_file)
                contents.append(img)
            
            response = chat.send_message(contents)
            full_response = response.text
            
            message_placeholder.markdown(full_response)
            save_message(st.session_state.current_session_id, "assistant", full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # 確保重新命名聊天室後，側邊欄能立刻更新顯示
            if len(st.session_state.messages) == 3:
                st.rerun()
                
        except Exception as e:
            message_placeholder.markdown(f"發生錯誤：{e}")