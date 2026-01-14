import streamlit as st
import google.generativeai as genai
import random
import re

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 文案產生器 V56", page_icon="🛡️")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 深度結構化資料庫 (嚴格依照您的檔案內容) ---
DB = {
    "💉 針劑/微整": {
        "topics": ["玻尿酸填補淚溝", "肉毒瘦小臉", "降解酶凹陷風險", "耳垂招財針"],
        "examples": "主題關於針劑與微整，常提到：無底洞、訂閱制、饅化、降解酶會溶掉自己的肉。"
    },
    "⚡ 電音波/雷射": {
        "topics": ["鳳凰電波效果", "韓版電波平替", "皮秒雷射恢復期", "海芙音波痛感"],
        "examples": "主題關於電波雷射，常提到：一分錢一分貨、安慰劑、熱石按摩、鳳凰痛歸痛。"
    },
    "🏥 醫美診所/黑幕": {
        "topics": ["諮詢師話術", "審美觀喪失", "海外醫美廣告", "醫美糾紛處理"],
        "examples": "主題關於診所黑幕，常提到：喪失判斷力、複製人、饅化臉、法規限制。"
    },
    "🔪 整形手術": {
        "topics": ["隆乳手術心得", "隆鼻變納美人", "抽脂後遺症", "割雙眼皮失敗"],
        "examples": "主題關於整形手術，常提到：自然美女分不出來、失敗的整形、金錢的力量、一眼假。"
    }
}

# --- 3. 模型連線 (鎖定穩定版本) ---
@st.cache_resource
def get_stable_model():
    # 優先嘗試 1.5-pro，備選 1.5-flash
    return genai.GenerativeModel("gemini-1.5-flash")

model = get_stable_model()

# --- 4. 主介面 ---
if 'titles' not in st.session_state: st.session_state.titles = []

col1, col2 = st.columns(2)
with col1:
    tag = st.selectbox("選擇標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題分類：", list(DB.keys()))
with col2:
    tone = st.select_slider("強度設定：", ["溫和", "熱烈", "炎上"], value="熱烈")

st.markdown("---")
imported = st.text_area("📝 匯入網友議題 (若有貼入，AI會以此核心改寫)：", height=100)

# --- 5. 生成標題 ---
if st.button("🚀 生成 5 個標題", use_container_width=True):
    # 決定核心主題
    core = imported.strip() if imported.strip() else random.choice(DB[cat]["topics"])
    ref_style = DB[cat]["examples"]
    
    prompt = f"""你是一個 PTT 醫美版鄉民。
    【風格指南】：{ref_style}
    
    【任務】：針對「{core}」寫 5 個標題。
    【規則】：
    1. 內容**必須鎖定**在「{core}」，禁止寫到其他分類的內容！
    2. 禁止在內容中包含 [討論] 等標籤，禁止冒號。
    3. 語氣直白、像真人。
    
    直接列出 5 個標題，一行一個。"""

    try:
        res = model.generate_content(prompt).text.strip().split('\n')
        # Python 強制修正標籤與格式
        st.session_state.titles = [f"{tag} {re.sub(r'^.*?\]', '', t).strip()}" for t in res if t.strip()][:5]
    except:
        st.error("API 暫時繁忙，請再按一次按鈕")

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
    
    if st.button("✍️ 撰寫完整內文與推文"):
        with st.spinner("正在生成中..."):
            ref_style = DB[cat]["examples"]
            
            prompt = f"""你是一個 PTT 鄉民。
            【風格風格】：{ref_style}
            
            現在請寫：
            標題：{st.session_state.sel}
            素材：{imported if imported else st.session_state.sel}
            
            要求：
            1. 內文 120 字，口語化，第一人稱，禁止開頭問候。
            2. **內容鎖定**：必須針對標題寫。標題是手術就寫手術，禁止寫電波或針劑！
            3. 回文 8 則。格式「推|內容」。
            4. **禁止使用問號 (?) 結尾**。鄉民是來噴人的，不是來問問題的。
            
            格式請明確標示「內文：」與「回文：」。"""
            
            try:
                raw_res = model.generate_content(prompt).text
                parts = raw_res.split("回文")
                body = parts[0].replace("內文", "").replace("：", "").strip()
                
                st.markdown("#### 內文：")
                st.write(body.replace("\n", "  \n"))
                
                st.markdown("#### 回文：")
                cmts = parts[-1].strip().split("\n")
                prefix = ["推", "推", "→", "→", "噓"]
                for c in cmts:
                    # 清洗回文內容並移除問號
                    c = re.sub(r'^[推噓→\|:\s\d\.-]+', '', c).strip()
                    c = c.replace("?", "").replace("？", "")
                    if len(c) > 2:
                        st.write(f"{random.choice(prefix)}| {c}")
            except:
                st.error("連線超時，請點擊按鈕重試")
