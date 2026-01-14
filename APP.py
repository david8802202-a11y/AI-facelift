import streamlit as st
import google.generativeai as genai
import os

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 V15", page_icon="🧹")

# --- 2. 讀取 API Key ---
api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🧹 PTT/Dcard 文案產生器 V15 (智慧讀檔版)")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Streamlit 的 Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. 初始化 Session State ---
if 'used_titles' not in st.session_state:
    st.session_state.used_titles = set()

if 'candidate_titles' not in st.session_state:
    st.session_state.candidate_titles = []

# --- 4. 智慧讀取歷史標題 (關鍵更新：只抓標題，過濾雜訊) ---
blacklist_titles = set()

def smart_parse_lines(lines):
    """
    智慧解析函數：只保留以 '[' 開頭的 PTT 標題，
    過濾掉作者、日期、推文數等雜訊。
    """
    valid_titles = set()
    for line in lines:
        clean_line = line.strip()
        # 判斷邏輯：必須有內容，且以 '[' 開頭 (PTT標題特徵)
        if clean_line and clean_line.startswith("["):
            valid_titles.add(clean_line)
    return valid_titles

# 嘗試讀取 GitHub 的 history.txt
if os.path.exists("history.txt"):
    try:
        with open("history.txt", "r", encoding="utf-8") as f:
            file_lines = f.readlines()
            parsed_titles = smart_parse_lines(file_lines)
            blacklist_titles.update(parsed_titles)
        history_status = f"✅ 已載入 history.txt：成功擷取 {len(parsed_titles)} 筆標題 (已過濾雜訊)"
    except Exception as e:
        history_status = f"⚠️ 讀取 history.txt 失敗：{e}"
else:
    history_status = "ℹ️ 尚未建立 history.txt (可手動上傳)"

# --- 5. 側邊欄設定 ---
with st.sidebar:
    st.header("🤖 設定區")
    
    # 模型選擇
    model_options = [
        "models/gemini-1.5-flash", 
        "models/gemini-2.0-flash-exp", 
        "models/gemini-1.5-pro"
    ]
    selected_model = st.selectbox("選擇模型：", model_options)
    
    st.divider()
    
    # 黑名單顯示區
    st.header("🚫 標題去重 (防撞標)")
    st.info(history_status) 
    
    st.markdown("---")
    st.markdown("👇 **臨時補充** (直接貼上網頁複製的亂亂內容也沒關係，我會自己挑標題)")
    uploaded_file = st.file_uploader("上傳 .txt", type=['txt'])
    
    if uploaded_file is not None:
        stringio = uploaded_file.getvalue().decode("utf-8")
        uploaded_lines = stringio.splitlines()
        # 使用智慧解析
        new_titles = smart_parse_lines(uploaded_lines)
        blacklist_titles.update(new_titles)
        st.success(f"上傳內容包含 {len(uploaded_lines)} 行，系統智慧提取出 {len(new_titles)} 筆有效標題！")
    
    st.divider()
    st.metric("本次已採用標題數", len(st.session_state.used_titles))
    if st.button("清除「已使用」紀錄"):
        st.session_state.used_titles = set()
        st.rerun()

model = genai.GenerativeModel(selected_model)

# --- 6. 系統提示詞 ---
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊 Facelift 版) 與 Dcard (醫美版) 的資深鄉民。
你的語氣必須非常「台式地氣」，模仿真實論壇的討論風格。

【語氣與用詞資料庫】：
1. **關鍵詞彙**：平替、安慰劑、智商稅、
