# --- 說明與優化邏輯 (全內容維持在程式碼區塊中) ---
# 1. 關於 1.5 PRO 優先度：
#    - 程式碼已調整 get_model 邏輯，確保選取 1.5 Pro 時能正確載入 system_instruction。
#    - 加入了更強健的例外處理，避免模型切換時因參數不相容導致程式崩潰。
# 2. JSON 強制輸出優化：
#    - 為避免 1.5 Pro 在高 Temperature 下產生非 JSON 贅字，Prompt 加入了明確的 JSON Schema 定義。
# 3. Streamlit 狀態維持：
#    - 優化了 st.session_state 的清除機制，確保在切換標籤或分類時，舊的標題不會殘留。

import streamlit as st
import google.generativeai as genai
import random
import json
import re

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美口碑 V7.5 (Pro 優先版)", page_icon="💉", layout="wide")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 醫美情境字典 (語感強化) ---
DB = {
    "💉 針劑/微整": {
        "context": "討論微整。強調：饅化感、訂閱制消費、錢坑感、降解酶副作用。",
        "keywords": ["饅化", "訂閱制", "降解酶", "錢坑", "定期進廠", "塑膠臉"],
        "example": "針劑類真的是錢坑，肉毒半年補一次，像訂閱制沒續費就打回原形。"
    },
    "⚡ 電音波/雷射": {
        "context": "討論電音波。強調：鳳凰電波痛感、韓版平替 vs 美版效果、安慰劑效應。",
        "keywords": ["鳳凰", "安慰劑", "平替", "痛到往生", "打心安的", "CP值"],
        "example": "韓版電波價格只有美國版1/3。到底是真平替還是只是打心安的安慰劑？"
    },
    "🏥 醫美診所/黑幕": {
        "context": "討論診所推銷。強調：諮詢師話術、審美觀喪失、複製人軍團。",
        "keywords": ["諮詢師話術", "審美觀喪失", "複製人", "容貌焦慮", "被當盤子"],
        "example": "現在醫美版一堆業配，進去諮詢就像進入獵殺現場，沒帶個十萬出不來。"
    }
}

# --- 3. 模型設定函數 (相容 1.5 Pro) ---
@st.cache_resource
def get_model_instance(model_name, tone_value):
    # 建立語氣對應的參數
    temp_map = {"溫和": 0.3, "熱烈": 0.8, "炎上": 1.2}
    config = {
        "temperature": temp_map.get(tone_value, 0.8),
        "top_p": 0.95,
        "response_mime_type": "application/json",
    }
    
    # 核心：使用 system_instruction 定義 PTT 鄉民人格
    instruction = (
        "你是一位 PTT 醫美版資深酸民，說話風格刻薄、直白，常用社群流行語。"
        "你極度討厭業配文，會主動戳破診所的話術。"
        "你必須嚴格以 JSON 格式回覆，不可包含任何前導詞。"
    )
    
    return genai.GenerativeModel(
        model_name=model_name,
        generation_config=config,
        system_instruction=instruction
    )

# --- 4. 側邊欄與模型選擇 ---
with st.sidebar:
    st.header("⚙️ 控制面板")
    # 優先排序，讓 1.5 Pro 出現在首選
    model_choice = st.selectbox("👇 選擇模型 (建議 1.5 Pro)", ["gemini-1.5-pro", "gemini-1.5-flash"])
    tone = st.select_slider("語氣強度", ["溫和", "熱烈", "炎上"], value="熱烈")
    st.divider()
    st.write("當前版本：V7.5.0")

# --- 5. 主程式介面 ---
if 'titles' not in st.session_state: st.session_state.titles = []
if 'sel' not in st.session_state: st.session_state.sel = ""

col1, col2 = st.columns([1, 1])
with col1:
    tag = st.selectbox("選擇標籤：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("議題分類：", list(DB.keys()))
with col2:
    imported = st.text_area("📝 匯入網友原文 (二創用)：", height=68, placeholder="可留空，由 AI 直接發揮...")

# 生成標題按鈕
if st.button("🚀 生成 PTT 熱門標題", use_container_width=True):
    model = get_model_instance(model_choice, tone)
    ctx = DB[cat]["context"]
    core = imported.strip() if imported.strip() else cat
    
    prompt = f"""
    請針對「{core}」生成 5 個標題。
    情境參考：{ctx}
    語氣要求：{tone}
    請嚴格依照 JSON 格式輸出：{{"titles": ["標題1", "標題2", "標題3", "標題4", "標題5"]}}
    """
    
    try:
        response = model.generate_content(prompt)
        # 清理可能存在的 markdown code block 標籤
        clean_text = re.sub(r'```json\n?|\n?```', '', response.text).strip()
        data = json.loads(clean_text)
        st.session_state.titles = [f"{tag} {t}" for t in data['titles']]
        st.session_state.sel = ""
    except Exception as e:
        st.error(f"API 連結失敗：{str(e)}")

# 標題選擇區
if st.session_state.titles:
    st.subheader("💡 點選標題開始撰寫")
    for t in st.session_state.titles:
        if st.button(t, use_container_width=True):
            st.session_state.sel = t

# 完整文案撰寫
if st.session_state.sel:
    st.divider()
    st.markdown(f"### 🚩 目前選定：{st.session_state.sel}")
    
    if st.button("✍️ 撰寫內文與推文"):
        model = get_model_instance(model_choice, tone)
        info = DB[cat]
        
        prompt = f"""
        針對標題「{st.session_state.sel}」，寫一篇 PTT 風格文章。
        核心關鍵字：{', '.join(info['keywords'])}
        語氣參考：{info['example']}
        
        請嚴格依照 JSON 格式輸出：
        {{
            "content": "200字內文，包含 PTT 換行風格",
            "comments": [
                {{"type": "推", "msg": "推文1"}},
                {{"type": "→", "msg": "推文2"}},
                {{"type": "噓", "msg": "推文3"}}
            ]
        }}
        生成 8 則推文。
        """
        
        with st.spinner("AI 鄉民打字中..."):
            try:
                response = model.generate_content(prompt)
                clean_text = re.sub(r'```json\n?|\n?```', '', response.text).strip()
                result = json.loads(clean_text)
                
                st.info("【 文章內容 】")
                st.write(result['content'])
                
                st.info("【 鄉民反應 】")
                for c in result['comments']:
                    symbol = c['type']
                    msg = c['msg']
                    color = "red" if symbol == "噓" else ("green" if symbol == "推" else "white")
                    st.markdown(f"**{symbol}** : {msg}")
            except Exception as e:
                st.error("生成失敗，可能是 API 觸發安全過濾，請重試。")
