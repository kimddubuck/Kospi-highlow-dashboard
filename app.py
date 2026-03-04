import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="Kospi High-Low Dashboard", layout="wide")

# -----------------------------
# 키움 인증
# -----------------------------
@st.cache_data(ttl=300)
def get_kiwoom_token():
    try:
        appkey = st.secrets["KIWOOM_APPKEY"]
        secret = st.secrets["KIWOOM_SECRET"]
        use_mock = str(st.secrets.get("KIWOOM_USE_MOCK", "false")).lower() == "true"

        base_url = "https://mockapi.kiwoom.com" if use_mock else "https://api.kiwoom.com"
        url = f"{base_url}/oauth2/token"

        payload = {
            "grant_type": "client_credentials",
            "appkey": appkey,
            "secretkey": secret,
        }

        headers = {
            "Content-Type": "application/json;charset=UTF-8"
        }

        r = requests.post(url, json=payload, headers=headers, timeout=15)

        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text}"

        data = r.json()
        token = data.get("token")

        if not token:
            return None, f"토큰 없음: {data}"

        return token, None

    except Exception as e:
        return None, str(e)

# -----------------------------
# 예시 코스피 데이터 (실패 시 대체)
# -----------------------------
def make_sample_daily_data():
    dates = pd.date_range(end=pd.Timestamp.today(), periods=120, freq="B")
    values = []
    base = 2500
    pattern = [0, 8, -5, 12, -7, 6, -3, 10, -4, 5]

    current = base
    for i in range(len(dates)):
        current += pattern[i % len(pattern)]
        values.append(current)

    return pd.DataFrame({"Close": values}, index=dates)

def make_sample_4h_data():
    end_time = pd.Timestamp.now().floor("h")
    dates = pd.date_range(end=end_time, periods=120, freq="4h")
    values = []
    base = 2520
    pattern = [0, 3, -2, 5, -3, 4, -1, 2, -2, 3]

    current = base
    for i in range(len(dates)):
        current += pattern[i % len(pattern)]
        values.append(current)

    return pd.DataFrame({"Close": values}, index=dates)

# -----------------------------
# 코스피 데이터
# -----------------------------
@st.cache_data(ttl=300)
def get_kospi_daily():
    try:
        df = yf.download("^KS11", period="1y", interval="1d", auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()

        if df.empty:
            return make_sample_daily_data(), False
        return df, True
    except Exception:
        return make_sample_daily_data(), False

@st.cache_data(ttl=300)
def get_kospi_4h():
    try:
        df = yf.download("^KS11", period="60d", interval="60m", auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()

        if df.empty:
            return make_sample_4h_data(), False

        df.index = pd.to_datetime(df.index)

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

        if ohlc.empty:
            return make_sample_4h_data(), False

        result = pd.DataFrame({"Close": ohlc["Close"]})
        return result, True

    except Exception:
        return make_sample_4h_data(), False

# -----------------------------
# 차트 함수
# -----------------------------
def make_price_chart(df, title_text):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            name="코스피"
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
    n = len(index_values)
    if n == 0:
        return pd.Series(dtype=float)

    base = [0.12, 0.15, 0.18, 0.11, 0.20, 0.16, 0.14, 0.22, 0.13, 0.17]
    values = [base[i % len(base)] for i in range(n)]
    return pd.Series(values, index=index_values)

def make_indicator_chart(index_values, title_text):
    indicator = make_indicator_series(index_values)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=indicator.index,
            y=indicator.values,
            mode="lines",
            name="지표"
        )
    )
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
# 화면
# -----------------------------
st.title("코스피 신고가/신저가 비율 대시보드")
st.caption("현재는 키움 인증 확인 단계입니다. 인증이 성공하면 다음 단계에서 실제 신고가/신저가 데이터를 연결합니다.")

token, token_error = get_kiwoom_token()

if token:
    st.success("키움 인증 성공: 접근토큰 발급 완료")
else:
    st.error(f"키움 인증 실패: {token_error}")

chart_type = st.radio(
    "차트 기준을 선택하세요",
    ["4시간봉", "일봉"],
    horizontal=True
)

if chart_type == "4시간봉":
    kospi_df, is_real = get_kospi_4h()
    price_title = "1번 차트 - 코스피 지수 (4시간봉)"
    indicator_title = "2번 차트 - 신고가/신저가 비율 (예시 데이터, 4시간 기준)"
else:
    kospi_df, is_real = get_kospi_daily()
    price_title = "1번 차트 - 코스피 지수 (일봉)"
    indicator_title = "2번 차트 - 신고가/신저가 비율 (예시 데이터, 일봉 기준)"

latest_close = float(kospi_df["Close"].iloc[-1])
sample_high = 18
sample_low = 102
sample_ratio = sample_high / (sample_high + sample_low)

c1, c2, c3 = st.columns(3)
c1.metric("현재 코스피", f"{latest_close:,.2f}")
c2.metric("예시 신고가 종목수", f"{sample_high}")
c3.metric("예시 지표", f"{sample_ratio:.2%}")

if is_real:
    st.success("코스피 실제 데이터를 불러왔습니다.")
else:
    st.warning("코스피 실제 데이터를 불러오지 못해 예시 코스피 데이터로 표시 중입니다.")

st.plotly_chart(make_price_chart(kospi_df, price_title), use_container_width=True)
st.plotly_chart(make_indicator_chart(kospi_df.index, indicator_title), use_container_width=True)

st.info("다음 단계에서 실제 신고가/신저가 데이터를 연결합니다.")
