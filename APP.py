import streamlit as st
import google.generativeai as genai
import random
import re

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 文案產生器 V52", page_icon="🎯")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 資料庫 (嚴格分類，防止內容混淆) ---
DB = {
    "💉 針劑/微整": [
        {"title": "[討論] 針劑醫美根本是無底洞...算完年費嚇死人", "content": "微整就是訂閱制，肉毒玻尿酸半年就要補一次，一年維護費十幾萬。", "comments": ["推|微整就是訂閱制+1", "推|這就是溫水煮青蛙", "推|醫生最愛推針劑細水長流"]},
        {"title": "[討論] 聽說打降解酶會連自己的肉一起溶掉?", "content": "降解酶不只溶玻尿酸，還會連自體透明質酸一起溶掉導致凹陷？", "comments": ["推|會凹+1 降解酶敵我不分", "推|皮膚變得很薄很皺像老太太", "推|看過有人打完直接凹一塊"]}
    ],
    "⚡ 電音波/雷射": [
        {"title": "[討論] 韓版電波真的是平替?還是安慰劑?", "content": "鳳凰太貴，韓版價格1/3。效果差不多鳳凰怎麼沒倒？", "comments": ["推|打過玩美 真的就是安慰劑", "推|鳳凰貴在冷媒技術，韓版像熱石按摩", "推|想逆齡還是乖乖刷鳳凰"]}
    ],
    "🏥 醫美診所/黑幕": [
        {"title": "[討論] 醫美做久真的會喪失對正常人長相的判斷力嗎?", "content": "審美觀壞掉了，看路人都是缺點。忘記正常人類長什麼樣。", "comments": ["推|醫美成癮症會無限放大瑕疵", "推|諮詢師整張臉饅化還覺得美", "推|路上複製人越來越多"]}
    ],
    "🔪 整形手術": [
        {"title": "[討論] 男生說喜歡自然美女 其實分不出來吧", "content": "直男討厭的是失敗的整形，只要沒變蛇精臉他們都覺得是天然。", "comments": ["推|連淡妝都分不出來了何況醫美", "推|只要漂亮順眼就是天然", "推|貴的醫美就是讓你變美但看不出來"]}
    ]
}

# --- 3. 模型設定 ---
@st.cache_resource
def get_model():
    try:
        # 優先搜尋可用模型
        available_models = [m.name for m in genai.list_models()]
        for m_name in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
            for available in available_models:
                if m_name in available: return genai.GenerativeModel(available)
        return genai.GenerativeModel("gemini-pro")
    except:
        return genai.GenerativeModel("gemini-pro")

model = get_model()

# --- 4. 主介面 ---
if 'titles' not in st.session_state: st.session_state.titles = []

col1, col2 = st.columns(2)
with col1:
    tag = st.selectbox("選擇標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題內容：", list(DB.keys()))
with col2:
    tone = st.select_slider("強度：", ["溫和", "熱烈", "炎上"], value="熱烈")

st.markdown("---")
imported = st.text_area("匯入原文 (若有貼入，AI會以此核心改寫)：", height=100, placeholder="例如：我朋友去隆乳結果...")

# --- 5. 生成標題 ---
if st.button("🚀 生成 5 個標題", use_container_width=True):
    # 決定核心主題：如果有匯入則用匯入，否則從分類隨機指派一個具體主題
    if imported.strip():
        topic = imported.strip()
    else:
        # 如果是手術類，強迫指定一個具體手術，避免AI去寫電波
        if "手術" in cat:
            topic = random.choice(["隆乳手術後的疤痕", "隆鼻後變納美人", "抽脂後凹凸不平", "雙眼皮縫太高"])
        else:
            topic = cat

    # 抽取該分類的範例，禁止看其他分類
    refs = DB.get(cat, DB["💉 針劑/微整"])
    ref_str = "\n".join([f"範例標題：{r['title']}" for r in refs])

    prompt = f"""你是一個PTT醫美版鄉民。
    請參考這些真實標題的語氣：
    {ref_str}
    
    任務：針對「{topic}」寫5個標題。
    要求：
    1. 內容必須嚴格鎖定在「{topic}」，禁止提到電波或無關手術。
    2. 標題格式必須是「{tag} + 內容」。
    3. 語氣要像真人、口語化、禁止冒號。
    只輸出標題，一行一個，不要編號。"""

    try:
        response = model.generate_content(prompt)
        res_list = response.text.strip().split('\n')
        # 後處理：強迫修復格式
        final_titles = []
        for t in res_list:
            t = re.sub(r'^[\d\-\.\s\[\]討論問題心得閒聊黑特]+', '', t).strip()
            if t: final_titles.append(f"{tag} {t}")
        st.session_state.titles = final_titles[:5]
    except Exception as e:
        st.error("生成失敗，請再試一次")

# --- 6. 選擇與撰寫 ---
if st.session_state.titles:
    st.markdown("### 👇 點擊標題採用")
    for i, t in enumerate(st.session_state.titles):
        if st.button(t, key=f"t_{i}", use_container_width=True):
            st.session_state.sel = t
            st.session_state.titles = []
            st.rerun()

if 'sel' in st.session_state:
    st.divider()
    st.subheader(f"📝 標題：{st.session_state.sel}")
    
    if st.button("✍️ 撰寫內文與回文"):
        with st.spinner("撰寫中..."):
            # 取得對應分類的範文風格
            match = DB.get(cat, DB["💉 針劑/微整"])[0]
            
            prompt = f"""你是一個PTT鄉民，請模仿這篇範文的口吻寫作。
            標題：{st.session_state.sel}
            素材：{imported if imported else cat}
            範文參考：{match['content']}
            
            要求：
            1. 內文120字，禁止開頭問候，禁止提到無關主題(如隆乳變電波)。
            2. 回文10則，格式「推|內容」。
            3. 回文要酸、要直白、禁止問號結尾。
            """
            
            try:
                res = model.generate_content(prompt).text
                # 切割顯示
                parts = res.split("回文")
                body = parts[0].replace("內文", "").replace("：", "").strip()
                st.markdown("#### 內文：")
                st.write(body.replace("\n", "  \n"))
                
                st.markdown("#### 回文：")
                raw_cmts = parts[-1].strip().split("\n")
                for c in raw_cmts:
                    c = re.sub(r'^[推噓→\|:\s\d\.-]+', '', c).strip()
                    if len(c) > 2:
                        st.write(f"{random.choice(['推','推','→','噓'])}| {c.replace('?', '').replace('？', '')}")
            except:
                st.error("撰寫失敗，請再按一次按鈕")
