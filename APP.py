# --- PTT 醫美口碑生成器 V77 (變數修正與語感對齊版) ---
# 1. 修復 NameError：統一將參考資料變數名稱定為 all_refs，解決 all_references 未定義的報錯。
# 2. 標題擬真化：嚴格禁止 Emoji，並透過隨機引導詞確保每次點擊生成的 5 個標題角度均不同。
# 3. 推文格式化：固定生成 10 則回文，且開頭統一為「推|」，移除帳號與時間資訊。
# 4. facelift 語感：模擬醫美版求助、避雷、分享的真實氛圍，減少過激用詞。

import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
import re
import os

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美文案 V77", page_icon="💉", layout="wide")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key，請檢查 Streamlit Secrets 設定")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 醫美版情境字典 ---
DB = {
    "💉 針劑/微整": {
        "context": "討論微整分享。焦點：自然感、維持效果、有無饅化或硬塊、醫生技術。",
        "keywords": ["維持度", "饅化", "降解酶", "審美觀", "原廠認證", "填充過度"],
        "example": "最近照鏡子覺得臉有點凹，想去補一點，但很怕板上那種臉僵的感覺..."
    },
    "⚡ 電音波/雷射": {
        "context": "討論拉提雷射。焦點：發數分配、痛感程度、術後對比、CP 值比對。",
        "keywords": ["鳳凰電波", "海芙音波", "發數", "能量等級", "效果維持", "痛感"],
        "example": "考慮很久終於去打了鳳凰，醫生能量開蠻強的，但覺得下顎線有變明顯。"
    },
    "🏥 醫美診所/黑幕": {
        "context": "討論診所經驗。焦點：有無強迫推銷、價格是否透明、諮詢師態度。",
        "keywords": ["諮詢師推銷", "價格透明", "術後關心", "強迫推銷", "避雷"],
        "example": "去這間諮詢覺得壓力很大，諮詢師一直要我刷卡，大家有不推銷的診所嗎？"
    }
}

# --- 3. 模型設定 (提高 Temperature 增加隨機性) ---
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

# --- 5. 側邊欄：檔案讀取與環境檢查 ---
with st.sidebar:
    st.header("⚙️ 控制面板")
    selected_model = st.selectbox("👇 挑選模型", get_models(), index=0)
    
    st.divider()
    st.header("📁 參考內容來源")
    
    # 初始化本次執行的參考文本
    all_refs = ""
    if os.path.exists("ref_files"):
        valid_files = [f for f in os.listdir("ref_files") if f.endswith(('.txt', '.xlsx', '.xls'))]
        for f in valid_files:
            f_path = os.path.join("ref_files", f)
            try:
                if f.endswith(".txt"):
                    with open(f_path, "r", encoding="utf-8") as file:
                        all_refs += f"\n[檔案:{f}]\n{file.read()[:1000]}\n"
                elif f.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(f_path).head(15)
                    all_refs += f"\n[Excel:{f}]\n{df.to_string(index=False)}\n"
            except: pass
        if valid_files: st.success(f"✅ 已讀取 {len(valid_files)} 個檔案")
    
    # 存入 session 供不同按鈕共享
    st.session_state.current_refs = all_refs

# 設定模型
model = genai.GenerativeModel(
    model_name=selected_model,
    generation_config={"temperature": 0.9}, # 調高隨機性確保每次生成不同
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
    ref_data = st.session_state.get('current_refs', "")
    
    # 加入隨機切入點提示，確保每次生成的 5 個標題角度不同
    random_angles = random.sample(["價格疑問", "效果分享", "避雷警告", "醫生技術", "術後疑慮", "CP值分析"], 3)
    
    prompt = f"""你現在是 PTT facelift 版資深鄉民。
    任務：針對主題「{core}」生成 5 個標題。
    【參考附件資料】：{ref_data}
    【嚴格限制】：
    1. 禁止出現任何 Emoji 或表情符號。
    2. 禁止編號，每行僅輸出一個標題。
    3. 語氣要平實、真誠、有分享感，不要過度激進。
    4. 內容要涵蓋以下隨機維度：{', '.join(random_angles)}。
    5. 情境參考：{ctx}"""
    
    try:
        response = model.generate_content(prompt)
        res = response.text.strip().split('\n')
        # 過濾標題並加上標籤
        st.session_state.titles = [f"{tag} {re.sub(r'^[\d\-\.\s\[\]討論問題心得閒聊黑特：:]+', '', t).strip()}" for t in res if len(t)>2][:5]
        st.session_state.final_result = None
    except Exception as e:
        st.error(f"標題生成失敗：{str(e)}")

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
        with st.spinner("正在對齊 facelift 語感撰寫中..."):
            info = DB[cat]
            ref_data = st.session_state.get('current_refs', "")
            
            prompt = f"""你現在是 PTT facelift 版鄉民發文者。
            標題：{st.session_state.sel}
            參考參考資料：{ref_data}
            要求：
            1. 文章內容：150-200 字，禁止打招呼，語氣要真誠且稍微碎念。
            2. 排版：每 25 字左右必須手動換行 (使用 \\n 換行符號)，模擬終端機介面。
            3. 關鍵字：融入「{', '.join(info['keywords'])}」。
            4. 禁止使用 Emoji。
            5. 結尾加上標記 [END]。
            6. 標記後附上 10 則推文內容，語氣要包含詢問價錢、地點或分享類似經驗。"""
            
            try:
                raw_res = model.generate_content(prompt).text
                st.session_state.final_result = raw_res
            except Exception as e:
                st.error(f"文案生成失敗：{str(e)}")

    # 顯示結果
    if st.session_state.final_result:
        res_text = st.session_state.final_result
        if "[END]" in res_text:
            body, cmt_raw = res_text.split("[END]")
            comments = cmt_raw.strip().split("\n")
        else:
            body, comments = res_text, []

        st.info("【 文章內容 】")
        # 顯示內文並保持換行格式
        st.code(body.replace("內文", "").strip(), language=None)
        
        st.warning("【 鄉民反應 】")
        # 固定輸出 10 則開頭為 "推|" 的回文
        display_comments = [c for c in comments if len(c.strip()) > 1][:10]
        for c in display_comments:
            clean_c = re.sub(r'^[推噓→\|:\s\w\d\.-]+', '', c).strip()
            if clean_c:
                st.markdown(f"**推|** {clean_c}")
