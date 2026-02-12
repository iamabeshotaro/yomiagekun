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

# --- 関数群 ---

def set_bg_image(image_file):
    """背景画像を設定し、全体のスタイルを調整する"""
    if not os.path.exists(image_file):
        return
    with open(image_file, "rb") as f:
        img_data = f.read()
    b64_encoded = base64.b64encode(img_data).decode()
    style = f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{b64_encoded}");
        background-attachment: fixed;
        background-size: cover;
        color: #222222;
    }}
    /* 文字の視認性を高めるシャドウ */
    p, div, label, span, li, .stMarkdown {{
        text-shadow: 0 0 2px rgba(255,255,255, 0.9);
    }}
    h1, h2, h3, h4 {{
        color: #111111 !important;
        text-shadow: 2px 2px 4px rgba(255,255,255, 1.0), -2px -2px 4px rgba(255,255,255, 1.0) !important;
        font-family: 'Helvetica Neue', sans-serif;
    }}
    /* メインエリアのカード風デザイン */
    [data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {{
        background-color: rgba(255, 255, 255, 0.96); 
        padding: 2.5rem;
        border-radius: 15px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.2); 
    }}
    [data-testid="stSidebar"] {{
         background-color: rgba(250, 250, 250, 0.95);
    }}
    /* タブのデザイン調整 */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 10px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: rgba(255, 255, 255, 0.5);
        border-radius: 5px;
        padding: 5px 15px;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: #fff;
        font-weight: bold;
    }}
    </style>
    """
    st.markdown(style, unsafe_allow_html=True)

def get_problem_counts():
    """dataフォルダ内のCSVファイルと問題数を取得する"""
    counts = {}
    if not os.path.exists(DATA_DIR):
        return counts
    files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".csv")])
    for f_name in files:
        path = os.path.join(DATA_DIR, f_name)
        try:
            with open(path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None) # ヘッダーをスキップ
                count = sum(1 for row in reader if row)
                counts[f_name] = count
        except:
            counts[f_name] = 0
    return counts

def load_problems_from_csv(file_name):
    """指定されたCSVファイルから問題を読み込む"""
    problems = {}
    path = os.path.join(DATA_DIR, file_name)
    try:
        with open(path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    no = int(row['no'])
                    nums = []
                    for i in range(1, 100):
                        key = f'row{i}'
                        if key in row and row[key]:
                            nums.append(int(row[key]))
                        else:
                            break
                    problems[no] = nums
                except: continue
        return problems
    except:
        return {}

def get_next_digits_from_deck(rows, min_digit, max_digit):
    """
    セッションステートのデッキから次の桁数リストを取得する
    - 一巡ルール（偏り防止）
    - 最大・最小桁の保証
    """
    if 'digit_deck' not in st.session_state:
        st.session_state['digit_deck'] = []
    
    deck = st.session_state['digit_deck']
    # 設定が変わっていたらデッキをリセット
    if deck and (min(deck) < min_digit or max(deck) > max_digit):
        deck = []

    current_digits = []
    needed = rows
    digit_range = list(range(min_digit, max_digit + 1))

    while len(current_digits) < needed:
        if not deck:
            new_set = digit_range[:]
            random.shuffle(new_set)
            deck.extend(new_set)
        
        card = deck.pop(0)
        current_digits.append(card)
    
    st.session_state['digit_deck'] = deck

    # 最大・最小保証チェック
    if min_digit not in current_digits:
        replaceable_indices = [i for i, d in enumerate(current_digits) if d != max_digit]
        if not replaceable_indices: replaceable_indices = [0]
        target_idx = random.choice(replaceable_indices)
        current_digits[target_idx] = min_digit

    if max_digit not in current_digits:
        replaceable_indices = [i for i, d in enumerate(current_digits) if d != min_digit]
        if not replaceable_indices: replaceable_indices = [0]
        target_idx = random.choice(replaceable_indices)
        current_digits[target_idx] = max_digit

    return current_digits

def generate_single_problem(min_digit, max_digit, rows, allow_subtraction):
    """1問分のデータを生成する（答えがマイナスにならないよう調整）"""
    digits_list = get_next_digits_from_deck(rows, min_digit, max_digit)
    
    nums = []
    current_total = 0  # 現在の合計値を記録
    
    for r, d in enumerate(digits_list):
        lower = 10**(d-1)
        upper = 10**d - 1
        val = random.randint(lower, upper)
        
        # 符号の決定
        if r > 0 and allow_subtraction:
            # 50%の確率で引き算を試みる
            if random.choice([True, False]):
                # 【修正ポイント】引き算しても合計が0以上になる場合のみマイナスにする
                if current_total - val >= 0:
                    val = -val
                # ※合計がマイナスになってしまう場合は、プラス（足し算）のままにする
        
        nums.append(val)
        current_total += val
        
    return nums

def get_digit_info(numbers):
    """数字リストから桁数の範囲（最小〜最大）を文字列で返す"""
    if not numbers:
        return "-"
    lengths = [len(str(abs(n))) for n in numbers]
    min_len = min(lengths)
    max_len = max(lengths)
    return f"{min_len}桁" if min_len == max_len else f"{min_len}〜{max_len}桁"

def get_problem_type(numbers):
    """数字リストにマイナスが含まれるか判定し、「加算」か「加減算」を返す"""
    if not numbers:
        return "不明"
    is_subtraction = any(n < 0 for n in numbers)
    return "加減算" if is_subtraction else "加算"

def generate_audio_text(row_data):
    """読み上げ用の英文テキストを作成する"""
    speech_parts = []
    last_op = None 
    for i, num in enumerate(row_data):
        text_num = num2words(abs(num), lang='en').replace(" and ", " ").replace(",", "")
        text_with_unit = f"{text_num} dollars"
        
        if i == 0:
            speech_parts.append(f"starting with, {text_with_unit},")
            last_op = "Add"
        else:
            current_op = "Add" if num >= 0 else "Subtract"
            if current_op != last_op:
                speech_parts.append(f"{current_op}, {text_with_unit},")
                last_op = current_op
            else:
                speech_parts.append(f"{text_with_unit},")
            
    speech_parts.append("thats all")
    return " ".join(speech_parts)

async def generate_edge_audio(text, voice, output_file):
    """Edge-TTSを使って音声を生成しファイルに保存する（非同期）"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def create_and_play_audio(q_no, problems, voice_id, playback_rate):
    """音声生成のメイン処理"""
    if q_no not in problems:
        return
    
    full_text = generate_audio_text(problems[q_no])
    temp_file = f"temp_audio_{int(time.time())}.mp3"
    
    try:
        asyncio.run(generate_edge_audio(full_text, voice_id, temp_file))
        
        with open(temp_file, "rb") as f:
            audio_bytes = f.read()
        os.remove(temp_file)

        audio_b64 = base64.b64encode(audio_bytes).decode()
        player_id = f"audio_player_{int(time.time())}"
        
        audio_html_content = f"""
            <audio id="{player_id}" controls autoplay style="width: 100%; margin-top: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-radius: 30px;">
                <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
            </audio>
            <script>
                (function() {{
                    var audio = document.getElementById("{player_id}");
                    if (audio) {{
                        audio.playbackRate = {playback_rate};
                        var playPromise = audio.play();
                        if (playPromise !== undefined) {{
                            playPromise.then(_ => {{}}).catch(error => {{
                                console.log("Auto-play blocked");
                            }});
                        }}
                    }}
                }})();
            </script>
        """
        
        st.session_state['correct_ans'] = sum(problems[q_no])
        st.session_state['audio_html'] = audio_html_content
        st.session_state['current_q'] = q_no
        st.session_state['last_voice_id'] = voice_id
        
    except Exception as e:
        st.error(f"音声生成エラー: {e}")

