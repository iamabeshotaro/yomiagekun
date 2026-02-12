import streamlit as st
import os
import csv
import time
import base64
from gtts import gTTS
from num2words import num2words

# --- 設定 ---
DATA_DIR = "data"

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

def generate_audio_file(number, row_data):
    speech_parts = [f"Question {number},"]
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
    full_text = " ".join(speech_parts)
    
    tts = gTTS(text=full_text, lang='en')
    filename = f"temp_q{number}.mp3"
    tts.save(filename)
    return filename

# --- UI構築 ---
st.set_page_config(page_title="English Anzan Trainer", layout="centered")
st.title("🏆 英語読み上げ算 Web版")

# サイドバーで年度とスピード設定
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
if not files:
    st.error(f"'{DATA_DIR}' フォルダにCSVファイルを入れてください。")
else:
    selected_file = st.sidebar.selectbox("年度を選択", files)
    problems = load_problems(selected_file)
    
    # スピードレベル（Streamlitでは直接再生スピードを変えるのが難しいため、
    # gTTSのslowオプションを切り替えるか、audio要素で調整する形式にします）
    speed_mode = st.sidebar.radio("スピードモード", ("普通 (Normal)", "ゆっくり (Slow)"))
    is_slow = (speed_mode == "ゆっくり (Slow)")

    # メイン画面
    if problems:
        max_no = max(problems.keys())
        min_no = min(problems.keys())
        
        q_no = st.number_input("問題番号を選択", min_value=min_no, max_value=max_no, value=min_no)
        
        if st.button("問題を生成・再生"):
            with st.spinner('音声を生成中...'):
                audio_file = generate_audio_file(q_no, problems[q_no])
                
                # 音声ファイルを読み込んでブラウザで再生可能な状態にする
                audio_bytes = open(audio_file, "rb").read()
                st.audio(audio_bytes, format="audio/mp3", start_time=0)
                os.remove(audio_file)
                
                # 正解をセッション状態に保存
                st.session_state['correct_ans'] = sum(problems[q_no])
                st.session_state['current_q'] = q_no

        # 解答入力
        if 'correct_ans' in st.session_state:
            st.divider()
            user_input = st.text_input("答えを入力してください (Answer?)")
            
            if st.button("答え合わせ"):
                clean_input = user_input.replace(",", "").strip()
                if clean_input:
                    try:
                        if int(clean_input) == st.session_state['correct_ans']:
                            st.success(f"✨ 正解です！ (No.{st.session_state['current_q']})")
                            st.balloons()
                        else:
                            st.error(f"❌ 残念！ 正解は {st.session_state['correct_ans']:,} でした。")
                    except:
                        st.warning("有効な数値を入力してください。")