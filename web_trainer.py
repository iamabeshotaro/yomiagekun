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
APP_NAME_EN = "Bonjour, Yomiagesan"
APP_NAME_JP = "こんにちは、読み上げ算"
DATA_DIR = "data"
BG_IMAGE = "background.png"
LOADING_IMAGE = "loading.gif"

# --- ボイス設定（多国籍版 + ランダム） ---
VOICE_MAP = {
    "🎲 ランダム (Random)": "random",
    
    # 北米
    "🇺🇸 米国 - 女性 (Mary)": "en-US-JennyNeural", 
    "🇺🇸 米国 - 男性 (James)": "en-US-GuyNeural",
    "🇨🇦 カナダ - 女性 (Jennifer)": "en-CA-ClaraNeural",
    "🇨🇦 カナダ - 男性 (Robert)": "en-CA-LiamNeural",
    
    # 欧州
    "🇬🇧 英国 - 女性 (Margaret)": "en-GB-LibbyNeural",
    "🇬🇧 英国 - 男性 (David)": "en-GB-RyanNeural",
    "🇮🇪 アイルランド - 女性 (Mary)": "en-IE-EmilyNeural",
    "🇮🇪 アイルランド - 男性 (Patrick)": "en-IE-ConnorNeural",
    
    # オセアニア
    "🇦🇺 豪州 - 女性 (Charlotte)": "en-AU-NatashaNeural",
    "🇦🇺 豪州 - 男性 (John)": "en-AU-WilliamNeural",
    "🇳🇿 ニュージーランド - 女性 (Molly)": "en-NZ-MollyNeural",
    "🇳🇿 ニュージーランド - 男性 (Mitchell)": "en-NZ-MitchellNeural",
    
    # アジア
    "🇮🇳 インド - 女性 (Priya)": "en-IN-NeerjaNeural",
    "🇮🇳 インド - 男性 (Rahul)": "en-IN-PrabhatNeural",
    "🇸🇬 シンガポール - 女性 (Luna)": "en-SG-LunaNeural",
    "🇸🇬 シンガポール - 男性 (Wayne)": "en-SG-WayneNeural",
    "🇵🇭 フィリピン - 女性 (Rosa)": "en-PH-RosaNeural",
    "🇵🇭 フィリピン - 男性 (James)": "en-PH-JamesNeural",
    
    # アフリカ
    "🇿🇦 南アフリカ - 女性 (Leah)": "en-ZA-LeahNeural",
    "🇿🇦 南アフリカ - 男性 (Luke)": "en-ZA-LukeNeural",
    "🇳🇬 ナイジェリア - 女性 (Ezinne)": "en-NG-EzinneNeural",
    "🇳🇬 ナイジェリア - 男性 (Abeo)": "en-NG-AbeoNeural",
}

