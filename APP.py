import streamlit as st
import google.generativeai as genai
import os
import time

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 V17", page_icon="🧬")

# --- 2. 讀取 API Key ---
api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🧬 PTT/Dcard 文案產生器 V17 (自動偵測版)")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Streamlit 的 Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. 自動偵測模型 (核心新功能) ---
# 使用 cache_resource 避免每次按按鈕都重跑測試，但會在網頁重整時執行
@st.cache_resource(show_spinner=False)
def get_verified_models():
    # 我們只測試這三個最常用的 (避免掃描太久)
    candidates = [
        "models/gemini-1.5-flash", 
        "models/gemini-1.5-pro",
        "models/gemini-2.0-flash-exp"
    ]
    verified = []
    
    # 建立一個佔位區顯示進度 (讓你知道程式沒卡死)
    status_placeholder = st.empty()
    status_placeholder.text("🔍 正在自動檢測可用模型...")
    
    for model_name in candidates:
        try:
            # 實彈測試：發送一個字，看會不會報錯
            model = genai.GenerativeModel(model_name)
            model.generate_content("Hi", generation_config={"max_output_tokens": 1})
            verified.append(model_name)
        except Exception:
            # 報錯就跳過，不加入名單
            continue
            
    status_placeholder.empty() # 清除提示文字
    return verified

# 執行自動偵測
verified_models = get_verified_models()

# --- 4. 初始化 Session State ---
if 'used_titles' not in st.session_state:
    st.session_state.used_titles = set()

if 'candidate_titles' not in st.session_state:
    st.session_state.candidate_titles = []

# --- 5. 智慧讀取歷史標題 (V15 機制) ---
blacklist_titles = set()

def smart_parse_lines(lines):
    valid_titles = set()
    for line in lines:
        clean_line = line.strip()
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
        history_status = f"✅ 已自動過濾 {len(parsed_titles)} 筆歷史標題"
    except Exception as e:
        history_status = f"⚠️ 讀取失敗：{e}"
else:
    history_status = "ℹ️ 尚未建立 history.txt"

# --- 6. 側邊欄設定 ---
with st.sidebar:
    st.header("🤖 模型選擇")
    
    if verified_models:
        selected_model = st.selectbox(
            "🟢 已自動篩選可用模型：", 
            verified_models,
            index=0
        )
        st.caption("✨ 清單中的模型皆已通過連線測試。")
    else:
        st.error("❌ 所有模型皆連線失敗，請檢查 API Key 或額度。")
        st.stop()
        
    st.divider()
    
    # 黑名單顯示區
    st.header("🚫 防撞標設定")
    st.info(history_status) 
    
    uploaded_file = st.file_uploader("臨時上傳 .txt (網頁複製文字可)", type=['txt'])
    if uploaded_file is not None:
        stringio = uploaded_file.getvalue().decode("utf-8")
        uploaded_lines = stringio.splitlines()
        new_titles = smart_parse_lines(uploaded_lines)
        blacklist_titles.update(new_titles)
        st.success(f"已臨時加入 {len(new_titles)} 筆標題！")
    
    st.divider()
    st.metric("本次已採用標題數", len(st.session_state.used_titles))
    if st.button("清除「已使用」紀錄"):
        st.session_state.used_titles = set()
        st.rerun()

# 建立模型物件
model = genai.GenerativeModel(selected_model)

# --- 7. 系統提示詞 ---
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊 Facelift 版) 與 Dcard (醫美版) 的資深鄉民。
你的語氣必須非常「台式地氣」，模仿真實論壇的討論風格。

【語氣與用詞資料庫】：
1. **關鍵詞彙**：平替、安慰劑、智商稅、黑科技、無底洞、訂閱制、饅化、塑膠感、蛇精臉、一分錢一分貨、腦波弱、容貌焦慮、直男看不懂。
2. **標題風格**：喜歡用「反問法」、「強烈質疑」或「心得分享」。
3. **回文格式**：每一則回文必須**獨立一行**，且包含 `推|`、`噓|`、`→|`。

【重要任務】：
請發想標題，但**絕對不要**使用重複、老梗、或太像廣告的標題。
"""

# --- 8. 標題生成區 ---
col1, col2 = st.columns(2)
with col1:
    input_method = st.radio("話題來源：", ["醫美預設選單", "✍️ 自訂輸入"], horizontal=True)
    if input_method == "醫美預設選單":
        user_topic = st.selectbox("選擇類別：", ["醫美閒聊/八卦", "診所黑幕/銷售話術", "電音波/儀器心得", "針劑/微整", "假體/手術"])
    else:
        user_topic = st.text_input("輸入主題：", value="韓版電波是智商稅嗎？")

with col2:
    tone_intensity = st.select_slider("🔥 語氣強度：", options=["溫和理性", "熱烈討論", "辛辣炎上"], value="熱烈討論")

if st.button("🚀 生成 5 個新標題 (自動過濾重複)"):
    if not user_topic:
        st.warning("請輸入主題！")
        st.stop()
        
    with st.spinner(f'AI 正在避開 {len(blacklist_titles)}
