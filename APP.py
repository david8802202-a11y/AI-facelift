import streamlit as st
import google.generativeai as genai
import os
import random

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V36 腦袋分離版)", page_icon="🧠")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🧠 PTT/Dcard 文案產生器 (V36 腦袋分離版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 抓取所有模型清單 ---
@st.cache_resource
def get_all_models():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 排序：優先把 1.5-pro 排前面，因為它最聰明
        models.sort(key=lambda x: 0 if "1.5-pro" in x else 1)
        return models
    except:
        return ["models/gemini-pro", "models/gemini-1.5-pro"]

all_my_models = get_all_models()

# --- 3. 側邊欄：手動選擇模型 ---
with st.sidebar:
    st.header("⚙️ 模型設定")
    st.info("若產出亂碼，請切換不同模型試試。")
    selected_model_name = st.selectbox("👇 選擇模型：", all_my_models, index=0)
    
    # 顯示狀態
    if "2.5" in selected_model_name:
        st.warning("⚠️ 2.5 版額度極少，容易失敗。")
    elif "1.5-pro" in selected_model_name:
        st.success("✅ 1.5-Pro 是最推薦的穩定選擇。")

# 建立模型物件
model = genai.GenerativeModel(selected_model_name)

# --- 4. 關鍵修正：把指令拆開，不要混在一起 ---

# 這是「通用」的人設，大家都能用
BASE_PERSONA = "你是一個台灣 PTT (批踢踢實業坊 Facelift 版) 的資深鄉民。語氣要口語化、真實，多用「啊、吧、嗎、了」。"

# 這是「專門寫內文」的指令 (拿掉了回文規則)
BODY_INSTRUCTION = f"""
{BASE_PERSONA}
**任務：寫一篇「第一人稱」的 PTT 心得文或問題文。**
【風格要求】：
1. 就像跟朋友聊天，句子要碎，不要太完整。
2. **禁止**使用「首先、總結來說」這種 AI 用語。
3. **禁止**在開頭打招呼 (大家好)，也禁止在結尾自我介紹。
4. 直接切入重點，要有真實的情緒 (困擾、生氣、猶豫)。
"""

# 這是「專門寫回文」的指令 (強調格式)
COMMENT_INSTRUCTION = f"""
{BASE_PERSONA}
**任務：針對文章生成 8-10 則簡短的鄉民回文。**
【嚴格格式要求】：
1. 每一行**必須**以 `推|`、`噓|` 或 `→|` 開頭。
2. 格式範例：`推| 真的假的...我才剛想去`。
3. **絕對不要**生成帳號 ID。
4. 內容要簡短、嗆辣或中肯，不要長篇大論。
"""

# 設定「穩定器」參數，防止 AI 發瘋
stable_config = genai.types.GenerationConfig(
    temperature=0.7,  # 稍微降低創意度，讓它乖一點
    top_p=0.9,
    top_k=40,
    max_output_tokens=1000,
)

# 安全設定 (全開)
safe_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# --- 5. 歷史風格 ---
reference_titles = []
if os.path.exists("history.txt"):
    try:
        with open("history.txt", "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip().startswith("[")]
            if lines: reference_titles = random.sample(lines, min(len(lines), 5))
    except: pass

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
        with st.spinner(f"正在使用 {selected_model_name} 生成..."):
            try:
                target_tag = ptt_tag.split(" ")[0] if "隨機" not in ptt_tag else "[問題]"
                prompt = f"""
                {BASE_PERSONA}
                {ref_text}
                任務：發想 10 個 PTT 標題。
                嚴格限制：
                1. 必須以「{target_tag}」開頭。
                2. 字數(不含標籤)控制在 16~20 字。
                3. 主題：{user_topic}
                4. 語氣：{tone_intensity}
                一行一個，不要編號。
                """
                response = model.generate_content(prompt, safety_settings=safe_settings, generation_config=stable_config)
                titles = response.text.strip().split('\n')
                st.session_state.candidate_titles = [t.strip() for t in titles if t.strip()][:5]
            except Exception as e:
                st.error("❌ 生成失敗，請換個模型試試。")
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

    if st.button("✍️ 撰寫內文 (格式修復版)"):
        with st.spinner("正在分段撰寫中..."):
            try:
                # --- 第一步：只寫內文 (使用乾淨的指令) ---
                body_prompt = f"""
                {BODY_INSTRUCTION}
                標題：{st.session_state.sel_title}
                主題：{user_topic}
                語氣：{tone_intensity}
                """
                body_response = model.generate_content(body_prompt, safety_settings=safe_settings, generation_config=stable_config).text
                
                # --- 第二步：只寫回文 (給它看內文，但指令專注於回文) ---
                comment_prompt = f"""
                {COMMENT_INSTRUCTION}
                請針對這篇文章生成回文：
                文章內容："{body_response}"
                
                {f"【置入任務】：請在其中 1-2 則回文自然提到「{prod_info}」。" if is_promo else ""}
                """
                comment_response = model.generate_content(comment_prompt, safety_settings=safe_settings, generation_config=stable_config).text
                
                # --- 顯示結果 ---
                st.subheader("內文：")
                st.markdown(body_response)
                
                st.subheader("回文：")
                
                # 再次進行 Python 強制格式化，過濾掉亂碼
                comments = comment_response.strip().split('\n')
                formatted_comments = ""
                for c in comments:
                    c = c.strip()
                    # 只保留真正符合格式的行，過濾掉 AI 發瘋產生的 "嗎|" "的|"
                    if c.startswith("推") or c.startswith("噓") or c.startswith("→"):
                        formatted_comments += c + "  \n"
                    # 如果 AI 沒加符號但內容正常，我們幫它加一個箭頭
                    elif len(c) > 2 and "|" not in c:
                        formatted_comments += f"→| {c}  \n"
                        
                st.markdown(formatted_comments)
                
            except Exception as e:
                st.error("❌ 撰寫失敗")
                st.code(str(e))
