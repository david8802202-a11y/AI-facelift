import streamlit as st
import google.generativeai as genai
import random
import re

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美文案 V62", page_icon="💉")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 醫美情境字典 (絕對鎖定領域) ---
DB = {
    "💉 針劑/微整": {
        "context": "討論醫美微整。關鍵字：饅化、訂閱制、年費、錢坑、無底洞、降解酶。",
        "keywords": ["訂閱制", "饅化", "年費", "無底洞", "降解酶", "錢坑"],
        "example": "針劑類真的是錢坑，肉毒玻尿酸半年就要補一次，像訂閱制沒續費就打回原形。"
    },
    "⚡ 電音波/雷射": {
        "context": "討論電音波拉提。關鍵字：鳳凰電波、痛感、安慰劑、平替、熱石按摩。",
        "keywords": ["鳳凰", "安慰劑", "平替", "熱石按摩", "痛歸痛", "效果"],
        "example": "美國電波漲太兇，診所推韓版價格只有1/3。到底是真平替還是只是打心安的安慰劑？"
    },
    "🏥 醫美診所/黑幕": {
        "context": "討論診所黑幕。關鍵字：諮詢師、推銷、審美觀喪失、複製人、價格透明。",
        "keywords": ["諮詢師話術", "審美觀喪失", "複製人", "容貌焦慮", "黑幕"],
        "example": "入了醫美坑審美觀壞掉，看路人都在看瑕疵。是不是忘記正常人類長什麼樣了？"
    },
    "🔪 整形手術": {
        "context": "討論外科整形。關鍵字：納美人、副作用、金錢的力量、一眼假、高階醫美。",
        "keywords": ["一眼假", "納美人", "副作用", "修復期", "整形感"],
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
    st.info("💡 標題生成已加入『贅詞暴力過濾』邏輯")

model = genai.GenerativeModel(selected_model)

# --- 4. 主介面 ---
if 'titles' not in st.session_state: st.session_state.titles = []

col1, col2 = st.columns(2)
with col1:
    tag = st.selectbox("選擇標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題分類：", list(DB.keys()))
with col2:
    tone = st.select_slider("語氣強度：", ["溫和", "熱烈", "炎上"], value="熱烈")

st.markdown("---")
imported = st.text_area("📝 匯入網友原文 (選填)：", height=80, placeholder="貼上原文可讓 AI 進行二創改寫...")

# --- 5. 生成標題 ---
if st.button("🚀 生成 5 個標題", use_container_width=True):
    ctx = DB[cat]["context"]
    core = imported.strip() if imported.strip() else cat
    
    # 指令加入極度嚴格的格式警告
    prompt = f"""你現在是 PTT 醫美版資深鄉民。
    【重要指令】：
    1. 只輸出 5 個標題。
    2. 禁止包含『好的、沒問題、以下是、符合要求』等任何廢話開場白。
    3. 禁止使用編號 (如 1. 2.) 或符號開頭。
    4. 內容鎖定主題：{core}。禁止提到 3C 產品。
    5. 每行一個標題，禁止空行。語氣：{tone}。
    【情境參考】：{ctx}"""

    try:
        res = model.generate_content(prompt).text.strip().split('\n')
        
        final_list = []
        for t in res:
            t = t.strip()
            # 1. 物理刪除開場白贅詞
            if any(x in t for x in ["好的", "沒問題", "以下是", "符合您的要求", "吸睛標題"]):
                continue
            
            # 2. 強制清除所有標籤、編號、冒號、符號
            t = re.sub(r'^[\d\-\.\s\[\]討論問題心得閒聊黑特：:]+', '', t).strip()
            
            # 3. 確保標題有長度才加入
            if len(t) > 2:
                final_list.append(f"{tag} {t}")
        
        st.session_state.titles = final_list[:5]
        
    except:
        st.error("API 繁忙，請稍後重試")

# --- 6. 選擇與撰寫 ---
if st.session_state.titles:
    st.markdown("### 👇 選擇採用標題")
    for i, t in enumerate(st.session_state.titles):
        if st.button(t, key=f"t_{i}", use_container_width=True):
            st.session_state.sel = t
            st.session_state.titles = []
            st.rerun()

if 'sel' in st.session_state:
    st.divider()
    st.subheader(f"📝 {st.session_state.sel}")
    
    if st.button("✍️ 撰寫完整文案與推文"):
        with st.spinner("對齊語氣撰寫中..."):
            info = DB[cat]
            prompt = f"""你現在是 PTT 醫美版鄉民。
            【模仿範例】："{info['example']}"
            【關鍵字注入】：{", ".join(info['keywords'])}
            
            任務：針對標題「{st.session_state.sel}」寫一篇 130 字內文。
            要求：第一人稱，禁止開頭問候，語氣{tone}。
            附上 8 則回文，格式「推|內容」。禁止問號結尾。"""
            
            try:
                raw_res = model.generate_content(prompt).text
                st.subheader("內文：")
                # 簡單分段處理
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
                st.error("撰寫失敗，請重新按按鈕生成")
