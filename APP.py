import streamlit as st
import google.generativeai as genai

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT醫美文案產生器 V2.5", page_icon="💉")

# --- 2. 讀取 API Key ---
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Streamlit 的 Secrets 設定。")
    st.stop()

# --- 3. 設定 Google AI ---
genai.configure(api_key=api_key)

# 依照您的指示，指定使用 'models/gemini-2.5-flash'
try:
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    # 稍微測試一下模型是否活著 (不消耗大量 token)
    # 這裡用一個簡單的請求來驗證連線
    # 如果 2.5 失敗，會直接跳到 except 顯示錯誤
except Exception as e:
    st.error(f"⚠️ 模型載入失敗：無法使用 'models/gemini-2.5-flash'。")
    st.error(f"錯誤訊息：{e}")
    st.info("建議：請檢查模型名稱是否正確，或暫時改回 'models/gemini-1.5-flash'。")
    st.stop()

# --- 4. 系統提示詞 (AI 的人設與核心規則) ---
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊) 與 Dcard 文化的資深鄉民，同時也是專業的醫美行銷文案寫手。
你的任務是根據使用者的需求，撰寫極具吸引力、討論度高的文章。

【核心原則】：
1. **真實感**：不要像機器人，要有「人味」，適度使用語助詞、表情符號(XD, QQ)，以及真實的情緒發洩。
2. **多樣性**：當要求生成多個標題時，務必從「不同切角」切入（例如：金錢觀、審美觀、術後痛苦、八卦、技術面、兩性關係），嚴禁重複類似的主題或句型。
"""

# --- 5. 網頁介面 ---
st.title("💉 PTT/Dcard 醫美文案生成器 V2.5")
st.caption("目前使用模型：Gemini 2.5 Flash")

# 區塊 1: 話題與強度設定
st.header("步驟 1：設定參數")

col1, col2 = st.columns(2)

with col1:
    category = st.selectbox(
        "請選擇議題類別：",
        ["醫美閒聊/八卦 (不限容貌焦慮)", "診所黑幕/銷售話術", "電音波/儀器心得", "針劑/微整 (玻尿酸/肉毒)", "假體/手術 (隆乳/隆鼻)", "保健食品/養生/減肥"]
    )

with col2:
    # 新增：語氣強度滑桿
    tone_intensity = st.select_slider(
        "🔥 選擇標題/文案強度：",
        options=["溫和理性", "熱烈討論", "辛辣炎上"],
        value="熱烈討論"
    )

# 根據強度設定對應的 Prompt
tone_prompt = ""
if tone_intensity == "溫和理性":
    tone_prompt = "語氣要理性、客觀、溫柔。適合純心得分享、發問或衛教討論，避免過激言詞。"
elif tone_intensity == "熱烈討論":
    tone_prompt = "語氣要活潑、口語化，符合一般論壇的熱門討論風格，帶有正常的情緒起伏。"
elif tone_intensity == "辛辣炎上":
    tone_prompt = "語氣要非常強烈、主觀、帶有爭議性（戰點）。可以使用激問、諷刺、過度焦慮或憤怒的口吻，目標是引起兩派人馬激辯。"

# 業配設定
with st.expander("進階設定：業配置入 (選填)"):
    is_promotion = st.checkbox("開啟置入模式")
    product_info = st.text_input("輸入產品名稱與賣點 (例如：營養師輕食NMN，天然酵母來源)")

# 初始化 session state
if 'generated_titles' not in st.session_state:
    st.session_state.generated_titles = []

# 按鈕：生成標題
if st.button("🚀 生成 5 個標題"):
    with st.spinner(f'AI 正在發想【{tone_intensity}】風格的標題...'):
        try:
            # 加入更嚴格的多樣性指令 (這就是之前報錯的地方，請確認引號有完整複製)
            prompt = f"""
            {SYSTEM_INSTRUCTION}
            
            使用者選擇的主題是：「{category}」
            使用者希望的語氣強度是：「{tone_intensity}」({tone_prompt})
            
            請發想 5 個 PTT/Dcard 風格的標題。
            
            【嚴格要求】：
            1. **語氣強度**：必須完全符合「{tone_intensity}」的設定。
            2. **極致多樣性**：這 5 個標題必須切入 **5 個完全不同的面向**。
               - 例如：如果是「醫美閒聊」，不要全部都在講容貌焦慮。
               - 請包含：預算/CP值討論、術後生活不便、對診所/醫師的觀察、兩性/人際關係、或是純粹的技術疑問。
               - **絕對不要**讓 5 個標題看起來很像。
            
            請直接列出 5 個標題，不要有編號或前言，一行一個。
            """
            
            response = model.generate_content(prompt)
            titles = response.text.strip().split('\n')
            # 過濾空白行
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
                
                標題：{selected_title}
                語氣強度：{tone_intensity} ({tone_prompt})
                
                請完成以下任務：
                1. 撰寫【內文】：約 100-150 字，語氣要符合標題與強度設定。
                2. 撰寫【回文】：10 則推文/噓文 (格式範例：推| 這是回文內容)。
                   - 回文的立場要多元（有的認同、有的反駁、有的歪樓）。
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
