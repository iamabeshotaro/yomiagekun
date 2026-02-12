import streamlit as st
import os
import csv
import base64
import time
import asyncio
import edge_tts
import random
from num2words import num2words

# --- 設定 ---
APP_NAME_EN = "Bonjour, madame yomiage"
APP_NAME_JP = "こんにちは、読み上げ算"
DATA_DIR = "data"
BG_IMAGE = "background.png"

# --- ボイス設定 ---
VOICE_MAP = {
    "🇺🇸 米国 - 女性 (Ana)": "en-US-AnaNeural",
    "🇺🇸 米国 - 男性 (Guy)": "en-US-GuyNeural",
    "🇬🇧 英国 - 女性 (Sonia)": "en-GB-SoniaNeural",
    "🇬🇧 英国 - 男性 (Ryan)": "en-GB-RyanNeural",
    "🇦🇺 豪州 - 女性 (Natasha)": "en-AU-NatashaNeural",
    "🇦🇺 豪州 - 男性 (William)": "en-AU-WilliamNeural",
}

# --- スタイル設定 ---
def set_bg_image(image_file):
    if not os.path.exists(image_file): return
    with open(image_file, "rb") as f:
        img_data = f.read()
    b64_encoded = base64.b64encode(img_data).decode()
    style = f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{b64_encoded}");
        background-attachment: fixed;
        background-size: cover;
    }}
    p, div, label, span, li, .stMarkdown {{
        text-shadow: 0 0 2px rgba(255,255,255, 0.9);
        color: #222222;
    }}
    h1, h2, h3, h4 {{
        color: #111111 !important;
        text-shadow: 2px 2px 4px rgba(255,255,255, 1.0), -2px -2px 4px rgba(255,255,255, 1.0) !important;
    }}
    [data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {{
        background-color: rgba(255, 255, 255, 0.96); 
        padding: 2.5rem;
        border-radius: 15px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.2); 
    }}
    [data-testid="stSidebar"] {{
         background-color: rgba(250, 250, 250, 0.95);
    }}
    </style>
    """
    st.markdown(style, unsafe_allow_html=True)

# --- 共通関数 ---
def get_problem_counts():
    counts = {}
    if not os.path.exists(DATA_DIR): return counts
    files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".csv")])
    for f_name in files:
        path = os.path.join(DATA_DIR, f_name)
        try:
            with open(path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f); next(reader, None)
                counts[f_name] = sum(1 for row in reader if row)
        except: counts[f_name] = 0
    return counts

def load_problems_from_csv(file_name):
    problems = {}
    path = os.path.join(DATA_DIR, file_name)
    try:
        with open(path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    no = int(row['no'])
                    nums = [int(row[f'row{i}']) for i in range(1, 100) if f'row{i}' in row and row[f'row{i}']]
                    problems[no] = nums
                except: continue
        return problems
    except: return {}

def get_next_digits_from_deck(rows, min_digit, max_digit):
    if 'digit_deck' not in st.session_state: st.session_state['digit_deck'] = []
    deck = st.session_state['digit_deck']
    if deck and (min(deck) < min_digit or max(deck) > max_digit): deck = []
    current_digits = []
    digit_range = list(range(min_digit, max_digit + 1))
    while len(current_digits) < rows:
        if not deck:
            new_set = digit_range[:]; random.shuffle(new_set); deck.extend(new_set)
        current_digits.append(deck.pop(0))
    st.session_state['digit_deck'] = deck
    if min_digit not in current_digits:
        target_idx = random.choice([i for i, d in enumerate(current_digits) if d != max_digit] or [0])
        current_digits[target_idx] = min_digit
    if max_digit not in current_digits:
        target_idx = random.choice([i for i, d in enumerate(current_digits) if d != min_digit] or [0])
        current_digits[target_idx] = max_digit
    return current_digits

def generate_single_problem(min_digit, max_digit, rows, allow_subtraction):
    digits_list = get_next_digits_from_deck(rows, min_digit, max_digit)
    nums = []; current_total = 0
    for r, d in enumerate(digits_list):
        val = random.randint(10**(d-1), 10**d - 1)
        if r > 0 and allow_subtraction and random.choice([True, False]):
            if current_total - val >= 0: val = -val
        nums.append(val); current_total += val
    return nums

async def generate_edge_audio(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def create_and_play_audio(q_no, problems, voice_id, playback_rate):
    if q_no not in problems: return
    full_text = " ".join([f"starting with, {num2words(abs(n), lang='en').replace(' and ', ' ').replace(',', '')} dollars," if i == 0 else f"{'Add' if n >= 0 else 'Subtract'}, {num2words(abs(n), lang='en').replace(' and ', ' ').replace(',', '')} dollars," for i, n in enumerate(problems[q_no])]) + " thats all"
    temp_file = f"temp_audio_{int(time.time())}.mp3"
    try:
        asyncio.run(generate_edge_audio(full_text, voice_id, temp_file))
        with open(temp_file, "rb") as f: audio_b64 = base64.b64encode(f.read()).decode()
        os.remove(temp_file)
        audio_html = f'<audio id="ap" controls autoplay style="width: 100%; margin-top: 15px; border-radius: 30px;"><source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3"></audio><script>document.getElementById("ap").playbackRate = {playback_rate};</script>'
        st.session_state['correct_ans'] = sum(problems[q_no])
        st.session_state['audio_html'] = audio_html
        st.session_state['current_q'] = q_no
        st.session_state['last_voice_id'] = voice_id
    except Exception as e: st.error(f"Error: {e}")

# --- メインアプリ ---
st.set_page_config(page_title=APP_NAME_EN, layout="centered", initial_sidebar_state="expanded")
set_bg_image(BG_IMAGE)

st.title(APP_NAME_EN)
st.markdown(f"##### {APP_NAME_JP}")

# セッション初期化
for key in ['correct_ans', 'current_q', 'audio_html', 'last_voice_id', 'generated_problems', 'digit_deck']:
    if key not in st.session_state: st.session_state[key] = None if 'ans' in key or 'html' in key or 'voice' in key or 'q' in key else [] if 'deck' in key else {}

# ガイド
with st.expander("📖 はじめての方へ（使いかた）", expanded=True):
    st.markdown("""
    1.  **設定を確認する**: 左側のメニューで、**『モード』**と**『声』**を選びます。
    2.  **音声を聴く**: **『再生スタート』**ボタンを押すと、英語で問題が流れます。
    3.  **計算する**: 聴き取った数字をそろばんなどで計算します。
    4.  **答え合わせ**: 最後に答えを半角数字で入力し、**『答え合わせ』**を押してください。
    """)

# ファイル情報
file_counts = get_problem_counts()

# サイドバー
with st.sidebar:
    st.header("⚙️ 設定 (Settings)")
    mode = st.radio("📁 モード選択", ["CSV読み込み", "ランダム生成"])
    st.divider()
    
    if mode == "CSV読み込み":
        selected_file = st.selectbox("年度を選択", options=list(file_counts.keys()), format_func=lambda x: f"{x} ({file_counts.get(x, 0)}問)")
        problems = load_problems_from_csv(selected_file)
    else:
        min_d = st.number_input("最小桁数", 1, 16, 3)
        max_d = st.number_input("最大桁数", 1, 16, 16)
        rows_count = st.slider("口数 (行数)", 3, 15, 5)
        allow_sub = st.checkbox("引き算を含める", value=False)
        problems = st.session_state['generated_problems']

    st.divider()
    selected_voice_label = st.selectbox("話者の声を選択", options=list(VOICE_MAP.keys()))
    selected_voice_id = VOICE_MAP[selected_voice_label]

# メイン処理
if is_random_mode := (mode == "ランダム生成"):
    if not problems:
        if st.button("🚀 練習をスタートする", type="primary", use_container_width=True):
            new_p = generate_single_problem(min_d, max_d, rows_count, allow_sub)
            st.session_state['generated_problems'][1] = new_p
            create_and_play_audio(1, st.session_state['generated_problems'], selected_voice_id, 1.0)
            st.rerun()
        st.stop()

if problems:
    min_no, max_no = min(problems.keys()), max(problems.keys())
    st.markdown("---")
    c1, c2 = st.columns([1, 1], gap="medium")
    with c1:
        speed_level = st.slider("🚀 スピード (1-15)", 1, 15, 5)
        playback_rate = 0.5 + (speed_level * 0.1)
    with c2:
        # --- 修正箇所: エラー回避の安全装置 ---
        # セッションの値をチェックして、範囲外なら強制的に範囲内に収める
        default_val = st.session_state['current_q'] or min_no
        if default_val < min_no: default_val = min_no
        if default_val > max_no: default_val = max_no
        
        q_no = st.number_input("📝 問題番号", min_value=min_no, max_value=max_no, value=default_val)
        
        if q_no in problems:
            d_info = [len(str(abs(n))) for n in problems[q_no]]
            p_type = any(n < 0 for n in problems[q_no])
            st.markdown(f'<div style="display: flex; gap: 5px; margin-top: 8px;"><div style="flex: 1; background-color: #e8f5e9; color: #2e7d32; padding: 4px; border-radius: 4px; font-weight: bold; font-size: 0.85em; text-align: center; border: 1px solid #c8e6c9;">📊 {min(d_info)}〜{max(d_info)}桁</div><div style="flex: 1; background-color: {"#fff3e0" if p_type else "#e3f2fd"}; color: {"#ef6c00" if p_type else "#1565c0"}; padding: 4px; border-radius: 4px; font-weight: bold; font-size: 0.85em; text-align: center; border: 1px solid {"#ffe0b2" if p_type else "#bbdefb"};">⚙️ {"加減算" if p_type else "加算"}</div></div>', unsafe_allow_html=True)

    if st.session_state['current_q'] != q_no:
        st.session_state.update({'correct_ans': None, 'audio_html': None, 'current_q': q_no, 'last_voice_id': None})

    if st.session_state['audio_html'] and st.session_state['last_voice_id'] != selected_voice_id:
        create_and_play_audio(q_no, problems, selected_voice_id, playback_rate); st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if is_random_mode and q_no == max_no:
        if st.button("🆕 次の問題を出す", type="primary", use_container_width=True):
            new_q = max_no + 1
            st.session_state['generated_problems'][new_q] = generate_single_problem(min_d, max_d, rows_count, allow_sub)
            create_and_play_audio(new_q, st.session_state['generated_problems'], selected_voice_id, playback_rate); st.rerun()
    else:
        if st.button("▶️ 再生する (Play)", type="primary", use_container_width=True):
            create_and_play_audio(q_no, problems, selected_voice_id, playback_rate); st.rerun()

    if st.session_state['audio_html']:
        st.markdown("### 🎧 Listening...")
        st.components.v1.html(st.session_state['audio_html'], height=80)

    if q_no in problems:
        with st.expander("👀 問題の数字を確認する (Show Numbers)"):
            current_nums = problems[q_no]
            html_nums = "".join([f"<div style='text-align: right; font-family: monospace; font-size: 1.2em; border-bottom: 1px solid #eee;'>{n:,}</div>" for n in current_nums])
            st.markdown(html_nums, unsafe_allow_html=True)
            st.markdown(f"<div style='text-align: right; font-weight: bold; font-size: 1.2em; margin-top: 5px;'>Total: {sum(current_nums):,}</div>", unsafe_allow_html=True)

    if st.session_state['correct_ans'] is not None:
        st.divider()
        with st.form(key='ans_form'):
            user_input = st.text_input("答えを入力してください:", key=f"in_{st.session_state['current_q']}")
            if st.form_submit_button("答え合わせ (Check)", type="secondary", use_container_width=True):
                try:
                    val = int(user_input.replace(",", "").strip())
                    if val == st.session_state['correct_ans']:
                        st.success(f"正解! 🎉 Ans: {val:,}"); st.balloons()
                    else: st.error(f"残念... 正解は {st.session_state['correct_ans']:,} でした。")
                except: st.warning("半角数字で入力してください。")
