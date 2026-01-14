import streamlit as st
import google.generativeai as genai
import os
import random
import json
import requests
import re

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V46 暴力修正版)", page_icon="🔨")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🔨 PTT/Dcard 文案產生器 (V46 暴力修正版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 內建資料庫 (維持不變) ---
DEFAULT_DATABASE = [
    {
        "title": "[討論] 淨膚雷射打一打 臉變超乾 是正常情況嗎",
        "content": "最近存了一點錢終於衝了一發淨膚雷射，本來想說能讓臉亮一點，結果勒？現在整個脫皮超誇張...像蛇一樣啊！打完當天是還好，但隔天開始就覺得緊繃到不行，保濕做得再足都像沒擦一樣。問診所的美容師，她就說這是正常代謝，多敷面膜就好。可是我朋友打了好幾次也沒跟我講會乾成這樣啊？還是我皮膚太爛了？打完這樣是正常的還是一開始就打太強了啊？有沒有人能救救我這張乾臉？== 搞得我現在都不太敢出門了...",
        "comments": ["推|正常啊，光療都會這樣", "推|乾是代謝正常的訊號啊，別太緊張", "噓|診所都話術啦，問網友最實在"]
    },
    {
        "title": "[討論] 韓版電波真的是平替?還是那是給窮人打的安慰劑",
        "content": "美國電波實在漲太兇 打一次900發都要快10萬...大家都說「效果差不多」、「CP值很高」...但我心裡一直有個疑問，一分錢一分貨...韓版到底是真平替，還是只是打個心安、給預算不夠的人一種「我有做醫美」的安慰劑?",
        "comments": ["推|打過玩美 真的就是安慰劑...", "推|一分錢一分貨 鳳凰痛歸痛", "推|韓版適合25歲左右當保養"]
    }
]

# --- 3. 雲端抓取功能 ---
@st.cache_data(ttl=600)
def fetch_remote_data(url):
    if not url: return []
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return json.loads(response.text)
    except:
        return []
    return []

# --- 4. 取得模型清單 ---
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
    except:
        return ["models/gemini-1.5-pro", "models/gemini-pro"]

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
        if remote_data:
            final_database = remote_data
            st.success(f"✅ 雲端資料：{len(final_database)} 篇")
        else:
            st.error("❌ 讀取失敗，使用內建資料")
    else:
        st.info(f"📚 內建資料：{len(final_database)} 篇")

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
    ptt_tag = st.selectbox("選擇標籤：", ["[問題]", "[討論]", "[心得]", "[閒聊]", "[黑特]", "🎲 隨機"])
    topic_category = st.selectbox("議題內容：", ["💉 針劑/微整", "⚡ 電音波/雷射", "🏥 醫美診所/黑幕", "🔪 整形手術", "✍️ 自訂主題"])
    
    # 這裡只提取純文字，不要 Emoji
    clean_topic_text = re.sub(r'[^\w\u4e00-\u9fa5]', '', topic_category.split('(')[0])

    if "自訂" in topic_category:
        user_topic = st.text_input("輸入自訂主題 (若下方有貼文則忽略)：", "韓版電波是智商稅嗎？")
    else:
        user_topic = f"{clean_topic_text}"

with col2:
    st.subheader("🔥 設定語氣")
    tone_intensity = st.select_slider("強度：", ["溫和", "熱烈", "炎上"], value="熱烈")

st.markdown("---")
st.subheader("📝 匯入網友議題 (改寫/二創模式)")
imported_text = st.text_area(
    "請直接貼上網友原文 (AI 將針對此內容下標)：", 
    height=150,
    placeholder="在此貼上內容..."
)

st.markdown("---")

