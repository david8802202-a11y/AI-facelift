


# --- PTT 醫美口碑生成器 V72 (全功能整合穩定版) ---
# 1. 檔案讀取優化：自動偵測 ref_files 資料夾內的 .txt 與 .xlsx，並與手動上傳內容合併。
# 2. 移除語氣拉條：簡化 UI，將語氣強度直接內建在「鄉民人格」指令中，讓標題更引戰。
# 3. 穩定顯示機制：使用 Session State 儲存生成結果，徹底解決點擊按鈕後畫面全白的問題。
# 4. PTT 語感調校：強化「智商稅」、「割韭菜」、「饅化」等 2025/2026 熱門詞彙。
# 5. 模型相容性：保留動態模型清單邏輯，支援 1.5 Pro 與 1.5 Flash。

import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
import re
import os

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美文案 V72", page_icon="💉", layout="wide")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key，請檢查 Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 醫美情境字典 (2026 語感更新) ---
DB = {
    "💉 針劑/微整": {
        "context": "討論微整與填充。關鍵字：饅化、訂閱制、年費、錢坑、降解酶、智商稅、臉僵、醫美孤兒。",
        "keywords": ["訂閱制", "饅化", "年費", "錢坑", "降解酶", "智商稅", "塑膠感"],
        "example": "補完玻尿酸臉腫得像發酵過的饅頭，醫生還一直叫我補，真的當大家是盤子？"
    },
    "⚡ 電音波/雷射": {
        "context": "討論拉提儀器。關鍵字：鳳凰電波、能量等級、痛感、安慰劑、平替、打心安的、貓咪紋。",
        "keywords": ["鳳凰", "安慰劑", "平替", "能量等級", "發數", "痛到想死"],
        "example": "美國版貴到靠北，韓版真的有用嗎？還是只是打個心靈安撫的？"
    },
    "🏥 醫美診所/黑幕": {
        "context": "討論診所推銷亂象。關鍵字：諮詢師話術、審美觀喪失、複製人、強迫推銷、伸手牌、黑心診所。",
        "keywords": ["諮詢師話術", "審美觀喪失", "複製人", "容貌焦慮", "被推銷", "盤子"],
        "example": "進去只是想清個粉刺，諮詢師講得好像我不動手術明天臉就會掉下來。業配感超重。"
    },
    "🔪 整形手術": {
        "context": "討論外科整形。關鍵字：納美人、修復期地獄、翻車、一眼假、高階醫美、打掉重練、二次重修。",
        "keywords": ["一眼假", "納美人", "副作用", "修復期", "整形感", "重修", "翻車"],
        "example": "做完鼻子變超假，修復期腫得像被家暴，現在每天照鏡子都覺得後悔。"
    }
}

# --- 3. 模型下拉選擇 (維持原始動態邏輯) ---
@st.cache_resource
def get_models():
    try:
        m_list = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return m_list
    except:
        return ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"]

# --- 4. 初始化 Session State ---
if 'titles' not in st.session_state: st.session_state.titles = []
if 'sel' not in st.session_state: st.session_state.sel = ""
if 'final_result' not in st.session_state: st.session_state.final_result = None
if 'all_references' not in st.session_state: st.session_state.all_references = ""

# --- 5. 側邊欄：設定與雙重參考機制 ---
with st.sidebar:
    st.header("⚙️ 控制中心")
    selected_model_name = st.selectbox("👇 挑選模型：", get_models(), index=0)
    
    st.divider()
    st.header("📁 參考內容來源")
    
    # 邏輯 A：自動掃描 ref_files 資料夾 (支援 TXT, XLSX)
    auto_ref_content = ""
    if os.path.exists("ref_files"):
        files = os.listdir("ref_files")
        for f in files:
            file_path = os.path.join("ref_files", f)
            try:
                if f.endswith(".txt"):
                    with open(file_path, "r", encoding="utf-8") as file:
                        auto_ref_content += f"\n[資料夾檔案: {f}]\n{file.read()}\n"
                elif f.endswith((".xlsx", ".xls")):
                    df = pd.read_excel(file_path)
                    auto_ref_content += f"\n[資料夾 Excel: {f}]\n{df.to_string(index=False)}\n"
            except Exception as e:
                st.warning(f"讀取 {f} 失敗: {e}")
        if files: st.success(f"✅ 已讀取 {len(files)} 個資料夾檔案")

    # 邏輯 B：手動上傳
    uploaded_files = st.file_uploader("手動上傳檔 (TXT/Excel)", type=['txt', 'xlsx', 'xls'], accept_multiple_files=True)
    manual_ref_content = ""
    if uploaded_files:
        for file in uploaded_files:
            if file.name.endswith('.txt'):
                manual_ref_content += f"\n[上傳檔案: {file.name}]\n{file.read().decode('utf-8')}\n"
            elif file.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
                manual_ref_content += f"\n[上傳 Excel: {file.name}]\n{df.to_string(index=False)}\n"
        st.success(f"✅ 已讀取 {len(uploaded_files)} 個上傳檔案")

    st.session_state.all_references = auto_ref_content + manual_ref_content

