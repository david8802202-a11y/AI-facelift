import streamlit as st
import google.generativeai as genai
import os

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V26 全功能回歸版)", page_icon="💎")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("💎 PTT/Dcard 文案產生器 (V26 全功能回歸版)")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 核心連線邏輯 (保留 V25 的自動偵測，確保不報錯) ---
@st.cache_resource
def get_working_model():
    # 優先順序：1.5-pro -> 1.0-pro -> 1.5-flash -> 其他
    # 既然您之前說 flash 不行，我們讓它自動去測，測到誰就用誰
    all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    def sort_key(name):
        if "gemini-1.5-pro" in name and "exp" not in name: return 0
        if "gemini-1.0-pro" in name: return 1
        if "gemini-pro" in name: return 2
        if "flash" in name: return 3
        return 4
        
    all_models.sort(key=sort_key)
    
    for m in all_models:
        try:
            model = genai.GenerativeModel(m)
            model.generate_content("Hi", generation_config={"max_output_tokens": 1})
            return m # 找到第一個能用的就回傳
        except:
            continue
    return None

# 取得可用模型
valid_model_name = get_working_model()

if not valid_model_name:
    st.error("❌ 無法連接任何模型，請檢查額度或 Key。")
    st.stop()

model = genai.GenerativeModel(valid_model_name)

# 在側邊欄偷偷告訴您現在用的是哪一個 (讓您安心)
with st.sidebar:
    st.success(f"🟢 連線穩定！\n目前使用引擎：\n`{valid_model_name}`")
    if st.button("清除記憶 (重置)"):
        st.session_state.clear()
        st.rerun()

# --- 3. 初始化狀態 ---
if 'used_titles' not in st.session_state: st.session_state.used_titles = set()
if 'candidate_titles' not in st.session_state: st.session_state.candidate_titles = []

# --- 4. 參數設定 (選單回來了！) ---
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊 Facelift 版) 與 Dcard (醫美版) 的資深鄉民。
語氣必須非常「台式地氣」，模仿真實論壇的討論風格。

