import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="사릉중앙교회 출석부")

st.title("⛪ 사릉중앙교회 출석 관리")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기 (시트의 첫 번째 탭 내용을 읽어옴)
df = conn.read()

# 불러온 데이터 화면에 출력해보기
st.subheader("현재 명단 데이터")
st.dataframe(df)

st.info("데이터가 잘 보인다면 연결에 성공한 것입니다!")
