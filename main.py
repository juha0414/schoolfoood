
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from itertools import combinations
from collections import Counter

# --------------------------------------------------
# 1. 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

DATA_URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"

st.title("🍱 급식 규칙 찾기")

st.write(
    "송탄고등학교 중식 데이터를 분석하여 "
    "함께 자주 등장하는 메뉴와 메뉴 사이의 연관 규칙을 찾아봅니다."
)


# --------------------------------------------------
# 2. 데이터 불러오기
# --------------------------------------------------

@st.cache_data
def load_data():

    df = pd.read_csv(
        DATA_URL,
        encoding="utf-8",
        dtype=str,
        keep_default_na=False
    )

    required_columns = ["날짜", "식사", "메뉴"]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"CSV에 '{col}' 열이 없습니다.")

    df = df[required_columns].copy()

    # 중식만 분석
    df = df[df["식사"].str.strip() == "중식"]

    return df


# --------------------------------------------------
# 3. 메뉴 이름 정리
# --------------------------------------------------

def clean_menu(menu):

    # 일반 괄호와 전각 괄호 안의 내용 제거
    while True:

        new_menu = re.sub(
            r"\([^()]*\)|（[^（）]*）",
            "",
            menu
        )

        if new_menu == menu:
            break

        menu = new_menu

    return menu.strip()


# --------------------------------------------------
# 4. 장바구니 만들기
# --------------------------------------------------

def make_transactions(df):

    transactions = []

    for menu_text in df["메뉴"]:

        menus = menu_text.split("|")

        cleaned_menus = []

        for menu in menus:

            name = clean_menu(menu)

            if name:
                cleaned_menus.append(name)

        # 하루 식단 안의 중복 메뉴 제거
        transactions.append(set(cleaned_menus))

    return transactions


# --------------------------------------------------
# 5. 연관 규칙 분석
# --------------------------------------------------

def analyze_rules(transactions):

    total_days = len(transactions)

    menu_counts = Counter()
    pair_counts = Counter()

    # 메뉴별 등장 횟수
    for basket in transactions:

        menu_counts.update(basket)

        # 같은 날 함께 나온 메뉴 쌍
        for a, b in combinations(sorted(basket), 2):

            pair_counts[(a, b)] += 1

    rules = []

    for (a, b), together_count in pair_counts.items():

        support = together_count / total_days

        # A → B
        confidence_ab = together_count / menu_counts[a]

        lift_ab = confidence_ab / (
            menu_counts[b] / total_days
        )

        rules.append({
            "조건": a,
            "결과": b,
            "동시": together_count,
            "지지도": support,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B → A
        confidence_ba = together_count / menu_counts[b]

        lift_ba = confidence_ba / (
            menu_counts[a] / total_days
        )

        rules.append({
            "조건": b,
            "결과": a,
            "동시": together_count,
            "지지도": support,
            "신뢰도": confidence_ba,
            "향상도": lift_ba
        })

    rules_df = pd.DataFrame(rules)

    return menu_counts, pair_counts, rules_df


# --------------------------------------------------
# 6. 데이터 분석 실행
# --------------------------------------------------

try:

    df = load_data()

    if df.empty:
        st.error("분석할 중식 데이터가 없습니다.")
        st.stop()

    transactions = make_transactions(df)

    menu_counts, pair_counts, rules_df = analyze_rules(
        transactions
    )

except Exception as e:

    st.error(
        f"데이터를 불러오거나 분석하는 중 오류가 발생했습니다: {e}"
    )

    st.stop()


# --------------------------------------------------
# 7. 전체 데이터 요약
# --------------------------------------------------

total_days = len(transactions)
total_menus = len(menu_counts)
total_pairs = len(pair_counts)

st.subheader("📊 전체 데이터 요약")

col1, col2, col3 = st.columns(3)

col1.metric("급식 일수", f"{total_days:,}일")
col2.metric("메뉴 종류 수", f"{total_menus:,}개")
col3.metric("함께 나온 메뉴 쌍", f"{total_pairs:,}쌍")

st.divider()


# --------------------------------------------------
# 8. 연관 규칙 검색 조건
# --------------------------------------------------

st.subheader("🔎 연관 규칙 검색")

col1, col2 = st.columns(2)

with col1:

    selected_menu = st.selectbox(
        "좁혀 보기 - 메뉴 선택",
        ["전체 메뉴"] + sorted(menu_counts.keys())
    )

with col2:

    sort_option = st.selectbox(
        "정렬 기준",
        ["향상도순", "신뢰도순", "동시순"]
    )


# --------------------------------------------------
# 9. 최소 동시 일수 슬라이더
# --------------------------------------------------

min_together = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    help="선택한 일수보다 적게 함께 나온 규칙은 제외합니다."
)


# --------------------------------------------------
# 10. 연관 규칙 필터링
# --------------------------------------------------

filtered_df = rules_df.copy()

# 메뉴 선택 필터
if selected_menu != "전체 메뉴":

    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu) |
        (filtered_df["결과"] == selected_menu)
    ]

