import streamlit as st
import google.generativeai as genai
import os
import random
import json
import requests
import re

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V48 鎖定修復版)", page_icon="🔒")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🔒 PTT/Dcard 文案產生器 (V48 鎖定修復版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 定義子題庫 (防止 AI 偷懶抄範例) ---
# 如果使用者選了大分類但沒寫主題，程式會從這裡隨機抓一個具體的給 AI
SUBTOPICS = {
    "💉 針劑/微整": ["肉毒桿菌", "玻尿酸填充", "精靈針", "熊貓針", "消脂針"],
    "⚡ 電音波/雷射": ["鳳凰電波", "海芙音波", "皮秒雷射", "索夫波", "淨膚雷射"],
    "🏥 醫美診所/黑幕": ["諮詢師話術", "診所價格不透明", "醫生技術", "推銷手法", "醫美糾紛"],
    "🔪 整形手術": ["隆乳手術", "隆鼻手術", "抽脂手術", "雙眼皮手術", "拉皮手術"],
    "✍️ 自訂主題": ["醫美"] # 保底
}

# --- 3. 內建資料庫 (僅供語氣參考) ---
DEFAULT_DATABASE = [
    {"title": "[討論] 韓版電波真的是平替?還是那是給窮人打的安慰劑", "content": "...", "comments": ["推 真的就是安慰劑", "推 一分錢一分貨"]},
    {"title": "[討論] 針劑醫美根本是無底洞...算完年費嚇死人", "content": "...", "comments": ["推 真的...微整就是訂閱制", "推 這就是溫水煮青蛙"]},
    {"title": "[問題] 為了面相招財去打耳垂玻尿酸?", "content": "...", "comments": ["推 心理作用居多吧", "推 會痛到往生喔"]}
]

# --- 4. 雲端/模型功能 ---
@st.cache_data(ttl=600)
def fetch_remote_data(url):
    if not url: return []
    try:
        response = requests.get(url)
        if response.status_code == 200: return json.loads(response.text)
    except: return []
    return []

@st.cache_resource
def get_all_models():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        def sort_priority(name):
            if "gemma-2" in name: return 0
            if "gemma" in name: return 1
            if "gemini-1.5-pro" in name and "exp" not in name: return 2
            if "gemini-pro" in name: return 3
            return 10
        models.sort(key=sort_priority)
        return models
    except: return ["models/gemini-1.5-pro", "models/gemini-pro"]

all_my_models = get_all_models()

# --- 5. 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 設定")
    selected_model_name = st.selectbox("👇 選擇模型：", all_my_models, index=0)
    
    st.divider()
    st.header("☁️ 資料庫")
    data_url = st.text_input("JSON 資料網址 (選填)：", placeholder="https://raw.githubusercontent...")
    
    final_database = DEFAULT_DATABASE
    if data_url:
        remote_data = fetch_remote_data(data_url)
        if remote_data: final_database = remote_data

model = genai.GenerativeModel(selected_model_name)

# 安全設定
safe_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# --- 6. 主介面 ---
if 'used_titles' not in st.session_state: st.session_state.used_titles = set()
if 'candidate_titles' not in st.session_state: st.session_state.candidate_titles = []
if 'source_content' not in st.session_state: st.session_state.source_content = ""

col1, col2 = st.columns(2)

with col1:
    st.subheader("📌 設定分類")
    # 這裡只提取純文字標籤，例如 "[問題]"
    ptt_tag_full = st.selectbox("選擇標籤：", ["[問題]", "[討論]", "[心得]", "[閒聊]", "[黑特]", "🎲 隨機"])
    target_tag = ptt_tag_full.split(" ")[0] if "隨機" not in ptt_tag_full else "[問題]"

    topic_category = st.selectbox("議題內容：", ["💉 針劑/微整", "⚡ 電音波/雷射", "🏥 醫美診所/黑幕", "🔪 整形手術", "✍️ 自訂主題"])
    
    # --- V48 核心修復：決定具體主題 ---
    # 如果使用者沒輸入自訂主題，我們從子題庫隨機抓一個 (例如：隆乳)
    # 這樣 AI 就絕對不會去寫「電波」
    clean_category_key = topic_category # 用來查表的 key
    
    if "自訂" in topic_category:
        user_topic_input = st.text_input("輸入自訂主題：", "韓版電波是智商稅嗎？")
        final_topic = user_topic_input
    else:
        # 自動隨機鎖定一個子題
        random_subtopic = random.choice(SUBTOPICS.get(topic_category, ["醫美"]))
        st.info(f"💡 未輸入主題，系統自動鎖定：**{random_subtopic}** (避免內容跑掉)")
        final_topic = f"關於「{random_subtopic}」的討論"

with col2:
    st.subheader("🔥 設定語氣")
    tone_intensity = st.select_slider("強度：", ["溫和", "熱烈", "炎上"], value="熱烈")

st.markdown("---")
st.subheader("📝 匯入網友議題 (改寫/二創)")
imported_text = st.text_area("貼上網友原文 (AI 將針對此內容下標)：", height=100)

st.markdown("---")