# --- メインアプリ ---
st.set_page_config(page_title=APP_NAME_EN, layout="centered")
set_bg_image(BG_IMAGE)

st.title(APP_NAME_EN)
st.markdown(f"##### {APP_NAME_JP}")

# セッション状態の初期化
if 'correct_ans' not in st.session_state:
    st.session_state['correct_ans'] = None
if 'current_q' not in st.session_state:
    st.session_state['current_q'] = None
if 'audio_html' not in st.session_state:
    st.session_state['audio_html'] = None
if 'last_voice_id' not in st.session_state:
    st.session_state['last_voice_id'] = None
if 'generated_problems' not in st.session_state:
    st.session_state['generated_problems'] = {}
if 'digit_deck' not in st.session_state:
    st.session_state['digit_deck'] = []

# --- サイドバー設定 ---
with st.sidebar:
    st.header("Settings")
    
    mode = st.radio("📁 モード選択", ["CSV読み込み", "ランダム生成"])
    st.divider()

    problems = {}
    selected_file_label = ""
    is_random_mode = (mode == "ランダム生成")

    if mode == "CSV読み込み":
        file_counts = get_problem_counts()
        if not file_counts:
            st.error(f"'{DATA_DIR}' フォルダにCSVファイルが見つかりません。")
        else:
            def format_func(filename):
                count = file_counts.get(filename, 0)
                return f"{filename} ({count}問)"
            selected_file = st.selectbox("年度を選択", options=list(file_counts.keys()), format_func=format_func)
            problems = load_problems_from_csv(selected_file)
            selected_file_label = selected_file

    else: # ランダム生成モード
        st.subheader("🎲 生成設定")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            min_d = st.number_input("最小桁数", 1, 16, 3)
        with col_d2:
            max_d = st.number_input("最大桁数", 1, 16, 16)
        
        if min_d > max_d:
            st.warning("最小桁数が最大桁数を超えています")

        rows_count = st.slider("口数 (行数)", 3, 15, 5)
        allow_sub = st.checkbox("引き算を含める (加減算)", value=False)
        
        problems = st.session_state['generated_problems']
        selected_file_label = "ランダム生成"

    st.divider()
    st.subheader("🗣️ Voice / Accent")
    selected_voice_label = st.selectbox("話者を選択", options=list(VOICE_MAP.keys()), index=0)
    selected_voice_id = VOICE_MAP[selected_voice_label]

