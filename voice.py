import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 頁面配置與標題
st.set_page_config(page_title="口碑全文分析系統", layout="wide")
st.title("📊 專案口碑智慧分析系統")
st.caption("議定規格：下拉選擇模型、全文原文分類、無顏色標籤、粗體項目分類、字數限制分析")

# 2. API 配置 (從 Streamlit Secrets 讀取)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("請在 Streamlit Secrets 中設定 GEMINI_API_KEY")

# 3. 側邊欄：模型選擇選單
st.sidebar.header("系統設定")
model_choice = st.sidebar.selectbox(
    "選擇 Gemini 模型：",
    ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"],
    index=0,
    help="推薦使用 flash，速度最快且免費額度穩定。"
)
model = genai.GenerativeModel(model_choice)

# --- 步驟 1：輸入與分類 ---
st.subheader("1. 貼上專案言論內容")
raw_input = st.text_area("請輸入原始口碑資料：", height=250)

if st.button("開始執行完整分析流程"):
    if raw_input:
        # A. 整理全文分類的 Prompt
        summary_prompt = f"""
        請針對以下言論內容進行分析，並區分為「正向摘要」與「負向摘要」。
        
        規格要求：
        1. 摘要內容必須顯示「完整的正負向言論原文」，嚴禁縮減、改寫或摘要網友的原話。
        2. 嚴禁使用 <font> 或任何 HTML 顏色標籤。
        3. 分類標題必須使用 **【項目名稱】** 格式。
        4. 將原文原封不動地搬移到正確的分類項目下。
        
        待處理言論：
        {raw_input}
        """
        
        with st.spinner(f'正在使用 {model_choice} 分類全文內容...'):
            response = model.generate_content(summary_prompt)
            summary_result = response.text
            
        st.divider()
        st.subheader("2. 口碑正負評完整摘要表")
        st.markdown(summary_result)

        # B. 綜合分析的 Prompt (100-150 字)
        analysis_prompt = f"""
        請依據上述整理出的正負評原文，進行約 100-150 字的綜合分析。
        規格要求：
        1. 嚴禁使用顏色標籤。
        2. 字數必須嚴格控制在 100-150 字之間。
        3. 總結市場優勢、技術痛點與服務問題。
        
        摘要內容：
        {summary_result}
        """
        
        with st.spinner('正在進行深度分析...'):
            analysis_response = model.generate_content(analysis_prompt)
            st.divider()
            st.subheader("3. 綜合分析 (100-150字)")
            st.info(analysis_response.text)
            st.caption(f"字數統計：{len(analysis_response.text)} 字")

# --- 步驟 2：文字雲分析 ---
st.divider()
st.subheader("4. 文字雲圖片分析")
uploaded_file = st.file_uploader("上傳文字雲圖片", type=["png", "jpg", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, width=700)
    
    # C. 文字雲分析的 Prompt (約 100 字)
    wc_prompt = [
        "請分析這張文字雲圖片。規格要求：1. 字數約 100 字左右。2. 分析核心詞代表的反饋情緒。3. 禁止顏色標籤。",
        img
    ]
    
    if st.button("解讀文字雲"):
        with st.spinner('正在分析圖片內容...'):
            wc_response = model.generate_content(wc_prompt)
            st.success(wc_response.text)
            st.caption(f"字數統計：{len(wc_response.text)} 字")
