import streamlit as st
import google.generativeai as genai
import os
import random
import json
import re

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V51 終極版)", page_icon="🎯")

api_key = st.secrets.get("GOOGLE_API_KEY")
st.title("🎯 PTT/Dcard 文案產生器 (V51)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 核心資料庫 (嚴格依照提供範例) ---
DB = [
    {
        "category": "⚡ 電音波/雷射",
        "title": "[討論] 韓版電波真的是平替?還是那是給窮人打的安慰劑",
        "content": "美國電波漲太兇，打一次900發快10萬。看到診所狂推韓版，價格只要1/3。大家都說效果差不多、CP值高。但我疑問一分錢一分貨，如果效果真的差不多鳳凰怎麼沒倒？韓版到底是真平替還是安慰劑?",
        "comments": ["推|打過玩美 真的就是安慰劑...", "推|一分錢一分貨 鳳凰痛歸痛", "推|鳳凰貴在專利技術 韓版像熱石按摩XD"]
    },
    {
        "category": "💉 針劑/微整",
        "title": "[討論] 針劑醫美根本是無底洞...算完年費嚇死人",
        "content": "以前覺得動手術貴，結果記帳發現針劑才是錢坑。肉毒除皺+瘦小臉一年2-3次，玻尿酸補不停。算下一張臉維護費要10幾萬！這根本是訂閱制，沒續費就打回原形。大家算過年費嗎?",
        "comments": ["推|真的...微整就是訂閱制", "推|這就是溫水煮青蛙啊", "推|所以醫生最愛推針劑 細水長流"]
    },
    {
        "category": "🏥 醫美診所/黑幕",
        "title": "[討論] 醫美做久真的會喪失對正常人長相的判斷力嗎?",
        "content": "自從入了醫美坑審美觀壞掉了。看路人第一眼就是掃描瑕疵：淚溝深、咀嚼肌大、額頭平。是不是忘記正常人類該有的樣子了?",
        "comments": ["推|真的會有醫美成癮症", "推|看很多諮詢師臉都饅化了還覺得美XD", "推|這就是為什麼複製人越來越多"]
    }
]

# --- 3. 模型抓取 ---
@st.cache_resource
def get_best_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority = ["gemini-1.5-pro", "gemini-pro"] # 暫避 gemma-2 怕權限問題
        for p in priority:
            for m in models:
                if p in m: return m
        return models[0]
    except: return "models/gemini-pro"

current_model_name = get_best_model()
model = genai.GenerativeModel(current_model_name)

# --- 4. 主介面 ---
if 'candidate_titles' not in st.session_state: st.session_state.candidate_titles = []

st.sidebar.info(f"使用模型：{current_model_name}")

col1, col2 = st.columns(2)
with col1:
    selected_tag = st.selectbox("標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    topic_category = st.selectbox("議題內容：", ["💉 針劑/微整", "⚡ 電音波/雷射", "🏥 醫美診所/黑幕", "🔪 整形手術"])
with col2:
    tone_intensity = st.select_slider("語氣：", ["溫和", "熱烈", "炎上"], value="熱烈")

st.markdown("---")
imported_text = st.text_area("匯入原文 (AI會以此為核心發想)：", height=80)

# 準備生成標題
if st.button("🚀 生成 5 個標題", use_container_width=True):
    # 鎖定主題
    core_subject = imported_text if imported_text.strip() else topic_category
    if "手術" in topic_category and not imported_text.strip():
        core_subject = random.choice(["隆乳", "隆鼻", "抽脂", "割雙眼皮"])

    prompt = f"""你是一個PTT資深鄉民。
    任務：針對「{core_subject}」寫5個標題。
    規則：
    1. 標題必須是「{selected_tag} + 內容」格式。
    2. 禁止寫到電波或資料庫無關內容。
    3. 字數約18字，口語化。
    只輸出內容，一行一個。"""
    
    try:
        res = model.generate_content(prompt).text.strip().split('\n')
        # 簡單清洗：確保有正確標籤，去掉編號
        titles = []
        for t in res:
            t = re.sub(r'^[\d\-\.\s]+', '', t).strip()
            if not t.startswith("["): t = f"{selected_tag} {t}"
            titles.append(t)
        st.session_state.candidate_titles = titles[:5]
    except: st.error("生成標題失敗，請再按一次。")

if st.session_state.candidate_titles:
    st.markdown("### 👇 選擇標題")
    for i, t in enumerate(st.session_state.candidate_titles):
        if st.button(t, key=f"t_{i}", use_container_width=True):
            st.session_state.sel_title = t
            st.session_state.candidate_titles = []
            st.rerun()

# 撰寫內文
if 'sel_title' in st.session_state:
    st.divider()
    st.markdown(f"## 📝 標題：{st.session_state.sel_title}")
    
    if st.button("✍️ 撰寫內文"):
        with st.spinner("AI 正在模仿範文語氣中..."):
            # 尋找匹配範本
            match = next((d for d in DB if d["category"] in topic_category), DB[0])
            
            prompt = f"""你是一個PTT鄉民，請「完全模仿」這篇範文的口吻、用詞與抱怨方式。
            
            【風格參考範文】：
            標題：{match['title']}
            內文：{match['content']}
            -------------------
            【你要寫的任務】：
            標題：{st.session_state.sel_title}
            核心素材：{imported_text if imported_text else topic_category}
            語氣：{tone_intensity}
            
            【要求】：
            1. 內文120字。必須專注於標題主題，禁止寫無關手術。
            2. 不要開頭問候。
            3. 回文10則，每行格式為「推| 內容」或「→| 內容」。
            4. 回文禁止問號，要像真人在評論。
            
            格式請嚴格區分「內文」與「回文」段落。"""
            
            try:
                raw_res = model.generate_content(prompt).text
                
                # 分段邏輯優化：如果不幸 AI 沒分段，我們用 Python 硬分
                if "回文" in raw_res:
                    body_part = raw_res.split("回文")[0].replace("內文", "").replace("：", "").strip()
                    comment_part = raw_res.split("回文")[-1].strip()
                else:
                    body_part = raw_res
                    comment_part = "推| 真的...  \n→| 這家診所不錯  \n噓| 又是業配"

                st.subheader("內文：")
                st.write(body_part.replace("\n", "  \n"))
                
                st.subheader("回文：")
                # 重新整理回文格式
                lines = comment_part.split("\n")
                tags = ["推", "推", "→", "→", "噓"]
                for line in lines:
                    line = re.sub(r'^[推噓→\|:\s\d\.-]+', '', line).strip()
                    if len(line) > 1:
                        st.write(f"{random.choice(tags)}| {line.replace('?', '').replace('？', '')}")
            except: st.error("撰寫內文失敗，請再試一次。")
