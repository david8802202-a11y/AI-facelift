# --- PTT 醫美口碑生成器 V80 (真人敘事與資料隔離版) ---
# 1. 深度清理：使用 .fillna('') 徹底移除 NaN，並限制 Excel 轉字串的寬度，減少干擾。
# 2. 角色鎖定：將 Persona 鎖定為「剛動完手術、正在休息碎念」的網友，而非「資訊整理者」。
# 3. 輸出過濾：新增後處理邏輯，強制刪除所有包含「[Excel:」或「[檔案:」的行數。
# 4. 格式格式化：嚴格執行 推| 格式，並固定產出 10 則高品質回文。

import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
import re
import os

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美文案 V80", page_icon="💉", layout="wide")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 醫美版專用資料庫 ---
DB = {
    "💉 針劑/微整": {
        "context": "討論微整分享。焦點：自然度、有無饅化、醫生審美、術後維持時間。",
        "keywords": ["維持度", "饅化", "降解酶", "醫生美感", "術後照護", "原廠序號"],
        "example": "最近看鏡子覺得臉有點凹，想去補一點，但真的很怕補到臉很僵..."
    },
    "⚡ 電音波/雷射": {
        "context": "討論拉提雷射。焦點：發數分配、能量級數、痛感比較、醫師細心度。",
        "keywords": ["鳳凰電波", "海芙音波", "發數", "能量等級", "效果維持", "痛感"],
        "example": "終於去打了鳳凰，醫生能量開得不低，雖然痛但效果真的很有感。"
    },
    "🏥 醫美診所/黑幕": {
        "context": "討論診所經驗。焦點：價格透明度、諮詢師態度、有無強迫推銷、售後服務。",
        "keywords": ["諮詢師推銷", "價格透明", "術後關心", "強迫推銷", "避雷"],
        "example": "去這間諮詢覺得壓力超大，諮詢師一直要我買課程，大家有推薦不推銷的嗎？"
    }
}

# --- 3. 模型下拉選擇 ---
@st.cache_resource
def get_models():
    try:
        m_list = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        pref = ["gemini-1.5-flash", "gemini-1.5-pro"]
        return [m for m in pref if m in m_list] + [m for m in m_list if m not in pref]
    except:
        return ["gemini-1.5-flash", "gemini-1.5-pro"]

# --- 4. 初始化 Session State ---
if 'titles' not in st.session_state: st.session_state.titles = []
if 'sel' not in st.session_state: st.session_state.sel = ""
if 'final_result' not in st.session_state: st.session_state.final_result = None

# --- 5. 側邊欄：檔案讀取與清理 ---
with st.sidebar:
    st.header("⚙️ 控制面板")
    selected_model = st.selectbox("👇 挑選模型", get_models(), index=0)
    
    st.divider()
    st.header("📁 參考內容來源")
    
    all_refs = ""
    if os.path.exists("ref_files"):
        files = os.listdir("ref_files")
        valid_files = [f for f in files if f.endswith(('.txt', '.xlsx', '.xls'))]
        for f in valid_files:
            f_path = os.path.join("ref_files", f)
            try:
                if f.endswith(".txt"):
                    with open(f_path, "r", encoding="utf-8") as file:
                        all_refs += f"\n[DOC_START]\n{file.read()[:800]}\n[DOC_END]\n"
                elif f.endswith(('.xlsx', '.xls')):
                    # 徹底移除 NaN 並轉為字串
                    df = pd.read_excel(f_path).fillna('').head(12)
                    all_refs += f"\n[DATA_START]\n{df.to_string(index=False)}\n[DATA_END]\n"
            except: pass
        
        if valid_files: 
            st.success(f"✅ 已讀取 {len(valid_files)} 個檔案")
            st.session_state.all_refs = all_refs
        else:
            st.session_state.all_refs = ""

