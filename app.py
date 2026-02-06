import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="사릉중앙교회 스마트 출석부",
    page_icon="⛪",
    layout="centered"
)

# 커스텀 CSS로 버튼 디자인 강화
st.markdown("""
    <style>
    div.stButton > button:first-child {
        height: 3em;
        font-size: 20px;
        font-weight: bold;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⛪ 사릉중앙교회 스마트 출석부")
st.write("사릉중앙교회 공동체의 건강한 출석 관리를 위한 시스템입니다.")

st.divider()

# 메인 메뉴 구성
st.subheader("원하시는 작업을 선택해 주세요")

col1, col2 = st.columns(2)

with col1:
    st.info("### 📅 출석 체크")
    st.write("각 목양반 선생님들께서 성도님들의 출석 현황을 입력하는 화면입니다.")
    if st.button("출석 입력하기", use_container_width=True, type="primary"):
        st.switch_page("pages/1_출석체크.py")

with col2:
    st.success("### 📊 출석 통계")
    st.write("전체 출석 현황 및 목양반별 보고 여부를 확인하는 관리자 화면입니다.")
    if st.button("통계 확인하기", use_container_width=True):
        st.switch_page("pages/2_출석통계.py")

st.divider()

# 하단 안내 문구
with st.expander("ℹ️ 이용 안내"):
    st.write("""
    1. **선생님**: '출석 입력하기' 버튼을 눌러 해당 목양반 성도님들의 출석 여부를 체크해 주세요.
    2. **관리자**: '통계 확인하기' 버튼을 통해 실시간 출석 현황을 모니터링할 수 있습니다.
    3. 데이터는 구글 시트와 실시간으로 연동됩니다.
    """)

st.caption("© 2026 사릉중앙교회. All rights reserved.")
