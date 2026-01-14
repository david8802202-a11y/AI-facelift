import streamlit as st
import google.generativeai as genai
import random
import re

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 文案產生器 V59", page_icon="⚙️")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 核心資料庫 (嚴格依照您的 8 個檔案內容隔離) ---
DB = {
    "💉 針劑/微整": {
        "topics": ["玻尿酸填補淚溝", "肉毒瘦小臉", "降解酶凹陷風險", "耳垂招財針"],
        "keywords": "無底洞、訂閱制、饅化、降解酶會溶掉自己的肉、年費、溫水煮青蛙",
        "example_body": "針劑類才是真正的錢坑。肉毒玻尿酸一年維護費竟然要10幾萬！這根本是訂閱制，沒續費就打回原形。"
    },
    "⚡ 電音波/雷射": {
        "topics": ["鳳凰電波效果", "韓版電波平替", "皮秒雷射恢復期", "海芙音波痛感"],
        "keywords": "一分錢一分貨、安慰劑、平替、熱石按摩、鳳凰痛歸痛、存錢打音波",
        "example_body": "看到很多診所狂推韓版電波，價格大概只要1/3。韓版到底是真平替，還是只是打個心安的安慰劑?"
    },
    "🏥 醫美診所/黑幕": {
        "topics": ["諮詢師話術", "審美觀喪失", "海外醫美廣告", "價格不透明"],
        "keywords": "喪失判斷力、複製人、饅化臉、醫美成癮、容貌焦慮、像掃描機看瑕疵",
        "example_body": "自從入了醫美坑，審美觀壞掉了。看到路人第一眼就是像掃描機一樣看瑕疵。是不是忘記正常人類的樣子了?"
    },
    "🔪 整形手術": {
        "topics": ["隆乳手術心得", "隆鼻變納美人", "抽脂後遺症", "割雙眼皮失敗"],
        "keywords": "自然美女分不出來、失敗的整形、金錢的力量、一眼假、塑膠感、做得很高階",
        "example_body": "常聽到男生說不喜歡女生整形，喜歡自然的。但那些女神明明都有動過，只是做得很高階、沒有塑膠感而已。"
    }
}

# --- 3. 模型下拉挑選邏輯 ---
@st.cache_resource
def get_available_models():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 整理名稱方便閱讀
        clean_models = [m.replace('models/', '') for m in models]
        return clean_models
    except:
        return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]

with st.sidebar:
    st.header("⚙️ 模型設定")
    model_list = get_available_models()
    selected_model_name = st.selectbox("👇 挑選運作模型：", model_list, index=0)
    st.caption("💡 若發生『API 繁忙』，請嘗試切換至其他模型。")
    
    st.divider()
    st.info(f"目前鎖定模型：{selected_model_name}")

model = genai.GenerativeModel(selected_model_name)

# --- 4. 主介面 ---
if 'titles' not in st.session_state: st.session_state.titles = []

col1, col2 = st.columns(2)
with col1:
    tag = st.selectbox("標籤：", ["[討論]", "[問題]"])
    cat = st.selectbox("議題分類：", list(DB.keys()))
with col2:
    tone = st.select_slider("強度：", ["溫和", "熱烈", "炎上"], value="熱烈")

st.markdown("---")
imported = st.text_area("📝 匯入網友議題 (若有內容，AI會優先改寫此議題)：", height=100)

# --- 5. 生成標題 ---
if st.button("🚀 生成 5 個標題", use_container_width=True):
    # 主題硬性鎖定
    core = imported.strip() if imported.strip() else random.choice(DB[cat]["topics"])
    
    prompt = f"""你是一個 PTT 醫美版資深鄉民。
    針對主題「{core}」發想 5 個吸睛標題。
    規則：
    1. 格式必須是「{tag} 內容」。
    2. 內容鎖定在主題，禁止冒號，語氣口語。
    直接列出 5 個標題，一行一個。"""

    try:
        res = model.generate_content(prompt).text.strip().split('\n')
        # Python 後處理：清洗標籤，保證格式正確
        st.session_state.titles = [f"{tag} {re.sub(r'^.*?\]', '', t).strip()}" for t in res if t.strip()][:5]
    except:
        st.error("⚠️ API 繁忙或連線超時，請嘗試在左側選單切換模型，或再試一次。")

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
        with st.spinner("撰寫中..."):
            info = DB[cat]
            prompt = f"""你是一個 PTT 鄉民。
            模仿口吻："{info['example_body']}"
            常用關鍵字：{info['keywords']}
            
            請針對標題「{st.session_state.sel}」寫一篇 120 字文章。
            要求：第一人稱，禁止開頭問候，內容鎖定標題。
            並附上 8 則回文，格式「推|內容」。回文要酸、禁止問號。
            """
            
            try:
                raw_res = model.generate_content(prompt).text
                # 強制切割顯示
                st.subheader("內文：")
                body = raw_res.split("回文")[0].replace("內文", "").replace("：", "").strip()
                st.write(body.replace("\n", "  \n"))
                
                st.subheader("回文：")
                cmts = raw_res.split("回文")[-1].strip().split("\n")
                prefix = ["推", "推", "→", "→", "噓"]
                for c in cmts:
                    # 清洗回文並強制移除問號
                    c = re.sub(r'^[推噓→\|:\s\d\.-]+', '', c).strip().replace("?", "").replace("？", "")
                    if len(c) > 2:
                        st.write(f"{random.choice(prefix)}| {c}")
            except:
                st.error("⚠️ 撰寫失敗，請換個模型或再按一次。")
