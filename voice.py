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
