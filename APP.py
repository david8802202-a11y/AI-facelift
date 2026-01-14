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
    st.code(final_model_name)
    st.caption("這是系統實測後，第一個能正常回應的模型。")

# --- 5. 提示詞與輸入 ---
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊 Facelift 版) 與 Dcard (醫美版) 的資深鄉民。
語氣必須非常「台式地氣」，模仿真實論壇的討論風格。
關鍵詞：平替、安慰劑、智商稅、黑科技、無底洞、訂閱制、饅化、塑膠感。
標題風格：反問法、強烈質疑、心得分享。
回文格式：每一則回文必須**獨立一行**，且包含 `推|`、`噓|`、`→|`。
"""

col1, col2 = st.columns(2)
with col1:
    user_topic = st.text_input("輸入主題：", "韓版電波是智商稅嗎？")
with col2:
    tone_intensity = st.select_slider("🔥 語氣強度：", ["溫和", "熱烈", "炎上"], value="熱烈")

if st.button("🚀 生成 5 個標題"):
    with st.spinner(f"正在使用 {final_model_name} 生成..."):
        try:
            prompt = f"{SYSTEM_INSTRUCTION}\n主題：{user_topic}\n語氣：{tone_intensity}\n請發想 10 個標題，一行一個。"
            response = model.generate_content(prompt)
            titles = response.text.strip().split('\n')
            st.session_state.candidate_titles = [t.strip() for t in titles if t.strip()][:5]
        except Exception as e:
            st.error("❌ 生成失敗 (即便測試通過，生成時仍發生錯誤)")
            st.code(str(e))

# --- 6. 結果顯示 ---
if st.session_state.candidate_titles:
    st.subheader("👇 生成結果")
    for i, t in enumerate(st.session_state.candidate_titles):
        c1, c2 = st.columns([0.85, 0.15])
        with c1: st.code(t, language=None)
        with c2:
            if st.button("採用", key=f"btn_{i}"):
                st.session_state.sel_title = t
                st.session_state.candidate_titles = []
                st.rerun()

if 'sel_title' in st.session_state:
    st.divider()
    st.markdown(f"### 📝 標題：{st.session_state.sel_title}")
    
    with st.expander("置入設定"):
        is_promo = st.checkbox("開啟置入")
        prod_info = st.text_input("產品資訊", "營養師輕食魚油")

    if st.button("撰寫內文"):
        with st.spinner("撰寫中..."):
            p = f"{SYSTEM_INSTRUCTION}\n標題：{st.session_state.sel_title}\n主題：{user_topic}\n語氣：{tone_intensity}\n任務：1.內文(150字) 2.回文(10則)"
            if is_promo: p += f"\n置入推薦：{prod_info}"
            st.markdown(model.generate_content(p).text)
