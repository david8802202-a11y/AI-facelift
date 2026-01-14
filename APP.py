import streamlit as st
import google.generativeai as genai
import os
import random

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V38 換行修復版)", page_icon="🗣️")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🗣️ PTT/Dcard 文案產生器 (V38 換行修復版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 取得模型清單 (手動選擇最保險) ---
@st.cache_resource
def get_all_models():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 排序：把 1.5-pro 和 1.0-pro 排前面，避開 flash
        def sort_priority(name):
            if "gemini-1.5-pro" in name and "exp" not in name: return 0
            if "gemini-pro" in name: return 1
            return 10
        models.sort(key=sort_priority)
        return models
    except:
        return ["models/gemini-1.5-pro", "models/gemini-pro"]

all_my_models = get_all_models()

# --- 3. 側邊欄：手動選擇模型 ---
with st.sidebar:
    st.header("⚙️ 模型設定")
    selected_model_name = st.selectbox("👇 選擇模型 (若失敗請換一個)：", all_my_models, index=0)
    
    if "flash" in selected_model_name:
        st.warning("⚠️ Flash 模型在您帳號可能會有 404 問題，建議改用 Pro。")
    elif "2.5" in selected_model_name:
        st.warning("⚠️ 2.5 版本額度極少 (20次)，容易失敗。")
    else:
        st.success(f"目前使用：{selected_model_name} (推薦)")

model = genai.GenerativeModel(selected_model_name)

# --- 4. 餵入真實範文 (Few-Shot Prompting) ---
REAL_EXAMPLES = """
【參考範文 1】：
標題：[討論] 韓版電波真的是平替?
內文：美國電波實在漲太兇，打一次900發都要快10萬。看到很多診所狂推韓版電波，價格只要1/3。大家都說CP值很高，但我心裡一直有個疑問，一分錢一分貨，如果效果真的差不多，那鳳凰怎麼還沒倒？韓版到底是真平替，還是只是打個心安的安慰劑？

【參考範文 2】：
標題：[討論] 針劑醫美根本是無底洞
內文：以前覺得動手術貴，結果記帳發現針劑才是錢坑。肉毒一年要2-3次，玻尿酸半年消一半又要補。算下來一張臉每年的「維護費」竟然要10幾萬！而且是每年都要付！大家有算過自己的「臉部年費」嗎？

【參考範文 3】：
標題：[討論] 男生說喜歡自然美女 其實根本分不出來吧
內文：常聽到男生說「不喜歡女生整形」，結果轉頭狂讚IG網美。但我仔細看，那些女生明明都有動過啊！鼻子微調、額頭補脂...只是做得很高階而已。是不是對直男來說，只要沒有變成蛇精臉，看不出明顯痕跡的統統算天然？
"""

# --- 5. 設定指令 ---
BASE_PERSONA = f"""
你是一個台灣 PTT (Facelift版) 的資深鄉民。
請參考以下【真實範文】的語氣、長度與用詞風格：
{REAL_EXAMPLES}

**核心要求**：
1. **口語化**：像跟朋友聊天，不要有「首先、總之」這種 AI 轉折詞。
2. **字數**：**嚴格控制在 100-120 字左右**，短促有力。
3. **情緒**：要有真實的困惑、懷疑或抱怨 (例如：殺毀、真的假的、==)。
4. **格式**：第一人稱，不要開頭打招呼。
"""

# 安全設定 (全開)
safe_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# --- 6. 主介面 ---
if 'used_titles' not in st.session_state: st.session_state.used_titles = set()
if 'candidate_titles' not in st.session_state: st.session_state.candidate_titles = []

col1, col2 = st.columns(2)

with col1:
    st.subheader("📌 標題分類")
    ptt_tag = st.selectbox("選擇標籤：", ["[問題]", "[討論]", "[心得]", "[閒聊]", "[黑特]", "🎲 隨機"])
    topic_category = st.selectbox("議題內容：", ["💉 針劑/微整", "⚡ 電音波/雷射", "🏥 醫美診所/黑幕", "🔪 整形手術", "✍️ 自訂主題"])
    
    if "自訂" in topic_category:
        user_topic = st.text_input("輸入自訂主題：", "韓版電波是智商稅嗎？")
    else:
        user_topic = f"關於「{topic_category.split('(')[0]}」的討論"

with col2:
    st.subheader("🔥 設定")
    tone_intensity = st.select_slider("強度：", ["溫和", "熱烈", "炎上"], value="熱烈")
    
    st.markdown("---")
    if st.button("🚀 生成 5 個標題", use_container_width=True):
        with st.spinner(f"正在使用 {selected_model_name} 模仿鄉民..."):
            try:
                target_tag = ptt_tag.split(" ")[0] if "隨機" not in ptt_tag else "[問題]"
                prompt = f"""
                {BASE_PERSONA}
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

    if st.button("✍️ 撰寫內文 (真人短文模式)"):
        with st.spinner("撰寫中..."):
            try:
                # --- 第一步：寫內文 (100字左右) ---
                body_prompt = f"""
                {BASE_PERSONA}
                標題：{st.session_state.sel_title}
                主題：{user_topic}
                語氣：{tone_intensity}
                
                任務：寫一篇 PTT 內文。
                【非常重要】：
                1. **字數控制在 100-120 字之間**，不要太長。
                2. 像在用手機打字，句子短一點。
                3. 不要開頭問好，不要結尾總結。
                """
                body_response = model.generate_content(body_prompt, safety_settings=safe_settings).text
                
                # --- 第二步：寫回文 (口語化) ---
                comment_prompt = f"""
                {BASE_PERSONA}
                針對這篇文章生成 8 則回文：
                "{body_response}"
                
                【回文格式】：
                1. 每一行開頭必須是 `推|`。
                2. **不要**有 ID。
                3. 內容要簡短、像真人 (例如：真的...、笑死、+1)。
                {f"【置入】：請在其中 1 則回文自然提到「{prod_info}」，不要太硬。" if is_promo else ""}
                """
                comment_response = model.generate_content(comment_prompt, safety_settings=safe_settings).text
                
                # --- 顯示結果 (強制格式處理) ---
                st.subheader("內文：")
                # ⬇️ 這裡修正了：強制將 \n 換成 Markdown 的換行符號
                st.markdown(body_response.replace("\n", "  \n")) 
                
                st.subheader("回文：")
                comments = comment_response.strip().split('\n')
                formatted_comments = ""
                for c in comments:
                    c = c.strip()
                    if c:
                        if any(x in c for x in ["推|"]):
                             formatted_comments += c + "  \n"
                        elif len(c) > 2: 
                             formatted_comments += f"→| {c}  \n"

                st.markdown(formatted_comments)
                
            except Exception as e:
                st.error("❌ 撰寫失敗")
                st.code(str(e))
