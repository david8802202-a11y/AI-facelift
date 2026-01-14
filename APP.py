import streamlit as st
import google.generativeai as genai

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT醫美文案產生器 V3.5", page_icon="💉")

# --- 2. 讀取 API Key ---
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Streamlit 的 Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. 獲取可用模型 (不死鳥機制) ---
# 這裡改為：嘗試去抓清單，抓不到就用「備用清單」，絕不讓畫面空白
def get_models_safely():
    # 預設備用清單 (萬一 Google API 沒回應，就強制用這些)
    fallback_models = [
        "models/gemini-1.5-flash", 
        "models/gemini-1.5-pro",
        "models/gemini-1.0-pro"
    ]
    
    try:
        # 嘗試問 Google 有哪些模型
        model_list = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                model_list.append(m.name)
        
        # 排序：把 flash 排前面
        model_list.sort(key=lambda x: 'flash' not in x)
        
        if not model_list:
            return fallback_models # 抓到了但清單是空的(怪怪的)，回傳備用
            
        return model_list
        
    except Exception as e:
        # 抓取失敗 (可能是權限或網路問題)，直接回傳備用清單，讓使用者還是能選
        return fallback_models

available_models = get_models_safely()

# --- 4. 側邊欄與除錯工具 ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    
    # 模型選單
    selected_model_name = st.selectbox(
        "🤖 請選擇 AI 模型：",
        available_models,
        index=0
    )
    
    # 新增：除錯按鈕 (如果又不能用，按這個看真相)
    with st.expander("🔧 連線測試與除錯"):
        if st.button("測試目前模型連線"):
            try:
                test_model = genai.GenerativeModel(selected_model_name)
                response = test_model.generate_content("Hi", generation_config={"max_output_tokens": 1})
                st.success(f"✅ 連線成功！模型 {selected_model_name} 正常運作中。")
            except Exception as e:
                st.error("❌ 連線失敗，真實錯誤訊息如下：")
                st.code(str(e))
                st.caption("請將上方紅字錯誤訊息複製下來，可以查出真正原因。")

# 設定當前使用的模型
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
st.title("💉 PTT/Dcard 醫美文案生成器 V3.5")

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
            st.info("💡 建議：請點擊左側欄位的「測試目前模型連線」按鈕，查看詳細錯誤原因。")

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
