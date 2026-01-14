import streamlit as st
import google.generativeai as genai
import os
import random
import json
import requests

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V44 議題改寫版)", page_icon="♻️")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("♻️ PTT/Dcard 文案產生器 (V44 議題改寫版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 內建資料庫 (維持 V42 的完整版) ---
DEFAULT_DATABASE = [
    {
        "title": "[討論] 淨膚雷射打一打 臉變超乾 是正常情況嗎",
        "content": "最近存了一點錢終於衝了一發淨膚雷射，本來想說能讓臉亮一點，結果勒？現在整個脫皮超誇張...像蛇一樣啊！打完當天是還好，但隔天開始就覺得緊繃到不行，保濕做得再足都像沒擦一樣。問診所的美容師，她就說這是正常代謝，多敷面膜就好。可是我朋友打了好幾次也沒跟我講會乾成這樣啊？還是我皮膚太爛了？打完這樣是正常的還是一開始就打太強了啊？有沒有人能救救我這張乾臉？== 搞得我現在都不太敢出門了...",
        "comments": [
            "推|正常啊，光療都會這樣 →|敷面膜是基本，但你還要加強油類鎖水",
            "推|乾是代謝正常的訊號啊，別太緊張",
            "噓|診所都話術啦，問網友最實在 →|術後一個禮拜比較有感，忍一下",
            "推|妳是打幾發啊？能量太高當然乾",
            "噓|我打完都沒事耶，妳是不是沒買他們家術後產品 →|乾到爆是正常的，原Po太嫩了",
            "推|試試看貴鬆鬆的修護霜，可能比較有用 →|之前打完像沙漠，用理膚寶水B5有救回來"
        ]
    },
    {
        "title": "[討論] 韓版電波真的是平替?還是那是給窮人打的安慰劑",
        "content": "美國電波實在漲太兇 打一次900發都要快10萬\n看到很多診所狂推韓版電波 價格大概只要1/3甚至更低\n\n大家都說「效果差不多」、「CP值很高」、「適合怕痛的人」\n但我心裡一直有個疑問，一分錢一分貨\n如果效果真的差不多，那鳳凰怎麼還沒倒\n有沒有兩種都打過的人可以出來說實話，韓版到底是真平替\n還是只是打個心安、給預算不夠的人一種「我有做醫美」的安慰劑?",
        "comments": [
            "推|打過玩美 真的就是安慰劑...",
            "推|一分錢一分貨 鳳凰痛歸痛",
            "推|韓版適合25歲左右當保養",
            "推|我是把韓版當作兩次美國電波中間的維持",
            "推|如果你預算只能打韓版 那不如存錢去打音波",
            "推|所謂的平替通常都只有正版30%的效果 但價格也是30%算合理啦",
            "推|醫生技術也有差 有些醫生打韓版能量調得好 效果也不錯",
            "推|鳳凰貴在專利跟那個冷媒噴射技術 韓版真的很像熱石按摩XD",
            "推|想省錢就打韓版 想逆齡還是乖乖刷卡打鳳凰吧",
            "推|就去韓國打當保養吧"
        ]
    }
    # ... (為節省版面，其他資料省略，程式會正常運作) ...
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

# --- 4. 取得模型清單 (Gemma 優先) ---
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
if 'source_content' not in st.session_state: st.session_state.source_content = "" # 儲存來源內容

col1, col2 = st.columns(2)

with col1:
    st.subheader("📌 設定分類與標籤")
    ptt_tag = st.selectbox("選擇標籤：", ["[問題]", "[討論]", "[心得]", "[閒聊]", "[黑特]", "🎲 隨機"])
    topic_category = st.selectbox("議題內容：", ["💉 針劑/微整", "⚡ 電音波/雷射", "🏥 醫美診所/黑幕", "🔪 整形手術", "✍️ 自訂主題"])
    
    if "自訂" in topic_category:
        user_topic = st.text_input("輸入自訂主題 (若下方有貼文則忽略)：", "韓版電波是智商稅嗎？")
    else:
        user_topic = f"關於「{topic_category.split('(')[0]}」的討論"

with col2:
    st.subheader("🔥 設定語氣")
    tone_intensity = st.select_slider("強度：", ["溫和", "熱烈", "炎上"], value="熱烈")

# --- 新增：匯入網友議題區域 ---
st.markdown("---")
st.subheader("📝 匯入網友議題 (改寫/二創模式)")
imported_text = st.text_area(
    "請直接貼上網友的原文、新聞或故事 (AI 將讀取此內容並重新下標)：", 
    height=150,
    placeholder="在此貼上內容... 例如：\n我看朋友去打海芙音波，結果打完臉貓下去，超可怕...\n(若此欄位有內容，AI 會優先以此內容為主)"
)

st.markdown("---")

if st.button("🚀 生成 5 個標題", use_container_width=True):
    
    # 判斷使用者是否使用了「匯入模式」
    is_ref_mode = len(imported_text.strip()) > 5
    st.session_state.source_content = imported_text if is_ref_mode else ""
    
    # 準備範例
    sample_size = min(len(final_database), 3)
    examples = random.sample(final_database, sample_size)
    example_text = "\n".join([f"- {ex['title']}" for ex in examples])
    
    with st.spinner(f"AI 正在閱讀並發想..."):
        try:
            target_tag = ptt_tag.split(" ")[0] if "隨機" not in ptt_tag else "[問題]"
            
            if is_ref_mode:
                # --- 模式 A：讀取網友文章並改寫 ---
                prompt = f"""
                你是一個 PTT 醫美版資深鄉民。
                
                【任務目標】：
                請閱讀以下這篇【網友原文】，抓出它的核心爭議點或爆點，
                然後重新發想 5 個更吸睛、更符合 PTT 風格的標題。
                
                【網友原文】：
                "{imported_text}"
                
                【參考這些標題的語氣】：
                {example_text}
                
                【標題要求】：
                1. 必須以「{target_tag}」開頭。
                2. 針對原文內容進行改寫，不要無中生有。
                3. 語氣：{tone_intensity}。
                4. 字數 16~22 字。
                一行一個，不要編號。
                """
            else:
                # --- 模式 B：一般關鍵字發想 ---
                prompt = f"""
                你是一個 PTT 醫美版資深鄉民。
                請參考以下【真實資料庫標題】的下標邏輯：
                {example_text}
                
                任務：為主題「{user_topic}」發想 10 個新標題。
                限制：以「{target_tag}」開頭，字數 16~22 字，語氣：{tone_intensity}。
                一行一個，不要編號。
                """
            
            response = model.generate_content(prompt, safety_settings=safe_settings)
            titles = response.text.strip().split('\n')
            st.session_state.candidate_titles = [t.strip() for t in titles if t.strip()][:5]
            
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

    if st.button("✍️ 撰寫內文 (全方位仿寫模式)"):
        with st.spinner("正在模仿真實鄉民口吻..."):
            try:
                # 準備參考範文
                ref_article = random.choice(final_database)
                ref_comments_str = "\n".join(ref_article.get("comments", []))
                
                # 判斷是否有匯入的來源內容
                source_context = ""
                if st.session_state.source_content:
                    source_context = f"\n【請改寫這段網友原文的故事】：\n{st.session_state.source_content}\n"
                else:
                    source_context = f"\n主題：{user_topic}\n"

                # --- 1. 寫內文 ---
                body_prompt = f"""
                你是一個 PTT 醫美版鄉民。
                請模仿這篇【真實範文】的風格寫作：
                標題：{ref_article['title']}
                內文：{ref_article['content']}
                
                {source_context}
                
                現在請寫一篇新文章。
                標題：{st.session_state.sel_title}
                要求：字數約 100-150 字，第一人稱，口語化。
                """
                body_response = model.generate_content(body_prompt, safety_settings=safe_settings).text
                
                # --- 2. 寫回文 ---
                comment_prompt = f"""
                你是一個 PTT 鄉民。
                請參考以下【真實回文風格】，生成針對這篇文章的 8 則留言：
                
                【真實回文參考】：
                {ref_comments_str}
                
                【你的任務】：
                針對文章："{body_response}"
                生成 8 則類似風格的回文。
                要求：
                1. 每行開頭必須是 `推|`。
                2. 不要 ID。
                3. 語氣要像上面的參考範例一樣酸、簡短或中肯。
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
                        if any(x in c for x in ["推|"]):
                             formatted_comments += c + "  \n"
                        elif len(c) > 2: 
                             formatted_comments += f"→| {c}  \n"

                st.markdown(formatted_comments)
                
            except Exception as e:
                st.error("撰寫失敗")
                st.code(str(e))
