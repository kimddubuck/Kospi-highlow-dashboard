import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Kospi High-Low Dashboard", layout="wide")

st.title("코스피 신고가/신저가 비율 대시보드")
st.caption("현재는 1차 테스트 버전입니다. 두 번째 차트는 예시 지표입니다. 먼저 화면이 정상적으로 뜨는지 확인하는 단계입니다.")

# -----------------------------
# 데이터 가져오기
# -----------------------------
@st.cache_data(ttl=300)
def get_kospi_daily():
    df = yf.download("^KS11", period="1y", interval="1d", auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    return df

@st.cache_data(ttl=300)
def get_kospi_4h():
    df = yf.download("^KS11", period="60d", interval="60m", auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()

    if df.empty:
        return df

    df.index = pd.to_datetime(df.index)

    # 1시간봉을 4시간봉으로 묶기
    ohlc = (
        df[["Open", "High", "Low", "Close"]]
        .resample("4h")
        .agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last"
        })
        .dropna()
    )
    return ohlc

# -----------------------------
# 차트용 함수
# -----------------------------
def make_price_chart(df, title_text):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            name="코스피",
        )
    )

    fig.update_layout(
        title=title_text,
        xaxis_title="시간",
        yaxis_title="코스피 지수",
        height=420,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig

def make_indicator_series(index_values):
    # 지금은 키움 API 연결 전이므로 "예시 지표"를 만듭니다.
    # 실제 데이터가 아니라 테스트용입니다.
    n = len(index_values)

    if n == 0:
        return pd.Series(dtype=float)

    # 10% ~ 22% 범위를 왔다갔다 하는 예시값 생성
    values = []
    base = [0.12, 0.15, 0.18, 0.11, 0.20, 0.16, 0.14, 0.22, 0.13, 0.17]

    for i in range(n):
        values.append(base[i % len(base)])

    return pd.Series(values, index=index_values)

def make_indicator_chart(index_values, title_text):
    indicator = make_indicator_series(index_values)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=indicator.index,
            y=indicator.values,
            mode="lines",
            name="지표",
        )
    )

    # 기준선 10%, 20%
    fig.add_hline(y=0.10, line_dash="dash", annotation_text="10% 기준")
    fig.add_hline(y=0.20, line_dash="dash", annotation_text="20% 기준")

    fig.update_layout(
        title=title_text,
        xaxis_title="시간",
        yaxis_title="지표 비율",
        height=420,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig

# -----------------------------
# 화면 구성
# -----------------------------
chart_type = st.radio(
    "차트 기준을 선택하세요",
    ["4시간봉", "일봉"],
    horizontal=True
)

if chart_type == "4시간봉":
    kospi_df = get_kospi_4h()
    price_title = "1번 차트 - 코스피 지수 (4시간봉)"
    indicator_title = "2번 차트 - 신고가/신저가 비율 (예시 데이터, 4시간 기준)"
else:
    kospi_df = get_kospi_daily()
    price_title = "1번 차트 - 코스피 지수 (일봉)"
    indicator_title = "2번 차트 - 신고가/신저가 비율 (예시 데이터, 일봉 기준)"

if kospi_df.empty:
    st.error("코스피 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
else:
    latest_close = float(kospi_df["Close"].iloc[-1])

    # 예시 현재값
    sample_high = 18
    sample_low = 102
    sample_ratio = sample_high / (sample_high + sample_low)

    c1, c2, c3 = st.columns(3)
    c1.metric("현재 코스피", f"{latest_close:,.2f}")
    c2.metric("예시 신고가 종목수", f"{sample_high}")
    c3.metric("예시 지표", f"{sample_ratio:.2%}")

    st.plotly_chart(make_price_chart(kospi_df, price_title), use_container_width=True)
    st.plotly_chart(make_indicator_chart(kospi_df.index, indicator_title), use_container_width=True)

    st.info(
        "안내: 현재 두 번째 차트는 '예시 데이터'입니다. "
        "다음 단계에서 키움 API를 연결하면 실제 신고가/신저가 비율로 바꿀 수 있습니다."
    )
