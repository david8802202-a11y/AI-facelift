import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 頁面配置
st.set_page_config(page_title="口碑全文分析系統", layout="wide")
st.title("📊 專案口碑智慧分析系統 (全文版)")
st.caption("議定規格：正負向摘要顯示完整言論、無顏色標籤、粗體項目分類、字數限制分析")

# 2. API 配置
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-pro')
else:
    st.error("請在 Streamlit Secrets 中設定 GEMINI_API_KEY")

# --- 步驟 1：輸入區域 ---
st.subheader("1. 貼上專案言論內容")
raw_input = st.text_area("請輸入原始口碑資料：", height=250, placeholder="在此貼上網友原始言論...")

if st.button("開始執行完整分析流程"):
    if raw_input:
        # A. 整理完整正負評言論的 Prompt (要求保留全文)
        summary_prompt = f"""
        請針對以下言論內容進行分析，並區分為「正向摘要」與「負向摘要」。
        
        規格要求（極重要）：
        1. 摘要內容必須顯示「完整的正負向言論原文」，嚴禁縮減、改寫或摘要網友的原話。
        2. 嚴禁使用 <font> 或任何 HTML 顏色標籤。
        3. 分類標題必須使用 **【項目名稱】** 格式。
        4. 請將性質相近的「完整原文」歸類在同一個項目標題下。
        
        待處理言論：
        {raw_input}
        """
        
        with st.spinner('正在分類完整言論內容...'):
            response = model.generate_content(summary_prompt)
            summary_result = response.text
            
        st.divider()
        st.subheader("2. 口碑正負評完整摘要表")
        st.markdown(summary_result)

        # B. 綜合分析的 Prompt (字數限制 100-150 字)
        analysis_prompt = f"""
        請依據上述整理出的正負評言論，進行約 100-150 字的綜合分析。
        規格要求：
        1. 嚴禁使用顏色標籤。
        2. 字數必須嚴格控制在 100-150 字之間。
        3. 請針對市場優勢、技術痛點與服務問題進行總結。
        
        摘要內容：
        {summary_result}
        """
        
        with st.spinner('正在進行深度綜合分析...'):
            analysis_response = model.generate_content(analysis_prompt)
            st.divider()
            st.subheader("3. 綜合分析 (100-150字)")
            st.info(analysis_response.text)
            st.caption(f"字數統計：{len(analysis_response.text)} 字")

# --- 步驟 2：文字雲上傳與分析 ---
st.divider()
st.subheader("4. 文字雲分析")
uploaded_file = st.file_uploader("上傳文字雲圖片", type=["png", "jpg", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, width=700)
    
    # C. 文字雲分析的 Prompt (約 100 字)
    wc_prompt = [
        "請分析這張文字雲圖片。規格要求：1. 字數控制在約 100 字左右。2. 分析核心詞彙代表的市場反饋與情緒。3. 禁止使用任何顏色標籤。",
        img
    ]
    
    if st.button("解讀文字雲意義"):
        with st.spinner('正在分析文字雲圖示...'):
            wc_response = model.generate_content(wc_prompt)
            st.success(wc_response.text)
            st.caption(f"字數統計：{len(wc_response.text)} 字")
