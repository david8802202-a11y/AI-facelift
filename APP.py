import streamlit as st
import google.generativeai as genai

st.title("🔧 API 除錯檢測工具")

# 1. 讀取金鑰
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Streamlit Secrets 設定。")
    st.stop()
else:
    # 遮蔽部分金鑰以策安全
    masked_key = api_key[:5] + "*" * 10 + api_key[-2:]
    st.success(f"✅ 成功讀取 API Key: {masked_key}")

# 2. 測試連線與列出模型
st.write("正在嘗試連線到 Google 查詢可用模型...")

try:
    genai.configure(api_key=api_key)
    
    # 呼叫 list_models 看看這把鑰匙能看到什麼
    models = list(genai.list_models())
    
    st.write(f"🔍 搜尋到 {len(models)} 個可用模型：")
    
    found_flash = False
    
    for m in models:
        # 只顯示能產生內容的模型 (generateContent)
        if 'generateContent' in m.supported_generation_methods:
            st.code(f"model_name = '{m.name}'")
            if 'flash' in m.name:
                found_flash = True
    
    if found_flash:
        st.success("🎉 恭喜！您的 Key 可以使用 Flash 模型！請記下上面顯示的名稱（通常是 models/gemini-1.5-flash）")
    else:
        st.warning("⚠️ 您的 Key 似乎看不到 Flash 模型，請嘗試使用列表中的其他名稱。")

except Exception as e:
    st.error("❌ 連線失敗！原因如下：")
    st.error(e)
    st.markdown("""
    **常見失敗原因：**
    1. **API Key 無效**：請確認去 [Google AI Studio](https://aistudio.google.com/) 申請的是 **Create API key**。
    2. **區域限制**：極少數情況下，某些 IP 會被擋，但在台灣通常沒問題。
    3. **Secrets 格式錯誤**：請確認 Secrets 裡面沒有多餘的引號 (例如 `Key = "xxx"` 是對的，但 `Key = "'xxx'"` 會有錯)。
    """)
