# --- 請將生成標題的 try-except 區塊替換為此段 ---
    try:
        response = model.generate_content(prompt)
        
        # 檢查是否被安全機制過濾
        if response.candidates[0].finish_reason == 3: # SAFETY 封鎖
            st.error("🚫 內容被 Gemini 安全過濾器攔截：主題過於敏感或語氣過於激進。")
            st.stop()
            
        res = response.text.strip().split('\n')
        # ... 後續處理邏輯 ...
        
    except Exception as e:
        # 顯示真正的報錯訊息，不要只寫 API 繁忙
        st.error(f"❌ 發生錯誤：{str(e)}")
