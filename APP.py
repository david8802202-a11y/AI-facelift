import streamlit as st
import google.generativeai as genai
import os
import random
import json
import requests
import re

# --- 1. 設定頁面 ---
st.set_page_config(page_title="PTT/Dcard 文案產生器 (V46 修正版)", page_icon="🛠️")

api_key = st.secrets.get("GOOGLE_API_KEY")

st.title("🛠️ PTT/Dcard 文案產生器 (V46 修正版)")

if not api_key:
    st.error("❌ 找不到 API Key！")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. 內建資料庫 ---
DEFAULT_DATABASE = [
    {
        "title": "[討論] 淨膚雷射打一打 臉變超乾 是正常情況嗎",
        "content": "最近存了一點錢終於衝了一發淨膚雷射，本來想說能讓臉亮一點，結果勒？現在整個脫皮超誇張...像蛇一樣啊！打完當天是還好，但隔天開始就覺得緊繃到不行，保濕做得再足都像沒擦一樣。問診所的美容師，她就說這是正常代謝，多敷面膜就好。可是我朋友打了好幾次也沒跟我講會乾成這樣啊？還是我皮膚太爛了？打完這樣是正常的還是一開始就打太強了啊？有沒有人能救救我這張乾臉？== 搞得我現在都不太敢出門了...",
        "comments": ["推|正常啊，光療都會這樣", "推|乾是代謝正常的訊號啊，別太緊張", "噓|診所都話術啦，問網友最實在"]
    },
    {
        "title": "[討論] 韓版電波真的是平替?還是那是給窮人打的安慰劑",
        "content": "美國電波實在漲太兇 打一次900發都要快10萬...大家都說「效果差不多」、「CP值很高」...但我心裡一直有個疑問，一分錢一分貨...韓版到底是真平替，還是只是打個心安、給預算不夠的人一種「我有做醫美」的安慰劑?",
        "comments": ["推|打過玩美 真的就是安慰劑...", "推|一分錢一分貨 鳳凰痛歸痛", "推|韓版適合25歲左右當保養"]
    },
    {
        "title": "[討論] 針劑醫美根本是無底洞...算完年費嚇死人",
        "content": "以前覺得動手術貴，結果記帳發現針劑才是錢坑。肉毒除皺+瘦小臉一年快2萬，玻尿酸半年消一半又要補。算下來一張臉每年的「維護費」竟然要10幾萬！這根本是訂閱制，沒續費就打回原形。",
        "comments": ["推|真的...微整就是訂閱制", "推|這就是溫水煮青蛙啊", "推|算完不敢面對"]
    },
    {
        "title": "[問題] 為了面相招財去打耳垂玻尿酸?",
        "content": "朋友天生耳垂薄，長輩說留不住錢，想去打玻尿酸變成招財耳。雖然聽起來迷信，但如果能改運好像也值得？但擔心耳垂神經多會不會超痛？",
        "comments": ["推|心理作用居多吧", "推|會痛到往生喔...耳朵神經超多", "推|小心打到血管栓塞"]
    }
]

# --- 3. 雲端抓取功能 ---
@st.cache_data(ttl=600)
def fetch_remote_data(url):
    if not url: return []
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return json.loads(response.text)
    except:
        return []
    return []

# --- 4. 取得模型清單 ---
@st.cache_resource
def get_all_models():
    try:
        models = [m.name for m in genai.list_models() if 'generate
