import streamlit as st

# 設定網頁標題與風格
st.set_page_config(page_title="口碑分析工具", layout="wide")

st.title("📊 專案口碑智慧分析系統")
st.caption("議定規格：無顏色標籤、粗體項目分類、字數限制分析")

# --- 第一步：貼上言論內容 ---
st.subheader("1. 貼上專案言論內容")
raw_text = st.text_area("請輸入原始口碑資料：", height=200, placeholder="在此貼上 PTT/Dcard 內容...")

if st.button("開始執行分析流程"):
    if raw_text:
        # --- 第二步：整理正負評摘要 (模擬 AI 產出) ---
        st.divider()
        st.subheader("2. 口碑正負評摘要表")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### **正向摘要**")
            # 依照議定格式：粗體項目分類
            st.markdown("""
            **【內容陣容】**
            * 獨家劇集更新穩定且內容豐富。
            * 翻譯品質受網友高度認同，優於其他平台。
            
            **【優惠/方案】**
            * VIP 天數疊加機制對老用戶非常友善。
            """)
            
        with col2:
            st.markdown("### **負向摘要**")
            st.markdown("""
            **【App/技術】**
            * App 穩定性待加強，經常出現轉圈或黑屏。
            * 電視端播放 4K 內容畫質不如預期。
            """)

        # --- 第三步：摘要分析 ---
        st.divider()
        st.subheader("3. 綜合分析 (100-150字)")
        # 這裡未來可串接 Gemini API 生成內容
        analysis_text = "根據口碑摘要分析，該平台的核心競爭力在於強大的日韓劇陣容與優於競品的翻譯品質，尤其 VIP 疊加機制與異業贈送方案成功建立了高 CP 值的品牌形象。然而，技術層面的 App 穩定性與 4K 畫質模糊是主要負評痛點。此外，退訂流程設計過於隱晦，結合電信綁約產生的爭議，成為服務端亟待優化的核心問題。"
        st.info(analysis_text)
        st.write(f"當前字數：{len(analysis_text)} 字")

# --- 第四步：貼上文字雲與分析 ---
st.divider()
st.subheader("4. 貼上文字雲分析")
uploaded_file = st.file_uploader("請上傳文字雲圖片：", type=["png", "jpg", "jpeg"])

if uploaded_file:
    st.image(uploaded_file, caption="已上傳之文字雲", width=500)
    
    st.subheader("文字雲分析報告 (約100字)")
    # 模擬文字雲分析內容
    wc_analysis = "此文字雲顯現出『平台』與『影音』為討論核心，反映網友對收視體驗的高度關注。『獨家』與『上架』字眼頻繁出現，呼應了平台以強檔內容帶動熱度的正向評價。同時，『期限』與『合約』的出現，則顯示出用戶對訂閱制度與資費變動的負面疑慮。整體雲圖呈現出內容拉動力強，但合約透明度仍有改善空間的現況。"
    st.success(wc_analysis)
    st.write(f"當前字數：{len(wc_analysis)} 字")
