import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="안식일 출석 체크 - 사릉중앙교회", layout="centered")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(worksheet="구성원정보", ttl=0) 
    # 데이터 정제: .0 제거 및 공백 제거, NaN 처리
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(".0", "", regex=False).str.strip()
        df[col] = df[col].replace("nan", "") # 7번: nan 표기 제거
    return df

try:
    df_members = load_data()
except Exception as e:
    st.error(f"❌ 데이터를 불러오지 못했습니다: {e}")
    st.stop()

st.title("⛪ 사릉중앙교회 안식일 출석") # 3번: 안식일로 명칭 변경

# --- 1, 2, 4번: 필터 영역 및 초기값 설정 ---
if 'search_clicked' not in st.session_state:
    st.session_state.search_clicked = False

col1, col2, col3 = st.columns(3)

with col1:
    years = ["--"] + sorted(df_members["년도"].unique().tolist(), reverse=True)
    selected_year = st.selectbox("📅 년도 선택", years)

with col2:
    if selected_year != "--":
        # 4번: 화면에는 "1 목양반" 형태로 표시
        raw_groups = sorted(df_members[df_members["년도"] == selected_year]["목양반"].unique().tolist())
        display_groups = {f"{g} 목양반": g for g in raw_groups}
        selected_display_group = st.selectbox("📌 목양반 선택", ["--"] + list(display_groups.keys()))
        selected_group = display_groups.get(selected_display_group, "--")
    else:
        st.selectbox("📌 목양반 선택", ["--"], disabled=True)
        selected_group = "--"

with col3:
    # 2번: 가장 가까운 토요일 계산
    today = datetime.now()
    days_until_saturday = (5 - today.weekday()) % 7
    default_saturday = today + timedelta(days=days_until_saturday)
    
    # date_input에서 선택 가능한 날짜를 제한할 수는 없으나 확인 로직 추가
    selected_date = st.date_input("🗓️ 날짜 선택 (토)", value=default_saturday)
    if selected_date.weekday() != 5:
        st.error("⚠️ 토요일만 선택 가능합니다.")

# 1번: 확인 버튼
if st.button("🔍 확인", use_container_width=True):
    if selected_year != "--" and selected_group != "--" and selected_date.weekday() == 5:
        st.session_state.search_clicked = True
    else:
        st.warning("년도와 목양반을 선택해 주세요.")

st.divider()

# --- 5, 8, 9, 10번: 명단 출력 로직 ---
if st.session_state.search_clicked:
    # 데이터 필터링 (선택한 목양반 전체)
    group_members = df_members[
        (df_members["년to"] == str(selected_year)) & 
        (df_members["목양반"] == str(selected_group))
    ].copy()

    # 10번: 정렬 순서 정의 (출석중 -> 장기 미결석 -> 전출)
    status_order = {"출석중": 0, "장기 미결석": 1, "전출": 2}
    group_members['sort_order'] = group_members['상태'].map(lambda x: status_order.get(x, 3))
    group_members = group_members.sort_values('sort_order').drop('sort_order', axis=1)

    st.subheader(f"📋 {selected_group} 목양반 명단") # 5번

    attendance_results = {}
    status_updates = {} # 9번용 상태 변경 저장

    with st.form("attendance_form"):
        for index, row in group_members.iterrows():
            name = row["이름"]
            duty = row["직분"]
            current_status = row["상태"]
            
            # 8번 해결: 불필요한 레이블 제거 및 UI 정리
            st.write(f"**{name}** | {duty}")
            
            c1, c2, c3 = st.columns([2, 1, 1])
            
            with c1:
                # 출석 여부 선택
                att_status = st.radio(f"출석_{name}", ["출석", "불참"], key=f"att_{index}", horizontal=True, label_visibility="collapsed")
            
            with c2:
                # 9번: 이름 오른쪽 상태 드롭다운
                new_status = st.selectbox(f"상태변경_{name}", ["출석중", "장기 미결석", "전출"], 
                                         index=["출석중", "장기 미결석", "전출"].index(current_status) if current_status in ["출석중", "장기 미결석", "전출"] else 0,
                                         key=f"stat_{index}", label_visibility="collapsed")
            
            with c3:
                reason = "-"
                if att_status == "불참":
                    reason = st.selectbox(f"사유_{name}", ["근무", "건강", "타교회", "미확인"], key=f"re_{index}", label_visibility="collapsed")
            
            attendance_results[name] = {"출석": att_status, "사유": reason, "최종상태": new_status}
            st.write("---")

        submitted = st.form_submit_button("✅ 안식일 출석 확정", use_container_width=True)

    if submitted:
        with st.status("데이터를 기록 중입니다...", expanded=True) as status:
            try:
                # A. 출석체크 탭 업데이트
                st.write("1. 출석 기록 생성 중...")
                existing_att = conn.read(worksheet="출석체크", ttl=0)
                new_records = []
                for name, res in attendance_results.items():
                    new_records.append({
                        "년도": selected_year, "날짜": selected_date.strftime("%Y-%m-%d"),
                        "이름": name, "목양반": selected_group,
                        "출석여부": res["출석"], "불참사유": res["사유"]
                    })
                updated_att_df = pd.concat([existing_att, pd.DataFrame(new_records)], ignore_index=True)
                conn.update(worksheet="출석체크", data=updated_att_df)

                # B. 구성원정보 탭 상태 업데이트 (9번 핵심 로직)
                st.write("2. 구성원 상태 변경사항 반영 중...")
                for name, res in attendance_results.items():
                    df_members.loc[(df_members["이름"] == name) & (df_members["목양반"] == selected_group), "상태"] = res["최종상태"]
                
                conn.update(worksheet="구성원정보", data=df_members)

                status.update(label="✅ 모든 데이터가 반영되었습니다!", state="complete", expanded=False)
                st.balloons()
                st.success("출석 기록 완료 및 구성원 정보가 업데이트되었습니다.")
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")
