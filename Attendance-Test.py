import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="출석 체크 - 사릉중앙교회", layout="centered")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 불러오기 (구성원정보 탭)
@st.cache_data(ttl=600)
def load_member_data():
    return conn.read(worksheet="구성원정보")

df_members = load_member_data()

st.title("📅 안식일 출석 체크")

# --- 상단 필터 영역 ---
with st.container():
    col1, col2, col3 = st.columns(3)
    
    with col1:
        years = sorted(df_members["년도"].unique().tolist(), reverse=True)
        selected_year = st.selectbox("📅 년도 선택", years)
        
    with col2:
        # 선택한 년도에 해당하는 목양반 목록 추출
        groups = sorted(df_members[df_members["년도"] == selected_year]["목양반"].unique().tolist())
        selected_group = st.selectbox("📌 목양반 선택", groups)
        
    with col3:
        # 토요일만 선택 가능하도록 로직 설정
        today = datetime.now()
        # 가장 가까운 토요일 계산 (0:월, 5:토, 6:일)
        default_date = today + timedelta(days=(5 - today.weekday()) if today.weekday() <= 5 else 6)
        selected_date = st.date_input("🗓️ 날짜 선택 (토)", value=default_date)
        
        if selected_date.weekday() != 5:
            st.error("⚠️ 토요일만 선택 가능합니다.")

st.divider()

# --- 명단 출력 및 상태 입력 영역 ---
# 선택된 조건에 맞는 구성원 필터링
filtered_members = df_members[
    (df_members["년도"] == selected_year) & 
    (df_members["목양반"] == selected_group) &
    (df_members["상태"] == "출석중") # 상태가 '출석중'인 사람만 표시
]

if not filtered_members.empty:
    st.subheader(f"📋 {selected_group} 명단 ({len(filtered_members)}명)")
    
    # 임시 저장소(session_state) 초기화 (입력값 보존용)
    if "attendance_data" not in st.session_state:
        st.session_state.attendance_data = {}

    # 명단 루프
    for index, row in filtered_members.iterrows():
        name = row["이름"]
        st.write(f"**{name}** ({row['직분']})")
        
        c1, c2 = st.columns([1, 1])
        
        with c1:
            # 출석/불참 선택 (라디오 버튼)
            status = st.radio(
                f"{name} 상태", ["출석", "불참"], 
                key=f"status_{name}", horizontal=True, label_visibility="collapsed"
            )
            st.session_state.attendance_data[name] = {"출석여부": status, "불참사유": "-"}

        with c2:
            # 불참일 때만 사유 드롭다운 활성화
            if status == "불참":
                reason = st.selectbox(
                    f"{name} 사유", ["근무", "건강 문제", "타교회 출석", "미확인"],
                    key=f"reason_{name}", label_visibility="collapsed"
                )
                st.session_state.attendance_data[name]["불참사유"] = reason
        st.write("---")

    # --- 최종 확정/취소 버튼 ---
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("✅ 출석 데이터 확정", use_container_width=True):
            # 전송할 데이터 리스트 생성
            new_records = []
            for name, info in st.session_state.attendance_data.items():
                new_records.append({
                    "년도": selected_year,
                    "날짜": selected_date.strftime("%Y-%m-%d"),
                    "이름": name,
                    "목양반": selected_group,
                    "출석여부": info["출석여부"],
                    "불참사유": info["불참사유"]
                })
            
            # 구글 시트 "출석체크" 탭에 추가
            try:
                # 기존 데이터 읽기
                existing_data = conn.read(worksheet="출석체크")
                updated_df = pd.concat([existing_data, pd.DataFrame(new_records)], ignore_index=True)
                # 업데이트 실행
                conn.update(worksheet="출석체크", data=updated_df)
                st.success("🎉 성공적으로 기록되었습니다!")
                # 세션 초기화
                del st.session_state.attendance_data
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

    with col_btn2:
        if st.button("❌ 입력 취소 (초기화)", use_container_width=True):
            if "attendance_data" in st.session_state:
                del st.session_state.attendance_data
            st.rerun()

else:
    st.info("선택한 조건에 맞는 구성원이 없습니다.")
