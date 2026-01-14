import streamlit as st
import google.generativeai as genai
import random
import re

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V53 終極修正版)", page_icon="⚖️")

api_key = st.secrets.get("GOOGLE_API_KEY")
st.title("⚖️ PTT/Dcard 文案產生器 (V53)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 核心子題庫 (確保內容不跑掉) ---
SUBTOPICS = {
    "💉 針劑/微整": ["肉毒瘦臉", "玻尿酸補淚溝", "舒顏萃", "水光針心得"],
    "⚡ 電音波/雷射": ["鳳凰電波", "海芙音波", "皮秒雷射", "索夫波"],
    "🏥 醫美診所/黑幕": ["諮詢師一直推銷", "診所價格水很深", "醫生技術好壞", "醫美糾紛"],
    "🔪 整形手術": ["隆乳手術心得", "隆鼻變納美人", "抽脂後遺症", "割雙眼皮失敗"],
    "✍️ 自訂主題": ["醫美討論"]
}

# --- 3. 語氣資料庫 (拿掉具體療程，防止 AI 亂抄內容) ---
TONE_EXAMPLES = [
    "標題：[討論] 某療程根本是無底洞...算完錢嚇死人",
    "標題：[討論] 聽說某個手術會連自己的肉一起壞掉?",
    "標題：[問題] 為了面相招財去打某個針劑?"
]

# --- 4. 模型抓取 ---
@st.cache_resource
def get_working_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 優先順序：Pro > Flash > Gemma
        for m_name in ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro", "gemma"]:
            for m in models:
                if m_name in m: return m
        return models[0]
    except: return "models/gemini-pro"

current_model = get_working_model()
model = genai.GenerativeModel(current_model)

# --- 5. 主介面 ---
if 'candidate_titles' not in st.session_state: st.session_state.candidate_titles = []

st.sidebar.info(f"運作中模型：{current_model}")

col1, col2 = st.columns(2)
with col1:
    ptt_tag = st.selectbox("標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    topic_category = st.selectbox("分類：", list(SUBTOPICS.keys()))
    
    # 決定核心主題
    if "自訂" in topic_category:
        user_topic = st.text_input("輸入主題：", "韓版電波是智商稅嗎？")
        final_topic = user_topic
    else:
        random_sub = random.choice(SUBTOPICS[topic_category])
        final_topic = random_sub

with col2:
    tone_intensity = st.select_slider("強度：", ["溫和", "熱烈", "炎上"], value="熱烈")

st.markdown("---")
imported_text = st.text_area("📝 匯入網友原文 (若有，AI會以此核心改寫)：", height=100)

# --- 6. 生成標題 ---
if st.button("🚀 生成 5 個標題", use_container_width=True):
    # 決定素材
    subject = imported_text if len(imported_text.strip()) > 5 else final_topic
    
    prompt = f"""你是一個 PTT 醫美版資深鄉民。
    【語氣參考】：{TONE_EXAMPLES}
    
    【任務】：針對「{subject}」發想 5 個標題。
    【規則】：
    1. **內容鎖定**：你必須只寫關於「{subject}」的內容，禁止寫到其他手術或雷射！
    2. **格式要求**：不要包含 [討論] 或 [問題] 標籤。
    3. **風格**：直白、口語、要有真人感。禁止冒號。
    
    直接列出 5 個純文字標題，一行一個。"""
    
    try:
        response = model.generate_content(prompt).text.strip().split('\n')
        clean_titles = []
        for t in response:
            t = re.sub(r'^[\d\-\.\s\[\]討論問題心得閒聊黑特]+', '', t).strip() # 強制清洗所有標籤
            if t: clean_titles.append(f"{ptt_tag} {t}") # Python 強制補上正確標籤
        st.session_state.candidate_titles = clean_titles[:5]
    except:
        st.error("生成失敗，請再按一次")

# --- 7. 顯示標題與撰寫內文 ---
if st.session_state.candidate_titles:
    st.markdown("### 👇 點擊標題採用")
    for i, t in enumerate(st.session_state.candidate_titles):
        if st.button(t, key=f"t_{i}", use_container_width=True):
            st.session_state.sel_title = t
            st.session_state.candidate_titles = []
            st.rerun()

if 'sel_title' in st.session_state:
    st.divider()
    st.subheader(f"📝 標題：{st.session_state.sel_title}")
    
    if st.button("✍️ 撰寫內文與回文"):
        with st.spinner("撰寫中..."):
            prompt = f"""你是一個 PTT 鄉民。
            標題：{st.session_state.sel_title}
            內容主題：{imported_text if imported_text else final_topic}
            語氣強度：{tone_intensity}
            
            【內文要求】：
            1. 100-150 字，第一人稱。
            2. **內容鎖定**：必須針對標題寫。如果是手術就寫手術，不要寫到電波！
            3. 禁止問候語。
            
            【回文要求】：
            1. 給出 8 則回文。
            2. 語氣要像酸民、直白、簡短。
            3. **禁止使用問號 (?) 結尾**。鄉民是來噴人的，不是來問問題的。
            4. 內容要具體，提到如「盤子」、「智商稅」、「饅化」、「推」、「爛死」。
            
            格式：每行一則回文，內容開頭不需要 推/噓。"""
            
            try:
                raw_res = model.generate_content(prompt).text
                
                # 簡單分段處理
                st.subheader("內文：")
                # 嘗試過濾掉 AI 的標頭
                clean_body = re.sub(r'^好的.*?：', '', raw_res, flags=re.S).strip()
                st.write(clean_body.split("\n\n")[0].replace("\n", "  \n"))
                
                st.subheader("回文：")
                # 抓取最後 8 行
                cmt_lines = clean_body.split("\n")[-10:]
                tags = ["推", "推", "→", "→", "噓", "推"]
                for line in cmt_lines:
                    line = re.sub(r'^[推噓→\|:\d\.-]+', '', line).strip()
                    if len(line) > 2 and "標題" not in line:
                        # 強制去掉問號
                        line = line.replace("?", "").replace("？", "")
                        st.write(f"{random.choice(tags)}| {line}")
            except:
                st.error("撰寫失敗，請重新點擊按鈕")