# --- メインエリア ---

if is_random_mode and not problems:
    st.info("設定を決めて、下のボタンからスタートしてください！")
    if st.button("🚀 スタート (最初の問題を生成)", type="primary", use_container_width=True):
        new_q_no = 1
        new_problem = generate_single_problem(min_d, max_d, rows_count, allow_sub)
        st.session_state['generated_problems'][new_q_no] = new_problem
        problems = st.session_state['generated_problems']
        create_and_play_audio(new_q_no, problems, selected_voice_id, 1.0)
        st.rerun()

elif not problems and mode == "CSV読み込み":
    st.error("データの読み込みに失敗しました。")
    
else:
    min_no = min(problems.keys())
    max_no = max(problems.keys())
    
    if mode == "CSV読み込み":
        st.info(f"📂 **{selected_file_label}** を読み込みました。（No.{min_no} 〜 No.{max_no}）")
    else:
        st.success(f"🎲 **ランダムモード** 実施中（現在: {max_no}問目）")
        
    st.markdown("---")

    col1, col2 = st.columns([1, 1], gap="medium")
    with col1:
        st.markdown("##### 🚀 スピード")
        speed_level = st.slider("Level (1-15)", 1, 15, 5, label_visibility="collapsed")
        playback_rate = 0.5 + (speed_level * 0.1)
        st.caption(f"再生倍率: **{playback_rate:.1f}x**")
        
    with col2:
        st.markdown("##### 📝 問題番号")
        default_val = st.session_state['current_q'] if st.session_state['current_q'] else min_no
        if default_val not in problems:
            default_val = max_no
        q_no = st.number_input("No.", min_value=min_no, max_value=max_no, value=default_val, label_visibility="collapsed")
        
        if q_no in problems:
            digit_info = get_digit_info(problems[q_no])
            prob_type = get_problem_type(problems[q_no])
            
            type_color = "#e3f2fd" if prob_type == "加算" else "#fff3e0"
            type_text_color = "#1565c0" if prob_type == "加算" else "#ef6c00"
            type_border = "#bbdefb" if prob_type == "加算" else "#ffe0b2"

            badge_html = f"""
            <div style="display: flex; gap: 5px; margin-top: 8px;">
                <div style="flex: 1; background-color: #e8f5e9; color: #2e7d32; padding: 4px 5px; border-radius: 4px; font-weight: bold; font-size: 0.85em; text-align: center; border: 1px solid #c8e6c9;">
                    📊 {digit_info}
                </div>
                <div style="flex: 1; background-color: {type_color}; color: {type_text_color}; padding: 4px 5px; border-radius: 4px; font-weight: bold; font-size: 0.85em; text-align: center; border: 1px solid {type_border};">
                    ⚙️ {prob_type}
                </div>
            </div>
            """
            st.markdown(badge_html, unsafe_allow_html=True)

    if st.session_state['current_q'] != q_no:
            st.session_state['correct_ans'] = None
            st.session_state['audio_html'] = None
            st.session_state['current_q'] = q_no
            st.session_state['last_voice_id'] = None

    if (st.session_state['current_q'] == q_no and 
        st.session_state['audio_html'] is not None and 
        st.session_state['last_voice_id'] != selected_voice_id):
        create_and_play_audio(q_no, problems, selected_voice_id, playback_rate)
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True) 

    if is_random_mode:
        if q_no == max_no:
            if st.button("🆕 次の問題を作成して進む (Next)", type="primary", use_container_width=True):
                new_q_no = max_no + 1
                new_problem = generate_single_problem(min_d, max_d, rows_count, allow_sub)
                st.session_state['generated_problems'][new_q_no] = new_problem
                create_and_play_audio(new_q_no, st.session_state['generated_problems'], selected_voice_id, playback_rate)
                st.rerun()
        else:
            if st.button("▶️ 再生スタート (Play)", use_container_width=True):
                create_and_play_audio(q_no, problems, selected_voice_id, playback_rate)
                st.rerun()

    else:
        if st.button("▶️ 再生スタート (Play)", type="primary", use_container_width=True):
            if q_no in problems:
                create_and_play_audio(q_no, problems, selected_voice_id, playback_rate)
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True) 
    if st.session_state['audio_html']:
            st.markdown("### 🎧 Listening...")
            st.components.v1.html(st.session_state['audio_html'], height=70)

    if st.session_state['correct_ans'] is not None:
        st.divider()
        st.markdown("#### ✍️ Answer Check")
        with st.form(key='answer_form'):
            input_key = f"user_answer_input_{st.session_state['current_q']}"
            user_input = st.text_input("答えを入力してください (Enter Answer):", key=input_key)
            st.markdown("<br>", unsafe_allow_html=True)
            submit_btn = st.form_submit_button("答え合わせ (Check)", type="secondary", use_container_width=True)
            
            if submit_btn:
                clean_input = user_input.replace(",", "").strip()
                if clean_input:
                    try:
                        val = int(clean_input)
                        correct = st.session_state['correct_ans']
                        if val == correct:
                            st.success(f"**Tres bien! (正解!)** 🎉\n\nAns: {correct:,}")
                            st.balloons()
                        else:
                            st.error(f"**Dommage... (残念...)**\n\n正解は **{correct:,}** でした。")
                    except ValueError:
                        st.warning("数字を入力してください。")
