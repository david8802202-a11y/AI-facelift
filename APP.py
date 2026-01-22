import streamlit as st
import google.generativeai as genai
import random
import json
import re

# --- 1. 頁面設定 ---
st.set_page_config(page_title="PTT 醫美口碑生成器 V7.0", page_icon="💉", layout="wide")
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 找不到 API Key")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 醫美情境字典 (強化 PTT 語感) ---
DB = {
    "💉 針劑/微整": {
        "context": "討論微整。強調：過度填充感、像充氣娃娃、定期回診的疲勞感。",
        "keywords": ["饅化", "訂閱制", "降解酶", "錢坑", "膠原蛋白流失", "補到變形"],
        "example": "針劑真的是條不歸路，身邊朋友補到臉都僵了還覺得不夠。"
    },
    "⚡ 電音波/雷射": {
        "context": "討論拉提雷射。強調：痛感、CP值比較、美國版與韓版的價差爭議。",
        "keywords": ["鳳凰電波", "玩真的還是玩心安", "平替版", "痛到往生", "沒效最貴"],
        "example": "打完鳳凰臉真的有縮，但那個荷包失血的速度比臉垂還快。"
    },
    "🏥 醫美診所/黑幕": {
        "context": "討論診所行銷亂象。強調：諮詢師強硬推銷、複製人臉、美感喪失。",
        "keywords": ["諮詢師話術", "盤子", "審美疲勞", "複製人", "容貌焦慮", "業配感"],
        "example": "現在診所推銷越來越誇張，進去只是想清粉刺出來變要分期割雙眼皮。"
    },
    "🔪 整形手術": {
        "context": "討論高階整形。強調：修復期的煎熬、一眼假、自然的邊界感。",
        "keywords": ["納美人", "縮鼻翼", "修復期", "整形痕跡", "人工感", "打掉重練"],
        "example": "雖然動過，但做得好真的看不出來，最慘的是花大錢還變蛇精男。"
    }
}

# --- 3. 模型設定與 System Instruction ---
@st.cache_resource
def get_model(selected_model, tone_value):
    # 根據語氣強度設定 Temperature
    temp_map = {"溫和": 0.4, "熱烈": 0.7, "炎上": 1.1}
    
    generation_config = {
        "temperature": temp_map.get(tone_value, 0.7),
        "top_p": 0.95,
        "response_mime_type": "application/json", # 強制 JSON 輸出
    }
    
    # 這裡將人格特質寫入 System Instruction
    system_instruction = (
        "你是一位混跡 PTT 醫美版多年的老鄉民，說話風格犀利、直白，不屑於客套。"
        "你會使用『肥宅』、『原PO』、『盤子』、『酸民』等社群用語。"
        "你對醫美產業的黑幕瞭若指掌，討厭過度業配的行為。"
        "所有輸出必須嚴格遵循 JSON 格式。"
    )
    
    return genai.GenerativeModel(
        model_name=selected_model,
        generation_config=generation_config,
        system_instruction=system_instruction
    )

# --- 4. Sidebar 設定 ---
with st.sidebar:
    st.header("⚙️ 進階控制項")
    selected_model = st.selectbox("👇 模型選擇", ["gemini-1.5-flash", "gemini-1.5-pro"])
    tone = st.select_slider("語氣強度", ["溫和", "熱烈", "炎上"], value="熱烈")
    st.divider()
    st.caption("V7.0 優化：JSON 結構化輸出 & 溫度動態調校")

# --- 5. 主介面邏輯 ---
if 'titles' not in st.session_state: st.session_state.titles = []
if 'sel' not in st.session_state: st.session_state.sel = ""

col1, col2 = st.columns([1, 1])
with col1:
    tag = st.selectbox("標題類型：", ["[討論]", "[問題]", "[心得]", "[閒聊]", "[黑特]"])
    cat = st.selectbox("核心議題：", list(DB.keys()))
with col2:
    imported = st.text_area("📝 參考資料/原文 (選填)：", height=68)

# 生成標題
if st.button("🚀 構思 PTT 熱門標題", use_container_width=True):
    model = get_model(selected_model, tone)
    ctx = DB[cat]["context"]
    core_content = imported if imported else cat
    
    prompt = f"""
    請針對以下主題生成 5 個吸引 PTT 鄉民點閱的標題：
    主題：{core_content}
    分類情境：{ctx}
    
    請以 JSON 格式輸出：
    {{
        "titles": ["標題1", "標題2", "標題3", "標題4", "標題5"]
    }}
    注意：標題不可包含分類標籤(如[討論])，語氣需呈現「{tone}」感。
    """
    
    try:
        response = model.generate_content(prompt)
        res_json = json.loads(response.text)
        st.session_state.titles = [f"{tag} {t}" for t in res_json['titles']]
        st.session_state.sel = "" # 重置選擇
    except Exception as e:
        st.error(f"生成出錯：{e}")

# 展示標題供選擇
if st.session_state.titles:
    st.markdown("### 💡 鄉民可能會想看的標題：")
    for t in st.session_state.titles:
        if st.button(t, use_container_width=True):
            st.session_state.sel = t

# 撰寫文案
if st.session_state.sel:
    st.divider()
    st.subheader(f"📍 當前選用標題：{st.session_state.sel}")
    
    if st.button("✍️ 開始撰寫完整 PTT 文章與推文"):
        model = get_model(selected_model, tone)
        info = DB[cat]
        
        prompt = f"""
        針對標題「{st.session_state.sel}」，撰寫一篇 PTT 風格文章。
        情境：{info['context']}
        必須包含關鍵字：{', '.join(info['keywords'])}
        參考語氣：{info['example']}
        
        請以 JSON 格式輸出：
        {{
            "content": "文章內文，約 200 字，要像真人發文，有換行",
            "comments": [
                {{"type": "推", "text": "推文內容"}},
                {{"type": "噓", "text": "噓文內容"}},
                {{"type": "→", "text": "註解內容"}}
            ]
        }}
        生成 8 則推文，包含「推」、「噓」、「→」，比例隨機。
        """
        
        with st.spinner("AI 鄉民正在敲鍵盤..."):
            try:
                response = model.generate_content(prompt)
                res_data = json.loads(response.text)
                
                # 顯示內文
                st.info("【 文章內文 】")
                st.write(res_data['content'])
                
                # 顯示推文
                st.info("【 鄉民反應 】")
                for c in res_data['comments']:
                    color = "red" if c['type'] == "噓" else ("green" if c['type'] == "推" else "white")
                    st.markdown(f"**{c['type']}** : {c['text']}")
            except Exception as e:
                st.error("文章生成失敗，請重試。")
