import streamlit as st
import pandas as pd
from datetime import datetime
from image_data import IMAGES_DATA

st.set_page_config(page_title="SmartFit", page_icon="💪", layout="wide")

BODY_PARTS = ["胸部", "背部", "肩膀", "手臂", "腿部", "核心"]

# ==================== 50個動作 ====================
EXERCISES = [
    # 徒手/啞鈴 (1-20)
    {"id": "001", "nameCN": "俯臥撑", "bodyPart": "胸部", "difficulty": "初級", "sets": 3, "reps": 12, "category": "徒手/啞鈴", "equipment": "無", "filename": "push_ups.jpg", "tips": ["保持身體直線", "降低至胸部", "推回起始位置"]},
    {"id": "002", "nameCN": "寬距俯臥撑", "bodyPart": "胸部", "difficulty": "初級", "sets": 3, "reps": 10, "category": "徒手/啞鈴", "equipment": "無", "filename": "wide_push_ups.jpg", "tips": ["雙手寬距", "保持直線", "完整範圍"]},
    {"id": "003", "nameCN": "菱形俯臥撑", "bodyPart": "胸部", "difficulty": "中級", "sets": 3, "reps": 8, "category": "徒手/啞鈴", "equipment": "無", "filename": "diamond_push_ups.jpg", "tips": ["雙手在胸下", "肘部靠近", "完全伸展"]},
    {"id": "004", "nameCN": "下斜俯臥撑", "bodyPart": "胸部", "difficulty": "中級", "sets": 3, "reps": 10, "category": "徒手/啞鈴", "equipment": "無", "filename": "decline_push_ups.jpg", "tips": ["雙腳放高", "身體直線", "完整動作"]},
    {"id": "005", "nameCN": "箭手俯臥撑", "bodyPart": "胸部", "difficulty": "高級", "sets": 3, "reps": 6, "category": "徒手/啞鈴", "equipment": "無", "filename": "archer_push_ups.jpg", "tips": ["一側彎曲", "一側伸直", "平衡訓練"]},
    {"id": "006", "nameCN": "引體向上", "bodyPart": "背部", "difficulty": "中級", "sets": 3, "reps": 8, "category": "徒手/啞鈴", "equipment": "無", "filename": "pull_ups.jpg", "tips": ["握距寬", "下巴超杆", "控制下降"]},
    {"id": "007", "nameCN": "窄握引體向上", "bodyPart": "背部", "difficulty": "中級", "sets": 3, "reps": 8, "category": "徒手/啞鈴", "equipment": "無", "filename": "chin_ups.jpg", "tips": ["掌心向內", "肘部靠近", "平順動作"]},
    {"id": "008", "nameCN": "反向划船", "bodyPart": "背部", "difficulty": "初級", "sets": 3, "reps": 12, "category": "徒手/啞鈴", "equipment": "無", "filename": "reverse_rows.jpg", "tips": ["身體直線", "拉至胸部", "控制下降"]},
    {"id": "009", "nameCN": "啞鈴划船", "bodyPart": "背部", "difficulty": "中級", "sets": 4, "reps": 10, "category": "徒手/啞鈴", "equipment": "啞鈴", "filename": "dumbbell_rows.jpg", "tips": ["膝蓋跪", "核心穩定", "拉至腰"]},
    {"id": "010", "nameCN": "超人式", "bodyPart": "背部", "difficulty": "初級", "sets": 3, "reps": 30, "category": "徒手/啞鈴", "equipment": "無", "filename": "superman_hold.jpg", "tips": ["手臂前伸", "腿後伸", "胸部離地"]},
    {"id": "011", "nameCN": "深蹲", "bodyPart": "腿部", "difficulty": "初級", "sets": 3, "reps": 15, "category": "徒手/啞鈴", "equipment": "無", "filename": "squats.jpg", "tips": ["挺胸", "臀部後坐", "腳跟推起"]},
    {"id": "012", "nameCN": "跳躍深蹲", "bodyPart": "腿部", "difficulty": "中級", "sets": 3, "reps": 12, "category": "徒手/啞鈴", "equipment": "無", "filename": "jump_squats.jpg", "tips": ["全力跳", "軟著陸", "快速起身"]},
    {"id": "013", "nameCN": "弓步", "bodyPart": "腿部", "difficulty": "初級", "sets": 3, "reps": 12, "category": "徒手/啞鈴", "equipment": "無", "filename": "lunges.jpg", "tips": ["前腳90度", "後腳接地", "保持直立"]},
    {"id": "014", "nameCN": "啞鈴深蹲", "bodyPart": "腿部", "difficulty": "中級", "sets": 4, "reps": 10, "category": "徒手/啞鈴", "equipment": "啞鈴", "filename": "dumbbell_squats.jpg", "tips": ["拿著啞鈴", "挺胸下蹲", "腳跟推起"]},
    {"id": "015", "nameCN": "提踵", "bodyPart": "腿部", "difficulty": "初級", "sets": 3, "reps": 20, "category": "徒手/啞鈴", "equipment": "無", "filename": "calf_raises.jpg", "tips": ["站直", "提起腳跟", "控制下降"]},
    {"id": "016", "nameCN": "棒式", "bodyPart": "核心", "difficulty": "初級", "sets": 3, "reps": 30, "category": "徒手/啞鈴", "equipment": "無", "filename": "plank.jpg", "tips": ["身體直線", "核心緊縮", "臀部不下沉"]},
    {"id": "017", "nameCN": "側棒式", "bodyPart": "核心", "difficulty": "初級", "sets": 3, "reps": 20, "category": "徒手/啞鈴", "equipment": "無", "filename": "side_plank.jpg", "tips": ["身體直線", "核心收緊", "臀部不下沉"]},
    {"id": "018", "nameCN": "仰臥起坐", "bodyPart": "核心", "difficulty": "初級", "sets": 3, "reps": 15, "category": "徒手/啞鈴", "equipment": "無", "filename": "sit_ups.jpg", "tips": ["膝蓋彎曲", "不拉脖子", "胸部向膝"]},
    {"id": "019", "nameCN": "爬山者", "bodyPart": "核心", "difficulty": "中級", "sets": 3, "reps": 20, "category": "徒手/啞鈴", "equipment": "無", "filename": "mountain_climbers.jpg", "tips": ["快速交替", "保持俯臥撑", "核心緊縮"]},
    {"id": "020", "nameCN": "抬腿", "bodyPart": "核心", "difficulty": "初級", "sets": 3, "reps": 12, "category": "徒手/啞鈴", "equipment": "無", "filename": "leg_raises.jpg", "tips": ["背部貼地", "腿部直", "控制速度"]},
    
    # 健身房儀器 (21-50) - 21-27 有圖片
    {"id": "021", "nameCN": "槓鈴臥推", "bodyPart": "胸部", "difficulty": "中級", "sets": 4, "reps": 8, "category": "健身房儀器", "equipment": "槓鈴", "filename": "barbell_bench.jpg", "tips": ["背貼板", "肩膀穩定", "平順動作"]},
    {"id": "022", "nameCN": "胸部推蹬機", "bodyPart": "胸部", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "推蹬機", "filename": "chest_machine.jpg", "tips": ["坐直對齊", "完全推出", "控制回放"]},
    {"id": "023", "nameCN": "拉力機夾胸", "bodyPart": "胸部", "difficulty": "中級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "拉力機", "filename": "cable_flyes.jpg", "tips": ["手臂微彎", "控制回放", "集中收縮"]},
    {"id": "024", "nameCN": "史密斯機臥推", "bodyPart": "胸部", "difficulty": "初級", "sets": 4, "reps": 12, "category": "健身房儀器", "equipment": "史密斯機", "filename": "smith_machine_bench.jpg", "tips": ["槓在肩", "直線下降", "完整動作"]},
    {"id": "025", "nameCN": "胸部飛鳥機", "bodyPart": "胸部", "difficulty": "中級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "飛鳥機", "filename": "pec_deck.jpg", "tips": ["手臂微彎", "控制回放", "充分收縮"]},
    {"id": "026", "nameCN": "槓鈴划船", "bodyPart": "背部", "difficulty": "中級", "sets": 4, "reps": 8, "category": "健身房儀器", "equipment": "槓鈴", "filename": "barbell_rows.jpg", "tips": ["膝蓋微彎", "背部直", "拉至腹"]},
    {"id": "027", "nameCN": "下拉機", "bodyPart": "背部", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "下拉機", "filename": "lat_pulldown.jpg", "tips": ["拉至胸", "控制回放", "核心緊縮"]},
    {"id": "028", "nameCN": "拉力機划船", "bodyPart": "背部", "difficulty": "初級", "sets": 4, "reps": 12, "category": "健身房儀器", "equipment": "拉力機", "filename": None, "tips": ["坐直挺胸", "拉至腹", "控制回放"]},
    {"id": "029", "nameCN": "T槓划船", "bodyPart": "背部", "difficulty": "中級", "sets": 4, "reps": 10, "category": "健身房儀器", "equipment": "T槓", "filename": None, "tips": ["身體穩定", "拉至胸", "控制下降"]},
    {"id": "030", "nameCN": "背闊肌拉力機", "bodyPart": "背部", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "背闊肌機", "filename": None, "tips": ["坐直", "拉至腹", "控制回放"]},
    {"id": "031", "nameCN": "槓鈴肩推", "bodyPart": "肩膀", "difficulty": "中級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "槓鈴", "filename": None, "tips": ["槓在肩", "上推至頂", "控制下降"]},
    {"id": "032", "nameCN": "肩推機", "bodyPart": "肩膀", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "肩推機", "filename": None, "tips": ["坐直", "推至頂部", "控制下降"]},
    {"id": "033", "nameCN": "側平舉機", "bodyPart": "肩膀", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "側平舉機", "filename": None, "tips": ["坐直", "抬至肩高", "控制速度"]},
    {"id": "034", "nameCN": "反向夾胸機", "bodyPart": "肩膀", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "夾胸機", "filename": None, "tips": ["坐直", "手臂向外", "控制回放"]},
    {"id": "035", "nameCN": "前平舉機", "bodyPart": "肩膀", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "前平舉機", "filename": None, "tips": ["坐直", "推至肩高", "控制速度"]},
    {"id": "036", "nameCN": "繩索下壓", "bodyPart": "手臂", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "拉力機", "filename": None, "tips": ["肘部不動", "完全伸展", "控制回放"]},
    {"id": "037", "nameCN": "拉力機彎舉", "bodyPart": "手臂", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "拉力機", "filename": None, "tips": ["肘部固定", "張力持續", "控制回放"]},
    {"id": "038", "nameCN": "三頭撐體機", "bodyPart": "手臂", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "撐體機", "filename": None, "tips": ["身體向前", "肘部90度", "完整動作"]},
    {"id": "039", "nameCN": "二頭彎舉機", "bodyPart": "手臂", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "彎舉機", "filename": None, "tips": ["坐直", "充分收縮", "控制速度"]},
    {"id": "040", "nameCN": "三頭肌機器", "bodyPart": "手臂", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "三頭機", "filename": None, "tips": ["坐直", "完全伸展", "控制回放"]},
    {"id": "041", "nameCN": "推蹬機", "bodyPart": "腿部", "difficulty": "初級", "sets": 3, "reps": 15, "category": "健身房儀器", "equipment": "推蹬機", "filename": None, "tips": ["腳在機器", "完全伸展", "控制下降"]},
    {"id": "042", "nameCN": "腿部卷舉機", "bodyPart": "腿部", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "卷舉機", "filename": None, "tips": ["坐直", "卷至胸", "控制回放"]},
    {"id": "043", "nameCN": "腿部伸展機", "bodyPart": "腿部", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "伸展機", "filename": None, "tips": ["坐直", "完全伸展", "控制回放"]},
    {"id": "044", "nameCN": "哈克深蹲機", "bodyPart": "腿部", "difficulty": "中級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "哈克機", "filename": None, "tips": ["肩膀靠機", "深蹲至平行", "完整動作"]},
    {"id": "045", "nameCN": "槓鈴深蹲", "bodyPart": "腿部", "difficulty": "中級", "sets": 4, "reps": 8, "category": "健身房儀器", "equipment": "槓鈴", "filename": None, "tips": ["槓在肩", "直立姿勢", "深蹲至平行"]},
    {"id": "046", "nameCN": "拉力卷腹", "bodyPart": "核心", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "拉力機", "filename": None, "tips": ["膝蓋彎", "卷至膝", "控制回放"]},
    {"id": "047", "nameCN": "腹肌卷腹機", "bodyPart": "核心", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "卷腹機", "filename": None, "tips": ["坐直對齊", "卷起完整", "控制回放"]},
    {"id": "048", "nameCN": "滑輪卷腹", "bodyPart": "核心", "difficulty": "中級", "sets": 3, "reps": 10, "category": "健身房儀器", "equipment": "滑輪", "filename": None, "tips": ["膝蓋跪", "向前滾", "回收縮腹"]},
    {"id": "049", "nameCN": "旋轉腹肌機", "bodyPart": "核心", "difficulty": "初級", "sets": 3, "reps": 12, "category": "健身房儀器", "equipment": "旋轉機", "filename": None, "tips": ["坐直", "緩慢旋轉", "控制速度"]},
    {"id": "050", "nameCN": "懸掛抬腿", "bodyPart": "核心", "difficulty": "中級", "sets": 3, "reps": 10, "category": "健身房儀器", "equipment": "單槓", "filename": None, "tips": ["握把穩定", "腿抬至水平", "控制下降"]},
]

# ==================== Session State ====================
if "page" not in st.session_state:
    st.session_state.page = "home"
if "user" not in st.session_state:
    st.session_state.user = {"name": "", "age": 25}
if "records" not in st.session_state:
    st.session_state.records = []
if "workout" not in st.session_state:
    st.session_state.workout = None
if "current_ex" not in st.session_state:
    st.session_state.current_ex = None
if "progress" not in st.session_state:
    st.session_state.progress = {"ex_idx": 0, "sets": 1, "reps": 1}
if "selected_exercises" not in st.session_state:
    st.session_state.selected_exercises = []

# ==================== 函數 ====================
def get_exercises(body_parts, category):
    return [e for e in EXERCISES if e["category"] == category and e["bodyPart"] in body_parts]

def display_image(filename):
    """直接用 data URL 顯示圖片"""
    if filename and filename in IMAGES_DATA:
        st.image(IMAGES_DATA[filename])
        return True
    else:
        st.warning("⏳ 圖片準備中...")
        return False

# ==================== 側邊欄 ====================
with st.sidebar:
    st.title("💪 SmartFit")
    st.write("✅ 已上傳: 27/50 張圖片")
    st.write("📍 進度: 54%")
    
    if st.button("🏠 首頁", use_container_width=True, key="nav_home"):
        st.session_state.page = "home"
        st.rerun()
    if st.button("📊 統計", use_container_width=True, key="nav_stats"):
        st.session_state.page = "stats"
        st.rerun()
    if st.button("⚙️ 設置", use_container_width=True, key="nav_settings"):
        st.session_state.page = "settings"
        st.rerun()

# ==================== 首頁 ====================
if st.session_state.page == "home":
    st.title("💪 SmartFit - 您的私人健身教練")
    
    col1, col2 = st.columns(2)
    with col1:
        mode = st.radio("訓練模式", ["🏠 徒手/啞鈴", "🏋️ 健身房儀器"], key="mode_select")
        category = "徒手/啞鈴" if "徒手" in mode else "健身房儀器"
    with col2:
        duration = st.radio("訓練時長", [15, 30, 45, 60], horizontal=True, key="duration_select")
    
    st.divider()
    st.subheader("🎯 選擇訓練部位")
    cols = st.columns(3)
    selected_parts = []
    for i, part in enumerate(BODY_PARTS):
        with cols[i % 3]:
            if st.checkbox(part, key=f"part_{part}"):
                selected_parts.append(part)
    
    st.divider()
    
    if selected_parts:
        st.success(f"✅ 已選擇: {', '.join(selected_parts)}")
        
        all_exercises = get_exercises(selected_parts, category)
        
        if all_exercises:
            st.subheader(f"🏆 可用動作 ({len(all_exercises)}個)")
            
            st.session_state.selected_exercises = []
            
            for ex in all_exercises:
                col1, col2, col3, col4 = st.columns([2, 0.8, 1, 1.2])
                with col1:
                    has_img = "✅" if ex["filename"] and ex["filename"] in IMAGES_DATA else "⏳"
                    st.write(f"{has_img} **{ex['nameCN']}** ({ex['difficulty']})")
                with col2:
                    if st.checkbox("選", key=f"select_{ex['id']}"):
                        if ex not in st.session_state.selected_exercises:
                            st.session_state.selected_exercises.append(ex)
                with col3:
                    st.write(f"{ex['sets']}×{ex['reps']}")
                with col4:
                    if st.button("👀", key=f"btn_detail_{ex['id']}", help="查看詳情"):
                        st.session_state.current_ex = ex
                        st.session_state.page = "detail"
                        st.rerun()
            
            st.divider()
            
            if st.session_state.selected_exercises:
                st.success(f"✅ 已選擇 {len(st.session_state.selected_exercises)} 個動作")
                if st.button("🎬 開始訓練", use_container_width=True, key="btn_start"):
                    st.session_state.workout = {"exercises": st.session_state.selected_exercises, "start": datetime.now(), "duration": duration}
                    st.session_state.progress = {"ex_idx": 0, "sets": 1, "reps": 1}
                    st.session_state.page = "workout"
                    st.rerun()

# ==================== 動作詳情 ====================
elif st.session_state.page == "detail":
    if st.session_state.current_ex:
        ex = st.session_state.current_ex
        st.title(f"{ex['nameCN']}")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**難度**: {ex['difficulty']} | **部位**: {ex['bodyPart']}")
            st.write(f"**推薦**: {ex['sets']}×{ex['reps']} | **器材**: {ex['equipment']}")
            st.subheader("✅ 執行技巧")
            for tip in ex["tips"]:
                st.write(f"• {tip}")
        with col2:
            if ex["filename"]:
                display_image(ex["filename"])
        
        if st.button("⬅️ 返回首頁"):
            st.session_state.page = "home"
            st.rerun()

# ==================== 訓練執行 ====================
elif st.session_state.page == "workout":
    if st.session_state.workout:
        exs = st.session_state.workout["exercises"]
        prog = st.session_state.progress
        idx = prog["ex_idx"]
        
        st.progress(idx / len(exs) if len(exs) > 0 else 0, text=f"進度: {idx}/{len(exs)}")
        
        if idx < len(exs):
            ex = exs[idx]
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.title(f"{ex['nameCN']}")
                st.write(f"部位: {ex['bodyPart']} | 難度: {ex['difficulty']}")
                st.write(f"器材: {ex['equipment']}")
            with col2:
                if ex["filename"]:
                    display_image(ex["filename"])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("組", prog["sets"])
            with col2:
                st.metric("次", prog["reps"])
            
            st.divider()
            st.subheading("執行技巧:")
            for tip in ex["tips"]:
                st.write(f"✅ {tip}")
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            
            with c1:
                if st.button("⏭️ 跳過", use_container_width=True, key="btn_skip"):
                    st.session_state.progress["ex_idx"] += 1
                    st.session_state.progress["sets"] = 1
                    st.session_state.progress["reps"] = 1
                    st.rerun()
            
            with c2:
                if st.button("✅ 完成一次", use_container_width=True, key="btn_done"):
                    if prog["reps"] < ex["reps"]:
                        st.session_state.progress["reps"] += 1
                    else:
                        if prog["sets"] < ex["sets"]:
                            st.session_state.progress["sets"] += 1
                            st.session_state.progress["reps"] = 1
                        else:
                            st.session_state.progress["ex_idx"] += 1
                            st.session_state.progress["sets"] = 1
                            st.session_state.progress["reps"] = 1
                    st.rerun()
            
            with c3:
                if st.button("⏹️ 結束", use_container_width=True, key="btn_finish"):
                    dur = int((datetime.now() - st.session_state.workout["start"]).total_seconds() / 60)
                    st.session_state.records.append({
                        "日期": datetime.now().strftime("%Y-%m-%d"),
                        "動作": len(exs),
                        "時長(分)": dur,
                        "熱量": dur * 7
                    })
                    st.session_state.workout = None
                    st.session_state.page = "stats"
                    st.balloons()
                    st.rerun()
        else:
            st.success("🎉 訓練完成！")
            dur = int((datetime.now() - st.session_state.workout["start"]).total_seconds() / 60)
            c1, c2, c3 = st.columns(3)
            c1.metric("動作", len(exs))
            c2.metric("時長", f"{dur}分")
            c3.metric("熱量", dur * 7)

# ==================== 統計 ====================
elif st.session_state.page == "stats":
    st.title("📊 訓練統計")
    if st.session_state.records:
        df = pd.DataFrame(st.session_state.records)
        c1, c2, c3 = st.columns(3)
        c1.metric("訓練次", len(st.session_state.records))
        c2.metric("總時長", f"{df['時長(分)'].sum()}分")
        c3.metric("總熱量", df['熱量'].sum())
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("還沒有訓練記錄")

# ==================== 設置 ====================
elif st.session_state.page == "settings":
    st.title("⚙️ 設置")
    st.session_state.user["name"] = st.text_input("姓名", st.session_state.user["name"])
    st.session_state.user["age"] = st.slider("年齡", 15, 100, st.session_state.user["age"])
    
    c1, c2, c3 = st.columns(3)
    c1.metric("版本", "10.0 完整版")
    c2.metric("動作", "50")
    c3.metric("圖片進度", "27/50 (54%)")
    
    st.divider()
    st.success("✅ SmartFit v10 - 27張圖片已完全集成！")
