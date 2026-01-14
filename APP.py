import streamlit as st
import google.generativeai as genai
import os
import random

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V30 格式終極版)", page_icon="📝")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("📝 PTT/Dcard 文案產生器 (V30 格式終極版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 核心連線邏輯 ---
@st.cache_resource
def find_working_model():
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
            return m
        except:
            continue
    return None

valid_model_name = find_working_model()
if not valid_model_name:
    st.error("❌ 無法連接任何模型。")
    st.stop()
model = genai.GenerativeModel(valid_model_name)

# --- 3. 讀取歷史風格 ---
reference_titles = []
if os.path.exists("history.txt"):
    try:
        with open("history.txt", "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip().startswith("[")]
            if lines:
                reference_titles = random.sample(lines, min(len(lines), 5))
    except:
        pass

# --- 4. 參數設定 ---
SYSTEM_INSTRUCTION = """
你是一個台灣 PTT (批踢踢實業坊 Facelift 版) 的資深鄉民。
**任務：寫出「完全不像 AI、口語化」的文章。**

【風格準則】：
1. **口語化**：句子要短，多用「啊、吧、嗎、了、的」。禁止使用「首先、其次、最後」。
2. **情緒化**：符合PTT真實網友回文。
3. **格式要求**：
   - 內文：第一人稱，像在跟朋友聊天。
   - 回文：**每一行回文必須以 `推|`開頭**，後面接內容，不要有帳號。
"""

# --- 5. 主介面 ---
if 'used_titles' not in st.session_state: st.session_state.used_titles = set()
if 'candidate_titles' not in st.session_state: st.session_state.candidate_titles = []

col1, col2 = st.columns(2)

with col1:
    st.subheader("📌 標題分類")
    ptt_tag = st.selectbox("選擇標籤：", ["[問題]", "[討論]", "[心得]", "[閒聊]", "[請益]", "[黑特]", "🎲 隨機"])
    topic_category = st.selectbox("議題內容：", ["💉 針劑/微整", "⚡ 電音波/雷射", "🏥 醫美診所/黑幕", "🔪 整形手術", "✍️ 自訂主題"])
    
    if "自訂" in topic_category:
        user_topic = st.text_input("輸入自訂主題：", "韓版電波是智商稅嗎？")
    else:
        user_topic = f"關於「{topic_category.split('(')[0]}」的討論"

with col2:
    st.subheader("🔥 設定")
    tone_intensity = st.select_slider("強度：", ["溫和", "熱烈", "炎上"], value="熱烈")
    ref_text = ("【參考風格】：\n" + "\n".join(reference_titles)) if reference_titles else ""

    st.markdown("---")
    if st.button("🚀 生成 5 個標題 (約18字)", use_container_width=True):
        with st.spinner("AI 正在模仿鄉民語氣..."):
            try:
                target_tag = ptt_tag.split(" ")[0] if "隨機" not in ptt_tag else "[問題]或[閒聊]"
                prompt = f"""
                {SYSTEM_INSTRUCTION}
                {ref_text}
                任務：發想 10 個 PTT 標題。
                【嚴格限制】：
                1. 必須以「{target_tag}」開頭。
                2. **標題字數(不含標籤)請控制在 16~20 字之間**。
                3. 主題：{user_topic}
                4. 語氣：{tone_intensity}
                直接列出，一行一個，不要編號。
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

    if st.button("✍️ 撰寫內文 (去 AI 感模式)"):
        with st.spinner("正在用鄉民口吻寫作..."):
            
            # --- 分兩段生成，確保格式不會亂 ---
            # 1. 先生成內文
            body_prompt = f"""
            {SYSTEM_INSTRUCTION}
            標題：{st.session_state.sel_title}
            主題：{user_topic}
            語氣：{tone_intensity}
            
            任務：請寫一篇 PTT 內文 (約150-200字)。
            要求：第一人稱，口語化，不要有開頭問候，不要結尾總結，就像隨手打的。
            """
            body_response = model.generate_content(body_prompt).text
            
            # 2. 再生成回文
            comment_prompt = f"""
            {SYSTEM_INSTRUCTION}
            針對這篇文章：
            "{body_response}"
            
            生成 10 則 PTT 回文。
            【嚴格格式要求】：
            1. 每一行開頭必須是 `推|`。
            2. 不要顯示 ID。
            3. 直接換行，不要有空行。
            4. 內容要風格自然。
            {f"【置入】：請在其中 1-2 則自然提到「{prod_info}」。" if is_promo else ""}
            """
            comment_response = model.generate_content(comment_prompt).text
            
            # --- 顯示結果 (強制格式處理) ---
            st.subheader("內文：")
            st.markdown(body_response)
            
            st.subheader("回文：")
            
            # 手動處理每一行，確保 Markdown 換行生效
            comments = comment_response.strip().split('\n')
            formatted_comments = ""
            for c in comments:
                c = c.strip()
                if c:
                    # 在每一行後面加上兩個空格 (Markdown 強制換行語法)
                    formatted_comments += c + "  \n" 
            
            st.markdown(formatted_comments)
