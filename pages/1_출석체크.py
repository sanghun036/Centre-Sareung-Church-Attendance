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
        group_members['sort_priority'] = group_members['상태'].map(lambda x: status_order.get(x, 3))
        group_members = group_members.sort_values('sort_priority').drop('sort_priority', axis=1)

        st.subheader(f"📋 {selected_group} 목양반 명단")

        attendance_results = {}

        # 폼 대신 일반 컨테이너 사용하여 실시간 반응성 확보
        for index, row in group_members.iterrows():
            name = row["이름"]
            duty = row["직분"]
            current_status = row["상태"]
            
            # 레이아웃 수정: 이름 | 직분 | 상태 드롭다운
            name_col, status_col = st.columns([2, 1])
            with name_col:
                st.write(f"**{name}** {f'({duty})' if duty else ''}")
            with status_col:
                # 상태 드롭다운 (제목 제거)
                status_list = ["출석중", "장기 미결석", "전출"]
                default_idx = status_list.index(current_status) if current_status in status_list else 0
                new_status = st.selectbox("상태", status_list, index=default_idx, key=f"stat_{name}_{index}", label_visibility="collapsed")
            
            # 출석 및 사유 레이아웃
            att_col, reason_col = st.columns([1, 1])
            with att_col:
                att_status = st.radio(f"출석_{name}", ["출석", "불참"], key=f"att_{name}_{index}", horizontal=True, label_visibility="collapsed")
            
            with reason_col:
                reason = "-"
                # 불참일 때만 사유 드롭다운 노출 (실시간 반영)
                if att_status == "불참":
                    reason = st.selectbox("사유", ["근무", "건강", "타교회", "미확인"], key=f"re_{name}_{index}", label_visibility="collapsed")
            
            attendance_results[name] = {"출석": att_status, "사유": reason, "변경상태": new_status}
            st.write("---")

        # 저장 버튼을 별도로 배치
        if st.button("✅ 안식일 출석 최종 확정", use_container_width=True, type="primary"):
            with st.status("데이터를
