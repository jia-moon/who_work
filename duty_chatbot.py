import streamlit as st
import pandas as pd
import datetime
import re
import os
from io import StringIO

st.set_page_config(page_title="당직 알림 챗봇", layout="centered")
st.title("🤖 스면 비상대응 담당자 알림봇")

# 말풍선 스타일 함수
def chat_bubble(message, sender="user"):
    style = "background-color:#DCF8C6; padding:10px; border-radius:10px; margin:5px; max-width:80%;" if sender == "user" else "background-color:#F1F0F0; padding:10px; border-radius:10px; margin:5px; max-width:80%;"
    align = "flex-end" if sender == "user" else "flex-start"
    st.markdown(f"""
        <div style='display: flex; justify-content: {align};'>
            <div style='{style}'>{message}</div>
        </div>
    """, unsafe_allow_html=True)

# 텍스트 파일 파싱 함수
def parse_txt(file):
    content = file.read().decode("utf-8")
    lines = content.splitlines()
    data = []
    current_task = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not re.match(r"\d{1,2}/\d{1,2}|\d{1,2}\(.*\)", line):
            current_task = line
        else:
            date_info, persons = line.split(":")
            date_info = date_info.strip()
            persons = persons.strip()
            data.append({"업무": current_task, "날짜": date_info, "담당자": persons})
    df = pd.DataFrame(data)
    return df

# 관리자용 비밀번호 설정
ADMIN_PASSWORD = "tltmxpaxla1!"

# 파일 저장 경로
UPLOAD_PATH = "/tmp/duty_data"

if not os.path.exists(UPLOAD_PATH):
    os.makedirs(UPLOAD_PATH)

# 사이드바 로그인 항상 표시
st.sidebar.header("🔐 관리자 로그인")
password_input = st.sidebar.text_input("비밀번호를 입력하세요", type="password")
is_admin = password_input == ADMIN_PASSWORD

# 파일 업로드 (관리자만)
if is_admin:
    uploaded_file = st.sidebar.file_uploader("📄 새 당직표 파일 업로드 (엑셀 또는 텍스트)", type=["xlsx", "xls", "csv", "txt"])
    if uploaded_file:
        for old_file in os.listdir(UPLOAD_PATH):
            old_file_path = os.path.join(UPLOAD_PATH, old_file)
            os.remove(old_file_path)
        file_path = os.path.join(UPLOAD_PATH, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("파일 업로드가 완료되었습니다. 새로고침 후 사용 가능합니다.")

# 파일 불러오기
uploaded_files = [f for f in os.listdir(UPLOAD_PATH) if f.endswith(('.xlsx', '.xls', '.csv', '.txt'))]
if uploaded_files:
    file_name = uploaded_files[0]
    file_path = os.path.join(UPLOAD_PATH, file_name)

    if file_name.endswith(('.xlsx', '.xls')):
        df_raw = pd.read_excel(file_path, header=0)
        is_txt_format = False
    elif file_name.endswith(('.csv')):
        df_raw = pd.read_csv(file_path, header=0)
        is_txt_format = False
    elif file_name.endswith(('.txt')):
        with open(file_path, "rb") as f:
            df_raw = parse_txt(f)
        is_txt_format = True
    else:
        st.error("지원하지 않는 파일 형식입니다.")
        st.stop()

    df_raw = df_raw.fillna("")

    # 날짜 매핑 함수
    def parse_date(text):
        match = re.search(r"(\d{1,2})[\/\.\(월](\d{1,2})", text)
        if match:
            return datetime.date(datetime.datetime.now().year, int(match.group(1)), int(match.group(2)))
        return None

    # 사용자 입력
    query = st.text_input("💬 날짜를 입력하세요 (예: 오늘 / 내일 / 5월2일)")

    if query:
        chat_bubble(query, sender="user")

        today = datetime.date.today()
        target_date = today
        if "오늘" in query:
            target_date = today
        elif "내일" in query:
            target_date = today + datetime.timedelta(days=1)
        else:
            match = re.search(r"(\d{1,2})[\/\.\(월](\d{1,2})", query)
            if match:
                month = int(match.group(1))
                day = int(match.group(2))
                target_date = datetime.date(today.year, month, day)

        if is_txt_format:
            df_raw["매칭날짜"] = df_raw["날짜"].apply(lambda x: parse_date(x))
            matched_df = df_raw[df_raw["매칭날짜"] == target_date]
        else:
            date_cols = [col for col in df_raw.columns if isinstance(col, datetime.datetime) or re.match(r"\d{1,2}[\/\.\(]\d{1,2}", str(col))]
            date_map = {col: parse_date(col) for col in date_cols}
            matched_col = None
            for col, d in date_map.items():
                if d == target_date:
                    matched_col = col
                    break

        if (is_txt_format and matched_df.empty) or (not is_txt_format and not matched_col):
            response = f"❗ {target_date}에 해당하는 정보를 찾을 수 없어요."
            chat_bubble(response, sender="bot")
        else:
            responses = []
            if is_txt_format:
                for idx, row in matched_df.iterrows():
                    responses.append(f"🛠️ <b>{row['업무']}</b>: <b>{row['담당자']}</b>")
            else:
                for idx, row in df_raw.iterrows():
                    task = row["업무"]
                    person = row[matched_col]
                    responses.append(f"🛠️ <b>{task}</b>: <b>{person}</b>")
            response = f"📅 <b>{target_date.strftime('%Y-%m-%d')}</b> 전체 담당자 목록:<br>" + "<br>".join(responses)
            chat_bubble(response, sender="bot")
else:
    st.error("업로드된 파일이 없습니다. 관리자에게 문의하세요.")
