import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="출석 체크 - 사릉중앙교회", layout="centered")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 불러오기 및 전처리 (캐시 설정으로 속도 향상)
@st.cache_data(ttl=60)
def get_member_data():
    # '구성원정보' 탭 읽기
    df = conn.read(worksheet="구성원정보")
    
    # 데이터 전처리: 소수점 제거 및 공백 제거
    # 숫자로 들어온 경우를 대비해 문자열로 변환 후 .0 제거
    for col in ["년도", "목양반", "이름", "상태"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(".0", "", regex=False).str.strip()
    return df

try:
    df_members = get_member_data()
except Exception as e:
    st.error(f"시트 데이터를 불러오는데 실패했습니다: {e}")
    st.stop()

st.title("⛪ 사릉중앙교회 주일 출석")

# --- 상단 필터 영역 ---
with st.container():
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 년도 선택
        years = sorted(df_members["년도"].unique().tolist(), reverse=True)
        selected_year = st.selectbox("📅 년도 선택", years)
        
    with col2:
        # 선택한 년도에 맞는 목양반 목록
        groups = sorted(df_members[df_members["년도"] == selected_year]["목양반"].unique().tolist())
        selected_group = st.selectbox("📌 목양반 선택", groups)
        
    with col3:
        # 토요일만 선택 가능하도록 설정
        today = datetime.now()
        # 이번 주 토요일 계산
        default_date = today + timedelta(days=(5 - today.weekday()))
        selected_date = st.date_input("🗓️ 날짜 선택 (토)", value=default_date)
        
        if selected_date.weekday() != 5:
            st.warning("⚠️ 선택하신 날짜는 토요일이 아닙니다.")

st.divider()

# --- 명단 필터링 ---
# 필터링 조건: 년도, 목양반이 일치하고 상태가 '출석중'인 사람
filtered_members = df_members[
    (df_members["년도"] == selected_year) & 
    (df_members["목양반"] == selected_group) &
    (df_members["상태"] == "출석중")
]

# --- 입력 폼 영역 ---
if not filtered_members.empty:
    st.subheader(f"📋 {selected_group} 출석부")
    st.caption("출석/불참을 선택한 후 하단의 [확정] 버튼을 눌러주세요.")

    # 각 사용자의 선택값을 임시 저장할 딕셔너리
    attendance_results = {}

    for index, row in filtered_members.iterrows():
        name = row["이름"]
        duty = row.get("직분", "성도")
        
        with st.expander(f"👤 {name} ({duty})", expanded=True):
            c1, c2 = st.columns([1, 1])
            
            with c1:
                # 출석/불참 선택
                status = st.radio(
                    f"상태_{name}", ["출석", "불참"], 
                    key=f"radio_{name}_{index}", 
                    horizontal=True, label_visibility="collapsed"
                )
            
            with c2:
                # 불참일 때만 사유 드롭다운 활성화
                reason = "-"
                if status == "불참":
                    reason = st.selectbox(
                        f"사유_{name}", ["근무", "건강 문제", "타교회 출석", "미확인"],
                        key=f"reason_{name}_{index}", label_visibility="collapsed"
                    )
            
            # 현재 행의 결과 저장
            attendance_results[name] = {
                "출석여부": status,
                "불참사유": reason
            }

    st.write("")
    
    # --- 확정 / 취소 버튼 ---
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        if st.button("✅ 출석 데이터 확정", use_container_width=True, type="primary"):
            # 최종 전송 데이터 구성
            new_data_list = []
            for name, res in attendance_results.items():
                new_data_list.append({
                    "년도": selected_year,
                    "날짜": selected_date.strftime("%Y-%m-%d"),
                    "이름": name,
                    "목양반": selected_group,
                    "출석여부": res["출석여부"],
                    "불참사유": res["불참사유"]
                })
            
            try:
                # 기존 '출석체크' 탭 데이터 읽기
                existing_att = conn.read(worksheet="출석체크")
                # 새 데이터 합치기
                updated_df = pd.concat([existing_att, pd.DataFrame(new_data_list)], ignore_index=True)
                # 시트 업데이트
                conn.update(worksheet="출석체크", data=updated_df)
                
                st.balloons()
                st.success(f"축하합니다! {selected_group} {len(new_data_list)}명의 출석 기록이 완료되었습니다.")
                # 입력 후 새로고침 (선택 사항)
                # st.rerun()
                
            except Exception as e:
                st.error(f"기록 중 오류가 발생했습니다: {e}")

    with btn_col2:
        if st.button("❌ 전체 초기화", use_container_width=True):
            st.rerun()

else:
    st.info(f"선택하신 조건({selected_year}년, {selected_group})에 해당하는 '출석중' 구성원이 없습니다. 구글 시트의 '상태' 컬럼을 확인해 주세요.")
    
    # 디버깅용 (문제가 계속될 때 주석 해제하여 사용)
    # st.write("현재 시트 데이터 샘플:", df_members[["년도", "목양반", "상태"]].head())
