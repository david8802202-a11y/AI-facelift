import streamlit as st
import google.generativeai as genai

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT醫美文案產生器", page_icon="💉")

# --- 2. 讀取 API Key ---
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Streamlit 的 Secrets 設定。")
    st.stop()

# --- 3. 設定 Google AI ---
genai.configure(api_key=api_key)

# 【關鍵修改】改用最穩定的 'gemini-pro' (這是一代模型，絕對支援)
# 如果想要嘗試新版，可以以後再改回 'gemini-1.5-flash'
try:
    model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
    # 測試一發，確認活著
    response = model.generate_content("test")
except Exception as e:
    st.error(f"連線嚴重錯誤：{e}")
    st.stop()

# --- 4. 系統提示詞 ---
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊) 與 Dcard 文化的資深鄉民，同時也是專業的醫美行銷文案寫手。
你的任務是根據使用者的需求，撰寫極具討論度、真實感、甚至帶點爭議性的文章。

風格要求：
1. 【標題】：依照版規格式 (如 [閒聊]、[討論]、[問題])。
2. 【內文】：口語化，不要像教科書，要像真實使用者的抱怨、疑惑或心得分享。150字左右。
3. 【回文】：模擬鄉民推噓文，包含護航、酸民、反串、中肯分析等不同立場。需產出10則。
"""

# --- 5. 網頁介面 ---
st.title("💉 PTT/Dcard 醫美文案生成器")
st.caption("目前使用模型：Gemini Pro (穩定版)")

# 步驟 1: 選擇大綱
st.header("步驟 1：選擇話題")
category = st.selectbox(
    "請選擇議題切角：",
    ["診所黑幕/銷售話術", "電音波/儀器", "針劑/微整", "醫美閒聊/容貌焦慮", "假體/手術", "保健食品/養生"]
)

# 業配設定
with st.expander("進階設定：業配置入 (選填)"):
    is_promotion = st.checkbox("開啟置入模式")
    product_info = st.text_input("輸入產品名稱與賣點 (例如：營養師輕食NMN，天然酵母來源)")

# 初始化 session state
if 'generated_titles' not in st.session_state:
    st.session_state.generated_titles = []

# 按鈕：生成標題
if st.button("🚀 生成 5 個標題"):
    with st.spinner('AI 正在逛 PTT 找靈感...'):
        try:
            prompt = f"""
            {SYSTEM_INSTRUCTION}
            請針對「{category}」這個主題，發想 5 個 PTT/Dcard 風格的標題。
            標題要有吸引力，只要列出標題就好，不要有編號或其他廢話。
            """
            response = model.generate_content(prompt)
            titles = response.text.strip().split('\n')
            st.session_state.generated_titles = [t.strip() for t in titles if t.strip()]
        except Exception as e:
            st.error(f"生成失敗：{e}")

# 步驟 2: 選擇並生成內容
if st.session_state.generated_titles:
    st.header("步驟 2：選擇標題並生成內容")
    selected_title = st.radio("請選擇一個標題：", st.session_state.generated_titles)
    
    if st.button("✨ 生成內文與回文"):
        with st.spinner('AI 正在撰寫文章與水軍回覆...'):
            try:
                content_prompt = f"""
                {SYSTEM_INSTRUCTION}
                
                使用者選擇的標題是：{selected_title}
                
                請完成以下任務：
                1. 撰寫【內文】：約 100-150 字，語氣要符合標題的情境。
                2. 撰寫【回文】：10 則推文/噓文 (格式範例：推| 這是回文內容)。
                """
                
                if is_promotion and product_info:
                    content_prompt += f"""
                    【特殊要求】：
                    在 10 則回文中，請自然地安排 3 則回文推薦「{product_info}」。
                    切記：推薦要像真實使用者的分享，不要太生硬的廣告感。
                    """
                
                response = model.generate_content(content_prompt)
                
                st.divider()
                st.subheader("生成結果：")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"生成失敗：{e}")
