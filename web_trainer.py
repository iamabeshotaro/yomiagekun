import streamlit as st
import os
import csv
import base64
import time
import asyncio
import edge_tts
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
    p, div, label, span, li, .stMarkdown {{
        text-shadow: 0 0 2px rgba(255,255,255, 0.9);
    }}
    h1, h2, h3, h4 {{
        color: #111111 !important;
        text-shadow: 2px 2px 4px rgba(255,255,255, 1.0), -2px -2px 4px rgba(255,255,255, 1.0) !important;
        font-family: 'Helvetica Neue', sans-serif;
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

def get_problem_counts():
    counts = {}
    if not os.path.exists(DATA_DIR):
        return counts
    files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".csv")])
    for f_name in files:
        path = os.path.join(DATA_DIR, f_name)
        try:
            with open(path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)
                count = sum(1 for row in reader if row)
                counts[f_name] = count
        except:
            counts[f_name] = 0
    return counts

def load_problems(file_name):
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

def get_digit_info(numbers):
    if not numbers:
        return "-"
    lengths = [len(str(abs(n))) for n in numbers]
    min_len = min(lengths)
    max_len = max(lengths)
    return f"{min_len}桁" if min_len == max_len else f"{min_len}〜{max_len}桁"

def generate_audio_text(row_data):
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
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

# --- 共通の音声生成・登録関数 ---
def create_and_play_audio(q_no, problems, voice_id, playback_rate):
    if q_no not in problems:
        return
    
    full_text = generate_audio_text(problems[q_no])
    temp_file = f"temp_audio_{int(time.time())}.mp3"
    
    try:
        # 非同期処理でEdge-TTSを実行
        asyncio.run(generate_edge_audio(full_text, voice_id, temp_file))
        
        with open(temp_file, "rb") as f:
            audio_bytes = f.read()
        os.remove(temp_file)

        audio_b64 = base64.b64encode(audio_bytes).decode()
        player_id = f"audio_player_{int(time.time())}"
        
        # HTML生成
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
        
        # セッション情報の更新
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

# セッション初期化
if 'correct_ans' not in st.session_state:
    st.session_state['correct_ans'] = None
if 'current_q' not in st.session_state:
    st.session_state['current_q'] = None
if 'audio_html' not in st.session_state:
    st.session_state['audio_html'] = None
if 'last_voice_id' not in st.session_state:
    st.session_state['last_voice_id'] = None

file_counts = get_problem_counts()

if not file_counts:
    st.error(f"'{DATA_DIR}' フォルダにCSVファイルが見つかりません。")
else:
    # --- サイドバー ---
    with st.sidebar:
        st.header("Settings")
        def format_func(filename):
            count = file_counts.get(filename, 0)
            return f"{filename} ({count}問)"

        selected_file = st.selectbox(
            "年度を選択", 
            options=list(file_counts.keys()),
            format_func=format_func
        )

        st.divider()
        st.subheader("🗣️ Voice / Accent")
        selected_voice_label = st.selectbox(
            "話者を選択",
            options=list(VOICE_MAP.keys()),
            index=0
        )
        selected_voice_id = VOICE_MAP[selected_voice_label]
        
    problems = load_problems(selected_file)

    if not problems:
        st.error("データの読み込みに失敗しました。")
    else:
        min_no = min(problems.keys())
        max_no = max(problems.keys())

        st.info(f"📂 **{selected_file}** を読み込みました。（収録範囲: No.{min_no} 〜 No.{max_no}）")
        st.markdown("---")

        col1, col2 = st.columns([1, 1], gap="medium")
        with col1:
            st.markdown("##### 🚀 スピード")
            # --- 修正箇所: 1〜15段階に変更 ---
            speed_level = st.slider("Level (1-15)", 1, 15, 5, label_visibility="collapsed")
            playback_rate = 0.5 + (speed_level * 0.1)
            st.caption(f"再生倍率: **{playback_rate:.1f}x**")
            
        with col2:
            st.markdown("##### 📝 問題番号")
            q_no = st.number_input(
                "No.", min_value=min_no, max_value=max_no, value=min_no, label_visibility="collapsed"
            )
            if q_no in problems:
                digit_info = get_digit_info(problems[q_no])
                st.markdown(
                    f"""<div style="background-color: #e8f5e9; color: #2e7d32; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 0.9em; text-align: center; margin-top: 8px; border: 1px solid #c8e6c9;">📊 {digit_info}</div>""", 
                    unsafe_allow_html=True
                )

        # 問題番号変更時のリセット
        if st.session_state['current_q'] != q_no:
             st.session_state['correct_ans'] = None
             st.session_state['audio_html'] = None
             st.session_state['current_q'] = q_no
             st.session_state['last_voice_id'] = None

        # --- 自動更新ロジック ---
        # 声が変わったら自動再生
        if (st.session_state['current_q'] == q_no and 
            st.session_state['audio_html'] is not None and 
            st.session_state['last_voice_id'] != selected_voice_id):
            
            create_and_play_audio(q_no, problems, selected_voice_id, playback_rate)
            st.rerun()
            
        # スピードが変わった場合も、自動でプレイヤーの速度を更新したいが、
        # Python側でrerunすると音声が最初からになるため、
        # ここでは「次に再生ボタンを押した時」または「HTMLが再描画された時」に反映されます。
        # ※HTML内のJavaScriptが playback_rate を受け取っているので、
        # 　一度再生された後にスライダーを動かしてもリアルタイムには変わりませんが、
        # 　「再生スタート」を押せば新しい速度になります。

        st.markdown("<br><br>", unsafe_allow_html=True) 

        # --- 再生ボタン ---
        if st.button("▶️ 再生スタート (Play)", type="primary", use_container_width=True):
            if q_no in problems:
                create_and_play_audio(q_no, problems, selected_voice_id, playback_rate)
                st.rerun()
            else:
                st.error("指定された問題番号が見つかりません。")

        # 音声プレイヤー
        if st.session_state['audio_html']:
             st.markdown("### 🎧 Listening...")
             st.components.v1.html(st.session_state['audio_html'], height=70)

        # 解答エリア
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