【關鍵詞彙】：平替、安慰劑、智商稅、黑科技、無底洞、訂閱制、饅化、塑膠感、蛇精臉、一分錢一分貨、腦波弱、容貌焦慮。
【標題風格】：喜歡用「反問法」、「強烈質疑」或「心得分享」，這不是新聞標題，是論壇標題。
【回文格式】：每一則回文必須**獨立一行**，且包含 `推|`、`噓|`、`→|`。
"""

# --- 5. 主控台介面 ---
col1, col2 = st.columns(2)

with col1:
    # 這裡就是您要的功能：選單 vs 自訂
    input_method = st.radio("話題來源：", ["👇 醫美熱門話題選單", "✍️ 自訂輸入"], horizontal=True)
    
    if input_method == "👇 醫美熱門話題選單":
        # 這裡放入了您指定的分類
        category = st.selectbox("選擇大類別：", [
            "💉 針劑/微整 (肉毒/玻尿酸/精靈針)",
            "⚡ 電音波/雷射 (鳳凰/海芙/皮秒)",
            "🏥 診所/醫師 (黑幕/話術/諮詢)",
            "🔪 手術/假體 (隆乳/隆鼻/抽脂)",
            "🗣️ 閒聊/八卦 (容貌焦慮/價值觀)"
        ])
        
        # 根據大類別，給出更細的預設情境 (讓 AI 發揮得更好)
        if "針劑" in category:
            user_topic = f"關於 {category} 的討論，例如：打完失敗、饅化、是否值得、副作用"
        elif "電音波" in category:
            user_topic = f"關於 {category} 的心得，例如：痛感、效果不明顯、價格比較、是不是智商稅"
        elif "診所" in category:
            user_topic = f"關於 {category} 的內幕，例如：諮詢師推銷、醫師態度、價格不透明"
        else:
            user_topic = f"關於 {category} 的熱門討論"
            
    else:
        user_topic = st.text_input("輸入主題：", value="韓版電波是智商稅嗎？")

with col2:
    tone_intensity = st.select_slider("🔥 語氣強度：", options=["溫和理性", "熱烈討論", "辛辣炎上"], value="熱烈討論")

# --- 6. 生成標題 ---
if st.button("🚀 生成 5 個新標題"):
    with st.spinner(f"AI 正在構思關於「{category if input_method != '✍️ 自訂輸入' else user_topic}」的標題..."):
        try:
            prompt = f"""
            {SYSTEM_INSTRUCTION}
            主題：{user_topic}
            語氣：{tone_intensity}
            
            請發想 10 個 PTT/Dcard 風格標題。
            要求：
            1. 標題要吸睛，**不要有編號**。
            2. 不要使用太常見的農場標題，要有「真實鄉民感」。
            
            直接列出，一行一個。
            """
            response = model.generate_content(prompt)
            titles = response.text.strip().split('\n')
            
            # 過濾空白與重複
            valid_titles = []
            for t in titles:
                t = t.strip()
                if t and t not in st.session_state.used_titles:
                    valid_titles.append(t)
            
            st.session_state.candidate_titles = valid_titles[:5]
            
            if not st.session_state.candidate_titles:
                 st.warning("生成的標題剛好都重複了，請再試一次！")
                 
        except Exception as e:
            st.error("生成失敗，請稍後再試。")
            st.caption(f"錯誤訊息：{e}")

# --- 7. 標題選擇區 ---
if st.session_state.candidate_titles:
    st.markdown("### 👇 請選擇一個標題來寫內文")
    st.caption("點擊「採用」後，該標題會進入寫作模式，並從清單中移除。")
    
    for i, title in enumerate(st.session_state.candidate_titles):
        c1, c2 = st.columns([0.85, 0.15])
        with c1:
            st.info(title) # 使用 info 樣式比較好看
        with c2:
            if st.button("✨ 採用", key=f"btn_{i}"):
                st.session_state.sel_title = title
                st.session_state.used_titles.add(title) # 加入已使用清單
                st.session_state.candidate_titles = [] # 清空候選
                st.rerun()

# --- 8. 內文撰寫區 ---
if 'sel_title' in st.session_state:
    st.divider()
    st.markdown(f"## 📝 正在撰寫：{st.session_state.sel_title}")
    
    col_a, col_b = st.columns(2)
    with col_a:
        article_length = st.selectbox("文章長度", ["短文 (150字)", "中長文 (300字)", "長文 (500字)"])
    with col_b:
        is_promo = st.checkbox("開啟置入模式 (業配用)")
    
    prod_info = ""
    if is_promo:
        prod_info = st.text_input("置入產品/診所資訊：", value="XX診所的OO療程")
        st.caption("💡 AI 會試著在回文中自然帶入這個資訊，或者在內文中隱晦提到。")

    if st.button("✍️ 開始撰寫內文與回文"):
        with st.spinner("正在撰寫精彩的故事中..."):
            try:
                final_prompt = f"""
                {SYSTEM_INSTRUCTION}
                
                【寫作任務】：
                標題：{st.session_state.sel_title}
                長度：{article_length}
                語氣：{tone_intensity}
                
                【內容要求】：
                1. **內文**：使用第一人稱（原PO），分段清楚，口語化，要有真實的情緒（困擾、生氣、或開心）。
                2. **回文**：請生成 8-10 則鄉民回文，模擬不同立場（有的推、有的噓、有的歪樓）。
                
                {f"【特殊任務 - 置入】：請在回文中，讓 1-2 位鄉民自然地提到或推薦「{prod_info}」，不要太生硬。" if is_promo else ""}
                """
                
                response = model.generate_content(final_prompt)
                st.markdown(response.text)
                st.success("撰寫完成！")
            except Exception as e:
                st.error(f"撰寫失敗：{e}")
