import streamlit as st
import google.generativeai as genai
import os

st.set_page_config(page_title="API 除錯專用", page_icon="🔧")
st.title("🔧 API 連線診斷室")

# 1. 檢查 Key 是否存在
api_key = st.secrets.get("GOOGLE_API_KEY")

st.info("步驟 1：檢查環境設定...")
if not api_key:
    st.error("❌ 找不到 Key！請檢查 Secrets 設定 (變數名稱必須是 GOOGLE_API_KEY)")
    st.stop()
else:
    # 為了安全，只顯示前 5 碼
    masked_key = api_key[:5] + "..." + api_key[-3:]
    st.success(f"✅ 成功讀取到 Key：{masked_key}")

genai.configure(api_key=api_key)

# 2. 測試連線
st.info("步驟 2：測試連線 Google...")

if st.button("🚀 開始測試"):
    try:
        # 測試最基本的模型
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        response = model.generate_content("Hello", generation_config={"max_output_tokens": 5})
        st.balloons()
        st.success("🎉 恭喜！連線成功！模型可以用！")
        st.write("回傳內容：", response.text)
    except Exception as e:
        st.error("❌ 連線失敗！請截圖下方的錯誤訊息：")
        st.code(str(e)) # 這裡會印出真正的錯誤原因
        
        # 幫您分析錯誤原因
        err_msg = str(e)
        if "400" in err_msg:
            st.warning("💡 分析：400 錯誤通常代表 Key 無效。請確認 Key 是否複製完整，或是否在 Secrets 裡多按了空白鍵。")
        elif "404" in err_msg:
            st.warning("💡 分析：404 錯誤代表「找不到模型」。這 100% 是 requirements.txt 沒更新或沒 Reboot 造成的。")
        elif "429" in err_msg:
            st.warning("💡 分析：429 錯誤代表「額度爆了」。請換一個 Google 帳號申請新 Key。")
