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
        【主題內容】：{core}
        限制：
        1. 禁止廢話、禁止編號、禁止開場白。
        2. 每行一個標題。語氣要像真人、犀利、討厭業配。
        3. 情境：{ctx}"""

        try:
            response = model.generate_content(prompt)
            # 檢查 API 是否回傳了內容
            if response.candidates and response.candidates[0].content.parts:
                res = response.text.strip().split('\n')
                final_list = []
                for t in res:
                    t = re.sub(r'^[\d\-\.\s\[\]討論問題心得閒聊黑特：:]+', '', t).strip()
                    if len(t) > 2: final_list.append(f"{tag} {t}")
                st.session_state.titles = final_list[:5]
                st.session_state.final_result = None
            else:
                st.error("⚠️ API 未回傳標題。可能是安全過濾封鎖，請嘗試簡化參考資料內容。")
        except Exception as e:
            if "429" in str(e):
                st.error("🚫 額度已滿。請切換為 Flash 模型，或等一分鐘再試。")
            else:
                st.error(f"❌ 錯誤：{str(e)}")

# --- 8. 顯示標題按鈕 (獨立於生成按鈕外) ---
if st.session_state.titles:
    st.write("### 👇 選擇標題開始撰寫")
    # 使用 columns 讓按鈕橫向排列，節省空間
    t_cols = st.columns(len(st.session_state.titles))
    for i, t in enumerate(st.session_state.titles):
        if t_cols[i].button(t, key=f"t_{i}"):
            st.session_state.sel = t
            st.session_state.final_result = None

# --- 9. 文案撰寫與顯示 ---
if st.session_state.sel:
    st.divider()
    st.subheader(f"📍 當前標題：{st.session_state.sel}")
    
    if st.button("✍️ 撰寫內文與推文", type="primary"):
        with st.spinner("AI 鄉民打字中..."):
            info = DB[cat]
            prompt = f"""你現在是 PTT 鄉民。
            針對標題「{st.session_state.sel}」寫一篇 150 字內文。
            參考附件：{all_refs}
            要求：第一人稱，禁止打招呼。語句要短、自然、帶情緒。
            必須融入關鍵字：{", ".join(info['keywords'])}。
            結尾加 [END]，隨後附上 8 則 PTT 格式推文。"""
            
            try:
                raw_res = model.generate_content(prompt).text
                st.session_state.final_result = raw_res
            except Exception as e:
                st.error(f"生成失敗：{str(e)}")

    if st.session_state.final_result:
        full_text = st.session_state.final_result
        if "[END]" in full_text:
            body, cmt_raw = full_text.split("[END]")
            comments = cmt_raw.strip().split("\n")
        else:
            body, comments = full_text, []

        st.info("【 文章內容 】")
        st.code(body.replace("內文", "").strip(), language=None)
        
        st.warning("【 鄉民反應 】")
        for c in comments:
            clean_c = re.sub(r'^[推噓→\|:\s\d\.-]+', '', c).strip().replace("?", "").replace("？", "")
            if len(clean_c) > 2:
                st.write(f"**{random.choice(['推', '→', '噓', '推'])}** | {clean_c}")