def set_bg_image(image_file):
    if not os.path.exists(image_file): return
    with open(image_file, "rb") as f:
        img_data = f.read()
    b64_encoded = base64.b64encode(img_data).decode()
    style = f"""
    <style>
    @keyframes fadeInUp {{
        0% {{ opacity: 0; transform: translateY(20px); }}
        100% {{ opacity: 1; transform: translateY(0); }}
    }}
    .stApp {{
        background-image: url("data:image/png;base64,{b64_encoded}");
        background-attachment: fixed;
        background-size: cover;
        background-position: center;
    }}
    .block-container {{
        background-color: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(8px);
        border-radius: 20px;
        padding: 3rem !important;
        margin-top: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.4);
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
        max-width: 720px;
        opacity: 0;
        animation: fadeInUp 0.8s ease-out 0.3s forwards;
    }}
    h1, h2, h3, h4, h5, p, div, span, label, li, .stMarkdown, .stNumberInput, .stTextInput {{
        color: #2D3748;
        font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    h1 {{
        font-family: 'Dancing Script', cursive !important;
        font-size: 3.2rem;
        font-weight: 700;
        text-align: center;
        text-shadow: 2px 2px 0px rgba(255,255,255,0.8);
        margin-bottom: 10px;
        color: #1A202C !important;
        line-height: 1.2;
    }}
    h5 {{
        text-align: center;
        color: #4A5568 !important;
        font-weight: normal;
        margin-bottom: 40px;
    }}
    div.stButton > button {{
        background-color: #3498db !important;
        color: #ffffff !important;
        border: none !important;
        padding: 0.7rem 1.2rem !important;
        border-radius: 50px !important;
        font-weight: 600 !important;
        letter-spacing: 1px;
        width: 100%;
        box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3) !important;
        transition: all 0.3s ease;
    }}
    div.stButton > button:hover {{
        background-color: #2980b9 !important;
        transform: translateY(-2px);
    }}
    [data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.95);
        border-right: 1px solid #E2E8F0;
    }}
    [data-testid="stExpander"] {{
        background-color: white;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        color: #2D3748;
    }}
    .streamlit-expanderHeader {{
        background-color: transparent !important;
        color: #2D3748 !important;
    }}
    .custom-card {{
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        color: #2D3748;
    }}
    .number-display {{
        text-align: right; 
        font-family: monospace; 
        font-size: 1.2em; 
        border-bottom: 1px solid #EDF2F7;
        color: #2D3748;
        padding: 4px 0;
    }}
    input {{
        background-color: #FFFFFF !important;
        color: #2D3748 !important;
    }}
    @media (max-width: 640px) {{
        h1 {{ font-size: 2.0rem !important; }}
        .block-container {{ padding: 1.5rem !important; margin-top: 0.5rem; }}
    }}
    @media (prefers-color-scheme: dark) {{
        .block-container {{
            background-color: rgba(30, 30, 30, 0.75) !important;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
        }}
        h1, h2, h3, h4, h5, p, div, span, label, li, .stMarkdown, .stNumberInput, .stTextInput {{
            color: #E2E8F0 !important;
        }}
        h1 {{
            text-shadow: 1px 1px 2px rgba(255,255,255,0.1);
            color: #F7FAFC !important;
        }}
        h5 {{ color: #A0AEC0 !important; }}
        [data-testid="stSidebar"] {{
            background-color: rgba(26, 32, 44, 0.95) !important;
            border-right: 1px solid #2D3748;
        }}
        input {{
            background-color: #1A202C !important;
            color: #E2E8F0 !important;
        }}
        .custom-card, [data-testid="stExpander"] {{
            background-color: #2D3748 !important;
            color: #E2E8F0 !important;
            border: 1px solid #4A5568 !important;
        }}
        .number-display {{
            color: #E2E8F0 !important;
            border-bottom: 1px solid #4A5568 !important;
        }}
        .streamlit-expanderHeader {{ color: #E2E8F0 !important; }}
    }}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&display=swap" rel="stylesheet">
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

# 引き算の割合：中間行の半分以上
def generate_single_problem(min_digit, max_digit, rows, allow_subtraction):
    digits_list = get_next_digits_from_deck(rows, min_digit, max_digit)
    nums = []
    current_total = 0
    
    # マイナスにするインデックスを決定
    minus_indices = set()
    if allow_subtraction and rows > 2:
        # 最初(0)と最後(rows-1)を除くインデックス候補
        candidates = list(range(1, rows - 1))
        
        if candidates:
            # 「半分以上」なので、候補数の半分(切り上げ)を下限とする
            min_subtract_count = (len(candidates) + 1) // 2
            
            # 下限〜上限(全数) の間でランダムに個数を決める
            count = random.randint(min_subtract_count, len(candidates))
            
            minus_indices = set(random.sample(candidates, count))
    
    for r, d in enumerate(digits_list):
        # 桁数に基づく最小値と最大値
        min_val = 10**(d-1)
        max_val = 10**d - 1
        
        if r in minus_indices:
            # 引き算の場合：
            # 合計がマイナスにならないように、生成する乱数の上限を「現在の合計」でキャップする
            limit = min(max_val, current_total)
            
            if min_val <= limit:
                val = random.randint(min_val, limit)
                val = -val # 負の数にする
            else:
                # 桁数制約により引くことができない（現在の合計が小さすぎる）場合は、
                # やむを得ず足し算にする（合計を増やして次の引き算に備える）
                val = random.randint(min_val, max_val)
        else:
            # 足し算の場合
            val = random.randint(min_val, max_val)
        
        nums.append(val)
        current_total += val
        
    return nums

# 読み上げテキスト生成
def generate_audio_text(row_data):
    speech_parts = []
    n = len(row_data)
    
    for i, num in enumerate(row_data):
        # 内部のandを削除
        text_val = num2words(abs(num), lang='en').replace(",", "").replace(" and ", " ")
        
        # リズム調整
        delimiter = "." if (i + 1) % 3 == 0 else ","

        if i == 0:
            # 1口目
            speech_parts.append(f"Starting with, {text_val}{delimiter}")
        
        elif i == n - 1:
            # 【最後の数字】直前に "and" を入れる
            speech_parts.append(f"and, {text_val}{delimiter}")
            
        else:
            # 【中間の数字】
            if num < 0:
                # 引き算は Minus (間を詰めるためカンマなし)
                speech_parts.append(f"Minus {text_val}{delimiter}")
            else:
                # 足し算は宣言しない
                speech_parts.append(f"{text_val}{delimiter}")
    
    speech_parts.append("That's all.")
    return " ".join(speech_parts)

async def generate_edge_audio(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def create_and_play_audio(q_no, problems, voice_id, base_speed):
    if q_no not in problems: return
    
    loading_placeholder = st.empty()
    if os.path.exists(LOADING_IMAGE):
        loading_placeholder.image(LOADING_IMAGE, width=50)
    else:
        loading_placeholder.markdown("<span style='color:#718096; font-size:0.9em;'>Generating audio...</span>", unsafe_allow_html=True)

    actual_voice_id = voice_id
    if voice_id == "random":
        available_voices = [v for k, v in VOICE_MAP.items() if v != "random"]
        actual_voice_id = random.choice(available_voices)

    full_text = generate_audio_text(problems[q_no])
    temp_file = f"temp_audio_{int(time.time())}.mp3"
    
    try:
        asyncio.run(generate_edge_audio(full_text, actual_voice_id, temp_file))
        loading_placeholder.empty()

        with open(temp_file, "rb") as f: audio_b64 = base64.b64encode(f.read()).decode()
        os.remove(temp_file)
        
        player_id = f"ap_{int(time.time())}"
        
        audio_html = f"""
            <div class="custom-card">
                <audio id="{player_id}" controls autoplay style="width: 100%; margin-bottom: 10px;">
                    <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
                </audio>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2em;">🕰️</span>
                    <input type="range" min="1" max="20" value="{int((base_speed - 0.5) * 10)}" step="1" style="flex-grow: 1; cursor: pointer;"
                        oninput="
                            var level = this.value;
                            var rate = 0.5 + (level * 0.1);
                            var audio = document.getElementById('{player_id}');
                            if(audio) {{ audio.playbackRate = rate; }}
                            document.getElementById('rate_disp_{player_id}').innerText = rate.toFixed(1) + 'x';
                        "
                    >
                    <span id="rate_disp_{player_id}" style="font-weight: bold; width: 45px; text-align: right;">{base_speed:.1f}x</span>
                </div>
            </div>
            <script>
                var audio = document.getElementById("{player_id}");
                if(audio) {{ audio.playbackRate = {base_speed}; }}
            </script>
        """
        st.session_state.update({'correct_ans': sum(problems[q_no]), 'audio_html': audio_html, 'current_q': q_no, 'last_voice_id': voice_id})
    except Exception as e: 
        loading_placeholder.error("エラーが発生しました")
        st.error(f"Error: {e}")

def reset_audio_state():
    st.session_state.update({
        'audio_html': None, 
        'correct_ans': None, 
        'current_q': None, 
        'last_voice_id': None,
        'generated_problems': {} 
    })

# --- メイン UI ---
st.set_page_config(page_title=APP_NAME_EN, layout="centered", initial_sidebar_state="expanded")
set_bg_image(BG_IMAGE)
st.title(APP_NAME_EN)
st.markdown(f"##### {APP_NAME_JP}")

for key in ['correct_ans', 'current_q', 'audio_html', 'last_voice_id', 'generated_problems', 'digit_deck']:
    if key not in st.session_state: st.session_state[key] = None if 'ans' in key or 'html' in key or 'voice' in key or 'q' in key else [] if 'deck' in key else {}

with st.expander("📖 使いかた", expanded=False):
    st.markdown("""
    1. **設定**: 左側で**『モード』**と**『声』**を選びます。
    2. **スピード**: 左側の**『基本スピード』**で好みの速さを決めておくと、ずっとその速さで再生されます。
    3. **再生**: **『再生する』**ボタンを押すと、読み込みの後に音声が流れます。
    4. **答え合わせ**: 答えを入力して**『答え合わせ』**を押してください。
    """)

file_counts = get_problem_counts()
with st.sidebar:
    st.header("⚙️ 設定 (Settings)")
    mode = st.radio("📁 モード選択", ["ランダム生成", "CSV読み込み"], on_change=reset_audio_state)
    st.divider()
    
    st.subheader("🕰️ 基本スピード")
    speed_level = st.slider("Level (0.6x - 2.5x)", 1, 20, 10, help="ここでの設定は次の問題にも引き継がれます")
    base_speed = 0.5 + (speed_level * 0.1)
    st.caption(f"現在の設定: **{base_speed:.1f}倍速**")
    st.divider()

    if mode == "CSV読み込み":
        selected_file = st.selectbox("年度を選択", options=list(file_counts.keys()), format_func=lambda x: f"{x} ({file_counts.get(x, 0)}問)")
        problems = load_problems_from_csv(selected_file)
    else:
        min_d, max_d = st.number_input("最小桁数", 1, 16, 7), st.number_input("最大桁数", 1, 16, 14)
        rows_count = st.slider("口数 (行数)", 3, 15, 5)
        allow_sub = st.checkbox("引き算を含める", value=False)
        problems = st.session_state['generated_problems']
    st.divider()
    selected_voice_label = st.selectbox("話者の声を選択", options=list(VOICE_MAP.keys()))
    selected_voice_id = VOICE_MAP[selected_voice_label]

# メイン処理
if is_random_mode := (mode == "ランダム生成"):
    if not problems:
        if st.button("▶️ 再生する (Play)", type="primary", use_container_width=True):
            st.session_state['generated_problems'] = {1: generate_single_problem(min_d, max_d, rows_count, allow_sub)}
            create_and_play_audio(1, st.session_state['generated_problems'], selected_voice_id, base_speed); st.rerun()
        st.stop()

if problems:
    min_no, max_no = min(problems.keys()), max(problems.keys())
    st.markdown("---")
    
    current_q_val = st.session_state.get('current_q')
    if current_q_val is None or current_q_val < min_no or current_q_val > max_no:
        default_val = min_no
    else:
        default_val = current_q_val

    q_no = st.number_input("📝 問題番号", min_value=min_no, max_value=max_no, value=default_val, key=f"q_selector_{mode}")
    
    if q_no in problems:
        d_info = [len(str(abs(n))) for n in problems[q_no]]
        p_type = any(n < 0 for n in problems[q_no])
        
        # 【変更点】HTML/CSSでの装飾をやめ、標準のst.infoを使用して互換性を高める
        type_str = "加減算" if p_type else "加算のみ"
        st.info(f"📊 {min(d_info)}〜{max(d_info)}桁  |  ⚙️ {type_str}")

    if st.session_state['current_q'] != q_no:
        st.session_state.update({'correct_ans': None, 'audio_html': None, 'current_q': q_no, 'last_voice_id': None})
    
    if st.session_state['audio_html'] and st.session_state['last_voice_id'] != selected_voice_id:
        create_and_play_audio(q_no, problems, selected_voice_id, base_speed); st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    if is_random_mode and q_no == max_no:
        if st.button("🆕 次の問題を出す", type="primary", use_container_width=True):
            new_q = max_no + 1
            st.session_state['generated_problems'] = {new_q: generate_single_problem(min_d, max_d, rows_count, allow_sub)}
            create_and_play_audio(new_q, st.session_state['generated_problems'], selected_voice_id, base_speed); st.rerun()
    else:
        if st.button("▶️ 再生する (Play)", type="primary", use_container_width=True):
            create_and_play_audio(q_no, problems, selected_voice_id, base_speed); st.rerun()

    if st.session_state['audio_html']:
        st.markdown("### 🎧 Listening...")
        st.components.v1.html(st.session_state['audio_html'], height=130)

    with st.expander("📜 問題の数字を確認する"):
        if q_no in problems:
            html_nums = "".join([f"<div class='number-display'>{n:,}</div>" for n in problems[q_no]])
            st.markdown(f"""
            <div class="custom-card">
                {html_nums}
                <div style='text-align: right; font-weight: bold; font-size: 1.2em; margin-top: 5px; color: inherit;'>Total: {sum(problems[q_no]):,}</div>
            </div>
            """, unsafe_allow_html=True)

    if st.session_state['correct_ans'] is not None:
        st.divider()
        with st.form(key=f'ans_form_{q_no}'): 
            user_input = st.text_input("答えを入力:", key=f"in_{q_no}")
            if st.form_submit_button("答え合わせ", type="secondary", use_container_width=True):
                try:
                    val = int(user_input.replace(",", "").strip())
                    if val == st.session_state['correct_ans']:
                        st.success(f"正解です ✨ {val:,}")
                    else: st.error(f"残念... 正解は {st.session_state['correct_ans']:,} でした。")
                except: st.warning("数字を入力してください。")
