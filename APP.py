# --- 說明與優化邏輯 (全內容維持在程式碼區塊中) ---
# 1. 移除語氣拉條：如您所述，標題生成主要受「分類情境」影響，移除拉條可簡化 UI 並減少 AI 混淆，讓輸出更穩定。
# 2. 修復白屏問題：延續 Session State 儲存機制，確保點擊「撰寫」後，結果能穩定留存在畫面上。
# 3. 維持模型架構：完全保留 get_models() 動態選單與模型實體化邏輯，不影響您 1.5 Pro 的使用。
# 4. 強化標題擬真度：將原本語氣拉條省下的空間，轉化為更明確的 PTT 鄉民人格指令。

import streamlit as st
import google.generativeai as genai
import random
import re

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美文案 V66", page_icon="💉", layout="wide")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 醫美情境字典 ---
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

# --- 3. 模型下拉選擇 (維持原始邏輯) ---
@st.cache_resource
def get_models():
    try:
        m_list = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return m_list
    except:
        return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]

with st.sidebar:
    st.header("⚙️ 設定選單")
    selected_model_name = st.selectbox("👇 挑選模型：", get_models(), index=0)
    st.info(f"當前模型：{selected_model_name}")

model = genai.GenerativeModel(selected_model_name)

# --- 4. 初始化 Session State ---
if 'titles' not in st.session_state: st.session_state.titles = []
if 'sel' not in st.session_state: st.session_state.sel = ""
if 'final_result' not in st.session_state: st.session_state.final_result = None

# --- 5. 主介面 ---
col1, col2 = st.columns([1, 2])
with col1:
    tag = st.selectbox("選擇標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題分類：", list(DB.keys()))
with col2:
    imported = st.text_area("📝 匯入網友原文 (選填)：", height=68, placeholder="貼上原文可讓 AI 進行二創改寫...")

# --- 6. 生成標題邏輯 ---
if st.button("🚀 生成 5 個標題", use_container_width=True):
    ctx = DB[cat]["context"]
    core = imported.strip() if imported.strip() else cat
    
    # 移除語氣參數，改為強調 PTT 鄉民語感
    prompt = f"""你現在是 PTT 醫美版資深鄉民，說話風格犀利直白。
    任務：針對「{core}」生成 5 個會引起討論的標題。
    限制：
    1. 只輸出標題，禁止開場白、編號、贅詞。
    2. 每行一個標題。
    3. 必須符合情境：{ctx}。
    4. 禁止提到任何 3C 產品。"""

    try:
        res = model.generate_content(prompt).text.strip().split('\n')
        final_list = []
        for t in res:
            # 暴力過濾贅詞
            t = re.sub(r'^[\d\-\.\s\[\]討論問題心得閒聊黑特：:]+', '', t).strip()
            if len(t) > 2 and not any(x in t for x in ["好的", "以下是", "沒問題"]):
                final_list.append(f"{tag} {t}")
        st.session_state.titles = final_list[:5]
        st.session_state.final_result = None
    except:
        st.error("API 繁忙，請重新點擊")

# 標題選擇區
if st.session_state.titles:
    st.write("### 👇 選擇採用的標題")
    for i, t in enumerate(st.session_state.titles):
        if st.button(t, key=f"t_{i}", use_container_width=True):
            st.session_state.sel = t
            st.session_state.final_result = None

# --- 7. 文案顯示邏輯 (防止白屏) ---
if st.session_state.sel:
    st.divider()
    st.subheader(f"📍 選定標題：{st.session_state.sel}")
    
    if st.button("✍️ 撰寫完整文案與推文", type="primary"):
        with st.spinner("對齊鄉民口吻撰寫中..."):
            info = DB[cat]
            prompt = f"""你現在是 PTT 鄉民。
            標題：{st.session_state.sel}
            要求：
            1. 撰寫 150 字內的發文內文，第一人稱，禁止客套問候。
            2. 語氣要像真人分享（酸、直白、不屑業配感）。
            3. 融入關鍵字：{", ".join(info['keywords'])}。
            4. 結尾加上 [SPLIT] 標籤。
            5. 在標籤後附上 8 則回文，格式「推/→/噓|內容」。"""
            
            try:
                raw_res = model.generate_content(prompt).text
                st.session_state.final_result = raw_res
            except:
                st.error("生成失敗，請重試")

    # 顯示生成結果
    if st.session_state.final_result:
        res_text = st.session_state.final_result
        
        if "[SPLIT]" in res_text:
            body, cmt_raw = res_text.split("[SPLIT]")
            comments = cmt_raw.strip().split("\n")
        else:
            body = res_text
            comments = []

        st.info("【 文章內容 】")
        st.code(body.replace("內文", "").strip(), language=None)
        
        st.warning("【 鄉民反應 】")
        # 回文前綴權重
        prefix_pool = ["推", "推", "→", "→", "噓", "推", "→"]
        for c in comments:
            clean_c = re.sub(r'^[推噓→\|:\s\d\.-]+', '', c).strip().replace("?", "").replace("？", "")
            if len(clean_c) > 2:
                st.write(f"**{random.choice(prefix_pool)}** | {clean_c}")

# --- 下一步建議 ---
# 既然移除語氣拉條了，如果您覺得生成的內容還是不夠「酸」或不夠「專業」，
# 我可以再針對議題分類字典 (DB) 裡的 context 加入更多 PTT 專屬黑話。
# 需要我針對 Mobile01 或 Threads 另外做一套風格切換嗎？
