import streamlit as st
import google.generativeai as genai
import os

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT醫美文案產生器 V8", page_icon="🧬")

# --- 2. 讀取 API Key ---
api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🧬 PTT醫美文案產生器 V8 (優化版)")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Streamlit 的 Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. 環境與模型診斷 ---
try:
    import importlib.metadata
    version = importlib.metadata.version('google-generativeai')
    if version < "0.7.2":
        st.caption(f"🔧 系統警告：目前套件版本 {version} 過舊，建議重啟 App。")
except:
    pass

# --- 4. 抓取「真正可用」的模型清單 (維持 V7 架構) ---
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

# --- 5. 側邊欄：模型選擇 ---
with st.sidebar:
    st.header("🤖 模型選擇")
    
    if real_models:
        selected_model = st.selectbox(
            "請選擇要使用的模型：",
            real_models,
            index=0
        )
        st.success(f"已鎖定：{selected_model}")
    else:
        st.error("無法自動取得清單，請手動輸入")
        selected_model = st.text_input("手動輸入模型名稱", "models/gemini-1.5-flash")

# 建立模型物件
model = genai.GenerativeModel(selected_model)

# --- 6. 系統提示詞 (針對您的需求進行 4 點調整) ---
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊) 與 Dcard 文化的資深鄉民，同時也是專業的醫美行銷文案寫手。

【格式嚴格要求】：
1. **標題分類**：標題開頭的標籤，只能從 `[問題]` 或 `[討論]` 這兩者擇一使用。
2. **標題內容**：請發揮創意，不用在意字數限制，重點是吸引人點進來。
3. **內文排版**：
   - 請務必**分段**與**換行**。
   - 不要把所有文字擠成一大塊，要在適當的句點後按 Enter 換行，模擬真實閱讀體驗。
4. **回文格式 (重要)**：
   - 每一則回文必須**獨立一行**。
   - 必須嚴格保留 `推|`、`噓|`、`→|` 這些符號。
   - 範例：
     推| 真的假的？我以為那個沒效
     噓| 業配文也太明顯了吧
     →| 樓上在兇什麼
"""

st.divider()

# --- 7. 操作介面 ---
col1, col2 = st.columns(2)
with col1:
    category = st.selectbox(
        "請選擇議題類別：",
        ["醫美閒聊/八卦", "診所黑幕/銷售話術", "電音波/儀器心得", "針劑/微整 (玻尿酸/肉毒)", "假體/手術 (隆乳/隆鼻)", "保健食品/養生/減肥"]
    )
with col2:
    tone_intensity = st.select_slider(
        "🔥 選擇強度：",
        options=["溫和理性", "熱烈討論", "辛辣炎上"],
        value="熱烈討論"
    )

tone_prompt = ""
if tone_intensity == "溫和理性": tone_prompt = "語氣理性客觀"
elif tone_intensity == "熱烈討論": tone_prompt = "語氣活潑口語"
elif tone_intensity == "辛辣炎上": tone_prompt = "語氣強烈爭議"

# 業配設定
with st.expander("進階設定：業配置入 (選填)"):
    is_promotion = st.checkbox("開啟置入模式")
    product_info = st.text_input("輸入產品名稱與賣點")

if 'generated_titles' not in st.session_state:
    st.session_state.generated_titles = []

# 生成標題按鈕
if st.button("🚀 生成 5 個標題"):
    with st.spinner(f'正在構思標題...'):
        try:
            prompt = f"""
            {SYSTEM_INSTRUCTION}
            主題：{category}，語氣：{tone_intensity}。
            請發想 5 個 PTT 風格標題。
            要求：
            1. 只能使用 `[問題]` 或 `[討論]` 作為開頭分類。
            2. 切角要多元，不要重複。
            直接列出，一行一個。
            """
            response = model.generate_content(prompt)
            titles = response.text.strip().split('\n')
            st.session_state.generated_titles = [t.strip() for t in titles if t.strip()]
        except Exception as e:
            st.error(f"生成失敗：{e}")

# 生成內文按鈕
if st.session_state.generated_titles:
    selected_title = st.radio("選擇標題：", st.session_state.generated_titles)
    if st.button("✨ 生成內文與回文"):
        with st.spinner('撰寫中...'):
            try:
                content_prompt = f"""
                {SYSTEM_INSTRUCTION}
                標題：{selected_title}
                語氣：{tone_intensity} ({tone_prompt})
                請撰寫：
                1. 內文 (約150字，請記得適度換行分段)
                2. 10則回文 (務必包含 推| 噓| →| 符號)
                """
                if is_promotion and product_info:
                    content_prompt += f"需自然置入 3 則關於「{product_info}」的推薦回文。"
                
                response = model.generate_content(content_prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"生成失敗：{e}")
