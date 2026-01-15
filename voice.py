import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 頁面配置
st.set_page_config(page_title="口碑全文分析系統", layout="wide")
st.title("📊 專案口碑智慧分析系統")
st.caption("議定規格：使用最新 Gemma 3 / Gemini 3 模型、原文分類、無顏色標籤")

# 2. API 配置
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("請在 Streamlit Secrets 中設定 GEMINI_API_KEY")

# 3. 模型選擇 (優先列出您指定的 gemma-3 系列)
st.sidebar.header("模型設定")
model_choice = st.sidebar.selectbox(
    "選擇模型：",
    [
        "gemma-3-27b-it",   # 您指定的 Gemma 3 系列 (27B 旗艦版)
        "gemma-3-12b-it",   # Gemma 3 中階版
        "gemma-3-4b-it",    # Gemma 3 輕量版
        "gemini-3-flash",   # 最新 Gemini 3 系列 (極速版)
        "gemini-3-pro-preview" # 最新 Gemini 3 系列 (專業預覽版)
    ],
    index=0,
    help="根據您的回饋，gemma-3 開頭的模型在此環境最為穩定。"
)

# 建立模型實例
try:
    model = genai.GenerativeModel(model_choice)
except Exception as e:
    st.error(f"模型初始化失敗：{e}")

# --- 步驟 1：內容分類 ---
st.subheader("1. 貼上專案言論內容")
raw_input = st.text_area("請輸入原始口碑資料：", height=250)

if st.button("開始執行完整分析流程"):
    if raw_input:
        summary_prompt = f"""
        請針對以下言論，區分為「正向摘要」與「負向摘要」。
        規格：
        1. 必須顯示「完整的言論原文」，嚴禁縮減或改寫。
        2. 嚴禁使用 <font> 或任何顏色標籤。
        3. 分類標題必須使用 **【項目名稱】** 格式。
        待處理言論：{raw_input}
        """
        
        with st.spinner(f'正在使用 {model_choice} 分類全文內容...'):
            try:
                response = model.generate_content(summary_prompt)
                summary_result = response.text
                st.divider()
                st.subheader("2. 口碑正負評完整摘要表")
                st.markdown(summary_result)

                # --- 綜合分析 ---
                analysis_prompt = f"請依據上述摘要，產出 100-150 字綜合分析。禁止顏色標籤。摘要內容：{summary_result}"
                analysis_response = model.generate_content(analysis_prompt)
                st.divider()
                st.subheader("3. 綜合分析 (100-150字)")
                st.info(analysis_response.text)
                st.caption(f"字數統計：{len(analysis_response.text)} 字")
            except Exception as e:
                st.error(f"分析過程出錯：{e}")

# --- 步驟 2：文字雲分析 ---
st.divider()
st.subheader("4. 文字雲分析")
uploaded_file = st.file_uploader("上傳文字雲圖片", type=["png", "jpg", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, width=700)
    if st.button("解讀文字雲"):
        wc_prompt = ["分析此文字雲，字數約 100 字，禁止顏色標籤。", img]
        with st.spinner('圖片分析中...'):
            try:
                wc_response = model.generate_content(wc_prompt)
                st.success(wc_response.text)
                st.caption(f"字數統計：{len(wc_response.text)} 字")
            except Exception as e:
                st.error(f"圖片分析失敗：{e}")