# 최소 동시 일수 필터
filtered_df = filtered_df[
    filtered_df["동시"] >= min_together
]

# 정렬
if sort_option == "향상도순":

    filtered_df = filtered_df.sort_values(
        ["향상도", "신뢰도", "동시"],
        ascending=[False, False, False]
    )

elif sort_option == "신뢰도순":

    filtered_df = filtered_df.sort_values(
        ["신뢰도", "향상도", "동시"],
        ascending=[False, False, False]
    )

elif sort_option == "동시순":

    filtered_df = filtered_df.sort_values(
        ["동시", "향상도", "신뢰도"],
        ascending=[False, False, False]
    )


# --------------------------------------------------
# 11. 남은 규칙 개수
# --------------------------------------------------

st.write(
    f"현재 조건에서 표에 남은 규칙: **{len(filtered_df):,}개**"
)


# --------------------------------------------------
# 12. 연관 규칙 표
# --------------------------------------------------

st.subheader("📋 연관 규칙 분석 결과")

if filtered_df.empty:

    st.info(
        "선택한 조건에 해당하는 연관 규칙이 없습니다."
    )

else:

    display_df = filtered_df.copy()

    display_df["지지도"] = display_df["지지도"].map(
        lambda x: f"{x:.3%}"
    )

    display_df["신뢰도"] = display_df["신뢰도"].map(
        lambda x: f"{x:.3%}"
    )

    display_df["향상도"] = display_df["향상도"].map(
        lambda x: f"{x:.3f}"
    )

    display_df = display_df[
        ["조건", "결과", "동시", "지지도", "신뢰도", "향상도"]
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


# --------------------------------------------------
# 13. 향상도 TOP 10 그래프
# --------------------------------------------------

st.divider()

st.subheader("📈 향상도 TOP 10")

st.write(
    "향상도가 높은 메뉴 조합일수록 "
    "두 메뉴가 독립적으로 등장할 때보다 "
    "함께 등장하는 경향이 강합니다."
)

if filtered_df.empty:

    st.info("그래프에 표시할 데이터가 없습니다.")

else:

    chart_df = filtered_df.sort_values(
        ["향상도", "신뢰도", "동시"],
        ascending=[False, False, False]
    ).head(10).copy()

    chart_df["규칙"] = (
        chart_df["조건"] + " → " + chart_df["결과"]
    )

    chart_df = chart_df.sort_values(
        "향상도",
        ascending=True
    )

    fig = px.bar(
        chart_df,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        hover_data={
            "동시": True,
            "신뢰도": ":.3%",
            "지지도": ":.3%",
            "향상도": ":.3f",
            "규칙": False
        },
        labels={
            "향상도": "향상도 (Lift)",
            "규칙": "연관 규칙"
        },
        title="연관 규칙 향상도 상위 10개"
    )

    fig.update_traces(
        texttemplate="%{x:.2f}",
        textposition="outside"
    )

    fig.update_layout(
        height=max(400, len(chart_df) * 45),
        xaxis_title="향상도",
        yaxis_title="메뉴 규칙",
        yaxis=dict(automargin=True),
        margin=dict(l=20, r=70, t=70, b=40)
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# --------------------------------------------------
# 14. 함께 나온 적 없는 짝
# --------------------------------------------------

st.divider()

st.subheader("🚫 함께 나온 적 없는 짝")

st.write(
    "선택한 메뉴와 한 번도 같은 날 나오지 않았지만, "
    "다른 날에는 10일 이상 등장한 메뉴를 찾아봅니다."
)

# 위의 좁혀 보기와 독립적인 메뉴 선택
selected_menu_for_absence = st.selectbox(
    "함께 나온 적 없는 짝을 찾을 메뉴",
    sorted(menu_counts.keys()),
    key="absence_menu_select"
)

# 선택한 메뉴가 나온 날짜 수
selected_menu_days = menu_counts[
    selected_menu_for_absence
]

st.metric(
    f"'{selected_menu_for_absence}'이(가) 나온 날",
    f"{selected_menu_days:,}일"
)

# 선택한 메뉴가 나온 날들의 메뉴 모음
selected_days = [
    basket
    for basket in transactions
    if selected_menu_for_absence in basket
]

# 선택한 메뉴와 함께 나온 적 있는 메뉴 집합
menus_that_appeared_together = set()

for basket in selected_days:

    menus_that_appeared_together.update(basket)

# 선택 메뉴 자체는 제외
menus_that_appeared_together.discard(
    selected_menu_for_absence
)

# 조건에 맞는 메뉴 찾기
absence_results = []

for menu, count in menu_counts.items():

    # 선택한 메뉴 자체 제외
    if menu == selected_menu_for_absence:
        continue

    # 혼자서는 10일 이상 등장
    if count < 10:
        continue

    # 선택한 메뉴와 한 번도 함께 나온 적 없음
    if menu not in menus_that_appeared_together:

        absence_results.append({
            "메뉴": menu,
            "나온 날 수": count
        })

# 나온 날이 많은 순으로 정렬
absence_df = pd.DataFrame(absence_results)

if not absence_df.empty:

    absence_df = absence_df.sort_values(
        ["나온 날 수", "메뉴"],
        ascending=[False, True]
    ).reset_index(drop=True)

    st.write(
        f"조건에 맞는 메뉴: **{len(absence_df):,}개**"
    )

    st.dataframe(
        absence_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "조건에 맞는 메뉴가 없습니다. "
        "다른 메뉴를 선택해 보세요."
    )


# --------------------------------------------------
# 15. 연관 규칙 지표 설명
# --------------------------------------------------

st.divider()

st.subheader("📖 연관 규칙 지표 알아보기")

st.markdown("""
| 지표 | 의미 |
|---|---|
| 조건 | 기준으로 삼는 메뉴 |
| 결과 | 조건 메뉴와 함께 등장하는 메뉴 |
| 동시 | 두 메뉴가 같은 날 나온 횟수 |
| 지지도 | 전체 급식 중 두 메뉴가 함께 나온 비율 |
| 신뢰도 | 조건 메뉴가 나왔을 때 결과 메뉴도 나온 비율 |
| 향상도 | 두 메뉴의 동시 출현이 독립적인 경우보다 얼마나 높은지 |

### 향상도 해석

- 향상도 > 1 : 두 메뉴가 독립적일 때보다 더 자주 함께 나옴
- 향상도 = 1 : 두 메뉴가 서로 독립적인 수준
- 향상도 < 1 : 두 메뉴가 독립적일 때보다 덜 자주 나옴

### 함께 나온 적 없는 짝 해석

- 선택한 메뉴가 나온 날을 기준으로 비교합니다.
- 한 번이라도 같은 날 나온 메뉴는 제외합니다.
- 전체 급식에서 혼자 10일 이상 나온 메뉴만 남깁니다.
- 나온 날이 많은 메뉴부터 표시합니다.

**주의:** 연관 규칙은 메뉴 사이의 통계적 관계를 보여 주며,
한 메뉴가 다른 메뉴의 원인이라는 뜻은 아닙니다.
""")

st.caption(
    "데이터 출처: 송탄고등학교 중식 급식 CSV"
)
