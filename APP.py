# --- PTT 醫美口碑生成器 V76 (facelift 深度擬真版) ---
# 1. 標題優化：強制移除 Emoji，並在 Prompt 加入隨機性指令，確保每次點擊生成的角度（價錢、效果、醫生）都不同。
# 2. 語氣校正：對齊 PTT facelift 版真實鄉民語感，減少過度激進的用詞，轉向真實經驗分享。
# 3. 推文格式：固定產出 10 則推文，且所有推文開頭強制格式化為「推|」。
# 4. 內文分行：維持手動換行邏輯，確保在 PTT 介面中閱讀的擬真感。

import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
import re
import os

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美文案 V76", page_icon="💉", layout="wide")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 醫美版專用情境 (facelift 風格) ---
DB = {
    "💉 針劑/微整": {
        "context": "討論微整。焦點：美感、自然度、維持時間、有無副作用、是否饅化。",
        "keywords": ["饅化", "維持度", "降解酶", "審美感", "術後照護", "原廠序號"],
        "example": "最近覺得臉有點凹，想補一點玻尿酸，但又怕像板上說的補到變饅頭人..."
    },
    "⚡ 電音波/雷射": {
        "context": "討論拉提雷射。焦點：發數分配、醫生細心度、原廠認證、痛感比對、CP值。",
        "keywords": ["鳳凰電波", "海芙音波", "發數", "能量等級", "痛感", "效果維持"],
        "example": "考慮很久終於去打了鳳凰，醫生能量開蠻強的，雖然很痛但覺得下顎線有變明顯。"
    },
    "🏥 醫美診所/黑幕": {
        "context": "討論診所經驗。焦點：環境、推銷感、價格透明度、售後服務、避雷。",
        "keywords": ["諮詢師推銷", "價格透明", "術後關心", "強迫推銷", "避雷"],
        "example": "去這間諮詢覺得壓力超大，諮詢師一直要我刷卡買課程，大家有推薦不推銷的診所嗎？"
    }
}

# --- 3. 模型選擇 (調高 Temperature 以增加標題多樣性) ---
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

# 設定模型參數：增加隨機性 (Temperature)
generation_config = {
    "temperature": 0.95,
    "top_p": 1,
    "top_k": 32,
}

model = genai.GenerativeModel(
    model_name=selected_model,
    generation_config=generation_config,
    safety_settings=[{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
)

# --- 6. 主介面 ---
col1, col2 = st.columns([1, 2])
with col1:
    tag = st.selectbox("標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題：", list(DB.keys()))
with col2:
    imported = st.text_area("📝 參考原文 (選填)：", height=68)

# 生成標題建議
if st.button("🚀 生成標題建議", use_container_width=True):
    ctx = DB[cat]["context"]
    core = imported.strip() if imported.strip() else cat
    
    # 在 Prompt 加入「隨機切入點」指令，避免標題僵化
    prompt = f"""你現在是 PTT facelift 版資深鄉民。
    任務：針對主題「{core}」生成 5 個符合醫美版生態的標題。
    【重要限制】：
    1. 禁止使用任何表情符號 (Emoji)。
    2. 禁止編號，每行一個標題。
    3. 每次生成的 5 個標題必須從「不同切入點」出發（例如：一個問價錢、一個分效果、一個求避雷、一個討論醫生、一個心得分享）。
    4. 參考情境：{ctx}
    【參考資料】：{all_references}
    """
    
    try:
        response = model.generate_content(prompt)
        res = response.text.strip().split('\n')
        # 過濾贅詞並加上標籤
        st.session_state.titles = [f"{tag} {re.sub(r'^[\d\-\.\s\[\]討論問題心得閒聊黑特：:]+', '', t).strip()}" for t in res if len(t)>2][:5]
        st.session_state.final_result = None
    except Exception as e:
        st.error(f"標題生成失敗：{e}")

# 標題按鈕區
if st.session_state.titles:
    st.write("### 👇 選擇標題")
    t_cols = st.columns(len(st.session_state.titles))
    for i, t in enumerate(st.session_state.titles):
        if t_cols[i].button(t, key=f"t_{i}"):
            st.session_state.sel = t
            st.session_state.final_result = None

# --- 7. 文案撰寫 ---
if st.session_state.sel:
    st.divider()
    if st.button("✍️ 撰寫完整文案與推文", type="primary"):
        with st.spinner("模擬 facelift 版發文中..."):
            info = DB[cat]
            prompt = f"""你現在是 PTT facelift 版鄉民。
            標題：{st.session_state.sel}
            參考附件資料：{all_refs}
            要求：
            1. 文章內容：約 200 字，語氣真誠、帶點分享的碎念感。
            2. 內文排版：每句 25 字左右必須手動換行 (使用 \n)，模擬終端機閱讀感。
            3. 關鍵字融入：{', '.join(info['keywords'])}。
            4. 禁止出現任何 Emoji。
            5. 結尾加上 [END] 標記。
            6. 標記後附上 10 則回文，回文要討論到細節（如價錢、診所名、痛感等）。"""
            
            try:
                raw_res = model.generate_content(prompt).text
                st.session_state.final_result = raw_res
            except Exception as e:
                st.error(f"文案撰寫失敗：{e}")

    # 穩定顯示生成結果
    if st.session_state.final_result:
        res_text = st.session_state.final_result
        if "[END]" in res_text:
            body, cmt_raw = res_text.split("[END]")
            comments = cmt_raw.strip().split("\n")
        else:
            body, comments = res_text, []

        st.info("【 文章內容 】")
        # 顯示內文並保持手動換行
        st.code(body.replace("內文", "").strip(), language=None)
        
        st.warning("【 鄉民反應 】")
        # 強制格式化為 推| 且顯示 10 筆
        display_comments = [c for c in comments if len(c.strip()) > 2][:10]
        
        for c in display_comments:
            # 清除 AI 可能生成的「推/噓/→」原始符號與 ID
            clean_c = re.sub(r'^[推噓→\|:\s\w\d\.-]+', '', c).strip()
            if clean_c:
                st.markdown(f"**推|** {clean_c}")
            else:
                # 若清除後為空，則顯示原始內容但強制標籤
                st.markdown(f"**推|** {c.strip()[:30]}")
