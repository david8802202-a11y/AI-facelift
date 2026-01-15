import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 頁面配置
st.set_page_config(page_title="口碑全文分析系統", layout="wide")
st.title("📊 專案口碑智慧分析系統")
st.caption("議定規格：品牌聚焦過濾、Gemma 3 模型、原文去重分類、無顏色標籤")

# 2. API 配置
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("請在 Streamlit Secrets 中設定 GEMINI_API_KEY")

# 3. 模型選擇
st.sidebar.header("模型設定")
model_choice = st.sidebar.selectbox(
    "選擇模型：",
    [
        "gemma-3-27b-it",   # 推薦：處理長文本與去重能力較佳
        "gemma-3-12b-it",
        "gemma-3-4b-it",
        "gemini-3-flash",
        "gemini-3-pro-preview"
    ],
    index=0,
    help="Gemma 3 27B 對於過濾無關資訊與去重的指令遵循度較高。"
)

try:
    model = genai.GenerativeModel(model_choice)
except Exception as e:
    st.error(f"模型初始化失敗：{e}")

# --- 步驟 1：內容分類 ---
st.subheader("1. 輸入資料與品牌設定")

# [新增功能] 品牌鎖定
col1, col2 = st.columns([1, 3])
with col1:
    target_brand = st.text_input("輸入要分析的品牌 (必填)：", placeholder="例如：Hami Video")
with col2:
    st.info("💡 系統將只提取與此品牌相關的評價，並自動過濾無關廣告與競品雜訊。")

raw_input = st.text_area("請輸入原始口碑資料：", height=250, placeholder="在此貼上 PTT/Dcard 討論串...")

if st.button("開始執行完整分析流程"):
    if raw_input and target_brand:
        # A. 整理全文分類的 Prompt (已針對品牌鎖定與去重進行強化)
        summary_prompt = f"""
        請針對以下輸入的網路言論進行清洗與分類。
        
        【分析目標】：
        專注於分析品牌 **「{target_brand}」** 的相關評價。
        
        【極重要規格要求】：
        1. **品牌聚焦**：只提取與 **「{target_brand}」** 直接相關的評價。若言論是在討論毫不相關的內容（如 7-11 活動、其他無關新聞），請直接忽略不計。
        2. **嚴格去重**：若有多則內容完全相同或高度相似的推文（例如重複的 "Hami棒棒"），**請只保留一條**，不要重複列出。
        3. **保留原文**：在符合上述兩點的前提下，請保留網友的「完整原話」，不要縮寫。
        4. **格式規範**：
           - 嚴格區分為「正向摘要」與「負向摘要」。
           - 使用 Markdown 列表 (* ) 開頭，確保換行。
           - 分類標題使用 **【項目名稱】**。
           - 嚴禁使用 HTML 顏色標籤。
        
        【待處理言論】：
        {raw_input}
        """
        
        with st.spinner(f'正在鎖定 {target_brand} 進行雜訊過濾與分析...'):
            try:
                # 執行分類
                response = model.generate_content(summary_prompt)
                summary_result = response.text
                
                st.divider()
                st.subheader(f"2. {target_brand} 口碑正負評摘要表")
                st.markdown(summary_result)

                # B. 綜合分析 (100-150 字)
                analysis_prompt = f"""
                請依據上述整理出的 {target_brand} 正負評原文，進行約 100-150 字的綜合分析。
                
                規格要求：
                1. 嚴禁使用顏色標籤。
                2. 字數必須嚴格控制在 100-150 字之間。
                3. 請針對該品牌的市場優勢、技術痛點與服務問題進行總結。
                
                摘要內容：
                {summary_result}
                """
                
                analysis_response = model.generate_content(analysis_prompt)
                st.divider()
                st.subheader("3. 綜合分析 (100-150字)")
                st.info(analysis_response.text)
                st.caption(f"字數統計：{len(analysis_response.text)} 字")
                
            except Exception as e:
                st.error(f"分析過程出錯：{e}")
    else:
        st.warning("⚠️ 請務必輸入「品牌名稱」與「口碑資料」才能開始分析。")

# --- 步驟 2：文字雲分析 ---
st.divider()
st.subheader("4. 文字雲分析")
uploaded_file = st.file_uploader("上傳文字雲圖片", type=["png", "jpg", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, width=700)
    
    if st.button("解讀文字雲"):
        # 加入品牌名稱作為背景知識
        wc_brand_context = target_brand if target_brand else "影音平台"
        wc_prompt = [
            f"請分析這張關於「{wc_brand_context}」的文字雲圖片。規格要求：1. 字數約 100 字左右。2. 分析核心詞代表的市場情緒。3. 禁止顏色標籤。",
            img
        ]
        with st.spinner('圖片分析中...'):
            try:
                wc_response = model.generate_content(wc_prompt)
                st.success(wc_response.text)
                st.caption(f"字數統計：{len(wc_response.text)} 字")
            except Exception as e:
                st.error(f"圖片分析失敗：{e}")
