import streamlit as st
import google.generativeai as genai
import os
import random

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V34 生存版)", page_icon="🏳️")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🏳️ PTT/Dcard 文案產生器 (V34 生存版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 核心連線邏輯 (不猜名字，直接抓清單) ---
@st.cache_resource
def get_any_working_model():
    try:
        # 1. 直接向 Google 要一張「現在能用的清單」
        models = list(genai.list_models())
        
        # 2. 過濾出能寫字的 (generateContent)
        available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        if not available_models:
            return None, "您的 Key 連線成功，但 Google 說您沒有任何可用的模型權限。"

        # 3. 智慧排序 (盡量避開 2.5 這種額度少的，優先找 1.5 或 1.0)
        # 我們把看起來比較穩的排前面，但如果沒有，就用剩下的
        def sort_priority(name):
            if "gemini-1.5-flash" in name: return 0  # 首選
            if "gemini-1.0-pro" in name: return 1    # 次選
            if "gemini-pro" in name: return 2        # 備用
            if "gemini-1.5-pro" in name: return 3
            return 10 # 其他 (包含 2.5)
            
        available_models.sort(key=sort_priority)
        
        # 4. 回傳排在第一位的那個 (就是它了！)
        best_pick = available_models[0]
        return best_pick, None
        
    except Exception as e:
        return None, str(e)

# 執行抓取
final_model_name, error_msg = get_any_working_model()

if not final_model_name:
    st.error("❌ 嚴重錯誤：無法抓取任何模型。")
    st.error(f"錯誤訊息：{error_msg}")
    st.stop()

# 建立模型
model = genai.GenerativeModel(final_model_name)

# --- 3. 顯示目前抓到的救命模型 ---
with st.sidebar:
    st.header("🤖 目前運作模型")
    st.success(f"已自動抓取：\n`{final_model_name}`")
    st.caption("這是系統掃描後，您帳號中「目前排第一位」的可用模型。")
    
    # 如果抓到 2.5，還是提醒一下
    if "2.5" in final_model_name:
        st.warning("⚠️ 注意：系統抓到了 2.5 版本，這個版本免費額度極少(約20次)，請珍惜使用。")

# --- 4. 安全設定 (全開) ---
safe_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# --- 5. 歷史風格讀取 ---
reference_titles = []
if os.path.exists("history.txt"):
    try:
        with open("history.txt", "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip().startswith("[")]
            if lines:
                reference_titles = random.sample(lines, min(len(lines), 5))
    except:
        pass

# --- 6. 提示詞設定 ---
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

# --- 7. 主介面 ---
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
        with st.spinner(f"正在使用 {final_model_name} 生成..."):
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
                # 使用安全設定
                response = model.generate_content(prompt, safety_settings=safe_settings)
                titles = response.text.strip().split('\n')
                st.session_state.candidate_titles = [t.strip() for t in titles if t.strip()][:5]
            except Exception as e:
                st.error("❌ 生成失敗！")
                st.code(str(e))

# --- 8. 結果顯示 ---
if st.session_state.candidate_titles:
    st.markdown("### 👇 生成結果 (點擊採用)")
    for i, t in enumerate(st.session_state.candidate_titles):
        if st.button(t, key=f"btn_{i}", use_container_width=True):
            st.session_state.sel_title = t
            st.session_state.candidate_titles = []
            st.rerun()

# --- 9. 內文撰寫區 ---
if 'sel_title' in st.session_state:
    st.divider()
    st.markdown(f"## 📝 標題：{st.session_state.sel_title}")
    
    with st.expander("置入設定 (選填)"):
        is_promo = st.checkbox("開啟置入")
        prod_info = st.text_input("產品資訊", "XX診所")

    if st.button("✍️ 撰寫內文 (去 AI 感模式)"):
        with st.spinner("正在用鄉民口吻寫作..."):
            try:
                # 1. 生成內文
                body_prompt = f"""
                {SYSTEM_INSTRUCTION}
                標題：{st.session_state.sel_title}
                主題：{user_topic}
                語氣：{tone_intensity}
                任務：請寫一篇 PTT 內文 (約150-200字)。
                要求：第一人稱，口語化，不要有開頭問候，不要結尾總結。
                """
                body_response = model.generate_content(body_prompt, safety_settings=safe_settings).text
                
                # 2. 生成回文
                comment_prompt = f"""
                {SYSTEM_INSTRUCTION}
                針對這篇文章：
                "{body_response}"
                生成 10 則 PTT 回文。
                【嚴格格式要求】：
                1. 每一行開頭必須是 `推|`、`噓|` 或 `→|`。
                2. 不要顯示 ID。
                3. 直接換行，不要有空行。
                {f"【置入】：請在其中 1-2 則自然提到「{prod_info}」。" if is_promo else ""}
                """
                comment_response = model.generate_content(comment_prompt, safety_settings=safe_settings).text
                
                # --- 顯示結果 (保留格式修復) ---
                st.subheader("內文：")
                st.markdown(body_response)
                
                st.subheader("回文：")
                comments = comment_response.strip().split('\n')
                formatted_comments = ""
                for c in comments:
                    c = c.strip()
                    if c:
                        formatted_comments += c + "  \n" 
                
                st.markdown(formatted_comments)
                
            except Exception as e:
                st.error("❌ 撰寫失敗")
                st.code(str(e))
