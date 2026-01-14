import streamlit as st
import google.generativeai as genai
import os

st.set_page_config(page_title="金鑰透視鏡", page_icon="🧐")
st.title("🧐 API Key 權限透視鏡")

# 1. 讀取 Key
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 尚未設定 Secrets！")
    st.stop()

# 顯示 Key 的前幾碼確認有沒有換新
st.info(f"🔑 目前使用的 Key：{api_key[:8]}... (請確認這是不是您剛申請的那把)")

genai.configure(api_key=api_key)

# 2. 測試：列出所有可用模型
st.write("正在詢問 Google 這把 Key 能看到哪些模型...")

try:
    # 這是最底層的查詢指令，直接問 Google "我有什麼權限？"
    models = list(genai.list_models())
    
    if len(models) == 0:
        st.error("❌ 連線成功，但這把 Key 的權限列表是空的！")
        st.warning("👉 這代表您申請 Key 時選到了「舊的/壞掉的專案」。請重新申請，務必選擇 **'Create in NEW project'**。")
    else:
        st.success(f"🎉 成功！這把 Key 可以存取 {len(models)} 個模型！")
        
        # 顯示模型清單
        model_names = [m.name for m in models]
        st.code(model_names)
        
        # 檢查有沒有我們需要的
        if "models/gemini-1.5-flash" in model_names:
            st.balloons()
            st.markdown("### ✅ 檢測通過！您的 Key 包含 `gemini-1.5-flash`！")
            st.markdown("現在您可以放心地把程式碼換回 **正式版** 了！")
        else:
            st.warning("⚠️ 雖然有連上，但清單裡沒看到 gemini-1.5-flash，可能需要用 gemini-pro。")

except Exception as e:
    st.error("❌ 連線發生錯誤 (無法列出清單)")
    st.code(str(e))
    
    if "400" in str(e) or "INVALID_ARGUMENT" in str(e):
        st.warning("💡 錯誤代碼 400：Key 的格式有錯，或專案權限未開通。")
    elif "404" in str(e):
        st.warning("💡 錯誤代碼 404：這把 Key 所屬的專案沒有開啟 'Generative Language API'。解決方法：申請 Key 時請選 **New Project**。")
