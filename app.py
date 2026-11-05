# 쉬운 스윙 스캐너 — 일목균형표 + 미국 성장주 추세 철학 결합
# 실행: streamlit run app.py
# requirements.txt: streamlit yfinance plotly pandas numpy requests lxml
import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

st.set_page_config(page_title="쉬운 스윙 스캐너", page_icon="📈", layout="wide")

# ---------------------------------------------------------------- (선택) 비밀번호
try:
    _pw = st.secrets.get("APP_PASSWORD")
except Exception:
    _pw = None
if _pw:
    if st.session_state.get("auth") is not True:
        inp = st.text_input("비밀번호", type="password")
        if inp == _pw:
            st.session_state["auth"] = True
            st.rerun()
        st.stop()

# ================================================================ 종목 유니버스
THEMES = {
    "반도체": "NVDA AMD AVGO TSM ASML MU ARM MRVL AMAT LRCX KLAC INTC QCOM TXN ON MPWR ALAB CRDO COHR LITE SNPS CDNS TER SMCI WDC STX ENTG NXPI ADI MCHP SWKS QRVO GFS UMC LSCC RMBS MTSI AMKR ONTO FORM ACLS POWI SITM AEHR CAMT NVMI PLAB VSH AMBA SLAB DIOD",
    "AI·소프트웨어": "MSFT GOOGL AMZN META ORCL PLTR CRWV NBIS APP SNOW NOW CRM ADBE DDOG CRWD PANW PATH AI NET ZS MDB TEAM TTD GTLB S ESTC HUBS DOCN IBM INTU SOUN BBAI FTNT WDAY OKTA CYBR TENB QLYS MNDY TWLO DT CFLT PCOR APPF PEGA DOCU SHOP TYL FICO VEEV",
    "데이터센터·전력인프라": "VRT MOD NVT TT JCI CARR LII AAON FIX ETN ANET EQIX DLR PWR EME STRL DELL HPE CLS APH GLW HUBB POWL GNRC FLEX JBL CIEN VIAV CSCO IRM AMT WMS BLDR PSTG NTAP ATKR MYRG PRIM IESC",
    "에너지·원전": "CEG VST NRG TLN GEV OKLO SMR NNE CCJ LEU BWXT BE FLNC FSLR ENPH NEE SO DUK ETR XOM CVX OXY SLB AEP D EXC PEG SRE AES RUN NXT EOSE PLUG LNG EQT COP EOG FANG HAL UEC UUUU MPC VLO PSX KMI WMB OKE TRGP DVN",
    "우주·방산·로봇": "TSLA RKLB ASTS LUNR RDW PL SATS KTOS JOBY ACHR LMT NOC ISRG AVAV HWM RTX GD HII LDOS TDY BA GE SERV RR IRDM VSAT TDG AXON ROK EMR ZBRA CGNX",
    "핀테크·크립토": "COIN HOOD MSTR XYZ PYPL SOFI AFRM UPST MARA RIOT CLSK IREN CORZ CIFR HUT GLXY V MA FI FIS NU DKNG TOST",
    "바이오·헬스": "LLY NVO VRTX REGN DXCM ABBV AMGN GILD MRNA ALNY ARGX BMRN INCY NBIX EXAS INSM SMMT RVMD CRSP BEAM HIMS PODD TMDX GKOS INSP ALGN ZTS IDXX MEDP NTRA TEM RXRX",
    "소비·플랫폼": "AAPL NFLX UBER ABNB DASH SPOT RBLX DUOL CAVA CMG SBUX NKE LULU ONON DECK CELH MNST WING ELF TJX COST WMT BKNG MELI SE CPNG LYV RCL CCL NCLH TKO DKS RH",
    "산업·금융·원자재": "CAT DE URI PH ITW GWW FAST PCAR ODFL SAIA XPO SPGI MCO MSCI ICE CME NDAQ BX KKR APO ARES GS MS JPM BAC WFC C SCHW IBKR LPLA FCX NUE STLD AA SCCO MP ALB NEM AEM WPM FNV KGC",
    "퀀텀·신기술": "IONQ RGTI QBTS QUBT LAES EVLV KULR RZLV",
}
THEMES = {k: list(dict.fromkeys(v.split())) for k, v in THEMES.items()}
THEME_OF = {}
for _th, _ts in THEMES.items():
    for _t in _ts:
        THEME_OF.setdefault(_t, _th)

ETFS = ("SPY QQQ DIA IWM MDY IJR VTI SMH SOXX XLK IGV VGT ARKK ARKW ARKG ARKQ ARKX UFO XLE XOP OIH XLU URA URNM TAN GRID PAVE LIT "
        "XME COPX GDX GDXJ SLV GLD XLF KRE XLV IBB XBI XLI ITA XAR XLC XLY XLP XLB ITB XHB JETS EEM FXI KWEB EWJ EWY INDA IBIT").split()

FALLBACK = ("AAPL MSFT NVDA AMZN GOOGL META AVGO TSLA LLY JPM V UNH XOM MA COST HD PG JNJ ABBV WMT NFLX BAC CRM ORCL CVX KO MRK AMD "
            "PEP TMO ADBE LIN ACN MCD CSCO ABT WFC DIS GE TXN INTU QCOM VZ CAT AMGN IBM ISRG NOW DHR GS UBER AMAT BKNG RTX LOW NEE "
            "UNP HON AXP BLK PGR SYK TJX LMT COP VRTX BSX ETN C ADI MU PLD MMC SBUX GILD DE KLAC LRCX PANW ANET CMG SNPS CDNS").split()

WIKI = {
    "S&P 500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "나스닥 100": "https://en.wikipedia.org/wiki/Nasdaq-100",
    "S&P 400 (중형주)": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
    "S&P 600 (소형주)": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
}


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_index(name: str) -> pd.DataFrame:
    try:
        html = requests.get(WIKI[name], headers={"User-Agent": "Mozilla/5.0"}, timeout=20).text
        for t in pd.read_html(io.StringIO(html)):
            tcol = next((c for c in t.columns if str(c) in ("Symbol", "Ticker")), None)
            if tcol is None or len(t) < 30:
                continue
            ncol = next((c for c in t.columns if str(c) in ("Security", "Company")), None)
            return pd.DataFrame({
                "ticker": t[tcol].astype(str).str.replace(".", "-", regex=False).str.strip(),
                "이름": t[ncol].astype(str) if ncol is not None else "",
            })
    except Exception:
        pass
    return pd.DataFrame(columns=["ticker", "이름"])


def build_universe(sel, extra):
    fr = []
    for nm in WIKI:
        if nm in sel:
            f = fetch_index(nm)
            if f.empty and nm == "S&P 500":
                f = pd.DataFrame({"ticker": FALLBACK, "이름": ""})
            fr.append(f)
    if "테마 성장주" in sel:
        fr.append(pd.DataFrame({"ticker": list(THEME_OF), "이름": ""}))
    if "ETF" in sel:
        fr.append(pd.DataFrame({"ticker": ETFS, "이름": ""}))
    ex = [x.strip().upper() for x in extra.replace("\n", ",").split(",") if x.strip()]
    if ex:
        fr.append(pd.DataFrame({"ticker": ex, "이름": ""}))
    if not fr:
        return pd.DataFrame(columns=["ticker", "이름", "테마"])
    u = pd.concat(fr, ignore_index=True).drop_duplicates("ticker").reset_index(drop=True)
    u["테마"] = u["ticker"].map(THEME_OF).fillna("-")
    u["이름"] = u["이름"].replace("", np.nan).fillna(u["ticker"])
    return u


