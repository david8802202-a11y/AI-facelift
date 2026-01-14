import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="模型偵測器", page_icon="🕵️")

st.title("🕵️ Google Gemini 模型偵測器")
st.write("我們不要猜了，直接問 Google 你的 API Key 能用誰。")

# 1. 讀取金鑰
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Secrets 設定。")
    st.stop()

# 2. 顯示金鑰前幾碼 (確認有沒有讀錯)
st.info(f"🔑 目前使用的 API Key 開頭是：{api_key[:5]}...")

# 3. 測試連線
genai.configure(api_key=api_key)

if st.button("🔍 開始掃描可用模型"):
    try:
        st.write("正在連線到 Google 伺服器...")
        
        # 呼叫 Google 列表 API
        models_list = list(genai.list_models())
        
        valid_models = []
        for m in models_list:
            # 只找可以「生成內容」的模型
            if 'generateContent' in m.supported_generation_methods:
                valid_models.append(m.name)

        if valid_models:
            st.success(f"🎉 連線成功！找到 {len(valid_models)} 個可用模型：")
            st.markdown("請直接複製下面其中一個名稱（推薦選 flash）：")
            
            for name in valid_models:
                st.code(f"model = genai.GenerativeModel('{name}')")
                # 這裡直接列出代碼讓你複製
        else:
            st.warning("⚠️ 連線成功，但你的 Key 似乎沒有權限存取任何生成模型。")
            
    except Exception as e:
        st.error("❌ 連線失敗！錯誤訊息如下：")
        st.error(e)
        st.markdown("""
        **可能原因：**
        1. **API Key 是壞的**：請去 [Google AI Studio](https://aistudio.google.com/) 重新產生一把。
        2. **未開通權限**：如果是用 Google Cloud Console 申請的，可能沒開通 Vertex AI API。請務必使用 **AI Studio** 申請的 Key。
        """)
