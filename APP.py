import streamlit as st
import google.generativeai as genai
import os
import random

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V29 擬真優化版)", page_icon="🎭")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🎭 PTT/Dcard 文案產生器 (V29 擬真優化版)")

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

# --- 3. 讀取歷史標題作為風格參考 (關鍵新功能) ---
reference_titles = []
if os.path.exists("history.txt"):
    try:
        with open("history.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            # 隨機抓 5 個標題給 AI 參考，讓它知道什麼是人類寫的
            clean_lines = [l.strip() for l in lines if l.strip().startswith("[")]
            if clean_lines:
                reference_titles = random.sample(clean_lines, min(len(clean_lines), 5))
    except:
        pass

# --- 4. 參數設定 (針對您的回饋優化) ---
# 這裡使用了 Few-Shot Prompting (少樣本提示)，讓 AI 模仿爛爛的口語
SYSTEM_INSTRUCTION = """
你是一個台灣 PTT (批踢踢實業坊 Facelift 版) 的資深鄉民。
**你的任務是寫出「完全不像 AI」的文章。**

【風格準則】：
1. **口語化**：句子要短，不要有完整的起承轉合。多用「啊、吧、嗎、了、的」。
2. **禁止說教**：不要用「建議大家」、「總結來說」、「首先/其次/最後」。
3. **情緒化**：要有真實的困惑、生氣或猶豫。
4. **格式要求**：
   - 內文：第一人稱，像在跟朋友聊天，不要太有禮貌。
   - 回文：**絕對不要出現帳號 ID**。
   - 回文格式：每行開頭必須是 `推|`、`噓|` 或 `→|`，後面直接接內容。

【範例風格參考】：
- "最近想打肉毒，但爬文看很多人說會臉僵...真的假的啊？" (O)
- "關於肉毒桿菌的施打建議，我個人認為有以下幾點..." (X -> 太假了)
"""

# --- 5. 主介面 ---
if 'used_titles' not in st.session_state: st.session_state.used_titles = set()
if 'candidate_titles' not in st.session_state: st.session_state.candidate_titles = []

col1, col2 = st.columns(2)

with col1:
    st.subheader("📌 標題分類")
    ptt_tag = st.selectbox(
        "選擇標籤：",
        ["[問題]", "[討論]", "[心得]", "[閒聊]", "[請益]", "[黑特]", "🎲 隨機"]
    )
    
    topic_category = st.selectbox(
        "議題內容：",
        [
            "💉 針劑/微整 (肉毒、玻尿酸、熊貓針)",
            "⚡ 電音波/雷射 (鳳凰、海芙、皮秒)",
            "🏥 醫美診所/黑幕 (諮詢話術、推銷)",
            "🔪 整形手術 (隆乳、隆鼻、抽脂)",
            "✍️ 自訂主題"
        ]
    )
    
    if "自訂" in topic_category:
        user_topic = st.text_input("輸入自訂主題：", "韓版電波是智商稅嗎？")
    else:
        user_topic = f"關於「{topic_category.split('(')[0]}」的討論"

with col2:
    st.subheader("🔥 設定")
    tone_intensity = st.select_slider("強度：", ["溫和", "熱烈", "炎上"], value="熱烈")
    
    # 組合參考資料給 AI
    ref_text = ""
    if reference_titles:
        ref_text = "【參考這些真實人類寫的標題風格】：\n" + "\n".join(reference_titles)

    st.markdown("---")
    if st.button("🚀 生成 5 個標題 (長度約18字)", use_container_width=True):
        with st.spinner("AI 正在模仿鄉民語氣..."):
            try:
                target_tag = ptt_tag.split(" ")[0] if "隨機" not in ptt_tag else "[問題]或[閒聊]"
                
                prompt = f"""
                {SYSTEM_INSTRUCTION}
                
                {ref_text}
                
                任務：發想 10 個 PTT 標題。
                【嚴格限制】：
                1. 每個標題必須以「{target_tag}」開頭。
                2. **標題字數(不含標籤)請控制在 16~20 字之間**，不要太短也不要太長。
                3. 標題要像真人寫的，可以用疑問句。
                4. 主題：{user_topic}
                5. 語氣：{tone_intensity}
                
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
            
            # 這是針對內容優化的 Prompt
            content_prompt = f"""
            {SYSTEM_INSTRUCTION}
            
            現在你要寫一篇 PTT 文章。
            標題：{st.session_state.sel_title}
            主題：{user_topic}
            語氣：{tone_intensity}
            
            【內文要求】：
            1. 字數約 150-200 字。
            2. **不要**有開頭問候語（如：大家好）。
            3. **不要**有結尾總結（如：總之推薦給大家）。
            4. 就像是隨手打的，想到什麼講什麼，可以用「...」或「= =」。
            
            【回文要求】：
            1. 請生成 10 則回文。
            2. **格式嚴格規定**：只顯示 `狀態| 內容`。
               範例：
               推| 真的假的...
               噓| 業配文吧這
               →| 我上次去也是這樣
            3. **絕對不要**生成帳號 ID。
            4. 回文要簡短、嗆辣或中肯。
            
            {f"【秘密任務】：請在回文中，讓 1-2 則自然提到「{prod_info}」，不要太明顯。" if is_promo else ""}
            """
            
            st.markdown(model.generate_content(content_prompt).text)
