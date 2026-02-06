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

# 필터 영역
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

# 명단 출력 및 기록 로직
if st.session_state.search_clicked:
    group_members = df_members[
        (df_members["년도"] == str(selected_year)) & 
        (df_members["목양반"] == str(selected_group))
    ].copy()

    if not group_members.empty:
        # 정렬 로직 (출석중 -> 장기 미결석 -> 전출)
        status_order = {"출석중": 0, "장기 미결석": 1, "전출": 2}
        group_members['sort_priority'] = group_members['상태'].apply(lambda x: status_order.get(x, 3))
        group_members = group_members.sort_values('sort_priority').drop('sort_priority', axis=1)

        st.subheader(f"📋 {selected_group} 목양반 명단")
        
        attendance_results = {}

        for index, row in group_members.iterrows():
            name = row["이름"]
            duty = row["직분"]
            current_status = row["상태"]
            
            # 레이아웃: 이름 | 상태 드롭다운
            name_col, status_col = st.columns([2, 1])
            with name_col:
                st.write(f"**{name}** {f'({duty})' if duty else ''}")
            with status_col:
                s_list = ["출석중", "장기 미결석", "전출"]
                d_idx = s_list.index(current_status) if current_status in s_list else 0
                new_s = st.selectbox("상태", s_list, index=d_idx, key=f"st_{name}_{index}", label_visibility="collapsed")
            
            # 출석 라디오 | 불참 사유
            att_col, re_col = st.columns([1, 1])
            with att_col:
                att_s = st.radio(f"출_{name}", ["출석", "불참"], key=f"at_{name}_{index}", horizontal=True, label_visibility="collapsed")
            
            with re_col:
                re_val = "-"
                if att_s == "불참":
                    re_val = st.selectbox("사유", ["근무", "건강", "타교회", "미확인"], key=f"re_{name}_{index}", label_visibility="collapsed")
            
            attendance_results[name] = {"출석": att_s, "사유": re_val, "변경상태": new_s}
            st.write("---")

        if st.button("✅ 안식일 출석 최종 확정", use_container_width=True, type="primary"):
            with st.status("기록 중...", expanded=True) as status:
                try:
                    # 1. 출석체크 기록 (중복 방지 적용)
                    st.write("출석 데이터 병합 및 중복 확인 중...")
                    existing_att = conn.read(worksheet="출석체크", ttl=0)
                    
                    new_records = []
                    formatted_date = selected_date.strftime("%Y-%m-%d")
                    for name, res in attendance_results.items():
                        new_records.append({
                            "년도": selected_year, "날짜": formatted_date,
                            "이름": name, "목양반": selected_group,
                            "출석여부": res["출석"], "불참사유": res["사유"]
                        })
                    
                    # 기존 데이터 + 새 데이터 합치기
                    new_df = pd.DataFrame(new_records)
                    updated_att = pd.concat([existing_att, new_df], ignore_index=True)
                    
                    # 핵심: [날짜, 이름]이 겹치면 마지막에 들어온(keep='last') 데이터만 남기고 중복 제거
                    updated_att = updated_att.drop_duplicates(subset=['날짜', '이름'], keep='last')
                    
                    st.write("구글 시트에 최종 기록 중...")
                    conn.update(worksheet="출석체크", data=updated_att)

                    # 2. 구성원정보 업데이트
                    for name, res in attendance_results.items():
                        df_members.loc[(df_members["이름"] == name) & (df_members["목양반"] == selected_group), "상태"] = res["변경상태"]
                    conn.update(worksheet="구성원정보", data=df_members)

                    status.update(label="✅ 저장 완료! 행복한 안식일 되세요.", state="complete", expanded=False)
                    st.balloons()
                    st.success("데이터가 안전하게 저장되었습니다.")
                except Exception as e:
                    st.error(f"저장 중 오류 발생: {e}")
    else:
        st.warning("등록된 명단이 없습니다.")
