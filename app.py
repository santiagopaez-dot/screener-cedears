import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Screener CEDEARs", layout="wide")
st.title("Screener de CEDEARs: RSI y dividendos")
st.caption("Datos de NYSE/Nasdaq vía Yahoo Finance. Informativo, no es recomendación de inversión.")

TICKERS = ["AAPL", "TSLA", "NVDA", "MELI", "AMZN", "KO", "PEP", "JNJ", "MCD"]


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def señal(x):
    if x > 70: return "🔴 Sobrecompra"
    if x < 30: return "🟢 Sobreventa"
    return "⚪ Neutral"


@st.cache_data(ttl=3600)  # cachea 1 hora para no saturar Yahoo
def cargar(tickers):
    tickers = list(tickers)
    ajustado = yf.download(tickers, period="6mo", auto_adjust=True, progress=False)["Close"]
    real = yf.download(tickers, period="5d", auto_adjust=False, progress=False)["Close"].ffill().iloc[-1]

    corte = pd.Timestamp.today() - pd.DateOffset(years=1)
    filas = []
    for t in tickers:
        d = yf.Ticker(t).dividends
        if len(d) and d.index.tz is not None:
            d.index = d.index.tz_localize(None)
        ult12 = d[d.index > corte] if len(d) else d
        ttm = float(ult12.sum()) if len(ult12) else 0.0

        filas.append({
            "Ticker": t,
            "Precio USD": real[t],
            "RSI (14)": rsi(ajustado[t].dropna()).iloc[-1],
            "Div. 12m USD": ttm,
            "Yield 12m %": ttm / real[t] * 100,
        })

    tabla = pd.DataFrame(filas).set_index("Ticker")
    tabla["Señal RSI"] = tabla["RSI (14)"].apply(señal)
    return tabla.round(2), ajustado.index[-1].date()


def color_rsi(v):
    if v > 70: return "background-color: #ffcdd2"   # rojo: sobrecompra
    if v < 30: return "background-color: #c8e6c9"   # verde: sobreventa
    return ""


def color_yield(v):
    if pd.isna(v) or v == 0: return "background-color: #e0e0e0; color: #555"  # gris: no paga
    if v >= 6: return "background-color: #ffe0b2"   # naranja: muy alto, ojo
    if v >= 3: return "background-color: #c8e6c9"   # verde: alto
    if v >= 1.5: return "background-color: #fff9c4" # amarillo: medio
    return "background-color: #ffcdd2"              # rojo claro: bajo


tabla, fecha = cargar(tuple(TICKERS))
st.write(f"Última rueda con datos: **{fecha}**")

estilo = (
    tabla.style
    .map(color_rsi, subset=["RSI (14)"])
    .map(color_yield, subset=["Yield 12m %"])
    .format(precision=2, na_rep="-")
)
st.dataframe(estilo, width="stretch")

st.markdown(
    "**RSI:** 🔴 más de 70 sobrecompra · 🟢 menos de 30 sobreventa.  \n"
    "**Yield:** gris no paga · rojo <1,5% · amarillo 1,5-3% · verde 3-6% · naranja ≥6% (revisar por qué es tan alto).  \n"
    "El yield es bruto, sobre la acción en NY; el CEDEAR cobra en pesos y con retención en origen."
)