# --- 6. 模型建立 ---
model = genai.GenerativeModel(
    model_name=selected_model,
    generation_config={"temperature": 0.95},
    safety_settings=[{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
)

# --- 7. 主介面 ---
col1, col2 = st.columns([1, 2])
with col1:
    tag = st.selectbox("標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題：", list(DB.keys()))
with col2:
    imported = st.text_area("📝 參考原文 (選填)：", height=68, placeholder="可留空，或貼上內容讓 AI 進行二創...")

# 生成標題
if st.button("🚀 生成標題建議", use_container_width=True):
    ctx = DB[cat]["context"]
    core_text = imported.strip() if imported.strip() else cat
    ref_data = st.session_state.get('all_refs', "")
    
    prompt = f"""你現在是 PTT facelift 版資深鄉民。
    【任務】：針對主題「{core_text}」生成 5 個標題。
    【參考數據】：{ref_data}
    【限制要求】：
    1. 絕對禁止使用 Emoji。
    2. 禁止在標題中出現檔名、表格標題、NaN 或 [DATA_START] 等字眼。
    3. 語氣要像真人在板上詢問或分享心得。
    4. 每次點擊生成的 5 個標題必須角度互異（詢問價錢/分享效果/求避雷）。
    5. 情境：{ctx}"""
    
    try:
        response = model.generate_content(prompt)
        res_lines = response.text.strip().split('\n')
        st.session_state.titles = [f"{tag} {re.sub(r'^[\d\-\.\s\[\]討論問題心得閒聊黑特：:]+', '', t).strip()}" for t in res_lines if len(t)>2][:5]
        st.session_state.final_result = None
    except Exception as e:
        st.error(f"標題生成失敗：{str(e)}")

# 標題選擇按鈕
if st.session_state.titles:
    st.write("### 👇 選擇標題")
    t_cols = st.columns(len(st.session_state.titles))
    for i, t in enumerate(st.session_state.titles):
        if t_cols[i].button(t, key=f"t_{i}"):
            st.session_state.sel = t
            st.session_state.final_result = None

# --- 8. 文案撰寫 ---
if st.session_state.sel:
    st.divider()
    if st.button("✍️ 撰寫完整文案與推文", type="primary"):
        with st.spinner("模擬 facelift 鄉民撰寫中..."):
            info = DB[cat]
            ref_data = st.session_state.get('all_refs', "")
            
            prompt = f"""你現在是 PTT facelift 版鄉民發文者。
            【標題】：{st.session_state.sel}
            【參考資訊】：{ref_data}
            【寫作指令】：
            1. 你正在寫一篇分享或詢問文，約 200 字，語氣真誠且稍微碎念。
            2. 嚴格禁止列出「參考資料」、「檔案名稱」或任何 Excel 表格內容。
            3. 每 25 字左右必須手動換行 (使用 \\n)。
            4. 融入關鍵字：{', '.join(info['keywords'])}。禁止使用 Emoji。
            5. 結尾加上 [END]。
            6. 標記後附上 10 則「推|」開頭的鄉民評論，討論要具體（如：價錢、診所名）。"""
            
            try:
                raw_res = model.generate_content(prompt).text
                st.session_state.final_result = raw_res
            except Exception as e:
                st.error(f"文案生成失敗：{str(e)}")

    if st.session_state.final_result:
        res_text = st.session_state.final_result
        if "[END]" in res_text:
            body, cmt_raw = res_text.split("[END]")
            comments = cmt_raw.strip().split("\n")
        else:
            body, comments = res_text, []

        st.info("【 文章內容 】")
        # 清除 AI 常犯的錯誤（在內文重複標題或列出參考資料）
        clean_body = re.sub(r'(參考資料|Excel|表格資訊|檔案名稱)\s*[:：].*', '', body, flags=re.S | re.I).strip()
        st.code(clean_body, language=None)
        
        st.warning("【 鄉民反應 】")
        display_comments = [c for c in comments if len(c.strip()) > 1][:10]
        for c in display_comments:
            # 移除所有模擬帳號與複雜符號
            clean_c = re.sub(r'^[推噓→\|:\s\w\d\.-]+', '', c).strip()
            if clean_c:
                st.markdown(f"**推|** {clean_c}")
