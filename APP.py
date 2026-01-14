import streamlit as st
import google.generativeai as genai
import importlib.metadata
import os

st.set_page_config(page_title="V21 終極診斷", page_icon="🚑")
st.title("🚑 V21 系統健康檢查")

# --- 1. 檢查工具包版本 (關鍵！) ---
try:
    lib_version = importlib.metadata.version('google-generativeai')
    st.info(f"📦 目前安裝的 AI 工具包版本：{lib_version}")
    
    # 判斷版本是否合格
    if lib_version < "0.7.2":
        st.error(f"❌ 版本過舊！您需要 0.7.2 以上，但您只有 {lib_version}")
        st.warning("👉 請務必更新 requirements.txt 並重啟 App！")
    else:
        st.success("✅ 版本合格！(至少工具包是新的)")
except:
    st.error("❌ 無法偵測版本，環境嚴重損壞。")

# --- 2. 檢查 API Key ---
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("❌ Secrets 裡找不到 GOOGLE_API_KEY")
    st.stop()

# 檢查 Key 格式
if not api_key.startswith("AIza"):
    st.warning("⚠️ 警告：您的 Key 不是以 'AIza' 開頭！")
    st.warning("這代表您可能用到 GCP Service Account 或其他類型的 Key，這會導致連線失敗。")
    st.markdown("[請點此去申請正確的 Key (Google AI Studio)](https://aistudio.google.com/app/apikey)")
else:
    st.success("✅ Key 格式正確 (AIza 開頭)")

genai.configure(api_key=api_key)

# --- 3. 實彈射擊測試 (印出詳細錯誤) ---
st.divider()
st.subheader("🔫 模型連線測試")

models_to_test = ["models/gemini-1.5-flash", "models/gemini-pro"]

for m in models_to_test:
    st.write(f"正在測試：`{m}` ...")
    try:
        model = genai.GenerativeModel(m)
        response = model.generate_content("Hi", generation_config={"max_output_tokens": 1})
        st.success(f"🎉 {m} 連線成功！")
    except Exception as e:
        st.error(f"❌ {m} 失敗")
        # 這是最重要的部分，印出真實錯誤
        st.code(str(e))
