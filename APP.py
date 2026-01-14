import streamlit as st
import google.generativeai as genai
import os
import random

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V33 經典版)", page_icon="🏛️")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🏛️ PTT/Dcard 文案產生器 (V33 經典版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 核心連線邏輯 (強制使用 gemini-pro 1.0) ---
@st.cache_resource
def get_stable_model():
    # 這裡我們不自動亂抓了，直接指定最經典的 1.0 版本
    # 這個版本最不容易出錯，雖然速度沒 Flash 快，但最穩定
    target_models = [
        "gemini-pro",         # Google 最標準的名稱
        "models/gemini-pro",  # 另一種寫法
        "models/gemini-1.5-pro-latest" # 萬一 1.0 真的不行，才用 1.5 Pro (不是 Flash)
    ]
    
    for m in target_models:
        try:
            model = genai.GenerativeModel(m)
            # 發送一個極短的測試訊號
            model.generate_content("Hi", generation_config={"max_output_tokens": 1})
            return m
        except:
            continue
    return None

valid_model_name = get_stable_model()

if not valid_model_name:
    st.error("❌ 連線失敗。請確認您的 Key 是否有權限存取 gemini-pro。")
    st.stop()

# --- 3. 安全設定 (全開，防止醫美話題被擋) ---
safe_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

model = genai.GenerativeModel(valid_model_name)

# 顯示目前使用的模型 (讓您確認不是 Flash)
with st.sidebar:
    st.success(f"✅ 已鎖定經典版模型：\n{valid_model_name}")
    st.caption("已避開 1.5 Flash 與 2.5 版本")

# --- 4. 讀取歷史風格 ---
reference_titles = []
if os.path.exists("history.txt"):
    try:
        with open("history.txt", "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip().startswith("[")]
            if lines:
                reference_titles = random.sample(lines, min(len(lines), 5))
    except:
        pass

# --- 5. 提示詞設定 ---
SYSTEM_INSTRUCTION = """
你是一個台灣 PTT (批踢踢實業坊 Facelift 版) 的資深鄉民。
**任務：寫出「完全不像 AI、口語化」的文章。**

【風格準則】：
1. **口語化**：句子要短，多用「啊、吧、嗎、了、的」。禁止使用「首先、其次、最後」。
2. **情緒化**：要有真實的困惑、生氣或猶豫。
3. **格式要求**：
   - 內文：第一人稱，像在跟朋友聊天。
   - 回文：**每一行回文必須以 `推|`、`噓|` 或 `→|` 開頭**，後面接內容，不要有帳號。
"""

# --- 6. 主介面 ---
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
        with st.spinner(f"正在使用 {valid_model_name} 生成..."):
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
                # 加入 safety_settings
                response = model.generate_content(prompt, safety_settings=safe_settings)
                titles = response.text.strip().split('\n')
                st.session_state.candidate_titles = [t.strip() for t in titles if t.strip()][:5]
            except Exception as e:
                st.error("❌ 生成失敗！")
                st.code(str(e))

# --- 7. 結果顯示區 ---
if st.session_state.candidate_titles:
    st.markdown("### 👇 生成結果 (點擊採用)")
    for i, t in enumerate(st.session_state.candidate_titles):
        if st.button(t, key=f"btn_{i}", use_container_width=True):
            st.session_state.sel_title = t
            st.session_state.candidate_titles = []
            st.rerun()

# --- 8. 內文撰寫區 ---
if 'sel_title
