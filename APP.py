import streamlit as st
import google.generativeai as genai
import os

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT醫美文案產生器 V6 (診斷版)", page_icon="🩺")

# --- 2. 讀取 API Key ---
api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🩺 V6 系統診斷模式")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Streamlit 的 Secrets 設定。")
    st.stop()
else:
    # 顯示 Key 的前幾碼，讓你確認有沒有貼錯 (例如貼到舊的)
    st.info(f"🔑 目前使用的 API Key 開頭：{api_key[:6]}...... (請確認這是不是你剛申請的那把)")

genai.configure(api_key=api_key)

# --- 3. 直球對決：指定使用 gemini-1.5-flash ---
# 這是目前 Google 最穩、免費額度最高的模型
MODEL_NAME = "gemini-1.5-flash"

st.write(f"正在嘗試連線到模型：**{MODEL_NAME}** ...")

try:
    model = genai.GenerativeModel(MODEL_NAME)
    # 發送一個測試訊號
    response = model.generate_content("Hi", generation_config={"max_output_tokens": 1})
    st.success("✅ 連線成功！系統運作正常。")
    
except Exception as e:
    st.error("❌ 連線失敗！請截圖以下的錯誤訊息：")
    st.code(str(e))
    
    # 幫你分析錯誤原因
    err_msg = str(e)
    if "404" in err_msg:
        st.warning("👉 原因分析：找不到模型。這通常是因為 `requirements.txt` 沒有設定 `google-generativeai>=0.7.2`，導致雲端用了舊版工具。")
    elif "429" in err_msg:
        st.warning("👉 原因分析：額度已滿 (Quota Exceeded)。請稍等一分鐘後再試，或是這把 Key 的免費額度真的用完了。")
    elif "400" in err_msg or "INVALID_ARGUMENT" in err_msg:
        st.warning("👉 原因分析：API Key 無效。可能複製時多複製了空白鍵，或少複製了字元。")
    elif "403" in err_msg:
        st.warning("👉 原因分析：權限不足。請確認 Key 是在 Google AI Studio 申請的，不是 GCP Vertex AI。")
    st.stop()

# --- 4. 如果上面沒報錯，才會顯示生成介面 ---

# 系統提示詞
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊) 與 Dcard 文化的資深鄉民，同時也是專業的醫美行銷文案寫手。

【格式嚴格要求】：
1. **標題分類**：所有標題必須包含分類標籤。例如 `[閒聊]`、`[討論]`、`[問題]`、`[心得]`。
2. **標題長度**：標題文字部分 (不含前面的分類標籤) 必須控制在 18 個繁體中文字以內。
3. **回文排版**：每一則回文都必須獨立換行。
"""

st.divider()
st.header("📝 文案生成區")

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

if st.button("🚀 生成標題"):
    with st.spinner('生成中...'):
        try:
            prompt = f"""
            {SYSTEM_INSTRUCTION}
            主題：{category}，語氣：{tone_intensity}。
            請發想 5 個 PTT 風格標題，需包含分類標籤，標題文字 18 字內，切角要多元。
            直接列出，一行一個。
            """
            response = model.generate_content(prompt)
            titles = response.text.strip().split('\n')
            st.session_state.generated_titles = [t.strip() for t in titles if t.strip()]
        except Exception as e:
            st.error(f"生成失敗：{e}")

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
                1. 內文 (150字)
                2. 10則回文 (推/噓/→)，每一則回文前務必換行。
                """
                if is_promotion and product_info:
                    content_prompt += f"需自然置入 3 則關於「{product_info}」的推薦回文。"
                
                response = model.generate_content(content_prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"生成失敗：{e}")
