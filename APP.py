import streamlit as st
import google.generativeai as genai

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT醫美文案產生器 V5 (生存測試版)", page_icon="💉")

# --- 2. 讀取 API Key ---
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Streamlit 的 Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. 核彈級模型生存測試 (The Survival Test) ---
@st.cache_resource(ttl=600) # 測試結果存 10 分鐘
def get_surviving_models():
    # 這裡列出所有可能的模型名稱寫法，包含別名與版本號
    # 只要其中一個能用，我們就贏了
    suspects = [
        "gemini-1.5-flash",          # 標準寫法
        "models/gemini-1.5-flash",   # 完整寫法
        "gemini-1.5-flash-latest",   # 強制最新版
        "gemini-1.5-pro",
        "models/gemini-1.5-pro",
        "gemini-1.5-pro-latest",
        "gemini-pro",                # 1.0 的通用別名 (最穩)
        "models/gemini-pro",
        "gemini-1.0-pro",
        "models/gemini-1.0-pro"
    ]
    
    survivors = []
    
    # 建立一個進度條給你看
    progress_text = st.empty()
    
    for model_name in suspects:
        try:
            # 顯示正在測試誰
            progress_text.caption(f"正在測試模型連線：{model_name} ...")
            
            # 實際建立模型
            model = genai.GenerativeModel(model_name)
            # 發送一個 token 的超迷你測試
            response = model.generate_content("Hi", generation_config={"max_output_tokens": 1})
            
            # 如果沒報錯，代表它是活的！
            survivors.append(model_name)
            
        except Exception:
            # 報錯就代表死了 (404 或 429)，直接跳過
            continue
    
    progress_text.empty() # 清除進度文字
    return survivors

# 執行測試
with st.spinner('正在進行模型生存測試，請稍候...'):
    valid_models = get_surviving_models()

# --- 4. 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    
    if valid_models:
        # 讓使用者從存活名單中選
        selected_model_name = st.selectbox(
            "🟢 請選擇可用模型：",
            valid_models,
            index=0
        )
        st.success("✅ 系統已自動過濾掉壞掉的模型。")
    else:
        st.error("❌ 嚴重錯誤：所有已知的模型名稱都無法連線。")
        st.warning("請確認您的 API Key 是否有效，或是否開通了 Google AI Studio 權限。")
        st.stop()

    # 重新掃描按鈕
    if st.button("🔄 重新掃描模型"):
        st.cache_resource.clear()
        st.rerun()

# 設定模型
model = genai.GenerativeModel(selected_model_name)

# --- 5. 系統提示詞 ---
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊) 與 Dcard 文化的資深鄉民，同時也是專業的醫美行銷文案寫手。

【格式嚴格要求】：
1. **標題分類**：所有標題必須包含分類標籤。例如 `[閒聊]`、`[討論]`、`[問題]`、`[心得]`。
2. **標題長度**：**標題文字部分 (不含前面的分類標籤) 必須控制在 18 個繁體中文字以內**。精簡有力。
3. **回文排版**：每一則回文都必須**獨立換行**。
   - 錯誤範例：推| 好看 推| 真的
   - 正確範例：
     推| 好看
     推| 真的
"""

# --- 6. 主畫面 ---
st.title("💉 PTT/Dcard 醫美文案生成器 V5")
st.caption(f"目前使用模型：{selected_model_name}")

# 區塊 1: 話題與強度設定
st.header("步驟 1：設定參數")

col1, col2 = st.columns(2)

with col1:
    category = st.selectbox(
        "請選擇議題類別：",
        ["醫美閒聊/八卦", "診所黑幕/銷售話術", "電音波/儀器心得", "針劑/微整 (玻尿酸/肉毒)", "假體/手術 (隆乳/隆鼻)", "保健食品/養生/減肥"]
    )

with col2:
    tone_intensity = st.select_slider(
        "🔥 選擇標題/文案強度：",
        options=["溫和理性", "熱烈討論", "辛辣炎上"],
        value="熱烈討論"
    )

tone_prompt = ""
if tone_intensity == "溫和理性":
    tone_prompt = "語氣要理性、客觀。適合 [心得] 或 [請益]。"
elif tone_intensity == "熱烈討論":
    tone_prompt = "語氣活潑、口語化。適合 [閒聊] 或 [討論]。"
elif tone_intensity == "辛辣炎上":
    tone_prompt = "語氣強烈、帶有爭議性戰點。適合 [黑特] 或爭議性 [討論]。"

# 業配設定
with st.expander("進階設定：業配置入 (選填)"):
    is_promotion = st.checkbox("開啟置入模式")
    product_info = st.text_input("輸入產品名稱與賣點 (例如：營養師輕食NMN，天然酵母來源)")

if 'generated_titles' not in st.session_state:
    st.session_state.generated_titles = []

# 按鈕：生成標題
if st.button("🚀 生成 5 個標題"):
    with st.spinner(f'AI 正在發想標題...'):
        try:
            prompt = f"""
            {SYSTEM_INSTRUCTION}
            
            請針對主題「{category}」與語氣「{tone_intensity}」({tone_prompt})，發想 5 個 PTT 風格標題。
            
            【必要條件】：
            1. **必須包含分類標籤** (如 [閒聊], [問題])。
            2. **標題文字(不含標籤) 必須在 18 字以內**。
            3. 這 5 個標題要切入完全不同的面向 (例如預算、痛感、八卦、術後焦慮、另一半看法)。
            
            請直接列出 5 個標題，不要有編號，一行一個。
            """
            response = model.generate_content(prompt)
            titles = response.text.strip().split('\n')
            st.session_state.generated_titles = [t.strip() for t in titles if t.strip()]
        except Exception as e:
            st.error(f"生成失敗：{e}")
            if "429" in str(e):
                 st.warning("⚠️ 請求過快，請稍等一下再試。")

# 步驟 2: 選擇並生成內容
if st.session_state.generated_titles:
    st.header("步驟 2：選擇標題並生成內容")
    selected_title = st.radio("請選擇一個標題：", st.session_state.generated_titles)
    
    if st.button("✨ 生成內文與回文"):
        with st.spinner('AI 正在撰寫...'):
            try:
                content_prompt = f"""
                {SYSTEM_INSTRUCTION}
                
                標題：{selected_title}
                語氣強度：{tone_intensity} ({tone_prompt})
                
                請完成以下任務：
                1. 撰寫【內文】：約 100-150 字，語氣符合標題情境。
                2. 撰寫【回文】：10 則推文/噓文。
                   - **重要：每一則回文之前，請務必換行**。
                   - 格式：
                     推| 內容...
                     噓| 內容...
                     →| 內容...
                """
                
                if is_promotion and product_info:
                    content_prompt += f"""
                    【特殊要求】：
                    在 10 則回文中，請自然地安排 3 則回文推薦「{product_info}」。
                    """
                
                response = model.generate_content(content_prompt)
                
                st.divider()
                st.subheader("生成結果：")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"生成失敗：{e}")