if st.button("🚀 生成 5 個標題", use_container_width=True):
    
    is_ref_mode = len(imported_text.strip()) > 5
    st.session_state.source_content = imported_text if is_ref_mode else ""
    
    sample_size = min(len(final_database), 3)
    examples = random.sample(final_database, sample_size)
    example_text = "\n".join([f"- {ex['title']}" for ex in examples])
    
    with st.spinner(f"AI 正在發想中..."):
        try:
            target_tag = ptt_tag.split(" ")[0] if "隨機" not in ptt_tag else "[問題]"
            
            prompt = f"""
            你是一個 PTT 醫美版資深鄉民。
            
            【指令】：請發想 5 個 PTT 標題。
            
            【參考範例 (僅供參考語氣，禁止抄襲)】：
            {example_text}
            --------------------------------
            
            【你的主題】：
            {imported_text if is_ref_mode else user_topic}
            
            【嚴格格式要求】：
            1. 標題**必須**以「{target_tag}」開頭。
            2. **格式錯誤範例 (絕對禁止)**：
               ❌ [討論] 針劑：效果好嗎？ (不要冒號)
               ❌ [討論] 針劑/微整 的風險 (不要把分類名稱寫進去)
               ❌ 💉 [討論] ... (不要 Emoji)
            3. **正確格式範例**：
               ⭕ [討論] 打完肉毒臉僵掉是正常的嗎
               ⭕ [心得] 淚溝玻尿酸失敗勸世文
            4. 字數 16~22 字。
            
            請直接列出 5 個標題，一行一個。
            """
            
            response = model.generate_content(prompt, safety_settings=safe_settings)
            titles = response.text.strip().split('\n')
            
            # --- 標題強力去污 (Post-processing) ---
            clean_titles = []
            for t in titles:
                t = t.strip()
                # 1. 去掉編號 (1. , - )
                t = re.sub(r'^[\d\-\.\s]+', '', t)
                # 2. 強制把「分類名稱 + 冒號」拿掉 (例如 "針劑：" 或 "針劑/微整：")
                # 這行會把 "[討論] 針劑：" 變成 "[討論] "
                t = re.sub(rf'{clean_topic_text}\s*[：:]\s*', '', t)
                # 3. 如果標籤不見了，補上去
                if not t.startswith("["):
                    t = f"{target_tag} {t}"
                
                if t: clean_titles.append(t)
                
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

    if st.button("✍️ 撰寫內文 (暴力修正版)"):
        with st.spinner("正在撰寫中..."):
            try:
                ref_article = random.choice(final_database)
                
                # 決定寫作素材
                if st.session_state.source_content:
                    context_instruction = f"""
                    【寫作素材 (請改寫這段)】：
                    "{st.session_state.source_content}"
                    請將這段內容改寫成一篇 PTT 討論文。
                    """
                else:
                    context_instruction = f"【寫作主題】：{user_topic}"

                # --- 1. 寫內文 ---
                body_prompt = f"""
                你是一個 PTT 醫美版鄉民。
                標題：{st.session_state.sel_title}
                {context_instruction}
                
                要求：字數約 100-150 字，第一人稱，口語化。
                """
                body_response = model.generate_content(body_prompt, safety_settings=safe_settings).text
                
                # --- 2. 寫回文 (針對您的需求大改) ---
                comment_prompt = f"""
                你是一個 PTT 鄉民 (酸民/老鳥)。
                請針對這篇文章留言："{body_response}"
                
                【嚴格規則】：
                1. 生成 8 則留言。
                2. 每行開頭必須是 `推|`、`噓|` 或 `→|`。
                3. **禁止提問**！不要問原 PO 問題 (例如：真的嗎？有效嗎？)。
                4. **要給結論**、**給評價**、或是**分享經驗**。
                5. 語氣參考：
                   - "這就是智商稅啊" (斷定)
                   - "笑死，這家很有名" (嘲諷)
                   - "打過+1，無感" (經驗)
                   - "原PO太盤了吧" (攻擊)
                {f"【置入】：請在 1 則回文自然提到「{prod_info}」。" if is_promo else ""}
                """
                comment_response = model.generate_content(comment_prompt, safety_settings=safe_settings).text
                
                # --- 顯示 ---
                st.subheader("內文：")
                st.markdown(body_response.replace("\n", "  \n")) 
                
                st.subheader("回文：")
                comments = comment_response.strip().split('\n')
                formatted_comments = ""
                for c in comments:
                    c = c.strip()
                    if c:
                        if any(x in c for x in ["推|", "噓|", "→|"]):
                             formatted_comments += c + "  \n"
                        elif len(c) > 2: 
                             formatted_comments += f"→| {c}  \n"

                st.markdown(formatted_
