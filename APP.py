# --- PTT 醫美口碑生成器 V74 (標題修復與額度保護版) ---
# 1. 顯示修復：確保標題生成與顯示邏輯獨立，避免因為一次報錯導致按鈕永久消失。
# 2. Excel 讀取防撞：限制 Excel 讀取前 15 列，並強制轉換為字串，避免 Token 溢出。
# 3. 除錯模式：在生成時會抓取完整的 Response 內容，若被過濾會明確顯示原因。
# 4. 移除語氣拉條：維持簡潔介面，語氣由 Prompt 內建的「鄉民人格」控制。

import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
import re
import os

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美文案 V74", page_icon="💉", layout="wide")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key，請檢查 Secrets。")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 議題分類定義 ---
DB = {
    "💉 針劑/微整": {
        "context": "討論微整。關鍵字：饅化、訂閱制、年費、錢坑、降解酶、智商稅。",
        "keywords": ["訂閱制", "饅化", "年費", "錢坑", "智商稅"],
        "example": "補完玻尿酸臉腫得像饅頭，真的當大家是盤子？"
    },
    "⚡ 電音波/雷射": {
        "context": "討論拉提。關鍵字：鳳凰電波、能量等級、痛感、安慰劑、平替、打心安的。",
        "keywords": ["鳳凰", "安慰劑", "平替", "發數", "痛到想死"],
        "example": "美國版貴到靠北，韓版真的有用嗎？還是只是打個心靈安撫的？"
    },
    "🏥 醫美診所/黑幕": {
        "context": "討論診所推銷。關鍵字：諮詢師話術、審美觀喪失、複製人、強迫推銷。",
        "keywords": ["諮詢師話術", "審美觀喪失", "複製人", "業配感"],
        "example": "進去只是想清粉刺，諮詢師講得好像我不動手術明天臉就會掉下來。"
    }
}

# --- 3. 模型下拉清單 (優先度排序) ---
@st.cache_resource
def get_models():
    try:
        m_list = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 優先建議使用 flash，因為免費額度最高，不易出現 429
        preferred = ["gemini-1.5-flash", "gemini-1.5-pro"]
        m_list = [m for m in preferred if m in m_list] + [m for m in m_list if m not in preferred]
        return m_list
    except:
        return ["gemini-1.5-flash", "gemini-1.5-pro"]

# --- 4. 初始化 Session State (穩定顯示的關鍵) ---
if 'titles' not in st.session_state: st.session_state.titles = []
if 'sel' not in st.session_state: st.session_state.sel = ""
if 'final_result' not in st.session_state: st.session_state.final_result = None

# --- 5. 側邊欄：檔案讀取 ---
with st.sidebar:
    st.header("⚙️ 控制面板")
    selected_model = st.selectbox("👇 挑選模型", get_models(), index=0)
    
    st.divider()
    st.header("📁 資料夾參考狀態")
    
    all_refs = ""
    if os.path.exists("ref_files"):
        files = os.listdir("ref_files")
        valid_files = [f for f in files if f.endswith(('.txt', '.xlsx', '.xls'))]
        for f in valid_files:
            f_path = os.path.join("ref_files", f)
            try:
                if f.endswith(".txt"):
                    with open(f_path, "r", encoding="utf-8") as file:
                        all_refs += f"\n[檔案:{f}]\n{file.read()[:1000]}\n"
                elif f.endswith((".xlsx", ".xls")):
                    # 只取前 15 列，避免 Token 過多導致 429 錯誤
                    df = pd.read_excel(f_path).head(15)
                    all_refs += f"\n[Excel:{f}]\n{df.to_string(index=False)}\n"
            except: pass
        
        if valid_files:
            st.success(f"已讀取 {len(valid_files)} 個參考檔")
        else:
            st.info("ref_files 資料夾內尚無 .txt 或 .xlsx")
    else:
        st.warning("找不到 ref_files 資料夾")

# --- 6. 模型建立 ---
# 加入安全設定，防止因為語氣太酸而被 API 封鎖
model = genai.GenerativeModel(
    model_name=selected_model,
    safety_settings=[
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
)

# --- 7. 主介面 ---
col1, col2 = st.columns([1, 2])
with col1:
    tag = st.selectbox("標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題：", list(DB.keys()))
with col2:
    imported = st.text_area("📝 參考原文 (選填)：", height=68, placeholder="可留空，AI 會參考資料夾檔案...")

# 生成標題
if st.button("🚀 生成標題建議", use_container_width=True):
    with st.spinner("正在根據附件生成標題..."):
        ctx = DB[cat]["context"]
        core = imported.strip() if imported.strip() else cat
        
        prompt = f"""你現在是 PTT 醫美版資深鄉民。
        任務：針對以下內容生成 5 個引戰或能激起討論的標題。
        【參考附件資料】：{all_refs if all_refs else "無"}
