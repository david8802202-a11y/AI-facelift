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

    if input_method == "醫美預設選單":
        category = st.selectbox(
            "選擇類別：",
            ["醫美閒聊/八卦", "診所黑幕/銷售話術", "電音波/儀器心得", "針劑/微整", "假體/手術", "保健食品/養生"]
        )
        user_topic = category
    else:
        user_topic = st.text_input("請輸入想討論的主題：", value="韓版電波是智商稅嗎？")

with col2:
    tone_intensity = st.select_slider(
        "🔥 語氣強度：",
        options=["溫和理性", "熱烈討論", "辛辣炎上"],
        value="熱烈討論"
    )

tone_prompt = ""
if tone_intensity == "溫和理性": tone_prompt = "語氣偏向經驗分享，理性分析CP值"
elif tone_intensity == "熱烈討論": tone_prompt = "語氣活潑，帶有真實鄉民的口吻 (如：笑死、QQ)"
elif tone_intensity == "辛辣炎上": tone_prompt = "語氣犀利，直接使用「智商稅、盤子、饅化」等強烈詞彙"

# 業配設定
with st.expander("進階設定：業配置入 (選填)"):
    is_promotion = st.checkbox("開啟置入模式")
    product_info = st.text_input("輸入產品名稱與賣點 (例如：營養師輕食魚油，高濃度rTG)")

if 'generated_titles' not in st.session_state:
    st.session_state.generated_titles = []

# --- 生成標題 ---
if st.button("🚀 生成 5 個標題"):
    if not user_topic:
        st.warning("請輸入主題！")
        st.stop()
        
    with st.spinner(f'AI 正在用鄉民邏輯思考「{user_topic}」...'):
        try:
            prompt = f"""
            {SYSTEM_INSTRUCTION}
            
            主題：{user_topic}
            語氣強度：{tone_intensity}
            
            請發想 5 個 PTT/Dcard 風格標題。
            【要求】：
            1. 標題必須包含 `[討論]`、`[問題]` 或 `[閒聊]`。
            2. 嘗試使用資料庫中的詞彙 (如：平替、無底洞、智商稅)。
            3. 直接列出，一行一個。
            """
            response = model.generate_content(prompt)
            titles = response.text.strip().split('\n')
            st.session_state.generated_titles = [t.strip() for t in titles if t.strip()]
        except Exception as e:
            st.error(f"生成失敗：{e}")

# --- 生成內文 ---
if st.session_state.generated_titles:
    st.subheader("👇 選擇一個標題：")
    selected_title = st.radio("標題列表：", st.session_state.generated_titles)
    
    if st.button("✨ 生成內文與回文"):
        with st.spinner('AI 正在撰寫中...'):
            try:
                content_prompt = f"""
                {SYSTEM_INSTRUCTION}
                
                標題：{selected_title}
                原始主題：{user_topic}
                語氣強度：{tone_intensity} ({tone_prompt})
                
                請完成兩項任務：
                1. **內文**：約 150-200 字。請使用第一人稱（我），語氣要像是在抱怨或閒聊，請適度使用「QQ、XD、==」等符號。**必須分段換行**。
                2. **回文**：10 則。嚴格遵守 `推|`、`噓|`、`→|` 格式，**每一則都要換行**。
                """
                
                if is_promotion and product_info:
                    content_prompt += f"""
                    【特殊任務】：
                    在 10 則回文中，請自然地插入 3-4 則關於「{product_info}」的推薦。
                    重點：要像真實鄉民的「好物推薦」或「推坑」，不要像僵硬的廣告機器人。
                    """
                
                response = model.generate_content(content_prompt)
                st.divider()
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"生成失敗：{e}")
