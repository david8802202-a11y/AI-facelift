import streamlit as st
import google.generativeai as genai
import os

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 V10", page_icon="🌶️")

# --- 2. 讀取 API Key ---
api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🌶️ PTT/Dcard 文案產生器 V10 (深度在地化版)")
st.caption("已載入真實鄉民語料庫：包含「平替、饅化、智商稅、訂閱制」等慣用語")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Streamlit 的 Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. 抓取模型清單 ---
@st.cache_resource
def get_real_models():
    try:
        model_list = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                model_list.append(m.name)
        return model_list
    except Exception as e:
        return []

with st.spinner('正在同步 Google 模型清單...'):
    real_models = get_real_models()

# --- 4. 側邊欄設定 ---
with st.sidebar:
    st.header("🤖 模型設定")
    if real_models:
        selected_model = st.selectbox("選擇模型：", real_models, index=0)
    else:
        selected_model = st.text_input("手動輸入模型：", "models/gemini-1.5-flash")

model = genai.GenerativeModel(selected_model)

# --- 5. 系統提示詞 (注入您提供的 8 篇範例精髓) ---
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊 Facelift 版) 與 Dcard (醫美版) 的資深鄉民。
你的語氣必須非常「台式地氣」，模仿真實論壇的討論風格。

【語氣與用詞資料庫 (嚴格遵守)】：
1. **關鍵詞彙**：
   - 形容效果：平替、安慰劑、智商稅、黑科技、重新包裝、無底洞、訂閱制、饅化(填充過度)、塑膠感、蛇精臉、一分錢一分貨。
   - 形容心態：腦波弱、容貌焦慮、被洗版、生火、滅火、勸退、直男看不懂。
   - 平台慣用：小紅書、脆(Threads)、IG、網美。

2. **標題風格**：
   - 喜歡用「反問法」或「強烈質疑」。
   - 範例：「...真的有那麼神嗎？」、「...根本是無底洞吧」、「...是不是智商稅？」

3. **內文結構**：
   - **起頭**：通常是「最近滑IG/小紅書一直看到...」或「朋友跟我說...」或「最近記帳發現...」。
   - **中間**：提出質疑或個人慘痛經驗 (例如：打完臉很僵、錢包很痛)。
   - **結尾**：開放討論 (例如：大家覺得值得嗎？還是我盤子？)。
   - **排版**：必須分段，不要擠在一起。

4. **回文格式 (格式絕對要求)**：
   - 每一則回文必須**獨立一行**。
   - 必須保留 `推|` (贊同/驚訝)、`噓|` (反對/嘲諷)、`→|` (中立/補充) 的符號。
   - 回文內容要簡短有力，像真人推文。

【回文模擬範例】：
推| 打過玩美 真的就是安慰劑...
推| 一分錢一分貨 鳳凰痛歸痛還是有差
→| 小紅書的話術你也信？
推| 真的...微整就是訂閱制 沒續費就打回原形
噓| 這種業配文也太明顯了吧
"""

st.divider()

# --- 6. 操作介面 ---
col1, col2 = st.columns(2)

with col1:
    input_method = st.radio("話題來源：", ["醫美預設選單", "✍️ 自訂輸入 (自由發揮)"], horizontal=True)

    if input_method == "
