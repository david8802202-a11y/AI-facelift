import streamlit as st
import google.generativeai as genai
import os

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V25 實彈測試版)", page_icon="🥊")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🥊 PTT/Dcard 文案產生器 (V25 實彈測試版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 實彈射擊：找出第一個真的能用的模型 ---
@st.cache_resource
def find_first_working_model():
    # 顯示一個臨時狀態
    status = st.empty()
    status.info("🛡️ 正在為您逐一測試模型，尋找倖存者...")
    
    working_model = None
    
    try:
        # 1. 抓出所有名單
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 2. 優先排序：把通常比較穩的排前面測試，避免測到怪怪的模型
        # 順序：1.5-pro -> 1.0-pro -> 1.5-flash (因為您說flash不行) -> 其他
        def sort_key(name):
            if "gemini-1.5-pro" in name and "exp" not in name: return 0
            if "gemini-1.0-pro" in name: return 1
            if "gemini-pro" in name: return 2
            if "flash" in name: return 3
            return 4
            
        all_models.sort(key=sort_key)
        
        # 3. 逐一發射測試彈
        for model_name in all_models:
            try:
                # 建立模型
                test_model = genai.GenerativeModel(model_name)
                # 發送極短訊號
                test_model.generate_content("Hi", generation_config={"max_output_tokens": 1})
                
                # 如果這行沒報錯，代表它活著！
                working_model = model_name
                status.success(f"✅ 找到救星了！模型 `{working_model}` 測試通過，連線成功！")
                break # 找到一個就收工
            except:
                continue # 這個壞了，測下一個
                
    except Exception as e:
        status.error(f"嚴重錯誤：無法取得模型列表 ({e})")
        return None

    if not working_model:
        status.error("❌ 悲報：您的所有模型都無法通過測試 (全數陣亡)。")
    
    return working_model

# 執行測試 (只會跑一次)
final_model_name = find_first_working_model()

if not final_model_name:
    st.stop()

# --- 3. 建立確定能用的模型物件 ---
model = genai.GenerativeModel(final_model_name)

# --- 4. 介面與功能 (維持不變) ---
if 'used_titles' not in st.session_state: st.session_state.used_titles = set()
if 'candidate_titles' not in st.session_state: st.session_state.candidate_titles = []

with st.sidebar:
    st.header("🤖 目前使用模型")