# ================================================================ 데이터
def _clean(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


@st.cache_data(ttl=1800, show_spinner=False)
def load_chunk(tickers: tuple, period: str = "2y") -> dict:
    out = {}
    try:
        raw = yf.download(list(tickers), period=period, auto_adjust=True, progress=False,
                          group_by="ticker", threads=True)
    except Exception:
        return out
    if raw is None or raw.empty:
        return out
    if isinstance(raw.columns, pd.MultiIndex):
        lv0 = set(raw.columns.get_level_values(0))
        if "Close" in lv0:
            try:
                out[tickers[0]] = _clean(raw.copy())
            except Exception:
                pass
            return out
        for t in tickers:
            if t in lv0:
                try:
                    d = _clean(raw[t].copy())
                    if len(d):
                        out[t] = d
                except Exception:
                    pass
    else:
        try:
            out[tickers[0]] = _clean(raw.copy())
        except Exception:
            pass
    return out


def load_many(tickers, period, label=""):
    data, bar = {}, st.progress(0.0, text=f"{label} 시세 다운로드 중...")
    for i in range(0, len(tickers), 100):
        data.update(load_chunk(tuple(tickers[i:i + 100]), period))
        done = min(i + 100, len(tickers))
        bar.progress(done / max(len(tickers), 1), text=f"{label} 시세 {done}/{len(tickers)}")
    bar.empty()
    return data


def drop_live_bar(df):
    """장중 미완성 봉 제거"""
    now = pd.Timestamp.now(tz="America/New_York")
    if len(df) and df.index[-1].date() == now.date() and now.hour < 16:
        return df.iloc[:-1]
    return df


# ================================================================ 핵심: 8가지 상승 체력 + 진입 타이밍
COND_NAMES = [
    "추세: 종가 > 50일선 > 200일선",
    "장기추세: 200일선이 우상향",
    "일목: 종가가 구름 위",
    "일목: 양운 (선행A > 선행B)",
    "일목: 전환선 > 기준선",
    "강세: 52주 고점 20% 이내",
    "주도주: 3·6개월 수익률이 SPY보다 높음",
    "자금유입: 최근 5일 거래량 ≥ 50일 평균",
]


def feats(raw, spy_close):
    d = raw.copy()
    c, h, l, o, v = d["Close"], d["High"], d["Low"], d["Open"], d["Volume"]
    d["ma50"], d["ma200"] = c.rolling(50).mean(), c.rolling(200).mean()
    d["ema21"] = c.ewm(span=21, adjust=False).mean()
    d["tenkan"] = (h.rolling(9).max() + l.rolling(9).min()) / 2
    d["kijun"] = (h.rolling(26).max() + l.rolling(26).min()) / 2
    d["spanA"] = ((d["tenkan"] + d["kijun"]) / 2).shift(26)
    d["spanB"] = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
    d["top"] = d[["spanA", "spanB"]].max(axis=1)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14).mean()
    d["vol50"] = v.rolling(50).mean()
    dl = c.diff()
    g, ls = dl.clip(lower=0).rolling(14).mean(), (-dl.clip(upper=0)).rolling(14).mean()
    d["rsi"] = 100 - 100 / (1 + g / ls.replace(0, np.nan))
    hi252 = h.rolling(252, min_periods=200).max()
    s = spy_close.reindex(d.index).ffill()
    T = pd.DataFrame(index=d.index)
    T[0] = (c > d["ma50"]) & (d["ma50"] > d["ma200"])
    T[1] = d["ma200"] > d["ma200"].shift(20)
    T[2] = c > d["top"]
    T[3] = d["spanA"] > d["spanB"]
    T[4] = d["tenkan"] > d["kijun"]
    T[5] = c >= hi252 * 0.80
    T[6] = (c.pct_change(63) > s.pct_change(63)) & (c.pct_change(126) > s.pct_change(126))
    T[7] = v.rolling(5).mean() >= d["vol50"]
    T = T.fillna(False).astype(bool)
    for i in range(8):
        d[f"t{i}"] = T[i]
    d["trend"] = T.sum(axis=1)
    d["ext"] = c / d["kijun"] - 1
    d["ret126"] = c.pct_change(126)
    brk = (c > h.shift(1).rolling(20).max()) & (v >= 1.3 * d["vol50"])
    pull = (c > o) & (c > d["kijun"]) & (l <= d["ema21"] * 1.01) & ((c / d["ema21"] - 1).abs() < 0.04)
    okx = (d["ext"] <= 0.12) & (d["rsi"] < 78)
    d["setup"] = np.where(brk & okx, 1, np.where(pull & okx, 2, 0))
    d["buy"] = (d["trend"] >= 7) & (d["setup"] > 0)
    d["gate"] = (s > s.rolling(50).mean()).reindex(d.index).fillna(False)
    return d


def make_plan(entry, atr, kijun, tgt_mult):
    stop = max(entry - 2 * atr, kijun, entry * 0.92)
    if stop >= entry:
        stop = entry * 0.95
    risk = entry - stop
    return stop, entry + tgt_mult * risk, risk


# ================================================================ 백테스트 (승률 검증)
def backtest(d, tgt_mult, hold, use_gate):
    o, h, l, c = d["Open"].values, d["High"].values, d["Low"].values, d["Close"].values
    atr, kj = d["atr"].values, d["kijun"].values
    sig = (d["buy"] & (d["gate"] if use_gate else True)).values
    idx, n, rows, i = d.index, len(d), [], 0
    while i < n - 2:
        if not sig[i] or np.isnan(atr[i]) or np.isnan(kj[i]):
            i += 1
            continue
        e = o[i + 1]
        stop, tgt, _ = make_plan(e, atr[i], kj[i], tgt_mult)
        ex, why, j = c[min(i + hold, n - 1)], "기간만료", min(i + hold, n - 1)
        for k in range(i + 1, min(i + hold, n - 1) + 1):
            if l[k] <= stop:
                ex, why, j = min(o[k], stop), "손절", k
                break
            if h[k] >= tgt:
                ex, why, j = max(o[k], tgt), "목표도달", k
                break
        rows.append({"진입일": idx[i + 1].date(), "청산일": idx[j].date(), "셋업": "돌파" if d["setup"].values[i] == 1 else "눌림목",
                     "수익률(%)": round((ex / e - 1) * 100, 2), "청산사유": why})
        i = j + 1
    return pd.DataFrame(rows)


def show_stats(tr):
    if tr.empty:
        st.info("거래가 없습니다.")
        return
    r = tr["수익률(%)"]
    win, loss = r[r > 0], r[r <= 0]
    a, b, c3, d4 = st.columns(4)
    a.metric("거래 수", f"{len(tr):,}")
    b.metric("승률", f"{(r > 0).mean() * 100:.1f}%")
    c3.metric("평균 수익 / 평균 손실", f"{win.mean() if len(win) else 0:+.1f}% / {loss.mean() if len(loss) else 0:+.1f}%")
    d4.metric("거래당 기대수익", f"{r.mean():+.2f}%")


# ================================================================ 스캔
def run_scan(uni, tgt_mult):
    tick = list(uni["ticker"])
    data = load_many(tick, "2y", "스캔")
    spy = load_chunk(("SPY",), "2y").get("SPY")
    if spy is None:
        return None
    info = uni.set_index("ticker")
    rows, fails = [], []
    for t in tick:
        try:
            if t not in data:
                raise ValueError("데이터 없음")
            d = drop_live_bar(data[t])
            if len(d) < 260:
                raise ValueError("데이터 부족(신규상장)")
            f = feats(d, spy["Close"])
            r = f.iloc[-1]
            if pd.isna(r.atr) or pd.isna(r.kijun):
                raise ValueError("지표 계산 불가")
            stop, tgt, risk = make_plan(r.Close, r.atr, r.kijun, tgt_mult)
            passed = [COND_NAMES[i] for i in range(8) if r[f"t{i}"]]
            miss = [COND_NAMES[i] for i in range(8) if not r[f"t{i}"]]
            rows.append({
                "종목": t, "이름": info.loc[t, "이름"], "테마": info.loc[t, "테마"], "trend": int(r.trend), "setup": int(r.setup),
                "ret126": r.ret126, "현재가": round(float(r.Close), 2), "손절가": round(float(stop), 2),
                "목표가": round(float(tgt), 2), "손절폭(%)": round(risk / r.Close * 100, 1),
                "이격(%)": round(float(r.ext) * 100, 1), "미충족": ", ".join(miss) if miss else "-",
            })
        except Exception as e:
            fails.append(f"{t}: {e}")
    if not rows:
        return None
    R = pd.DataFrame(rows)
    R["RS"] = (R["ret126"].rank(pct=True) * 99).round(0)
    R["점수"] = (R["trend"] / 8 * 60 + R["RS"] / 100 * 25 + R["setup"].map({1: 15, 2: 12, 0: 0})
               - (R["이격(%)"] - 8).clip(lower=0) * 1.5).clip(lower=0).round(0)
    R["등급"] = np.where(R["점수"] >= 80, "A", np.where(R["점수"] >= 65, "B", "C"))

    def stt(x):
        if x.trend >= 7 and x.setup == 1:
            return "🚀 돌파 매수후보"
        if x.trend >= 7 and x.setup == 2:
            return "🎯 눌림목 매수후보"
        if x.trend >= 7:
            return "👀 상승중 (타이밍 대기)"
        return "제외"
    R["상태"] = R.apply(stt, axis=1)
    return R, fails, len(tick)


