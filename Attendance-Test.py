import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="출석 체크 - 사릉중앙교회", layout="centered")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 불러오기 (캐시를 0으로 설정하여 즉시 반영)
# 데이터가 반영 안 될 때는 ttl=0으로 설정하세요.
def load_data():
    # 탭 이름 '구성원정보'가 시트와 정확히 일치해야 합니다.
    df = conn.read(worksheet="구성원정보", ttl=0) 
    
    # 데이터 정제 (공백 제거 및 문자열 변환)
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(".0", "", regex=False).str.strip()
    return df

try:
    df_members = load_data()
except Exception as e:
    st.error(f"❌ 구글 시트를 읽어오지 못했습니다. 설정(Secrets)을 확인하세요: {e}")
    st.stop()

st.title("⛪ 사릉중앙교회 주일 출석")

# --- 필터 영역 ---
col1, col2, col3 = st.columns(3)

with col1:
    years = sorted(df_members["년도"].unique().tolist(), reverse=True)
    selected_year = st.selectbox("📅 년도 선택", years)

with col2:
    # 선택한 년도에 해당하는 데이터만 먼저 필터링
    year_filtered = df_members[df_members["년도"] == selected_year]
    groups = sorted(year_filtered["목양반"].unique().tolist())
    selected_group = st.selectbox("📌 목양반 선택", groups)

with col3:
    today = datetime.now()
    default_date = today + timedelta(days=(5 - today.weekday()))
    selected_date = st.date_input("🗓️ 날짜 선택", value=default_date)

st.divider()

# --- 필터링 로직 (매우 중요) ---
# '상태' 컬럼이 앱에서 검색을 막고 있을 수 있으므로, 
# 우선 년도와 목양반으로만 필터링한 결과를 먼저 봅니다.
filtered_members = df_members[
    (df_members["년도"] == str(selected_year)) & 
    (df_members["목양반"] == str(selected_group))
]

# --- 디버깅 모드 (문제가 해결될 때까지 켜두세요) ---
with st.expander("🔍 데이터 연결 상태 확인 (디버깅)"):
    st.write(f"현재 선택된 값: 년도={selected_year}, 목양반={selected_group}")
    st.write("시트에서 가져온 전체 데이터 건수:", len(df_members))
    st.write("필터링된 결과 건수:", len(filtered_members))
    st.dataframe(df_members.head(10)) # 실제 시트 데이터 상단 10줄 노출

# --- 명단 출력 ---
if not filtered_members.empty:
    st.subheader(f"📋 {selected_group} 명단")
    
    attendance_results = {}

    for index, row in filtered_members.iterrows():
        # '이름' 컬럼이 실제 시트 헤더와 일치하는지 확인하세요
        name = row["이름"]
        st.write(f"**{name}** ({row.get('직분', '성도')})")
        
        c1, c2 = st.columns(2)
        with c1:
            status = st.radio(f"상태_{name}", ["출석", "불참"], key=f"r_{index}", horizontal=True)
        with c2:
            reason = "-"
            if status == "불참":
                reason = st.selectbox(f"사유_{name}", ["근무", "건강 문제", "타교회 출석", "미확인"], key=f"s_{index}")
        
        attendance_results[name] = {"출석여부": status, "불참사유": reason}
        st.write("---")

    # --- 확정 / 취소 버튼 영역 ---
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        if st.button("✅ 출석 데이터 확정", use_container_width=True, type="primary"):
            # 1. 전송할 데이터 준비
            new_records = []
            for name, res in attendance_results.items():
                new_records.append({
                    "년도": selected_year,
                    "날짜": selected_date.strftime("%Y-%m-%d"),
                    "이름": name,
                    "목양반": selected_group,
                    "출석여부": res["출석여부"],
                    "불참사유": res["불참사유"]
                })
            
            # 2. 전송 중 상태 표시 (st.status 사용)
            with st.status("⛪ 구글 시트에 기록 중...", expanded=True) as status:
                try:
                    st.write("기존 기록을 불러오는 중...")
                    # 최신 데이터를 가져오기 위해 ttl=0 설정
                    existing_data = conn.read(worksheet="출석체크", ttl=0)
                    
                    st.write("새로운 데이터를 추가 중...")
                    # 기존 데이터 아래에 새 데이터 붙이기
                    updated_df = pd.concat([existing_data, pd.DataFrame(new_records)], ignore_index=True)
                    
                    st.write("최종 저장 중 (잠시만 기다려 주세요)...")
                    # 합쳐진 데이터를 시트에 업데이트
                    conn.update(worksheet="출석체크", data=updated_df)
                    
                    status.update(label="✅ 기록 완료!", state="complete", expanded=False)
                    st.balloons()
                    st.success(f"{selected_group} {len(new_records)}명의 기록이 성공적으로 저장되었습니다.")
                    
                    # 기록 후 세션 초기화가 필요하면 여기에 추가
                    # st.rerun()

                except Exception as e:
                    status.update(label="❌ 전송 실패", state="error")
                    st.error(f"오류 내용: {e}")

    with btn_col2:
        if st.button("❌ 전체 초기화", use_container_width=True):
            st.rerun()


else:
    st.warning("⚠️ 해당 조건에 맞는 구성원이 없습니다.")
    st.info("시트의 '년도'와 '목양반' 컬럼 값이 드롭다운에서 선택한 값과 정확히 일치하는지 확인해 주세요.")
