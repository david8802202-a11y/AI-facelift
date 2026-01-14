import streamlit as st
import google.generativeai as genai
import random
import re

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美文案 V61", page_icon="💉")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 醫美情境字典 (鎖定領域防止幻覺) ---
DB = {
    "💉 針劑/微整": {
        "context": "醫美微整形，包含肉毒、玻尿酸、水光針。關鍵字：饅化、訂閱制、錢坑、無底洞、降解酶。",
        "keywords": ["訂閱制", "饅化", "無底洞", "降解酶", "錢坑", "一分錢一分貨"],
        "example": "針劑類真的是錢坑，肉毒玻尿酸半年就要補，像訂閱制沒續費就打回原形。"
    },
    "⚡ 電音波/雷射": {
        "context": "醫美拉提療程，包含鳳凰電波、海芙音波、皮秒雷射。關鍵字：鳳凰、痛感、安慰劑、平替、熱石按摩。",
        "keywords": ["鳳凰", "安慰劑", "平替", "熱石按摩", "痛歸痛", "存錢打音波"],
        "example": "美國電波漲太兇，診所推韓版價格1/3。到底是真平替還是只是打心安的安慰劑？"
    },
    "🏥 醫美診所/黑幕": {
        "context": "醫美界潛規則與亂象。關鍵字：諮詢師、推銷、審美觀喪失、複製人、價格不透明。",
        "keywords": ["諮詢師話術", "審美觀喪失", "複製人", "容貌焦慮", "法規限制"],
        "example": "入了醫美坑審美觀壞掉，看路人都在看瑕疵。是不是忘記正常人類長怎樣了？"
    },
    "🔪 整形手術": {
        "topics": ["隆乳", "隆鼻", "抽脂", "雙眼皮"],
        "context": "侵入性外科整形手術。關鍵字：納美人、副作用、金錢的力量、一眼假、高階醫美。",
        "keywords": ["一眼假", "納美人", "副作用", "修復期", "金錢的力量"],
        "example": "直男討厭的是失敗的整形。那些女神明明都有動，只是做得很高階、沒有塑膠感。"
    }
}

# --- 3. 模型下拉選擇 ---
@st.cache_resource
def get_models():
    try:
        m_list = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return m_list
    except:
        return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]

with st.sidebar:
    st.header("⚙️ 設定選單")
    selected_model = st.selectbox("👇 挑選模型：", get_models(), index=0)
    st.info(f"當前模式：醫美領域絕對鎖定")

model = genai.GenerativeModel(selected_model)

# --- 4. 主介面 ---
if 'titles' not in st.session_state: st.session_state.titles = []

col1, col2 = st.columns(2)
with col1:
    tag = st.selectbox("標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題：", list(DB.keys()))
with col2:
    tone = st.select_slider("強度：", ["溫和", "熱烈", "炎上"], value="熱烈")

st.markdown("---")
imported = st.text_area("📝 匯入網友原文 (選填)：", height=80, placeholder="貼上內容可讓 AI 進行二創改寫...")

# --- 5. 生成標題 ---
if st.button("🚀 生成 5 個標題", use_container_width=True):
    ctx = DB[cat]["context"]
    core = imported.strip() if imported.strip() else (random.choice(DB[cat].get("topics", [cat])))
    
    # 絕對情境鎖定 Prompt
    prompt = f"""你現在是 PTT Facelift (醫美) 版的資深鄉民。
    【重要背景】：這是一個討論「整形醫美療程」的版面。禁止提到手機、耳機、音響等 3C 產品。
    【情境】：{ctx}
    【任務】：針對「{core}」寫 5 個吸睛標題。
    【要求】：格式為「{tag} 標題」，禁止冒號，長度 18 字內。語氣要酸、直白。
    一行一個。"""

    try:
        res = model.generate_content(prompt).text.strip().split('\n')
        st.session_state.titles = [f"{tag} {re.sub(r'^.*?\]', '', t).strip()}" for t in res if t.strip()][:5]
    except:
        st.error("API 繁忙，請稍後重試")

# --- 6. 選擇與撰寫 ---
if st.session_state.titles:
    st.markdown("### 👇 選擇標題")
    for i, t in enumerate(st.session_state.titles):
        if st.button(t, key=f"t_{i}", use_container_width=True):
            st.session_state.sel = t
            st.session_state.titles = []
            st.rerun()

if 'sel' in st.session_state:
    st.divider()
    st.subheader(f"📝 {st.session_state.sel}")
    
    if st.button("✍️ 撰寫內容與推文"):
        with st.spinner("情境對齊中..."):
            info = DB[cat]
            prompt = f"""你現在是 PTT 醫美版鄉民，禁止寫成 3C 產品評論。
            【模仿口吻】："{info['example']}"
            【必用關鍵字】：{", ".join(info['keywords'])}
            
            任務：針對標題「{st.session_state.sel}」寫一篇 120 字內文。
            要求：
            1. 第一人稱，鎖定醫美話題，禁止提到手機、耳機。
            2. 語氣：{tone}。不要開頭問候。
            3. 附上 8 則回文，格式「推|內容」。禁止問號。
            """
            
            try:
                raw_res = model.generate_content(prompt).text
                st.subheader("內文：")
                # 簡單分段顯示
                body = raw_res.split("回文")[0].replace("內文", "").replace("：", "").strip()
                st.write(body.replace("\n", "  \n"))
                
                st.subheader("回文：")
                cmts = raw_res.split("回文")[-1].strip().split("\n")
                prefix = ["推", "推", "→", "→", "噓", "推"]
                for c in cmts:
                    c = re.sub(r'^[推噓→\|:\s\d\.-]+', '', c).strip().replace("?", "").replace("？", "")
                    if len(c) > 2:
                        st.write(f"{random.choice(prefix)}| {c}")
            except:
                st.error("撰寫失敗，請重新嘗試")
