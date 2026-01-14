import streamlit as st
import google.generativeai as genai
import os

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V28 標籤精準版)", page_icon="🏷️")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🏷️ PTT/Dcard 文案產生器 (V28 標籤精準版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 核心連線邏輯 (維持 V25 自動找活路機制) ---
@st.cache_resource
def find_working_model():
    all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # 優先測試順序
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
            return m
        except:
            continue
    return None

valid_model_name = find_working_model()
if not valid_model_name:
    st.error("❌ 無法連接任何模型。")
    st.stop()

model = genai.GenerativeModel(valid_model_name)

# --- 3. 初始化 ---
if 'used_titles' not in st.session_state: st.session_state.used_titles = set()
if 'candidate_titles' not in st.session_state: st.session_state.candidate_titles = []

# --- 4. 參數設定 ---
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊 Facelift 版) 與 Dcard (醫美版) 的資深鄉民。
語氣必須非常「台式地氣」。
【標題格式嚴格要求】：每個標題都必須以 `[分類]` 開頭，例如 `[問題]`、`[討論]`、`[心得]`、`[閒聊]`。
"""

# --- 5. 主介面 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📌 設定標題分類")
    
    # 1. 這裡就是您指定的「分類標籤」
    ptt_tag = st.selectbox(
        "請選擇標題分類：",
        [
            "[問題] (針對發問、求救)",
            "[討論] (針對議題探討、比較)",
            "[心得] (針對術後分享、避雷)",
            "[閒聊] (針對八卦、價值觀)",
            "[請益] (針對醫師選擇、價格)",
            "[黑特] (針對抱怨、失敗經驗)",
            "🎲 隨機混合 (由 AI 自動判斷)"
        ]
    )
    
    # 2. 議題內容 (話題)
    topic_category = st.selectbox(
        "請選擇議題內容：",
        [
            "💉 針劑/微整 (肉毒、玻尿酸、精靈針)",
            "⚡ 電音波/雷射 (鳳凰、海芙、皮秒)",
            "🏥 醫美診所/黑幕 (諮詢話術、推銷)",
            "🔪 整形手術 (隆乳、隆鼻、抽脂)",
            "✍️ 自訂主題"
        ]
    )
    
    if "自訂" in topic_category:
        user_topic = st.text_input("輸入自訂主題：", "韓版電波是智商稅嗎？")
    else:
        user_topic = f"關於「{topic_category}」的熱門討論"

with col2:
    st.subheader("🔥 設定語氣")
    tone_intensity = st.select_slider("強度：", ["溫和理性", "熱烈討論", "辛辣炎上"], value="熱烈討論")
    
    st.markdown("---")
    
    # 處理標籤邏輯
    target_tag = ptt_tag.split(" ")[0] # 只抓取 [問題] 這種格式
    if "隨機" in target_tag:
        tag_instruction = "標題必須包含 [問題]、[討論] 或 [心得] 等 PTT 常見標籤。"
    else:
        tag_instruction = f"⚠️ 嚴格要求：生成的 10 個標題，每一個都必須以「{target_tag}」開頭。"

    if st.button("🚀 生成 5 個標題", use_container_width=True):
        with st.spinner(f"正在生成 {target_tag} 類型的標題..."):
            try:
                prompt = f"""
                {SYSTEM_INSTRUCTION}
                主題：{user_topic}
                語氣：{tone_intensity}
                
                {tag_instruction}
                
                請發想 10 個標題，一行一個，不要編號。
                """
                response = model.generate_content(prompt)
                titles = response.text.strip().split('\n')
                st.session_state.candidate_titles = [t.strip() for t in titles if t.strip()][:5]
            except Exception as e:
                st.error("生成失敗，請重試。")

# --- 6. 結果顯示區 ---
if st.session_state.candidate_titles:
    st.markdown("### 👇 生成結果 (點擊採用)")
    for i, t in enumerate(st.session_state.candidate_titles):
        if st.button(t, key=f"btn_{i}", use_container_width=True):
            st.session_state.sel_title = t
            st.session_state.candidate_titles = []
            st.rerun()

# --- 7. 內文撰寫區 ---
if 'sel_title' in st.session_state:
    st.divider()
    st.markdown(f"## 📝 標題：{st.session_state.sel_title}")
    
    with st.expander("置入設定 (選填)"):
        is_promo = st.checkbox("開啟置入")
        prod_info = st.text_input("產品資訊", "XX診所")

    if st.button("✍️ 撰寫內文"):
        with st.spinner("撰寫中..."):
            p = f"""
            {SYSTEM_INSTRUCTION}
            標題：{st.session_state.sel_title}
            主題：{user_topic}
            語氣：{tone_intensity}
            任務：
            1. 內文 (150字，第一人稱，口語化)
            2. 回文 (10則，嚴格遵守 推| 噓| →| 格式)
            """
            if is_promo: p += f"\n【特殊任務】：請在回文中自然置入推薦「{prod_info}」。"
            st.markdown(model.generate_content(p).text)
