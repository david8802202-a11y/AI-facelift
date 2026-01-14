import streamlit as st
import google.generativeai as genai
import os
import random

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V35 手動切換版)", page_icon="🔧")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🔧 PTT/Dcard 文案產生器 (V35 手動切換版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 抓取所有名單 (但不自動選，讓您選) ---
@st.cache_resource
def get_all_models():
    try:
        # 抓取所有支援寫作的模型
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 排序：把看起來像正式版的排前面
        models.sort(key=lambda x: 0 if "1.5-pro" in x else 1)
        return models
    except Exception as e:
        return []

all_my_models = get_all_models()

# 如果連名單都抓不到，就提供一組預設的讓您試
if not all_my_models:
    st.warning("⚠️ 無法自動抓取清單，已切換為手動輸入模式。")
    all_my_models = ["models/gemini-1.5-pro", "models/gemini-pro", "models/gemini-1.5-flash"]

# --- 3. 側邊欄：手動選擇模型 (關鍵救星) ---
with st.sidebar:
    st.header("⚙️ 模型設定 (救命區)")
    st.info("如果生成失敗，請在這裡換一個模型試試看！")
    
    # 這裡讓您自己選！
    selected_model_name = st.selectbox(
        "👇 請選擇模型：",
        all_my_models,
        index=0
    )
    
    if "2.5" in selected_model_name:
        st.warning("⚠️ 2.5 版本額度很少，容易失敗，建議換成 1.5-pro。")
    else:
        st.success(f"目前使用：{selected_model_name}")

# 建立模型物件
model = genai.GenerativeModel(selected_model_name)

# --- 4. 安全設定 (全開) ---
safe_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# --- 5. 歷史與參數 ---
reference_titles = []
if os.path.exists("history.txt"):
    try:
        with open("history.txt", "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip().startswith("[")]
            if lines: reference_titles = random.sample(lines, min(len(lines), 5))
    except: pass

SYSTEM_INSTRUCTION = """
你是一個台灣 PTT (批踢踢實業坊 Facelift 版) 的資深鄉民。
**任務：寫出「完全不像 AI、口語化」的文章。**
【風格準則】：
1. **口語化**：句子要短，多用「啊、吧、嗎、了、的」。禁止使用「首先、其次、最後」。
2. **格式要求**：回文每一行開頭必須是 `推|`、`噓|` 或 `→|`，後面接內容，不要有帳號。
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
    if st.button("🚀 生成 5 個標題", use_container_width=True):
        with st.spinner(f"正在嘗試使用 {selected_model_name} ..."):
            try:
                target_tag = ptt_tag.split(" ")[0] if "隨機" not in ptt_tag else "[問題]或[閒聊]"
                prompt = f"""
                {SYSTEM_INSTRUCTION}
                {ref_text}
                任務：發想 10 個 PTT 標題。
                嚴格限制：
                1. 必須以「{target_tag}」開頭。
                2. 字數(不含標籤)控制在 16~20 字。
                3. 主題：{user_topic}
                4. 語氣：{tone_intensity}
                一行一個，不要編號。
                """
                response = model.generate_content(prompt, safety_settings=safe_settings)
                titles = response.text.strip().split('\n')
                st.session_state.candidate_titles = [t.strip() for t in titles if t.strip()][:5]
            except Exception as e:
                st.error("❌ 這個模型失敗了！")
                st.warning("👉 請去左邊側邊欄的選單，**換另一個模型** 再試一次！")
                st.code(str(e))

# --- 7. 結果與內文區 ---
if st.session_state.candidate_titles:
    st.markdown("### 👇 生成結果 (點擊採用)")
    for i, t in enumerate(st.session_state.candidate_titles):
        if st.button(t, key=f"btn_{i}", use_container_width=True):
            st.session_state.sel_title = t
            st.session_state.candidate_titles = []
            st.rerun()

if 'sel_title' in st.session_state:
    st.divider()
    st.markdown(f"## 📝 標題：{st.session_state.sel_title}")
    
    with st.expander("置入設定 (選填)"):
        is_promo = st.checkbox("開啟置入")
        prod_info = st.text_input("產品資訊", "XX診所")

    if st.button("✍️ 撰寫內文 (去 AI 感模式)"):
        with st.spinner("撰寫中..."):
            try:
                # 1. 內文
                body_prompt = f"""
                {SYSTEM_INSTRUCTION}
                標題：{st.session_state.sel_title}
                主題：{user_topic}
                語氣：{tone_intensity}
                任務：寫一篇 PTT 內文 (約150字)。第一人稱，口語化，不要開頭問候結尾。
                """
                body_response = model.generate_content(body_prompt, safety_settings=safe_settings).text
                
                # 2. 回文
                comment_prompt = f"""
                {SYSTEM_INSTRUCTION}
                針對這篇文章："{body_response}"
                生成 10 則回文。每一行開頭必須是 `推|`、`噓|` 或 `→|`。直接換行。
                {f"【置入】：在其中 1-2 則自然提到「{prod_info}」。" if is_promo else ""}
                """
                comment_response = model.generate_content(comment_prompt, safety_settings=safe_settings).text
                
                st.subheader("內文：")
                st.markdown(body_response)
                
                st.subheader("回文：")
                # 強制格式修正
                comments = comment_response.strip().split('\n')
                formatted_comments = ""
                for c in comments:
                    c = c.strip()
                    if c: formatted_comments += c + "  \n"
                st.markdown(formatted_comments)
                
            except Exception as e:
                st.error("❌ 撰寫失敗，請換個模型再試。")
                st.code(str(e))
