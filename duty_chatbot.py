import streamlit as st
import pandas as pd
import datetime
import re
from io import StringIO

st.set_page_config(page_title="당직 알림 챗봇", layout="centered")
st.title("🤖 당직 알림 챗봇")

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

# 파일 업로드
uploaded_file = st.file_uploader("📄 당직표 파일을 업로드하세요 (엑셀 또는 텍스트)", type=["xlsx", "xls", "csv", "txt"])

if uploaded_file:
    file_name = uploaded_file.name
    if file_name.endswith(('.xlsx', '.xls')):
        df_raw = pd.read_excel(uploaded_file, header=0)
        is_txt_format = False
    elif file_name.endswith(('.csv')):
        df_raw = pd.read_csv(uploaded_file, header=0)
        is_txt_format = False
    elif file_name.endswith(('.txt')):
        df_raw = parse_txt(uploaded_file)
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
    st.info("👆 엑셀 또는 텍스트 파일을 먼저 업로드해주세요.")
