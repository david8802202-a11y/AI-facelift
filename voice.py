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

if st.button("開始執行完整分析流程"):
    if raw_input:
        # A. 整理全文分類的 Prompt (針對格式進行強制優化)
        summary_prompt = f"""
        請針對以下輸入的網路言論進行分類，嚴格區分為「正向摘要」與「負向摘要」兩個區塊。
        
        【極重要規格要求】：
        1. 必須保留「完整的網友言論原文」，嚴禁改寫、縮減或摘要。
        2. 輸出格式必須嚴格遵守 Markdown 列表，每一則言論都要換行。
        3. 嚴禁使用 <font>、<span> 或任何 HTML 顏色標籤。
        4. 分類標題請使用 **【項目名稱】** (如 **【內容陣容】**、**【價格方案】**)。
        5. 請過濾掉明顯無關的廣告文案（如 7-11 活動、純網址），只保留針對影音平台的評價言論。
        
        【預期輸出範例】：
        ### **正向摘要**
        **【內容陣容】**
        * 星期五真的日劇很多，好強
        * 模範計程車 3 真的好讚~ 還好有訂 friday
        
        **【優惠方案】**
        * 剛兌換成功，感謝分享
        
        ### **負向摘要**
        **【App技術】**
        * app很不穩定，切換畫面就黑屏
        
        ---
        【待處理言論】：
        {raw_input}
        """
        
        with st.spinner(f'正在使用 {model_choice} 分類全文內容...'):
            try:
                response = model.generate_content(summary_prompt)
                summary_result = response.text
                
                st.divider()
                st.subheader("2. 口碑正負評完整摘要表")
                st.markdown(summary_result)

                # B. 綜合分析的 Prompt (保持不變，或稍微強調引用上述格式)
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
                    
            except Exception as e:
                st.error(f"分析過程發生錯誤：{e}")
