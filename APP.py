import streamlit as st
import google.generativeai as genai
import os
import random
import json
import requests
import re

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V47 最終修正版)", page_icon="⚡")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("⚡ PTT/Dcard 文案產生器 (V47 最終修正版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 內建資料庫 ---
DEFAULT_DATABASE = [
    {
        "title": "[討論] 淨膚雷射打一打 臉變超乾 是正常情況嗎",
        "content": "最近存了一點錢終於衝了一發淨膚雷射，本來想說能讓臉亮一點，結果勒？現在整個脫皮超誇張...像蛇一樣啊！打完當天是還好，但隔天開始就覺得緊繃到不行，保濕做得再足都像沒擦一樣。問診所的美容師，她就說這是正常代謝，多敷面膜就好。可是我朋友打了好幾次也沒跟我講會乾成這樣啊？還是我皮膚太爛了？打完這樣是正常的還是一開始就打太強了啊？有沒有人能救救我這張乾臉？== 搞得我現在都不太敢出門了...",
        "comments": ["推 正常啊，光療都會這樣", "推 乾是代謝正常的訊號啊，別太緊張", "噓 診所都話術啦，問網友最實在"]
    },
    {
        "title": "[討論] 韓版電波真的是平替?還是那是給窮人打的安慰劑",
        "content": "美國電波實在漲太兇 打一次900發都要快10萬...大家都說「效果差不多」、「CP值很高」...但我心裡一直有個疑問，一分錢一分貨...韓版到底是真平替，還是只是打個心安、給預算不夠的人一種「我有做醫美」的安慰劑?",
        "comments": ["推 打過玩美 真的就是安慰劑...", "推 一分錢一分貨 鳳凰痛歸痛", "推 韓版適合25歲左右當保養"]
    },
    {
        "title": "[討論] 針劑醫美根本是無底洞...算完年費嚇死人",
        "content": "以前覺得動手術貴，結果記帳發現針劑才是錢坑。肉毒除皺+瘦小臉一年快2萬，玻尿酸半年消一半又要補。算下來一張臉每年的「維護費」竟然要10幾萬！這根本是訂閱制，沒續費就打回原形。",
        "comments": ["推 真的...微整就是訂閱制", "推 這就是溫水煮青蛙啊", "推 算完不敢面對"]
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
    
    # 清洗 Emoji
    clean_topic_text = topic_category.split('(')[0]
    clean_topic_text = re.sub(r'[^\w\s\u4e00-\u9fa5]', '', clean_topic_text).strip()

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
            
            # --- V47 標題修復 Prompt ---
            prompt = f"""
            你是一個 PTT 醫美版資深鄉民。
            
            【指令】：請發想 5 個 PTT 標題。
            
            【參考範例 (僅供參考語氣，禁止抄襲內容)】：
            {example_text}
            --------------------------------
            
            【主題】：{imported_text if is_ref_mode else user_topic}
            
            【嚴格格式要求】：
            1. 標題格式：`{target_tag} 標題內容`
            2. **絕對禁止**在標籤後加冒號 (例如：[討論]：... 是錯的)。
            3. **絕對禁止**把標題寫成「關於...的討論」這種論文標題。
            4. **禁止**使用 Emoji。
            5. 請直接用一句話講完重點 (例如：韓版電波真的是智商稅嗎)。
            
            請列出 5 個標題，一行一個。
            """
            
            response = model.generate_content(prompt, safety_settings=safe_settings)
            titles = response.text.strip().split('\n')
            
            clean_titles = []
            for t in titles:
                t = t.strip()
                # 強制清洗：去掉編號、去掉冒號
                t = re.sub(r'^[\d\-\.\s]+', '', t) # 去編號
                t = t.replace("：", " ").replace(":", " ") # 去冒號
                # 確保標籤格式正確
                if not t.startswith("["):
                    t = f"{target_tag} {t}"
                clean_titles.append(t)
                
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

    if st.button("✍️ 撰寫內文 (V47 回文邏輯修復版)"):
        with st.spinner("正在撰寫中..."):
            try:
                # 1. 內文生成
                body_prompt = f"""
                你是一個 PTT 醫美版鄉民。
                請寫一篇關於「{st.session_state.sel_title}」的文章。
                
                【素材】：{st.session_state.source_content if st.session_state.source_content else user_topic}
                
                【要求】：
                1. 字數 100-150 字 (短文)。
                2. 口語化，第一人稱。
                3. 禁止提到「降解酶」或「範文內容」，請專注於你的主題。
                """
                body_response = model.generate_content(body_prompt, safety_settings=safe_settings).text
                
                # 2. 回文生成 (V47 關鍵：極簡指令，不給符號)
                comment_prompt = f"""
                你現在扮演 8 位不同的 PTT 鄉民。
                請看完這篇文章後，給出 8 則留言。
                
                文章："{body_response}"
                
                【嚴格指令 - 關於內容】：
                1. **禁止使用問號 (?) 結尾**。不要反問原PO。
                2. 請直接給出評價 (例如：爛死、推、笑死、真的、盤子)。
                3. 要簡短，像真人在推文。
                
                【嚴格指令 - 關於格式】：
                1. 請輸出 8 行。
                2. 每一行只要寫「內容」就好，**不要寫** 推或噓。
                (系統會自動幫你加推噓，你只要寫內容)
                
                {f"【置入】：請在其中一句內容提到「{prod_info}」是好選擇。" if is_promo else ""}
                """
                comment_response = model.generate_content(comment_prompt, safety_settings=safe_settings).text
                
                # --- 顯示與後製處理 ---
                st.subheader("內文：")
                st.markdown(body_response.replace("\n", "  \n")) 
                
                st.subheader("回文：")
                
                # V47 獨家：由程式來決定推噓，AI 只要寫內容
                # 這樣就絕對不會有格式亂掉的問題
                raw_comments = comment_response.strip().split('\n')
                formatted_comments = ""
                
                tags = ["推", "推", "推", "→", "→", "噓", "推", "→"] # 隨機池
                
                for c in raw_comments:
                    c = c.strip()
                    # 去掉 AI 可能雞婆加上的符號
                    c = c.replace("推|", "").replace("噓|", "").replace("→|", "").replace("|", "")
                    
                    if len(c) > 1: # 確保有內容
                        tag = random.choice(tags)
                        formatted_comments += f"{tag}| {c}  \n" # 這裡幫您加上您要的格式

                st.markdown(formatted_comments)
                
            except Exception as e:
                st.error("撰寫失敗")
                st.code(str(e))