model = genai.GenerativeModel(selected_model_name)

# --- 6. 主介面設計 ---
col1, col2 = st.columns([1, 2])
with col1:
    tag = st.selectbox("選擇標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題分類：", list(DB.keys()))
with col2:
    imported = st.text_area("📝 參考原文 (選填)：", height=68, placeholder="可留空，AI 會優先參考上傳的檔案內容...")

# --- 7. 生成標題邏輯 ---
if st.button("🚀 生成 5 個標題 (參考附件)", use_container_width=True):
    ctx = DB[cat]["context"]
    core = imported.strip() if imported.strip() else cat
    refs = st.session_state.all_references
    
    prompt = f"""你現在是 PTT 醫美版資深鄉民，語氣酸溜溜但專業，極度討厭業配。
    任務：針對「{core}」生成 5 個引戰或吸引討論的標題。
    【重要附件參考】：{refs if refs else "無特定參考。"}
    要求：
    1. 標題請參考附件中的具體診所、數據或案例資訊。
    2. 禁止開場白、禁止編號、禁止符號開頭。語氣要像真人。
    3. 每行一個標題，符合情境：{ctx}。"""
# --- 請將生成標題的 try-except 區塊替換為此段 ---
    try:
        response = model.generate_content(prompt)
        
        # 檢查是否被安全機制過濾
        if response.candidates[0].finish_reason == 3: # SAFETY 封鎖
            st.error("🚫 內容被 Gemini 安全過濾器攔截：主題過於敏感或語氣過於激進。")
            st.stop()
            
        res = response.text.strip().split('\n')
        # ... 後續處理邏輯 ...
        
    except Exception as e:
        # 顯示真正的報錯訊息，不要只寫 API 繁忙
        st.error(f"❌ 發生錯誤：{str(e)}")
   
# 標題選擇顯示
if st.session_state.titles:
    st.write("### 👇 選擇採用的標題")
    for i, t in enumerate(st.session_state.titles):
        if st.button(t, key=f"t_{i}", use_container_width=True):
            st.session_state.sel = t
            st.session_state.final_result = None # 切換標題清空結果

# --- 8. 文案撰寫與穩定顯示邏輯 ---
if st.session_state.sel:
    st.divider()
    st.subheader(f"📍 當前標題：{st.session_state.sel}")
    
    if st.button("✍️ 撰寫完整 PTT 文案與推文", type="primary"):
        with st.spinner("AI 鄉民正在敲鍵盤..."):
            info = DB[cat]
            refs = st.session_state.all_references
            prompt = f"""你現在是 PTT 鄉民。
            針對標題「{st.session_state.sel}」寫一篇 150 字內文。
            【參考資料庫】：{refs}
            要求：
            1. 第一人稱視角。禁止問候，直接切入主題（抱怨、分享或詢問）。
            2. 使用「碎念式」短句，融入「欸、笑死、真的、智商稅、避雷」等詞。
            3. 融入關鍵字：{", ".join(info['keywords'])}。
            4. 內容請巧妙引用附件中的數據或細節，像是你親身經歷的一樣。
            5. 文章結束加 [PTT_END]，隨後附上 8 則 PTT 格式推文。"""
            
            try:
                raw_res = model.generate_content(prompt).text
                st.session_state.final_result = raw_res
            except:
                st.error("生成失敗，請再按一次。")

    # 顯示生成結果 (存於 Session State 以防止白屏)
    if st.session_state.final_result:
        full_text = st.session_state.final_result
        if "[PTT_END]" in full_text:
            body, cmt_raw = full_text.split("[PTT_END]")
            comments = cmt_raw.strip().split("\n")
        else:
            body, comments = full_text, []

        st.info("【 文章內文 】")
        st.code(body.replace("內文", "").strip(), language=None)
        
        st.warning("【 鄉民反應 】")
        prefix_pool = ["推", "推", "→", "→", "噓", "推", "→"]
        for c in comments:
            clean_c = re.sub(r'^[推噓→\|:\s\d\.-]+', '', c).strip().replace("?", "").replace("？", "")
            if len(clean_c) > 2:
                st.write(f"**{random.choice(prefix_pool)}** | {clean_c}")
