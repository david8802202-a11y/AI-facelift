# --- PTT 醫美口碑生成器 V73 (額度優化與安全版) ---
# 1. Excel 讀取優化：限制讀取前 20 列 (df.head(20))，防止 Token 爆炸。
# 2. 安全層級調整：調低安全過濾器，允許 AI 生成 PTT 風格的犀利、嘲諷言論。
# 3. 錯誤診斷：明確區分「API 額度限制」與「安全過濾封鎖」。
# 4. 模型建議：建議優先使用 gemini-1.5-flash，它的免費額度最穩定。

import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
import re
import os

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美文案 V73", page_icon="💉", layout="wide")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key，請檢查 Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 醫美情境字典 ---
DB = {
    "💉 針劑/微整": {
        "context": "討論微整。關鍵字：饅化、訂閱制、年費、錢坑、降解酶、智商稅、臉僵。",
        "keywords": ["訂閱制", "饅化", "年費", "降解酶", "智商稅", "塑膠感"],
        "example": "補完玻尿酸臉腫得像發酵過的饅頭，真的當大家是盤子？"
    },
    "⚡ 電音波/雷射": {
        "context": "討論拉提。關鍵字：鳳凰電波、能量等級、痛感、安慰劑、平替、打心安的。",
        "keywords": ["鳳凰", "安慰劑", "平替", "發數", "痛到想死"],
        "example": "美國版貴到靠北，韓版真的有用嗎？還是只是打個心靈安撫的？"
    },
    "🏥 醫美診所/黑幕": {
        "context": "討論診所推銷。關鍵字：諮詢師話術、審美觀喪失、複製人、強迫推銷、伸手牌。",
        "keywords": ["諮詢師話術", "審美觀喪失", "複製人", "容貌焦慮", "業配感"],
        "example": "進去只是想清個粉刺，諮詢師講得好像我不動手術明天臉就會掉下來。"
    }
}

# --- 3. 模型下拉選擇 ---
@st.cache_resource
def get_models():
    try:
        m_list = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 強制將 1.5-flash 排在第一位，因為它額度最高最不容易報錯
        if "gemini-1.5-flash" in m_list:
            m_list.insert(0, m_list.pop(m_list.index("gemini-1.5-flash")))
        return m_list
    except:
        return ["gemini-1.5-flash", "gemini-1.5-pro"]

# --- 4. 初始化 Session State ---
if 'titles' not in st.session_state: st.session_state.titles = []
if 'sel' not in st.session_state: st.session_state.sel = ""
if 'final_result' not in st.session_state: st.session_state.final_result = None

# --- 5. 側邊欄：安全與檔案處理 ---
with st.sidebar:
    st.header("⚙️ 控制面板")
    selected_model_name = st.selectbox("👇 挑選模型 (首選 Flash)", get_models(), index=0)
    
    st.divider()
    st.header("📁 參考來源 (Excel 已限制列數)")
    
    auto_ref_content = ""
    if os.path.exists("ref_files"):
        files = os.listdir("ref_files")
        for f in files:
            file_path = os.path.join("ref_files", f)
            try:
                if f.endswith(".txt"):
                    with open(file_path, "r", encoding="utf-8") as file:
                        auto_ref_content += f"\n[檔案: {f}]\n{file.read()[:2000]}\n" # 限制 2000 字
                elif f.endswith((".xlsx", ".xls")):
                    # 重要：只讀取前 20 列，避免 Token 爆炸
                    df = pd.read_excel(file_path).head(20)
                    auto_ref_content += f"\n[Excel 表格: {f}]\n{df.to_string(index=False)}\n"
            except: pass
    
    st.session_state.all_references = auto_ref_content

# --- 6. 模型建立 (加入安全設定) ---
# 調低安全過濾，避免因為 PTT 風格而被封鎖
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]
model = genai.GenerativeModel(selected_model_name, safety_settings=safety_settings)

# --- 7. 主介面 ---
col1, col2 = st.columns([1, 2])
with col1:
    tag = st.selectbox("選擇標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題分類：", list(DB.keys()))
with col2:
    imported = st.text_area("📝 參考原文 (選填)：", height=68)

# 生成標題
if st.button("🚀 生成 5 個標題", use_container_width=True):
    ctx = DB[cat]["context"]
    core = imported.strip() if imported.strip() else cat
    refs = st.session_state.all_references
    
    prompt = f"你現在是 PTT 醫美版鄉民。針對「{core}」生成 5 個標題。附件內容：{refs}。限制：禁止編號與廢話，語氣引戰且專業。情境：{ctx}"

    try:
        response = model.generate_content(prompt)
        # 診斷安全封鎖
        if response.candidates[0].finish_reason == 3:
            st.warning("⚠️ 標題生成被安全過濾器攔截，請嘗試修改關鍵字或縮減參考資料。")
        else:
            res = response.text.strip().split('\n')
            final_list = []
            for t in res:
                t = re.sub(r'^[\d\-\.\s\[\]討論問題心得閒聊黑特：:]+', '', t).strip()
                if len(t) > 2: final_list.append(f"{tag} {t}")
            st.session_state.titles = final_list[:5]
            st.session_state.final_result = None
    except Exception as e:
        if "429" in str(e):
            st.error("🚫 API 額度用完了 (每分鐘 Token 限制)。請等 1 分鐘後再試，或更換為 Flash 模型。")
        else:
            st.error(f"❌ 錯誤：{str(e)}")

# 後續顯示邏輯維持穩定版本... (略，建議沿用 V72 的顯示區塊)