if st.button("🚀 生成 5 個標題", use_container_width=True):
    
    # 判斷是否有匯入文
    is_ref_mode = len(imported_text.strip()) > 5
    st.session_state.source_content = imported_text if is_ref_mode else ""
    
    # 最終要寫的主題
    subject_to_write = imported_text if is_ref_mode else final_topic
    
    # 準備範例 (僅供語氣參考)
    sample_size = min(len(final_database), 3)
    examples = random.sample(final_database, sample_size)
    example_text = "\n".join([f"- {ex['title']}" for ex in examples])
    
    with st.spinner(f"AI 正在鎖定主題【{subject_to_write[:10]}...】發想中..."):
        try:
            # --- V48 標題 Prompt：強力鎖定 ---
            prompt = f"""
            你是一個 PTT 醫美版鄉民。
            
            【任務】：針對主題「{subject_to_write}」發想 5 個標題。
            
            【語氣參考 (禁止抄襲內容)】：
            {example_text}
            --------------------------------
            
            【嚴格限制】：
            1. **內容鎖定**：你必須寫「{subject_to_write}」。如果主題是隆乳，就只能寫隆乳，禁止寫電波或針劑！
            2. **標籤格式**：標題內容**不要**包含 `[問題]` 或 `[討論]` 這種標籤。(我會用程式幫你加，你只要寫標題文字就好)。
            3. **禁止符號**：禁止使用 Emoji、冒號、編號。
            4. 語氣：{tone_intensity}、口語化、像真人。
            
            請列出 5 個純標題文字，一行一個。
            """
            
            response = model.generate_content(prompt, safety_settings=safe_settings)
            raw_titles = response.text.strip().split('\n')
            
            clean_titles = []
            for t in raw_titles:
                t = t.strip()
                # 1. 去掉編號 (1. 或 -)
                t = re.sub(r'^[\d\-\.\s]+', '', t)
                # 2. 去掉 AI 雞婆加的標籤 (如果它還是不聽話加了 [問題]，我們就把它砍了)
                t = re.sub(r'^\[.*?\]', '', t).strip()
                # 3. 去掉冒號
                t = t.replace("：", "").replace(":", "")
                
                # 4. 最後由我們強制加上正確的標籤
                if t: 
                    final_t = f"{target_tag} {t}"
                    clean_titles.append(final_t)
                
            st.session_state.candidate_titles = clean_titles[:5]
            
        except Exception as e:
            st.error("生成失敗")
            st.code(str(e))

# --- 7. 結果與內文區 ---
if st.session_state.candidate_titles:
    st.markdown("### 👇 生成結果 (點擊採用)")
    for i, t in enumerate(st.session_state.candidate_titles):
        if st.button(t, key=f"btn_{i}", use_container_width=True):
            st.session_state.sel_title = t
            st.session_state.candidate_titles = []
            st.rerun()

if 'sel_title' in st.session_state:
    st.divider()
    st.markdown(f"## 📝 標題：{st.session_state.sel_title}")
    
    with st.expander("置入設定 (選填)"):
        is_promo = st.checkbox("開啟置入")
        prod_info = st.text_input("產品資訊", "XX診所")

    if st.button("✍️ 撰寫內文 (V48 邏輯鎖定版)"):
        with st.spinner("撰寫中..."):
            try:
                # 決定寫作素材
                if st.session_state.source_content:
                    topic_instruction = f"改寫網友原文：\n{st.session_state.source_content}"
                else:
                    # 這裡也要用 final_topic (確保不會跑掉)
                    # 因為 rerun 後 final_topic 會重算，所以我們直接用標題來反推主題
                    topic_instruction = f"主題：{st.session_state.sel_title}"

                # 1. 寫內文
                body_prompt = f"""
                你是一個 PTT 醫美版鄉民。
                
                【任務】：寫一篇關於「{st.session_state.sel_title}」的內文。
                
                【限制】：
                1. 字數 100-150 字 (短文)。
                2. 口語化，第一人稱。
                3. **內容鎖定**：請看清楚標題！標題寫什麼就寫什麼。標題是手術就寫手術，不要寫去打雷射。
                """
                body_response = model.generate_content(body_prompt, safety_settings=safe_settings).text
                
                # 2. 寫回文 (禁止問句)
                comment_prompt = f"""
                你現在扮演 8 位不同的 PTT 鄉民。
                文章："{body_response}"
                
                【任務】：給出 8 則留言。
                
                【嚴格格式要求】：
                1. 請輸出 8 行。
                2. 每行**只要寫內容** (不要寫 推/噓，不要寫 ID)。
                3. **禁止使用問號 (?) 結尾**。鄉民是來給評價的 (例如：推、爛死、笑死、真的)，不是來反問的。
                
                {f"【置入】：請在其中一句內容自然提到「{prod_info}」。" if is_promo else ""}
                """
                comment_response = model.generate_content(comment_prompt, safety_settings=safe_settings).text
                
                # --- 顯示與後製 ---
                st.subheader("內文：")
                st.markdown(body_response.replace("\n", "  \n")) 
                
                st.subheader("回文：")
                
                # Python 強制排版 (不相信 AI)
                raw_comments = comment_response.strip().split('\n')
                formatted_comments = ""
                tags = ["推", "推", "推", "→", "→", "噓", "推", "→"] 
                
                for c in raw_comments:
                    c = c.strip()
                    # 清洗 AI 雞婆加的符號
                    c = re.sub(r'^[推噓→\|]+', '', c).strip()
                    
                    if len(c) > 1:
                        tag = random.choice(tags)
                        formatted_comments += f"{tag}| {c}  \n"

                st.markdown(formatted_comments)
                
            except Exception as e:
                st.error("撰寫失敗")
                st.code(str(e))
