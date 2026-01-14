import streamlit as st
import google.generativeai as genai
import os

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 V20", page_icon="🛡️")

# --- 2. 讀取 API Key ---
api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🛡️ PTT/Dcard 文案產生器 V20 (自動降級兼容版)")

if not api_key:
    st.error("❌ 找不到 API Key！請檢查 Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. 尋找能用的模型 (關鍵救星邏輯) ---
@st.cache_resource
def find_working_model():
    # 我們依序測試：最新的 -> 舊版穩定的
    candidate_models = [
        "models/gemini-1.5-flash", # 首選：新版快
        "models/gemini-pro",       # 備案：舊版 (相容性高)
        "gemini-pro"               # 備案：舊版簡寫
    ]
    
    placeholder = st.empty()
    placeholder.info("🔍 正在尋找適合您的模型，請稍候...")
    
    working_model = None
    
    for model_name in candidate_models:
        try:
            # 實彈測試
            model = genai.GenerativeModel(model_name)
            model.generate_content("Hi", generation_config={"max_output_tokens": 1})
            working_model = model_name
            break # 找到能用的就跳出
        except Exception:
            continue # 失敗就換下一個
            
    placeholder.empty()
    return working_model

# 執行檢測
final_model_name = find_working_model()

if not final_model_name:
    st.error("❌ 所有的模型都測試失敗。這通常代表 API Key 本身有問題 (例如是用 Vertex AI 申請的)，或者額度已滿。")
    st.stop()
else:
    # 顯示目前抓到的模型
    if "flash" in final_model_name:
        st.success(f"✅ 成功連線！使用模型：{final_model_name} (新版)")
    else:
        st.warning(f"⚠️ 環境較舊，已自動切換為相容模式：{final_model_name} (舊版)")

# 建立模型物件
model = genai.GenerativeModel(final_model_name)

# --- 4. 初始化 & 歷史標題 (V15 機制) ---
if 'used_titles' not in st.session_state:
    st.session_state.used_titles = set()
if 'candidate_titles' not in st.session_state:
    st.session_state.candidate_titles = []

blacklist_titles = set()
if os.path.exists("history.txt"):
    try:
        with open("history.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("["):
                    blacklist_titles.add(line.strip())
    except: pass

# --- 5. 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 設定")
    st.caption(f"目前運行模型：{final_model_name}")
    
    st.markdown("---")
    st.info(f"已載入 {len(blacklist_titles)} 筆歷史標題")
    
    uploaded_file = st.file_uploader("上傳歷史標題 .txt", type=['txt'])
    if uploaded_file:
        stringio = uploaded_file.getvalue().decode("utf-8")
        lines = stringio.splitlines()
        count = 0
        for l in lines:
            if l.strip().startswith("["):
                blacklist_titles.add(l.strip())
                count += 1
        st.success(f"已加入 {count} 筆！")
        
    if st.button("清除已使用紀錄"):
        st.session_state.used_titles = set()
        st.rerun()

# --- 6. 系統提示詞 ---
SYSTEM_INSTRUCTION = """
你是一個精通台灣 PTT (批踢踢實業坊 Facelift 版) 與 Dcard (醫美版) 的資深鄉民。
語氣必須非常「台式地氣」，模仿真實論壇的討論風格。

【關鍵詞彙】：平替、安慰劑、智商稅、黑科技、無底洞、訂閱制、饅化、塑膠感、蛇精臉、一分錢一分貨、腦波弱。
【標題風格】：反問法、強烈質疑、心得分享。
【回文格式】：每一則回文必須**獨立一行**，且包含 `推|`、`噓|`、`→|`。

【重要任務】：發想標題，絕對不要使用重複、老梗、或太像廣告的標題。
"""

# --- 7. 主畫面 ---
col1, col2 = st.columns(2)
with col1:
    input_method = st.radio("話題來源", ["醫美預設", "自訂輸入"])
    if input_method == "醫美預設":
        user_topic = st.selectbox("類別", ["醫美閒聊", "黑幕/話術", "電音波", "微整", "手術"])
    else:
        user_topic = st.text_input("輸入主題", "韓版電波是智商稅嗎？")

with col2:
    tone_intensity = st.select_slider("🔥 強度", ["溫和", "熱烈", "炎上"], value="熱烈")

if st.button("🚀 生成 5 個標題"):
    with st.spinner("正在發想中..."):
        try:
            prompt = f"""
            {SYSTEM_INSTRUCTION}
            主題：{user_topic}
            語氣：{tone_intensity}
            請發想 10 個標題，一行一個，不要編號。
            """
            response = model.generate_content(prompt)
            raw = response.text.strip().split('\n')
            
            clean = []
            for t in raw:
                t = t.strip()
                if not t: continue
                if t in st.session_state.used_titles: continue
                if t in blacklist_titles: continue
                clean.append(t)
            
            st.session_state.candidate_titles = clean[:5]
            if not clean: st.warning("標題全被過濾了，請重試。")
            
        except Exception as e:
            st.error(f"生成失敗：{e}")

# --- 8. 內文生成 ---
if st.session_state.candidate_titles:
    st.subheader("👇 選擇標題生成內文")
    for i, title in enumerate(st.session_state.candidate_titles):
        c1, c2 = st.columns([0.85, 0.15])
        with c1: st.code(title, language=None)
        with c2:
            if st.button("✨ 採用", key=f"btn_{i}"):
                st.session_state.sel_title = title
                st.session_state.used_titles.add(title)
                st.session_state.candidate_titles.pop(i)
                st.rerun()

if 'sel_title' in st.session_state:
    st.divider()
    st.markdown(f"### 📝 標題：{st.session_state.sel_title}")
    
    with st.expander("置入設定"):
        is_promo = st.checkbox("開啟置入")
        prod_info = st.text_input("產品資訊", "營養師輕食魚油")

    if st.button("撰寫內文"):
        with st.spinner("撰寫中..."):
            try:
                p = f"""
                {SYSTEM_INSTRUCTION}
                標題：{st.session_state.sel_title}
                主題：{user_topic}
                語氣：{tone_intensity}
                任務：1.內文(150字,分段) 2.回文(10則)
                """
                if is_promo: p += f"置入推薦：{prod_info}"
                st.markdown(model.generate_content(p).text)
            except Exception as e:
                st.error(str(e))
