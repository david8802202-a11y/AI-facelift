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
1. **關鍵詞彙**：平替、安慰劑、智商稅、黑科技、無底洞、訂閱制、饅化、塑膠感、蛇精臉、一分錢一分貨、腦波弱、容貌焦慮、直男看不懂。
2. **標題風格**：喜歡用「反問法」、「強烈質疑」或「心得分享」。
3. **回文格式**：每一則回文必須**獨立一行**，且包含 `推|`、`噓|`、`→|`。

【重要任務】：
請發想標題，但**絕對不要**使用重複、老梗、或太像廣告的標題。
"""

# --- 7. 標題生成區 ---
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
        
    with st.spinner(f'AI 正在參考 {len(blacklist_titles)} 筆歷史資料進行發想...'):
        try:
            # 為了過濾，我們要求 AI 多想一點
            prompt = f"""
            {SYSTEM_INSTRUCTION}
            主題：{user_topic}
            語氣：{tone_intensity}
            
            請發想 10 個 PTT/Dcard 風格標題。
            要求：
            1. 標題要吸睛，不要有編號。
            2. 不要使用太常見的農場標題。
            
            直接列出，一行一個。
            """
            response = model.generate_content(prompt)
            raw_titles = response.text.strip().split('\n')
            
            clean_titles = []
            for t in raw_titles:
                t = t.strip()
                if not t: continue
                
                # 檢查 1: 本次是否用過
                if t in st.session_state.used_titles:
                    continue
                    
                # 檢查 2: 是否在黑名單 (只要包含在黑名單標題裡就算撞)
                # 這裡做模糊比對會太慢，先用精準比對
                if t in blacklist_titles:
                    continue
                
                clean_titles.append(t)
            
            st.session_state.candidate_titles = clean_titles[:5]
            
            if len(clean_titles) < 5:
                st.warning(f"AI 生成了 10 個，過濾重複後剩 {len(clean_titles)} 個。")
                
        except Exception as e:
            st.error(f"生成失敗：{e}")

st.divider()

# --- 8. 標題互動區 ---
if st.session_state.candidate_titles:
    st.subheader("👇 點擊「採用」以生成內文 (該標題將不再出現)")
    
    for i, title in enumerate(st.session_state.candidate_titles):
        c1, c2 = st.columns([0.85, 0.15])
        with c1:
            st.code(title, language=None)
        with c2:
            if st.button("✨ 採用", key=f"btn_{i}"):
                st.session_state.selected_title_for_content = title
                st.session_state.used_titles.add(title)
                st.session_state.candidate_titles.pop(i)
                st.rerun()
else:
    st.info("👈 請點擊左上方按鈕生成標題")

# --- 9. 內文生成區 ---
if 'selected_title_for_content' in st.session_state:
    target_title = st.session_state.selected_title_for_content
    st.divider()
    st.markdown(f"### 📝 正在撰寫：{target_title}")
    
    with st.expander("置入設定 (選填)"):
        is_promotion = st.checkbox("開啟置入")
        product_info = st.text_input("產品資訊", value="營養師輕食魚油")

    if st.button("開始撰寫內文與回文"):
        with st.spinner('撰寫中...'):
            try:
                content_prompt = f"""
                {SYSTEM_INSTRUCTION}
                標題：{target_title}
                主題：{user_topic}
                語氣：{tone_intensity}
                
                任務：
                1. 內文 (150-200字，第一人稱，分段換行，口語化)
                2. 回文 (10則，嚴格遵守 推| 噓| →| 格式)
                """
                if is_promotion:
                    content_prompt += f"\n【置入任務】：在回文中自然推薦「{product_info}」。"
                
                response = model.generate_content(content_prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(str(e))