# ================================================================ 차트
def make_chart(d, title):
    x = d.tail(250)
    bull = x["spanA"] >= x["spanB"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22], vertical_spacing=0.03)
    for m, col, nm in ((bull, "rgba(239,83,80,0.22)", "양운"), (~bull, "rgba(66,133,244,0.22)", "음운")):
        fig.add_trace(go.Scatter(x=x.index, y=x["spanB"].where(m), line=dict(width=0), showlegend=False, hoverinfo="skip"), row=1, col=1)
        fig.add_trace(go.Scatter(x=x.index, y=x["spanA"].where(m), line=dict(width=0), fill="tonexty", fillcolor=col, name=nm, hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Candlestick(x=x.index, open=x["Open"], high=x["High"], low=x["Low"], close=x["Close"],
                                 increasing_line_color="#ef5350", decreasing_line_color="#1e88e5", name="캔들"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x.index, y=x["kijun"], line=dict(color="#1565c0", width=1.5), name="기준선"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x.index, y=x["ma50"], line=dict(color="#fb8c00", width=1.3), name="50일선"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x.index, y=x["ma200"], line=dict(color="#9e9e9e", width=1.2), name="200일선"), row=1, col=1)
    s = x[x["buy"]]
    fig.add_trace(go.Scatter(x=s.index, y=s["Low"] * 0.97, mode="markers", name="매수신호",
                             marker=dict(symbol="triangle-up", size=13, color="#00c853", line=dict(width=1, color="black"))), row=1, col=1)
    colors = np.where(x["Close"] >= x["Open"], "#ef5350", "#1e88e5")
    fig.add_trace(go.Bar(x=x.index, y=x["Volume"], marker_color=colors, showlegend=False), row=2, col=1)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(title=title, height=650, xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", y=1.06), margin=dict(l=10, r=10, t=70, b=10))
    return fig


# ================================================================ 사이드바 (설정은 최소한)
# ================================================================ 단타(당일 매매) 도구 — 5분봉
DT_DEFAULT = ("NVDA TSLA AMD PLTR AAPL META AMZN MSFT AVGO MU SMCI COIN MSTR HOOD SOFI RKLB IONQ ARM NFLX GOOGL "
              "UBER SHOP APP CRWD DELL ANET VRT CEG OKLO ASTS").split()
DT_ORB_BARS = 6  # 장 시작 후 30분 = 5분봉 6개


def dt_clean(d):
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d[["Open", "High", "Low", "Close", "Volume"]].dropna()
    idx = pd.to_datetime(d.index)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    d.index = idx.tz_convert("America/New_York").tz_localize(None)
    return d.between_time("09:30", "15:59")


@st.cache_data(ttl=120, show_spinner=False)
def load_intraday(tickers: tuple, period: str = "10d") -> dict:
    out = {}
    try:
        raw = yf.download(list(tickers), period=period, interval="5m", auto_adjust=True,
                          progress=False, group_by="ticker", threads=True, prepost=False)
    except Exception:
        return out
    if raw is None or raw.empty:
        return out
    for t in tickers:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                lv0 = set(raw.columns.get_level_values(0))
                if t in lv0:
                    d = raw[t].copy()
                elif len(tickers) == 1:
                    d = raw.copy()
                else:
                    continue
            else:
                d = raw.copy()
            d = dt_clean(d)
            if len(d) > 100:
                out[t] = d
        except Exception:
            pass
    return out


def dt_drop_live(raw):
    """아직 끝나지 않은 5분봉 제거"""
    now = pd.Timestamp.now(tz="America/New_York").tz_localize(None)
    if len(raw) and raw.index[-1] + pd.Timedelta(minutes=5) > now:
        return raw.iloc[:-1]
    return raw


def dt_prepare(raw):
    d = raw.copy()
    d["day"] = d.index.date
    tp = (d["High"] + d["Low"] + d["Close"]) / 3
    d["vwap"] = (tp * d["Volume"]).groupby(d["day"]).cumsum() / d.groupby("day")["Volume"].cumsum().replace(0, np.nan)
    d["ema9"] = d["Close"].ewm(span=9, adjust=False).mean()
    pc = d["Close"].shift()
    tr = pd.concat([d["High"] - d["Low"], (d["High"] - pc).abs(), (d["Low"] - pc).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14, min_periods=5).mean()
    d["bar_n"] = d.groupby("day").cumcount()
    d["cumvol"] = d.groupby("day")["Volume"].cumsum()
    # RVOL: 같은 시각까지의 누적 거래량 ÷ 직전 최대 5일 평균
    piv = d.pivot_table(index="bar_n", columns="day", values="cumvol")
    days = list(piv.columns)
    rv = pd.Series(np.nan, index=d.index)
    for i, dy in enumerate(days):
        if i == 0:
            continue
        base_s = piv[days[max(0, i - 5):i]].mean(axis=1)
        m = d["day"] == dy
        rv[m] = d.loc[m, "cumvol"] / d.loc[m, "bar_n"].map(base_s)
    d["rvol"] = rv
    dclose = d.groupby("day")["Close"].last()
    dopen = d.groupby("day")["Open"].first()
    d["gap"] = (d["day"].map(dopen) / d["day"].map(dclose.shift()) - 1) * 100
    orb = d[d["bar_n"] < DT_ORB_BARS].groupby("day").agg(orh=("High", "max"), orl=("Low", "min"))
    d["orh"], d["orl"] = d["day"].map(orb["orh"]), d["day"].map(orb["orl"])
    c, o, lo = d["Close"], d["Open"], d["Low"]
    ok_time = (d["bar_n"] >= DT_ORB_BARS) & (d["bar_n"] <= 66)  # 10:00 ~ 15:00 (뉴욕)
    # 🚀 시초 돌파: 첫 30분 고점을 거래량 실리며 처음 넘는 봉
    orb_sig = (ok_time & (c > d["orh"]) & (c.shift() <= d["orh"]) & (c > d["vwap"])
               & (c > d["ema9"]) & (d["rvol"] >= 1.3))
    # 🎯 VWAP 눌림: 오른 뒤 VWAP까지 눌렸다가 다시 위로 올라오는 양봉
    touched = lo.rolling(6).min() <= d["vwap"] * 1.002
    was_up = d.groupby("day")["High"].cummax() >= d["vwap"] * 1.004
    pb_raw = (ok_time & touched & was_up & (c > d["vwap"]) & (c > d["ema9"]) & (c > o)
              & (d["vwap"] > d["vwap"].shift(6)))
    recent = pb_raw.astype(int).rolling(6).sum().shift(1).fillna(0) > 0
    pb = pb_raw & ~recent
    d["setup"] = np.where(orb_sig, 1, np.where(pb, 2, 0))
    return d


def dt_plan(d, i, tgt):
    """손절·1R·목표 계산 (손절폭 = 최근 6봉 저점까지, 5분봉 ATR의 1.5~2.5배로 제한)"""
    r = d.iloc[i]
    price = float(r["Close"])
    atr = float(r["atr"]) if pd.notna(r["atr"]) else price * 0.004
    swing = float(d["Low"].iloc[max(0, i - 5):i + 1].min())
    risk = float(np.clip(price - swing, 1.5 * atr, 2.5 * atr))
    return price - risk, price + risk, price + tgt * risk, risk


def dt_backtest(d, tgt=1.0):
    """하루 최대 1회: 첫 신호 다음 봉 시가 매수 → 손절/목표/장마감 중 먼저 오는 것으로 청산"""
    rows = []
    for dy, g in d.groupby("day"):
        g = g.reset_index(drop=True)
        idx = np.flatnonzero((g["setup"].values > 0) & (g["bar_n"].values <= 60))
        if len(idx) == 0:
            continue
        i = int(idx[0])
        if i + 1 >= len(g) or pd.isna(g["atr"].iloc[i]):
            continue
        entry = float(g["Open"].iloc[i + 1])
        atr = float(g["atr"].iloc[i])
        swing = float(g["Low"].iloc[max(0, i - 5):i + 1].min())
        risk = float(np.clip(g["Close"].iloc[i] - swing, 1.5 * atr, 2.5 * atr))
        stop, target = entry - risk, entry + tgt * risk
        exit_p, why = float(g["Close"].iloc[-1]), "장마감"
        for j in range(i + 1, len(g)):
            if g["Low"].iloc[j] <= stop:      # 같은 봉에 둘 다 닿으면 손절로 보수적 처리
                exit_p, why = stop, "손절"
                break
            if g["High"].iloc[j] >= target:
                exit_p, why = target, "목표"
                break
        rows.append({"날짜": dy, "셋업": "시초돌파" if g["setup"].iloc[i] == 1 else "VWAP눌림",
                     "진입": round(entry, 2), "R": round((exit_p - entry) / risk, 2),
                     "수익률(%)": round((exit_p / entry - 1) * 100, 2), "청산": why})
    return pd.DataFrame(rows)


def dt_scan(tickers, daily_ok, tgt):
    data = {}
    for i in range(0, len(tickers), 40):
        data.update(load_intraday(tuple(tickers[i:i + 40]), "10d"))
    rows, fails = [], []
    for t in tickers:
        raw = data.get(t)
        if raw is None:
            fails.append(t)
            continue
        try:
            d = dt_prepare(dt_drop_live(raw))
            if len(d) < 30:
                fails.append(t)
                continue
            dd = d[d["day"] == d["day"].iloc[-1]]
            r = d.iloc[-1]
            rec = dd["setup"].tail(3)
            rec = rec[rec > 0]
            setup = int(rec.iloc[-1]) if len(rec) else 0
            vw = float((r.Close / r.vwap - 1) * 100)
            if len(dd) <= DT_ORB_BARS:
                status = "⏳ 시초범위 형성 중"
            elif setup == 1:
                status = "🚀 시초 돌파"
            elif setup == 2:
                status = "🎯 VWAP 눌림"
            elif r.Close > r.vwap and r.Close > r.orh:
                status = "👀 강세 유지 (추격 주의)"
            elif r.Close > r.vwap:
                status = "👀 대기 (VWAP 위)"
            else:
                status = "⚪ 관망 (VWAP 아래)"
            stop, t1, t2, risk = dt_plan(d, len(d) - 1, tgt)
            rv = float(r.rvol) if pd.notna(r.rvol) else 0.0
            gap = float(r.gap) if pd.notna(r.gap) else 0.0
            score = ((40 if setup else 0) + min(rv, 4) * 10 + (15 if vw > 0 else 0)
                     + (10 if t in daily_ok else 0) + min(max(gap, 0), 5) * 2)
            rows.append({"종목": t, "상태": status, "점수": round(score, 1), "현재가": round(float(r.Close), 2),
                         "갭(%)": round(gap, 1), "RVOL": round(rv, 1), "VWAP 대비(%)": round(vw, 2),
                         "일봉추세": "✅" if t in daily_ok else "-",
                         "손절가": round(stop, 2), "1R": round(t1, 2), "목표가": round(t2, 2),
                         "위험($/주)": round(risk, 2), "손절폭(%)": round(risk / float(r.Close) * 100, 2),
                         "마지막 봉": str(d.index[-1])[5:16]})
        except Exception:
            fails.append(t)
    return pd.DataFrame(rows), fails


def dt_chart(d, day, title, plan=None):
    x = d[d["day"] == day]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=x.index, open=x["Open"], high=x["High"], low=x["Low"], close=x["Close"],
                                 increasing_line_color="#ef5350", decreasing_line_color="#1e88e5", name="5분봉"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x.index, y=x["vwap"], line=dict(color="#fb8c00", width=2), name="VWAP"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x.index, y=x["ema9"], line=dict(color="#8e24aa", width=1.2), name="9EMA"), row=1, col=1)
    if len(x) > DT_ORB_BARS:
        fig.add_hline(y=float(x["orh"].iloc[0]), line_dash="dash", line_color="#757575", annotation_text="시초 고점", row=1, col=1)
        fig.add_hline(y=float(x["orl"].iloc[0]), line_dash="dash", line_color="#757575", annotation_text="시초 저점", row=1, col=1)
        fig.add_vrect(x0=x.index[0], x1=x.index[DT_ORB_BARS - 1] + pd.Timedelta(minutes=5),
                      fillcolor="rgba(150,150,150,0.12)", line_width=0, row=1, col=1)
    for k, nm, sym, col in ((1, "🚀 시초 돌파", "triangle-up", "#00c853"), (2, "🎯 VWAP 눌림", "diamond", "#2962ff")):
        s = x[x["setup"] == k]
        if len(s):
            fig.add_trace(go.Scatter(x=s.index, y=s["Low"] * 0.998, mode="markers", name=nm,
                                     marker=dict(symbol=sym, size=14, color=col, line=dict(width=1, color="black"))), row=1, col=1)
    if plan:
        stop, t1, t2, _ = plan
        for y, nm, col in ((stop, "손절", "#d32f2f"), (t1, "1R", "#2e7d32"), (t2, "목표", "#1b5e20")):
            fig.add_hline(y=y, line_dash="dot", line_color=col, annotation_text=f"{nm} {y:,.2f}", row=1, col=1)
    colors = np.where(x["Close"] >= x["Open"], "#ef5350", "#1e88e5")
    fig.add_trace(go.Bar(x=x.index, y=x["Volume"], marker_color=colors, showlegend=False, name="거래량"), row=2, col=1)
    fig.update_layout(title=title, height=640, xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", y=1.08), margin=dict(l=10, r=10, t=80, b=10))
    return fig


def dt_stats(B, tgt):
    if B is None or B.empty:
        st.info("신호가 나온 날이 없습니다. 종목 수를 늘리거나 다른 종목으로 해 보세요.")
        return
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("거래 수", f"{len(B):,}", help="하루 1번씩, 신호가 나온 날만 거래한 횟수입니다.")
    m2.metric("승률", f"{(B['R'] > 0).mean() * 100:.0f}%", help="이익으로 끝난 거래의 비율입니다.")
    m3.metric("평균 R", f"{B['R'].mean():+.2f}", help="거래 1번당 평균 결과를 '손절폭 몇 배'로 나타낸 값입니다. +이어야 장기적으로 이득입니다.")
    m4.metric("평균 수익률", f"{B['수익률(%)'].mean():+.2f}%", help="수수료·슬리피지 전 거래당 평균 수익률입니다.")
    st.caption(f"목표 {tgt}배 기준 손익분기 승률은 약 {100 / (1 + tgt):.0f}%입니다. 승률이 이보다 높고 평균 R이 +여야 의미가 있습니다.")


def dt_market_msg():
    now = pd.Timestamp.now(tz="America/New_York")
    mins = now.hour * 60 + now.minute
    if now.weekday() < 5 and 570 <= mins < 960:
        st.success(f"🟢 미국 장 진행 중 (뉴욕 {now:%H:%M}). 오전 10:00 이후부터 신호가 나옵니다.")
    else:
        st.info(f"🌙 지금은 미국 장이 닫혀 있습니다 (뉴욕 {now:%m-%d %H:%M}). 마지막 거래일 데이터로 복기·연습용으로 보세요.")


# ================================================================ 사이드바
with st.sidebar:
    st.title("📈 쉬운 스윙 스캐너")
    sel = st.multiselect("검색할 종목 범위", list(WIKI) + ["테마 성장주", "ETF"],
                         default=["S&P 500", "나스닥 100", "테마 성장주"],
                         help="어떤 종목 묶음을 검사할지 고릅니다. 많이 고를수록 후보는 늘지만 검사 시간이 길어집니다.")
    extra = st.text_area("추가 티커 (쉼표로 구분)", "", height=70,
                         help="위 목록에 없는 종목을 직접 넣습니다. 예: PLTR, RKLB, IONQ")
    tgt_mult = st.select_slider("목표 수익 (손절폭의 몇 배)", [1.0, 1.5, 2.0, 3.0], value=1.5,
                                help="낮을수록 목표에 빨리 닿아 승률↑, 대신 한 번 이길 때 이익이 작아집니다.")
    hold = st.slider("최대 보유일", 10, 40, 20,
                     help="승률 검증에서 손절·목표에 닿지 않아도 이 날짜가 지나면 정리한다고 가정합니다.")
    use_gate = st.checkbox("시장(SPY)이 50일선 위일 때만 매수", True,
                           help="시장이 약할 때 나온 신호를 제외합니다. 승률을 지키는 가장 효과적인 필터라 켜 두길 권합니다.")
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.session_state.pop("scan", None)
        st.rerun()
    st.caption("참고용 도구이며 매수 권유가 아닙니다.")

UNI = build_universe(sel, extra)

# 시장 신호등
try:
    spy_d = load_chunk(("SPY",), "2y").get("SPY")
    sf = feats(spy_d, spy_d["Close"]).iloc[-1]
    if sf.Close > sf.ma50 and sf.Close > sf.top:
        st.success("🟢 시장 양호: SPY가 50일선·구름 위 → 적극적으로 매수 후보를 보세요")
    elif sf.Close > sf.ma50:
        st.info("🟡 시장 보통: SPY가 50일선 위지만 구름 위는 아님 → 비중을 줄여서 접근")
    else:
        st.warning("🔴 시장 약세: SPY가 50일선 아래 → 신규 매수는 쉬는 것이 승률에 유리합니다")
except Exception:
    pass

tab1, tab2, tabD, tab3, tab4, tabG = st.tabs(
    ["🏆 오늘의 추천", "🔍 종목 분석", "⚡ 단타", "✅ 승률 검증", "📖 쉬운 설명", "📚 항목 사전"])

# ================================================================ 탭1: 오늘의 추천
with tab1:
    st.write(f"선택 범위 **{len(UNI):,}종목**을 한 번에 검사해서, 오를 확률이 높은 순서로 보여드립니다.")
    if st.button("🚀 오늘의 추천 종목 찾기", type="primary"):
        if UNI.empty:
            st.warning("사이드바에서 종목 범위를 선택하세요.")
        else:
            out = run_scan(UNI, tgt_mult)
            if out is None:
                st.error("시세를 불러오지 못했습니다. 잠시 후 다시 시도하세요.")
            else:
                st.session_state["scan"] = out
    S = st.session_state.get("scan")
    if S:
        R, fails, total = S
        buy = R[R["상태"].str.contains("매수후보")]
        wait = R[R["상태"].str.contains("대기")]
        m1, m2, m3 = st.columns(3)
        m1.metric("분석 완료", f"{len(R):,}/{total:,}", help="시세를 정상적으로 받아 검사를 마친 종목 수 / 전체 검색 대상 수")
        m2.metric("매수 후보", len(buy), help="상승 체력 조건을 충족하고, 돌파·눌림목 같은 매수 타이밍 신호까지 나온 종목 수")
        m3.metric("상승중 대기", len(wait), help="체력은 좋지만 아직 매수 타이밍이 아닌 종목. 관심종목에 담고 눌림이나 돌파를 기다립니다.")
        show = ["종목", "이름", "테마", "등급", "점수", "RS", "현재가", "손절가", "목표가", "손절폭(%)", "이격(%)"]
        st.subheader("🔥 지금 매수 검토 (A·B등급 우선)")
        bb = buy[buy["등급"].isin(["A", "B"])].sort_values("점수", ascending=False)
        if bb.empty:
            st.warning("조건을 모두 만족하는 종목이 없습니다. 이럴 땐 쉬는 것도 승률을 지키는 전략입니다.")
        else:
            st.dataframe(bb[["상태"] + show], hide_index=True, use_container_width=True)
        st.subheader("👀 상승 중인 강한 종목 (눌림·돌파 대기 → 관심종목)")
        ww = wait.sort_values("점수", ascending=False).head(50)
        st.dataframe(ww[show], hide_index=True, use_container_width=True)
        st.caption("RS = 6개월 수익률의 순위(99가 최상위). 손절가·목표가는 오늘 종가로 매수한다고 가정한 값입니다. 이격이 크면 추격 주의.")
        st.download_button("전체 결과 CSV", R.drop(columns=["ret126"]).to_csv(index=False).encode("utf-8-sig"), "scan.csv")
        if fails:
            with st.expander(f"불러오기 실패 {len(fails)}건"):
                st.write(", ".join(fails[:200]))

# ================================================================ 탭2: 종목 분석
with tab2:
    q = st.text_input("티커 입력 (예: NVDA)", "NVDA").strip().upper()
    if q:
        try:
            raw = load_chunk((q, "SPY"), "5y")
            if q not in raw or "SPY" not in raw:
                st.error("데이터를 찾을 수 없습니다.")
            else:
                d = feats(drop_live_bar(raw[q]), raw["SPY"]["Close"])
                r = d.iloc[-1]
                stop, tgt, risk = make_plan(r.Close, r.atr, r.kijun, tgt_mult)
                if r.trend >= 7 and r.setup > 0:
                    verdict = "🟢 매수 검토 (" + ("돌파" if r.setup == 1 else "눌림목") + ")"
                elif r.trend >= 7:
                    verdict = "🟡 상승 중이지만 타이밍 대기"
                else:
                    verdict = "🔴 지금은 패스"
                a, b, c3, d4 = st.columns(4)
                a.metric("판정", verdict, help="상승 체력 7개 이상 + 매수 타이밍이면 🟢, 체력만 좋으면 🟡, 그 외는 🔴 패스")
                b.metric("현재가", f"{r.Close:,.2f}", help="가장 최근 확정 종가")
                c3.metric("손절가", f"{stop:,.2f}", f"-{risk / r.Close * 100:.1f}%", help="이 가격 아래로 마감하면 미련 없이 정리하는 기준. 화살표 숫자는 현재가 대비 손절폭입니다.")
                d4.metric(f"목표가 ({tgt_mult}배)", f"{tgt:,.2f}", f"+{(tgt / r.Close - 1) * 100:.1f}%", help="손절폭의 목표 배수만큼 올랐을 때의 가격. 사이드바에서 배수를 바꿀 수 있습니다.")
                st.plotly_chart(make_chart(d, f"{q} — 일목구름 + 추세"), use_container_width=True)
                L, Rr = st.columns(2)
                with L:
                    st.subheader(f"상승 체력 {int(r.trend)}/8")
                    for i in range(8):
                        st.write(("✅ " if r[f"t{i}"] else "❌ ") + COND_NAMES[i])
                    st.write(f"{'✅' if r.ext <= 0.12 else '❌'} 과열 아님 (기준선 이격 {r.ext * 100:.1f}%, RSI {r.rsi:.0f})")
                    with st.expander("🧮 몇 주 살까? (계좌의 1%만 잃도록)"):
                        acct = st.number_input("투자 가능 금액($)", 0.0, value=10000.0, step=1000.0)
                        sh = int(min(acct * 0.01 / risk, acct // r.Close)) if risk > 0 else 0
                        st.write(f"권장 **{sh:,}주** · 투입 ${sh * r.Close:,.0f} · 손절 시 손실 ${sh * risk:,.0f}")
                with Rr:
                    st.subheader("이 종목의 과거 성적 (5년)")
                    tr = backtest(d, tgt_mult, hold, use_gate)
                    show_stats(tr)
                    if not tr.empty:
                        st.dataframe(tr, hide_index=True, use_container_width=True)
                    st.caption("한 종목은 거래 수가 적어 참고용입니다. 전체 성적은 '승률 검증' 탭에서 확인하세요.")
        except Exception as e:
            st.error(f"분석 실패: {e}")

# ================================================================ 탭3: 승률 검증
with tab3:
    st.write("같은 규칙을 여러 종목·5년간 돌려서 **실제 승률**이 얼마였는지 확인합니다. (신호 다음날 시가 매수, 손절·목표·기간만료 중 먼저 오는 것으로 청산)")
    n_samp = st.slider("검증할 종목 수 (무작위)", 50, 400, 150, 50)
    if st.button("🧪 승률 검증 실행", type="primary"):
        tick = list(UNI["ticker"])
        if not tick:
            st.warning("종목 범위를 선택하세요.")
        else:
            rng = np.random.default_rng(7)
            pick = list(rng.choice(tick, min(n_samp, len(tick)), replace=False))
            data = load_many(pick, "5y", "검증")
            spy = load_chunk(("SPY",), "5y").get("SPY")
            alltr = []
            if spy is not None:
                for t, dd in data.items():
                    if len(dd) < 320:
                        continue
                    try:
                        tr = backtest(feats(dd, spy["Close"]), tgt_mult, hold, use_gate)
                        if not tr.empty:
                            tr.insert(0, "종목", t)
                            alltr.append(tr)
                    except Exception:
                        pass
            st.session_state["bt"] = pd.concat(alltr, ignore_index=True) if alltr else pd.DataFrame()
    B = st.session_state.get("bt")
    if B is not None:
        show_stats(B)
        if not B.empty:
            g1, g2 = st.columns(2)
            g1.write("**셋업별**")
            g1.dataframe(B.groupby("셋업")["수익률(%)"].agg(거래수="count", 승률=lambda s: (s > 0).mean() * 100, 평균="mean").round(2))
            g2.write("**청산사유별**")
            g2.dataframe(B.groupby("청산사유")["수익률(%)"].agg(거래수="count", 평균="mean").round(2))
            with st.expander("전체 거래 내역"):
                st.dataframe(B, hide_index=True, use_container_width=True)
        st.warning("현재 구성종목 기준이라 실제보다 좋게 나오는 편향이 있습니다. 승률이 높아도 '평균 손실'이 '평균 수익'보다 훨씬 크면 "
                   "결국 손해이니, 반드시 '거래당 기대수익'이 + 인지 같이 보세요.")

# ================================================================ 탭: 단타
with tabD:
    st.subheader("⚡ 단타 도구 — 5분봉 · 당일 청산이 원칙")
    dt_market_msg()
    st.caption("미국 정규장은 한국시간 23:30~06:00 (서머타임 22:30~05:00). 무료 시세는 지연될 수 있으니 주문 전 증권사 앱의 실시간 호가를 꼭 확인하세요.")
    k1, k2, k3 = st.columns(3)
    dt_tgt = k1.select_slider("목표 (손절폭의 몇 배)", [0.5, 1.0, 1.5, 2.0], value=1.0,
                              help="단타는 짧게 먹고 나오는 게임이라 1배(손절폭만큼 오르면 익절)가 기본입니다. 낮을수록 승률↑, 건당 이익↓.")
    dt_risk = k2.slider("1회 감수 손실 (계좌의 %)", 0.1, 1.0, 0.3, 0.1,
                        help="손절에 걸렸을 때 계좌에서 잃어도 되는 비율. 단타는 횟수가 많아서 스윙(1%)보다 작게 잡습니다.")
    dt_acct = k3.number_input("투자 가능 금액($)", 0.0, value=10000.0, step=1000.0, key="dt_acct",
                              help="권장 수량 계산에 쓰는 금액입니다.")
    sA, sB, sC = st.tabs(["📡 단타 후보", "📈 차트로 확인", "🧪 단타 검증"])

    with sA:
        wl = st.text_area("후보 티커 (공백 또는 쉼표로 구분)", " ".join(DT_DEFAULT), height=90, key="dt_wl",
                          help="거래량이 많고 하루 변동이 있는 종목일수록 단타에 적합합니다. 자유롭게 바꾸세요.")
        c1, c2 = st.columns(2)
        add_daily = c1.checkbox("'오늘의 추천'(일봉) 상위 종목도 함께 검사", True,
                                help="🏆 탭에서 먼저 추천을 실행했다면 그 결과 중 상위 30개를 후보에 더합니다.")
        only_daily = c2.checkbox("일봉 추세도 좋은 종목만 보기", False,
                                 help="큰 흐름(일봉)이 오르는 종목만 남깁니다. 단타도 오르는 종목에서 할 때 유리합니다.")
        if st.button("⚡ 단타 후보 찾기", type="primary", key="dt_go"):
            tick = [x.strip().upper() for x in wl.replace(",", " ").split() if x.strip()]
            daily_ok = set()
            Sx = st.session_state.get("scan")
            if Sx:
                Rx = Sx[0]
                good = Rx[Rx["상태"].str.contains("매수후보|대기")]
                daily_ok = set(good["종목"])
                if add_daily:
                    tick += list(good.sort_values("점수", ascending=False)["종목"].head(30))
            tick = list(dict.fromkeys(tick))[:80]
            with st.spinner(f"{len(tick)}종목 5분봉 분석 중..."):
                res_df, fails = dt_scan(tick, daily_ok, dt_tgt)
            st.session_state["dt_scan"] = (res_df, fails, dt_tgt)
        X = st.session_state.get("dt_scan")
        if X:
            res, fails, used_tgt = X
            if res.empty:
                st.error("5분봉을 불러오지 못했습니다. 잠시 후 다시 시도하세요.")
            else:
                v = res.copy()
                if only_daily:
                    v = v[v["일봉추세"] == "✅"]
                qty = np.minimum(dt_acct * dt_risk / 100 / v["위험($/주)"].replace(0, np.nan), dt_acct // v["현재가"])
                v["권장수량"] = np.floor(qty).fillna(0).astype(int)
                is_sig = v["상태"].str.contains("🚀|🎯")
                m1, m2, m3 = st.columns(3)
                m1.metric("검사 종목", len(v), help="5분봉 분석을 마친 종목 수")
                m2.metric("🚀 시초 돌파", int(v["상태"].str.contains("🚀").sum()), help="장 시작 30분 고점을 거래량과 함께 넘은 종목")
                m3.metric("🎯 VWAP 눌림", int(v["상태"].str.contains("🎯").sum()), help="오른 뒤 VWAP까지 눌렸다가 다시 올라오는 종목")
                st.subheader("🔥 지금 진입 검토 (최근 15분 내 신호)")
                if not is_sig.any():
                    st.warning("지금 신호가 나온 종목이 없습니다. 억지로 들어가지 않는 것도 단타의 일부입니다.")
                else:
                    st.dataframe(v[is_sig].sort_values("점수", ascending=False), hide_index=True)
                st.subheader("👀 지켜볼 종목")
                st.dataframe(v[~is_sig].sort_values("점수", ascending=False).head(30), hide_index=True)
                st.caption("손절가·1R·목표가는 '현재가에 산다'고 가정한 값입니다. 갭 = 전일 종가 대비 시초 상승률, RVOL = 평소 같은 시각 대비 거래량 배수, "
                           "VWAP 대비 = 오늘 평균 매수단가보다 몇 % 위인지. 자세한 뜻은 '📚 항목 사전' 탭에서 확인하세요.")
                if fails:
                    with st.expander(f"불러오기 실패 {len(fails)}건"):
                        st.write(", ".join(fails))

    with sB:
        tq = st.text_input("티커 입력 (예: NVDA)", "NVDA", key="dt_q").strip().upper()
        if tq:
            raw5 = load_intraday((tq,), "10d").get(tq)
            if raw5 is None or len(raw5) < 100:
                st.error("5분봉 데이터를 찾을 수 없습니다. 티커를 확인하거나 잠시 후 다시 시도하세요.")
            else:
                d5 = dt_prepare(dt_drop_live(raw5))
                day_list = sorted(d5["day"].unique(), reverse=True)
                day = st.selectbox("날짜 (지난 날로 복기 가능)", day_list, format_func=str, key="dt_day")
                x = d5[d5["day"] == day]
                last = x.iloc[-1]
                sig_pos = np.flatnonzero(((d5["day"] == day) & (d5["setup"] > 0)).values)
                plan = dt_plan(d5, int(sig_pos[-1]), dt_tgt) if len(sig_pos) else None
                if len(sig_pos):
                    verdict = "🚀 시초 돌파 신호" if d5["setup"].iloc[int(sig_pos[-1])] == 1 else "🎯 VWAP 눌림 신호"
                elif last.Close > last.vwap:
                    verdict = "👀 VWAP 위 (신호 대기)"
                else:
                    verdict = "⚪ VWAP 아래 (관망)"
                a, b, c, e = st.columns(4)
                a.metric("판정", verdict, help="그 날 마지막으로 나온 신호 기준입니다.")
                b.metric("종가/현재가", f"{last.Close:,.2f}")
                c.metric("VWAP 대비", f"{(last.Close / last.vwap - 1) * 100:+.2f}%", help="+면 오늘 평균 매수단가보다 위 = 매수세 우위")
                e.metric("RVOL", f"{last.rvol:.1f}배" if pd.notna(last.rvol) else "-", help="평소 같은 시각 누적 거래량 대비 배수. 1.5배 이상이면 관심이 몰린 날입니다.")
                st.plotly_chart(dt_chart(d5, day, f"{tq} — {day} 5분봉", plan))
                if plan:
                    stop, t1, t2, risk = plan
                    px = float(d5['Close'].iloc[int(sig_pos[-1])])
                    sh = int(min(dt_acct * dt_risk / 100 / risk, dt_acct // px)) if risk > 0 else 0
                    st.info(f"💡 신호 봉 종가 {px:,.2f} 기준 · 손절 {stop:,.2f} (-{risk / px * 100:.2f}%) · 1R {t1:,.2f} · 목표 {t2:,.2f} · "
                            f"권장 {sh:,}주 (손절 시 손실 약 ${sh * risk:,.0f})")
                    st.caption("규칙: 1R에 닿으면 절반 정리 + 손절을 본전으로 올리고, 장 마감 15분 전(뉴욕 15:45)까지 전량 정리합니다.")
                else:
                    st.caption("이 날은 신호가 없었습니다. 회색 띠 = 시초 30분 범위, 주황선 = VWAP, 보라선 = 9EMA.")

    with sC:
        st.write("최근 약 1개월(야후 5분봉 제공 한도)에 같은 규칙을 돌려 봅니다. 하루 1번, 첫 신호 다음 봉 시가에 사서 손절·목표·장마감 중 먼저 오는 것으로 청산합니다.")
        n_t = st.slider("검증 종목 수", 5, 30, 20, 5, key="dt_n", help="후보 티커 목록의 앞에서부터 이 개수만큼 검증합니다.")
        if st.button("🧪 단타 검증 실행", type="primary", key="dt_bt_go"):
            tick = list(dict.fromkeys(x.strip().upper() for x in st.session_state.get("dt_wl", " ".join(DT_DEFAULT)).replace(",", " ").split() if x.strip()))[:n_t]
            with st.spinner("5분봉 검증 중..."):
                data5 = load_intraday(tuple(tick), "1mo")
            allb = []
            for t, rw in data5.items():
                try:
                    bt5 = dt_backtest(dt_prepare(rw), dt_tgt)
                    if not bt5.empty:
                        bt5.insert(0, "종목", t)
                        allb.append(bt5)
                except Exception:
                    pass
            st.session_state["dt_bt"] = (pd.concat(allb, ignore_index=True) if allb else pd.DataFrame(), dt_tgt)
        Z = st.session_state.get("dt_bt")
        if Z:
            Bd, used = Z
            dt_stats(Bd, used)
            if not Bd.empty:
                g1, g2 = st.columns(2)
                g1.write("**셋업별**")
                g1.dataframe(Bd.groupby("셋업")["R"].agg(거래수="count", 승률=lambda s: (s > 0).mean() * 100, 평균R="mean").round(2))
                g2.write("**청산사유별**")
                g2.dataframe(Bd.groupby("청산")["R"].agg(거래수="count", 평균R="mean").round(2))
                st.write("**누적 R (거래 순서대로 더한 값, 우상향이면 규칙이 통했다는 뜻)**")
                st.line_chart(Bd.sort_values("날짜")["R"].cumsum().reset_index(drop=True))
                with st.expander("전체 거래 내역"):
                    st.dataframe(Bd, hide_index=True)
            st.warning("기간이 약 1개월로 짧고 수수료·슬리피지(체결 오차)·스프레드가 빠져 있어 실제보다 좋게 나옵니다. "
                       "단타는 비용 영향이 커서, 평균 R이 +0.2 이상은 되어야 의미가 있습니다. 먼저 소액으로 연습하세요.")
    st.info("⚠️ 단타 주의: ① 미국 증권사 마진계좌는 당일 매매 횟수 제한(PDT 규정, 계좌 $25,000 기준)이 있었고 규정이 바뀌는 중이므로 본인 증권사 안내를 확인하세요. "
            "② 손절은 미리 주문으로 걸어 두세요. ③ 하루 손실 한도(계좌의 1%)에 닿으면 그날은 끝냅니다.")

# ================================================================ 탭4: 쉬운 설명
with tab4:
    st.markdown("""
### 이 앱이 하는 일 (3줄 요약)
1. **오르는 중인 강한 종목만** 골라냅니다. (내 일목균형표 + 미국 성장주 추세 기준 8가지)
2. 그중 **지금 사도 되는 타이밍**(돌파 / 눌림목)인 종목에 🚀·🎯 표시를 합니다.
3. **손절가·목표가·살 수량**까지 알려줍니다.

### 8가지 상승 체력 (7개 이상 충족해야 후보)
| 구분 | 조건 | 쉬운 뜻 |
|---|---|---|
| 추세 | 종가 > 50일선 > 200일선 | 단기·장기 모두 오르는 중 |
| 추세 | 200일선 우상향 | 큰 흐름이 상승 |
| 일목 | 종가가 구름 위 | 구름이 지지대 |
| 일목 | 양운 | 구름이 상승 구조 |
| 일목 | 전환선 > 기준선 | 단기 힘이 더 강함 |
| 강세 | 52주 고점 20% 이내 | 신고가 근처, 위 매물 적음 |
| 주도주 | SPY보다 많이 오름 | 시장보다 강한 종목 |
| 자금 | 거래량 증가 | 돈이 들어오는 중 |

### 매수 타이밍 2가지
- 🚀 **돌파**: 최근 20일 고점을 평소의 1.3배 이상 거래량으로 넘음
- 🎯 **눌림목**: 오르던 종목이 21일선 근처까지 쉬었다가 양봉이 나옴 (손절폭이 작아 유리)

### 승률을 높이는 5가지 습관
1. **시장 신호등이 🔴이면 쉽니다.** 가장 효과가 큰 규칙입니다.
2. **A등급 + 🎯눌림목**부터 봅니다. (손절이 짧고 이미 오른 뒤 추격이 아님)
3. **이격이 10% 넘으면 사지 않습니다.** 다음 눌림을 기다립니다.
4. **손절가는 반드시 지킵니다.** 승률이 높아도 한 번의 큰 손실이 다 까먹습니다.
5. 한 종목에 계좌의 1%만 잃도록 수량을 정합니다. (종목 분석 탭 계산기)

### 승률 vs 수익, 꼭 알아둘 점
- 사이드바 **목표 수익 배수를 낮출수록 승률은 올라가지만** 이길 때 이익이 작아집니다.
- 그래서 '승률 검증' 탭의 **승률 + 거래당 기대수익**을 같이 보고 배수를 고르세요.
- 어떤 방법도 수익을 보장하지 않습니다. 앱은 '확률이 좋은 구간'을 찾아주는 도구입니다.

### 하루 사용법
시장 신호등 확인 → 🏆 추천 버튼 → A등급 🎯/🚀 종목 클릭해서 🔍 분석 탭에서 차트 확인 → 손절가 주문 걸고 매수
""")
    st.warning("교육·참고용 도구입니다. 투자 판단과 책임은 본인에게 있습니다.")

# ================================================================ 항목 사전
GLOSS = {
    "🚦 시장·상태·점수": [
        ("시장 신호등", "미국 대표지수(SPY)가 지금 오르는 장인지 보여주는 신호입니다. 🟢 50일선과 구름 모두 위, 🟡 50일선 위지만 구름 위는 아님, 🔴 50일선 아래.", "🔴이면 신규 매수를 쉬는 것이 승률에 가장 큰 도움이 됩니다."),
        ("상태: 매수후보", "상승 체력 조건을 충족하고 매수 타이밍(돌파 또는 눌림목) 신호까지 나온 종목.", "A·B등급부터 차트를 확인하세요."),
        ("상태: 대기", "오르는 중인 강한 종목이지만 아직 사기 좋은 타이밍은 아닌 종목.", "관심종목에 담고 눌림이나 돌파를 기다립니다."),
        ("등급 (A·B…)", "상승 체력과 타이밍을 종합한 등급입니다. A가 가장 우수합니다.", "A등급 + 🎯 눌림목 조합을 먼저 보세요."),
        ("점수", "종목끼리 순서를 매기기 위한 종합 점수. 높을수록 우선순위가 높습니다.", "점수 자체보다 '순서'를 보는 용도입니다."),
        ("RS (상대강도)", "최근 6개월 수익률을 다른 종목과 비교한 순위. 99에 가까울수록 최상위 주도주.", "RS가 높은 종목이 시장이 좋아질 때 먼저 오릅니다."),
    ],
    "💲 추천표의 가격 항목": [
        ("현재가", "가장 최근 확정 종가.", "장중이면 한 봉 전 종가일 수 있습니다."),
        ("손절가", "이 가격 아래로 내려가면 손해를 확정하고 나오는 기준선. 변동성(ATR)과 일목 기준선을 참고해 계산합니다.", "주문을 미리 걸어 두세요. 손절을 지키는 것이 승률 유지의 핵심입니다."),
        ("목표가", "손절폭의 정해진 배수만큼 올랐을 때의 가격 (사이드바 '목표 수익' 배수).", "배수가 낮을수록 빨리 닿아 승률↑, 건당 이익↓."),
        ("손절폭(%)", "현재가에서 손절가까지의 거리. 작을수록 같은 돈으로 더 안전하게 살 수 있습니다.", "손절폭이 클수록 수량을 줄여야 합니다."),
        ("이격(%)", "일목 기준선에서 현재가가 얼마나 위쪽으로 떨어져 있는지.", "10% 넘으면 추격 위험. 다음 눌림을 기다리세요."),
    ],
    "🎛 사이드바 설정": [
        ("검색할 종목 범위", "S&P500, 나스닥100, 중·소형주, 테마 성장주, ETF 중 검사할 묶음.", "처음엔 기본값으로 충분합니다."),
        ("추가 티커", "목록에 없는 종목을 직접 추가.", "예: PLTR, RKLB"),
        ("목표 수익 (손절폭의 몇 배)", "익절 목표를 정하는 배수 (1.0~3.0).", "승률을 우선하면 1.0~1.5, 수익을 우선하면 2.0~3.0."),
        ("최대 보유일", "승률 검증에서 이 날짜가 지나면 강제로 정리한다고 가정.", "스윙은 보통 2~4주(10~20일)."),
        ("시장이 50일선 위일 때만 매수", "시장이 나쁜 날 나온 신호를 제외하는 필터.", "켜 두는 것을 권장합니다."),
    ],
    "🧱 8가지 상승 체력": [
        ("① 종가 > 50일선 > 200일선", "단기·장기 평균가격보다 모두 위, 단기 평균이 장기 평균보다 높음.", "가장 기본적인 상승 추세 확인."),
        ("② 200일선 우상향", "200일 평균선 자체가 올라가는 중.", "큰 흐름이 상승일 때만 통과."),
        ("③ 종가가 구름 위", "일목 구름이 지지대 역할을 해 줍니다.", "구름 아래 종목은 반등이어도 약한 편."),
        ("④ 양운", "구름의 선행A가 선행B보다 위 = 구름이 상승 구조.", ""),
        ("⑤ 전환선 > 기준선", "단기 힘(9일)이 중기 힘(26일)보다 강함.", "예전 방식과 달리 '교차하는 순간'이 아니라 '위에 있는 상태'만 봅니다."),
        ("⑥ 52주 고점 20% 이내", "1년 최고가에 가까운 강한 종목.", "위쪽에 대기 매물이 적습니다."),
        ("⑦ 주도주", "3·6개월 수익률이 SPY보다 높음.", "시장보다 강한 종목만 골라냅니다."),
        ("⑧ 자금 유입", "최근 5일 거래량이 50일 평균 이상.", "돈이 들어오는 종목인지 확인."),
    ],
    "📐 기본 용어": [
        ("50일선·200일선", "최근 50일/200일 종가의 평균선. 각각 중기·장기 추세의 기준.", ""),
        ("일목 구름", "선행스팬 A·B 사이의 띠. 주가가 위에 있으면 상승, 아래면 약세로 봅니다.", "구름이 두꺼울수록 지지·저항이 강합니다."),
        ("전환선·기준선", "각각 9일·26일 고저 평균선. 전환선이 위면 단기 힘이 강합니다.", "기준선은 스윙의 대표적 손절 참고선입니다."),
        ("ATR", "최근 며칠 동안 하루 평균 몇 달러 움직였는지(평균 변동폭).", "손절폭을 종목 성격에 맞추는 데 씁니다."),
        ("🚀 돌파", "최근 20일 고점을 평소의 1.3배 이상 거래량으로 넘는 것.", "거래량이 없는 돌파는 가짜일 확률이 높습니다."),
        ("🎯 눌림목", "오르던 종목이 21일선 근처까지 쉬었다가 양봉으로 다시 오르는 자리.", "손절폭이 작아 유리하고 추격매수가 아닙니다."),
        ("R (손절폭 단위)", "손절폭 1개를 1R로 부릅니다. +2R = 손절폭의 2배 이익.", "결과를 종목·금액과 상관없이 비교할 수 있습니다."),
        ("1% 룰 (수량 계산)", "손절에 걸려도 계좌의 1%만 잃도록 수량을 정하는 방법.", "'종목 분석' 탭 계산기가 자동으로 해 줍니다."),
    ],
    "⚡ 단타 항목": [
        ("5분봉", "5분마다 하나씩 그려지는 캔들. 단타는 이 차트로 판단합니다.", ""),
        ("VWAP", "오늘 거래된 평균 체결단가(거래량 가중). 주황색 선.", "VWAP 위 = 오늘 산 사람 대부분이 이익 → 매수세 우위. 단타는 VWAP 위에서만 삽니다."),
        ("시초 30분 범위", "장 시작 후 30분(5분봉 6개)의 고점·저점. 차트의 회색 띠와 점선.", "이 범위를 위로 벗어나는지가 그날 방향의 힌트입니다."),
        ("🚀 시초 돌파", "시초 30분 고점을 거래량(RVOL 1.3배↑)과 함께 처음 넘고, VWAP·9EMA 위에서 마감한 봉.", "오전 10시~오후 3시(뉴욕) 사이에만 인정합니다."),
        ("🎯 VWAP 눌림", "오른 뒤 VWAP까지 내려왔다가 VWAP·9EMA 위로 올라오는 양봉.", "손절이 가까워 손익비가 좋습니다."),
        ("👀 / ⚪ / ⏳", "👀 VWAP 위에서 신호 대기, ⚪ VWAP 아래라 관망, ⏳ 시초 30분 범위 형성 중.", "👀 중 '추격 주의'는 이미 시초 고점을 넘어 올라간 상태입니다."),
        ("RVOL", "평소 같은 시각까지의 거래량 대비 오늘 거래량 배수.", "1.5배 이상이면 관심이 몰린 날, 1배 미만이면 힘이 약합니다."),
        ("갭(%)", "전일 종가 대비 오늘 시초가의 상승·하락률.", "+갭 + 높은 RVOL이 단타 후보의 기본 조합입니다."),
        ("9EMA", "최근 봉에 가중치를 둔 9봉 평균선(보라색). 단기 힘의 지표.", ""),
        ("손절·1R·목표", "손절 = 최근 6봉 저점 근처(5분봉 ATR의 1.5~2.5배로 제한). 1R = 손절폭만큼 상승한 가격, 목표 = 설정한 배수 가격.", "1R에서 절반 정리 후 손절을 본전으로 올리는 방식을 권합니다."),
        ("위험($/주)", "한 주당 손절까지의 금액.", "권장수량 = 감수 손실 ÷ 이 값."),
        ("권장수량", "계좌의 설정 비율(기본 0.3%)만 잃도록 계산한 주식 수.", "투자 가능 금액을 넘지 않도록 자동 제한됩니다."),
        ("당일 청산", "단타는 밤새 들고 가지 않고 장 마감 전에 정리합니다.", "뉴욕 15:45까지 전량 정리를 권장합니다."),
        ("PDT 규정", "미국 마진계좌의 당일 매매 횟수 제한 규정(계좌 $25,000 기준).", "규정이 바뀌는 중이라 증권사 공지를 꼭 확인하세요."),
    ],
    "🧪 승률 검증 용어": [
        ("거래 수", "규칙대로 매매했을 때의 총 거래 횟수.", "30회 미만이면 우연일 수 있습니다."),
        ("승률", "이익으로 끝난 거래 비율.", "승률만 높고 손실이 크면 결국 손해입니다."),
        ("평균 R / 거래당 기대수익", "한 번 거래할 때 평균적으로 얻는 결과.", "반드시 + 인지 확인하세요. 승률보다 더 중요합니다."),
        ("손익분기 승률", "목표 배수에 따라 본전이 되는 승률. 목표 1배면 50%, 1.5배면 40%.", "이보다 승률이 높아야 이득입니다."),
        ("청산사유", "손절 / 목표 / 기간만료(장마감) 중 어떤 이유로 끝났는지.", ""),
        ("누적 R", "거래 결과(R)를 순서대로 더한 곡선.", "우상향이면 규칙이 꾸준히 통했다는 뜻."),
        ("생존편향", "현재 살아남은 우량 종목만으로 과거를 검증해 결과가 좋게 나오는 착시.", "검증 결과는 실제보다 좋게 나온다고 생각하세요."),
        ("슬리피지", "주문가와 실제 체결가의 차이.", "단타는 비용 영향이 커서 반드시 감안해야 합니다."),
    ],
}

with tabG:
    st.subheader("📚 항목 사전 — 화면에 나오는 말의 뜻")
    kw = st.text_input("찾고 싶은 말 (예: VWAP, 손절, RS)", "", key="gl_kw").strip().lower()
    shown = 0
    for cat, items in GLOSS.items():
        hit = [x for x in items if kw in (x[0] + x[1] + x[2]).lower()]
        if not hit:
            continue
        shown += len(hit)
        with st.expander(cat, expanded=bool(kw)):
            for a_, b_, c_ in hit:
                st.markdown(f"**{a_}** — {b_}" + (f"  \n💡 {c_}" if c_ else ""))
    if kw and shown == 0:
        st.info("검색 결과가 없습니다. 다른 단어로 찾아보세요.")
