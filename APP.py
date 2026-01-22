# --- PTT 醫美口碑生成器 V75 (facelift 語感對齊版) ---
# 1. 語法調校：對齊 facelift 版「分享、詢問、避雷」的真實語氣，降低無理攻擊性。
# 2. 格式優化：內文自動分行，模擬 PTT 終端機發文手感。
# 3. 回文修正：固定生成 10 則，且格式統一為「推/噓/→|」，去除帳號 ID。
# 4. 穩定機制：維持 Session State 儲存，確保不會白屏。

import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
import re
import os

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美文案 V75", page_icon="💉", layout="wide")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 醫美版專用情境 (facelift 風格) ---
DB = {
    "💉 針劑/微整": {
        "context": "討論微整。焦點：美感、自然度、維持時間、有無副作用。",
        "keywords": ["饅化", "維持度", "降解酶", "錢坑", "審美感", "術後照護"],
        "example": "最近覺得臉有點凹，想補一點玻尿酸，但又怕像板上說的補到變饅頭人..."
    },
    "⚡ 電音波/雷射": {
        "context": "討論拉提雷射。焦點：發數分配、醫生細心度、原廠認證、痛感比對。",
        "keywords": ["鳳凰電波", "海芙音波", "發數", "能量", "痛感", "效果維持"],
        "example": "考慮很久終於去打了鳳凰，醫生能量開蠻強的，雖然很痛但覺得下顎線有變明顯。"
    },
    "🏥 醫美診所/黑幕": {
        "context": "討論診所經驗。焦點：環境、推銷感、價格透明度、售後服務。",
        "keywords": ["諮詢師推銷", "價格透明", "術後關心", "強迫推銷", "避雷"],
        "example": "去這間諮詢覺得壓力超大，諮詢師一直要我刷卡買課程，大家有推薦不推銷的診所嗎？"
    }
}

# --- 3. 模型選擇 (優先 Flash 以確保 Token 額度) ---
@st.cache_resource
def get_models():
    try:
        m_list = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        pref = ["gemini-1.5-flash", "gemini-1.5-pro"]
        m_list = [m for m in pref if m in m_list] + [m for m in m_list if m not in pref]
        return m_list
    except:
        return ["gemini-1.5-flash", "gemini-1.5-pro"]

# --- 4. 初始化 Session State ---
if 'titles' not in st.session_state: st.session_state.titles = []
if 'sel' not in st.session_state: st.session_state.sel = ""
if 'final_result' not in st.session_state: st.session_state.final_result = None

# --- 5. 側邊欄：檔案讀取 ---
with st.sidebar:
    st.header("⚙️ 設定與檔案")
    selected_model = st.selectbox("👇 挑選模型", get_models(), index=0)
    
    all_refs = ""
    if os.path.exists("ref_files"):
        valid_files = [f for f in os.listdir("ref_files") if f.endswith(('.txt', '.xlsx', '.xls'))]
        for f in valid_files:
            f_path = os.path.join("ref_files", f)
            try:
                if f.endswith(".txt"):
                    with open(f_path, "r", encoding="utf-8") as file:
                        all_refs += f"\n[檔案:{f}]\n{file.read()[:1000]}\n"
                elif f.endswith((".xlsx", ".xls")):
                    df = pd.read_excel(f_path).head(15)
                    all_refs += f"\n[Excel:{f}]\n{df.to_string(index=False)}\n"
            except: pass
        if valid_files: st.success(f"已自動加載 {len(valid_files)} 個參考檔")

model = genai.GenerativeModel(
    model_name=selected_model,
    safety_settings=[{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
)

# --- 6. 主介面 ---
col1, col2 = st.columns([1, 2])
with col1:
    tag = st.selectbox("標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題：", list(DB.keys()))
with col2:
    imported = st.text_area("📝 參考原文 (選填)：", height=68)

# 生成標題
if st.button("🚀 生成標題建議", use_container_width=True):
    ctx = DB[cat]["context"]
    core = imported.strip() if imported.strip() else cat
    prompt = f"""你現在是 PTT facelift 版資深鄉民。針對「{core}」生成 5 個符合醫美版生態的標題。
    參考資料：{all_refs}
    要求：語氣平實、真誠，多用「求推薦、分享、慎入、真心話」等詞。禁止編號，每行一個。情境：{ctx}"""
    try:
        res = model.generate_content(prompt).text.strip().split('\n')
        st.session_state.titles = [f"{tag} {re.sub(r'^[\d\-\.\s\[\]讨论問題心得閒聊黑特：:]+', '', t).strip()}" for t in res if len(t)>2][:5]
        st.session_state.final_result = None
    except Exception as e:
        st.error(f"錯誤：{e}")

# 標題按鈕
if st.session_state.titles:
    st.write("### 👇 選擇標題")
    t_cols = st.columns(len(st.session_state.titles))
    for i, t in enumerate(st.session_state.titles):
        if t_cols[i].button(t, key=f"t_{i}"):
            st.session_state.sel = t
            st.session_state.final_result = None

# --- 7. 文案生成 ---
if st.session_state.sel:
    st.divider()
    if st.button("✍️ 撰寫完整文案與推文", type="primary"):
        with st.spinner("對齊 facelift 語感撰寫中..."):
            info = DB[cat]
            prompt = f"""你現在是 PTT facelift 版鄉民，正準備發文。
            標題：{st.session_state.sel}
            參考附件：{all_refs}
            要求：
            1. 文章內容：150-200字，語氣真誠、稍微碎念，像是在分享真實心路歷程。
            2. 排版：必須使用手動換行（每句大約 20-30 字就換行），讓它看起來像 PTT 介面。
            3. 關鍵字：融入「{', '.join(info['keywords'])}」。
            4. 結尾加上 [END]，隨後附上 10 則推文。
            5. 推文要求：不要帳號名，僅提供內容。語氣包含鼓勵、詢問細節、或中立評論。"""
            
            try:
                raw_res = model.generate_content(prompt).text
                st.session_state.final_result = raw_res
            except Exception as e:
                st.error(f"生成失敗：{e}")

    # 顯示結果
    if st.session_state.final_result:
        res_text = st.session_state.final_result
        if "[END]" in res_text:
            body, cmt_raw = res_text.split("[END]")
            comments = cmt_raw.strip().split("\n")
        else:
            body, comments = res_text, []

        st.info("【 文章內容 】")
        # 顯示內文並保持分行
        st.code(body.replace("內文", "").strip(), language=None)
        
        st.warning("【 鄉民反應 】")
        # 固定產出 10 則
        prefix_pool = ["推", "推", "→", "→", "推", "推", "→", "→", "噓", "推"]
        for i, c in enumerate(comments[:10]):
            clean_c = re.sub(r'^[推噓→\|:\s\d\.-]+', '', c).strip()
            if len(clean_c) > 2:
                symbol = prefix_pool[i % len(prefix_pool)]
                st.markdown(f"**{symbol}|** {clean_c}")
