import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="안식일 출석 체크 - 사릉중앙교회", layout="centered")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(worksheet="구성원정보", ttl=0) 
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(".0", "", regex=False).str.strip()
        df[col] = df[col].replace("nan", "")
    return df

try:
    df_members = load_data()
except Exception as e:
    st.error(f"❌ 데이터를 불러오지 못했습니다: {e}")
    st.stop()

st.title("⛪ 사릉중앙교회 안식일 출석")

if 'search_clicked' not in st.session_state:
    st.session_state.search_clicked = False

col1, col2, col3 = st.columns(3)

with col1:
    years = ["--"] + sorted(df_members["년도"].unique().tolist(), reverse=True)
    selected_year = st.selectbox("📅 년도 선택", years)

with col2:
    if selected_year != "--":
        raw_groups = sorted(df_members[df_members["년도"] == selected_year]["목양반"].unique().tolist())
        display_groups = {f"{g} 목양반": g for g in raw_groups}
        selected_display_group = st.selectbox("📌 목양반 선택", ["--"] + list(display_groups.keys()))
        selected_group = display_groups.get(selected_display_group, "--")
    else:
        st.selectbox("📌 목양반 선택", ["--"], disabled=True)
        selected_group = "--"

with col3:
    today = datetime.now()
    days_until_saturday = (5 - today.weekday()) % 7
    default_saturday = today + timedelta(days=days_until_saturday)
    selected_date = st.date_input("🗓️ 날짜 선택 (토)", value=default_saturday)

if st.button("🔍 명단 확인", use_container_width=True, type="primary"):
    if selected_year != "--" and selected_group != "--":
        if selected_date.weekday() != 5:
            st.error("⚠️ 안식일(토요일) 날짜만 선택 가능합니다.")
            st.session_state.search_clicked = False
        else:
            st.session_state.search_clicked = True
    else:
        st.warning("년도와 목양반을 정확히 선택해 주세요.")

st.divider()

# --- 명단 출력 및 기록 로직 ---
if st.session_state.search_clicked:
    group_members = df_members[
        (df_members["년도"] == str(selected_year)) & 
        (df_members["목양반"] == str(selected_group))
    ].copy()

    if not group_members.empty:
        status_order = {"출석중": 0, "장기 미결석": 1, "전출": 2}
        group_members['sort_priority'] = group_members
