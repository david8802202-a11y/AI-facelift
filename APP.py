import streamlit as st
import google.generativeai as genai
import os

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V22 無敵版)", page_icon="🏆")

# --- 2. 讀取 API Key ---
api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🏆 PTT/Dcard 文案產生器 (V22 無敵版)")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. 動態抓取您的 54 個模型 (關鍵新功能) ---
@st.cache_resource
def get_my_models():
    working_models = []
    try:
        # 直接問 Google 這把鑰匙能用什麼
        for m in genai.list_models():
            # 只抓取能「寫作」的模型 (generateContent)
            if 'generateContent' in m.supported_generation_methods:
                working_models.append(m.name)
        return working_models
    except Exception as e:
        return []

# 執行抓取
my_models = get_my_models()

if not my_models:
    st.error("❌ 連線失敗，無法取得模型清單。請確認網路或 API Key。")
    st.stop()

# --- 4. 側邊欄：讓您自己選模型 ---
with st.sidebar:
    st.header("🤖 模型選擇")
    st.success(f"✅ 您的鑰匙成功抓到 {len(my_models)} 個可用模型！")
    
    # 這裡的選單內容，完全來自您的鑰匙權限，絕對不會 404
    selected_model_name = st.selectbox(
        "請選擇一個順眼的：", 
        my_models,
        index=0
    )
    st.caption("💡 建議優先選擇有 'flash' 或 'pro' 字眼的最新版模型。")

# 建立模型物件
model = genai.GenerativeModel(selected_model_name)

# --- 5. 初始化 Session State ---
if 'used_titles' not in st.session_state:
    st.session_state.used_titles = set()
if 'candidate_titles' not in st.session_state:
    st.session_state.candidate_titles = []

# --- 6. 系統提示詞 ---
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊 Facelift 版) 與 Dcard (醫美版) 的資深鄉民。
語氣必須非常「台式地氣」，模仿真實論壇的討論風格。

【關鍵詞彙】：平替、安慰劑、智商稅、黑科技、無底洞、訂閱制、饅化、塑膠感、蛇精臉、一分錢一分貨。
【標題風格】：反問法、強烈質疑、心得分享。
【回文格式】：每一則回文必須**獨立一行**，且包含 `推|`、`噓|`、`→|`。
"""

# --- 7. 介面區 ---
col1, col2 = st.columns(2)
with col1:
    user_topic = st.text_input("輸入主題：", "韓版電波是智商稅嗎？")
with col2:
    tone_intensity = st.select_slider("🔥 語氣強度：", ["溫和", "熱烈", "炎上"], value="熱烈")

if st.button("🚀 生成 5 個標題"):
    with st.spinner(f"正在使用 {selected_model_name} 發想中..."):
        try:
            prompt = f"""
            {SYSTEM_INSTRUCTION}
            主題：{user_topic}
            語氣：{tone_intensity}
            請發想 10 個標題，一行一個。
            """
            response = model.generate_content(prompt)
            titles = response.text.strip().split('\n')
            st.session_state.candidate_titles = [t.strip() for t in titles if t.strip()][:5]
        except Exception as e:
            st.error("❌ 生成失敗！")
            st.code(str(e))

# --- 8. 結果顯示與互動 ---
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

# --- 9. 內文生成 ---
if 'sel_title' in st.session_state:
    st.divider()
    st.markdown(f"### 📝 標題：{st.session_state.sel_title}")
    
    with st.expander("置入設定 (選填)"):
        is_promo = st.checkbox("開啟置入")
        prod_info = st.text_input("產品資訊", "營養師輕食魚油")

    if st.button("撰寫內文"):
        with st.spinner("撰寫中..."):
            p = f"{SYSTEM_INSTRUCTION}\n標題：{st.session_state.sel_title}\n主題：{user_topic}\n語氣：{tone_intensity}\n任務：1.內文(150字) 2.回文(10則)"
            if is_promo: p += f"\n置入推薦：{prod_info}"
            st.markdown(model.generate_content(p).text)
