import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="출석 통계 - 사릉중앙교회", layout="wide")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 전처리 함수
def clean_df(df):
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(".0", "", regex=False).str.strip()
    return df

# 3. 데이터 불러오기
@st.cache_data(ttl=10) # 통계를 위해 캐시 시간을 짧게 설정
def load_all_data():
    df_members = conn.read(worksheet="구성원정보", ttl=0)
    df_att = conn.read(worksheet="출석체크", ttl=0)
    return clean_df(df_members), clean_df(df_att)

df_members, df_att = load_all_data()

st.title("📊 안식일 출석 현황 통계")

# --- 상단 필터 영역 ---
with st.sidebar:
    st.header("🔍 조회 설정")
    years = sorted(df_members["년도"].unique().tolist(), reverse=True)
    selected_year = st.selectbox("📅 년도 선택", years)
    
    # 해당 년도에 기록된 날짜들 추출
    available_dates = sorted(df_att[df_att["년도"] == selected_year]["날짜"].unique().tolist(), reverse=True)
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates if available_dates else ["기록 없음"])
    
    search_btn = st.button("📊 통계 업데이트", use_container_width=True, type="primary")

# --- 통계 로직 ---
if selected_date != "기록 없음":
    # 1. 특정 날짜의 출석 데이터 필터링
    day_att = df_att[(df_att["년도"] == selected_year) & (df_att["날짜"] == selected_date)]
    # 2. 해당 년도의 전체 목양반 리스트 추출 (구성원정보 기준)
    all_groups = sorted(df_members[df_members["년도"] == selected_year]["목양반"].unique().tolist())

    # --- 상단 요약 지표 ---
    t1, t2, t3 = st.columns(3)
    total_present = len(day_att[day_att["출석여부"] == "출석"])
    total_absent = len(day_att[day_att["출석여부"] == "불참"])
    
    t1.metric("오늘 총 출석", f"{total_present}명")
    t2.metric("오늘 총 불참", f"{total_absent}명")
    t3.metric("보고 완료 목장", f"{len(day_att['목양반'].unique())} / {len(all_groups)}")

    st.divider()

    # --- 목양반별 상세 현황 ---
    st.subheader(f"📍 {selected_date} 목양반별 세부 현황")
    
    # 보기 좋게 2열로 배치
    cols = st.columns(2)
    
    for i, group in enumerate(all_groups):
        # 현재 목양반의 출석 기록이 있는지 확인
        group_att_data = day_att[day_att["목양반"] == group]
        is_submitted = not group_att_data.empty # 데이터가 있으면 제출 완료
        
        with cols[i % 2]:
            with st.expander(f"{'✅' if is_submitted else '⚠️'} {group}", expanded=True):
                if is_submitted:
                    # 불참자 명단 추출
                    absent_members = group_att_data[group_att_data["출석여부"] == "불참"]
                    
                    c1, c2 = st.columns([1, 2])
                    c1.write("**체크 여부**")
                    c1.success("완료")
                    
                    c2.write("**불참자 및 사유**")
                    if not absent_members.empty:
                        for _, row in absent_members.iterrows():
                            c2.warning(f"• {row['이름']} ({row['불참사유']})")
                    else:
                        c2.info("불참자 없음")
                else:
                    st.error("보내진 출석 데이터가 없습니다. (미완료)")
else:
    st.info("왼쪽 사이드바에서 날짜를 선택한 후 통계를 확인해 주세요.")
