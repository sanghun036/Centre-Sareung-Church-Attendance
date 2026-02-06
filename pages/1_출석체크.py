import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="안식일 출석 체크 - 사릉중앙교회", layout="centered")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # 구성원정보 시트 읽기
    df = conn.read(worksheet="구성원정보", ttl=0) 
    # 데이터 정제: .0 제거 및 공백 제거, NaN 처리
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(".0", "", regex=False).str.strip()
        df[col] = df[col].replace("nan", "")
    return df

try:
    df_members = load_data()
except Exception as e:
    st.error(f"❌ 데이터를 불러오지 못했습니다. 시트 이름을 확인하세요: {e}")
    st.stop()

st.title("⛪ 사릉중앙교회 안식일 출석")

# --- 필터 영역 ---
if 'search_clicked' not in st.session_state:
    st.session_state.search_clicked = False

col1, col2, col3 = st.columns(3)

with col1:
    years = ["--"] + sorted(df_members["년도"].unique().tolist(), reverse=True)
    selected_year = st.selectbox("📅 년도 선택", years)

with col2:
    if selected_year != "--":
        # DB의 목양반 값 앞에 숫자를 붙여 출력
        raw_groups = sorted(df_members[df_members["년도"] == selected_year]["목양반"].unique().tolist())
        display_groups = {f"{g} 목양반": g for g in raw_groups}
        selected_display_group = st.selectbox("📌 목양반 선택", ["--"] + list(display_groups.keys()))
        selected_group = display_groups.get(selected_display_group, "--")
    else:
        st.selectbox("📌 목양반 선택", ["--"], disabled=True)
        selected_group = "--"

with col3:
    # 가장 가까운 토요일(안식일) 계산
    today = datetime.now()
    days_until_saturday = (5 - today.weekday()) % 7
    default_saturday = today + timedelta(days=days_until_saturday)
    selected_date = st.date_input("🗓️ 날짜 선택 (토)", value=default_saturday)

# 확인 버튼
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
    # 72번 라인 에러 수정: "년to" -> "년도"
    group_members = df_members[
        (df_members["년도"] == str(selected_year)) & 
        (df_members["목양반"] == str(selected_group))
    ].copy()

    if not group_members.empty:
        # 상태 정렬 순서 정의 (출석중 -> 장기 미결석 -> 전출)
        status_order = {"출석중": 0, "장기 미결석": 1, "전출": 2}
        group_members['sort_priority'] = group_members['상태'].map(lambda x: status_order.get(x, 3))
        group_members = group_members.sort_values('sort_priority').drop('sort_priority', axis=1)

        st.subheader(f"📋 {selected_group} 목양반 명단")

        attendance_results = {}

        with st.form("attendance_form"):
            for index, row in group_members.iterrows():
                name = row["이름"]
                duty = row["직분"]
                current_status = row["상태"]
                
                # 명단 UI 구성
                st.write(f"**{name}** {f'({duty})' if duty else ''}")
                
                c1, c2, c3 = st.columns([2, 1.5, 1.5])
                
                with c1:
                    att_status = st.radio(f"출석_{name}", ["출석", "불참"], key=f"att_{name}_{index}", horizontal=True, label_visibility="collapsed")
                
                with c2:
                    # 상태 변경 드롭다운
                    status_list = ["출석중", "장기 미결석", "전출"]
                    default_idx = status_list.index(current_status) if current_status in status_list else 0
                    new_status = st.selectbox(f"상태_{name}", status_list, index=default_idx, key=f"stat_{name}_{index}")
                
                with c3:
                    # 불참 사유
                    reason = "-"
                    if att_status == "불참":
                        reason = st.selectbox(f"사유_{name}", ["근무", "건강", "타교회", "미확인"], key=f"re_{name}_{index}")
                
                attendance_results[name] = {"출석": att_status, "사유": reason, "변경상태": new_status}
                st.write("---")

            submitted = st.form_submit_button("✅ 안식일 출석 확정", use_container_width=True)

        if submitted:
            with st.status("안식일 기록을 저장하고 있습니다...", expanded=True) as status:
                try:
                    # 1. 출석체크 기록 저장
                    st.write("출석 데이터 기록 중...")
                    existing_att = conn.read(worksheet="출석체크", ttl=0)
                    new_records = []
                    for name, res in attendance_results.items():
                        new_records.append({
                            "년도": selected_year,
                            "날짜": selected_date.strftime("%Y-%m-%d"),
                            "이름": name,
                            "목양반": selected_group,
                            "출석여부": res["출석"],
                            "불참사유": res["사유"]
                        })
                    updated_att_df = pd.concat([existing_att, pd.DataFrame(new_records)], ignore_index=True)
                    conn.update(worksheet="출석체크", data=updated_att_df)

                    # 2. 구성원정보 상태 업데이트
                    st.write("구성원 상태 정보 업데이트 중...")
                    # 전체 멤버 데이터에서 현재 목양반 멤버들의 상태를 일괄 업데이트
                    for name, res in attendance_results.items():
                        df_members.loc[(df_members["이름"] == name) & (df_members["목양반"] == selected_group), "상태"] = res["변경상태"]
                    
                    conn.update(worksheet="구성원정보", data=df_members)

                    status.update(label="✅ 저장 완료! 행복한 안식일 되세요.", state="complete", expanded=False)
                    st.balloons()
                    st.success("출석부 기록 및 구성원 상태 업데이트가 완료되었습니다.")
                except Exception as e:
                    st.error(f"저장 실패: {e}")
    else:
        st.warning("선택하신 목양반에 등록된 명단이 없습니다.")
