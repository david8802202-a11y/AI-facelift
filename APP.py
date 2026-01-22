# --- PTT 醫美口碑生成器 V78 (變數與格式徹底修正版) ---
# 1. 修復 NameError：全程式統一使用 st.session_state.all_refs，解決變數未定義報錯。
# 2. 移除 Excel 亂碼：優化讀取邏輯 (fillna('')) 並強制 AI 禁止在輸出中重複參考資料的原始表格。
# 3. 標題隨機性：透過 random.sample 加入多樣化切入點，確保每次生成標題都不同。
# 4. facelift 語感：維持 V76 的穩定優良語感，移除 Emoji，推文固定 10 則且開頭為「推|」。

import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
import re
import os

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美文案 V78", page_icon="💉", layout="wide")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key，請檢查 Secrets 設定")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 醫美版專用語感字典 (facelift 風格) ---
DB = {
    "💉 針劑/微整": {
        "context": "討論微整分享。焦點：自然感、有無饅化或硬塊、醫生美感、術後維持時間。",
        "keywords": ["維持度", "饅化", "降解酶", "美感", "術後照護", "原廠序號"],
        "example": "最近看鏡子覺得淚溝很深，想去補一點，但真的很怕補到臉很僵..."
    },
    "⚡ 電音波/雷射": {
        "context": "討論拉提雷射。焦點：發數分配、能量等級、醫生細心度、痛感比較、CP值。",
        "keywords": ["鳳凰電波", "海芙音波", "發數", "能量等級", "效果維持", "痛感"],
        "example": "終於去打了期待已久的鳳凰，醫生能量開得不低，雖然痛但效果很有感。"
    },
    "🏥 醫美診所/黑幕": {
        "context": "討論診所經驗。焦點：價格透明度、有無強迫推銷、環境設備、售後服務。",
        "keywords": ["諮詢師推銷", "價格透明", "術後關心", "強迫推銷", "避雷"],
        "example": "去這間諮詢覺得壓力超大，諮詢師一直要我買課程，大家有推薦不推銷的嗎？"
    }
}

# --- 3. 模型下拉選擇 (維持動態清單) ---
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
if 'all_refs' not in st.session_state: st.session_state.all_refs = ""

# --- 5. 側邊欄：檔案讀取與環境檢查 ---
with st.sidebar:
    st.header("⚙️ 控制面板")
    selected_model = st.selectbox("👇 挑選模型", get_models(), index=0)
    
    st.divider()
    st.header("📁 參考內容來源")
    
    temp_refs = ""
    if os.path.exists("ref_files"):
        valid_files = [f for f in os.listdir("ref_files") if f.endswith(('.txt', '.xlsx', '.xls'))]
        for f in valid_files:
            f_path = os.path.join("ref_files", f)
            try:
                if f.endswith(".txt"):
                    with open(f_path, "r", encoding="utf-8") as file:
                        temp_refs += f"\n[參考文字:{f}]\n{file.read()[:800]}\n"
                elif f.endswith(('.xlsx', '.xls')):
                    # 修正：fillna('') 處理 NaN，防止 AI 輸出亂碼
                    df = pd.read_excel(f_path).fillna('').head(12)
                    temp_refs += f"\n[參考表格:{f}]\n{df.to_string(index=False)}\n"
            except Exception as e:
                st.warning(f"檔案 {f} 讀取出錯")
        
        if valid_files: 
            st.success(f"✅ 已讀取 {len(valid_files)} 個檔案")
            st.session_state.all_refs = temp_refs
        else:
            st.session_state.all_refs = ""
            st.info("請將檔案放入 ref_files 資料夾")

model = genai.GenerativeModel(
    model_name=selected_model,
    generation_config={"temperature": 0.95}, # 保持標題多樣性
    safety_settings=[{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
)

# --- 6. 主介面 ---
col1, col2 = st.columns([1, 2])
with col1:
    tag = st.selectbox("標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題：", list(DB.keys()))
with col2:
    imported = st.text_area("📝 參考原文 (選填)：", height=68, placeholder="可留空，或貼上內容讓 AI 改寫...")

# 生成標題建議 (修正邏輯與隨機性)
if st.button("🚀 生成標題建議", use_container_width=True):
    ctx = DB[cat]["context"]
    core_text = imported.strip() if imported.strip() else cat
    ref_data = st.session_state.all_refs
    
    # 增加隨機維度以確保標題不同
    angles = random.sample(["價格與CP值", "效果真實心得", "術後副作用紀錄", "醫師技術評論", "避雷提醒", "能量等級分享"], 3)
    
    prompt = f"""你現在是 PTT facelift 版資深鄉民。
    任務：針對主題「{core_text}」生成 5 個標題。
    【參考附件內容】：{ref_data}
    【限制要求】：
    1. 禁止使用 Emoji。禁止編號，每行一個標題。
    2. 不要重複附件中的原始檔名或表格內容在標題裡。
    3. 語氣要像真人發文（如：求推薦、分享、入坑紀錄、反推）。
    4. 必須從以下角度切入：{', '.join(angles)}。
    5. 情境：{ctx}"""
    
    try:
        response = model.generate_content(prompt)
        res_lines = response.text.strip().split('\n')
        # 過濾贅詞
        st.session_state.titles = [f"{tag} {re.sub(r'^[\d\-\.\s\[\]討論問題心得閒聊黑特：:]+', '', t).strip()}" for t in res_lines if len(t)>2][:5]
        st.session_state.final_result = None
    except Exception as e:
        st.error(f"標題生成失敗，請再點一次：{str(e)}")

# 標題按鈕區
if st.session_state.titles:
    st.write("### 👇 選擇標題")
    t_cols = st.columns(len(st.session_state.titles))
    for i, t in enumerate(st.session_state.titles):
        if t_cols[i].button(t, key=f"t_{i}"):
            st.session_state.sel = t
            st.session_state.final_result = None

# --- 7. 文案撰寫 (強化輸出過濾與分行) ---
if st.session_state.sel:
    st.divider()
    if st.button("✍️ 撰寫完整文案與推文", type="primary"):
        with st.spinner("模擬 facelift 版發文中..."):
            info = DB[cat]
            ref_data = st.session_state.all_refs
            
            prompt = f"""你現在是 PTT facelift 版鄉民。
            標題：{st.session_state.sel}
            參考參考資料：{ref_data}
            【重要輸出限制】：
            1. 禁止在文案中列出「參考資料：[Excel:...]」或原始表格。
            2. 內容約 200 字，禁止打招呼，語氣要真誠且帶點碎念。
            3. 每 25 字左右強制換行 (\\n)，模擬終端機閱讀質感。
            4. 禁止使用 Emoji。關鍵字：{', '.join(info['keywords'])}。
            5. 結尾加上 [END]。
            6. 標記後附上 10 則開頭為「推|」的回文內容。"""
            
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
        # 清除 AI 可能在內文重複的參考標記
        clean_body = re.sub(r'參考資料\s*[:：].*', '', body, flags=re.S).strip()
        st.code(clean_body, language=None)
        
        st.warning("【 鄉民反應 】")
        # 強制輸出 10 則「推|」回文
        display_comments = [c for c in comments if len(c.strip()) > 1][:10]
        for c in display_comments:
            clean_c = re.sub(r'^[推噓→\|:\s\w\d\.-]+', '', c).strip()
            if clean_c:
                st.markdown(f"**推|** {clean_c}")
