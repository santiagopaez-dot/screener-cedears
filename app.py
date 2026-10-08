import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import timedelta

st.set_page_config(page_title="Panel de inversiones AR", layout="wide")
st.title("📊 Panel de inversiones: CEDEARs, FCI y renta fija")
st.caption("Versión resumida. Datos de Yahoo Finance (NY) y ArgentinaDatos. "
           "Informativo, no es recomendación de inversión.")

# Lista de ejemplo: confirmá en BYMA / tu broker cuáles tienen CEDEAR vigente.
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX", "AMD", "MELI",
    "KO", "PEP", "JNJ", "MCD", "WMT", "DIS", "JPM", "V", "XOM", "CVX",
    "PFE", "MRK", "BABA", "PLTR", "COIN", "INTC", "PYPL", "NKE", "BA", "VZ",
]


# ----------------------------------------------------------------------------
# Funciones de cálculo
# ----------------------------------------------------------------------------
def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def senal_rsi(x):
    if pd.isna(x):
        return "-"
    if x > 70:
        return "🔴 Sobrecompra"
    if x < 30:
        return "🟢 Sobreventa"
    return "⚪ Neutral"


def tea(tna, m):
    """TEA a partir de una TNA (decimal) con m capitalizaciones por año."""
    return (1 + tna / m) ** m - 1


def ytm(precio, tiempos, flujos):
    """TIR efectiva anual por bisección. tiempos en años, flujos por 100 VN."""
    tiempos = np.asarray(tiempos, dtype=float)
    flujos = np.asarray(flujos, dtype=float)

    def valor(y):
        return float(np.sum(flujos / (1 + y) ** tiempos))

    lo, hi = -0.95, 20.0
    if not (valor(hi) <= precio <= valor(lo)):
        return np.nan
    for _ in range(200):
        mid = (lo + hi) / 2
        if valor(mid) > precio:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def color_rsi(v):
    if pd.isna(v):
        return ""
    if v > 70:
        return "background-color: #ffcdd2"
    if v < 30:
        return "background-color: #c8e6c9"
    return ""


def color_yield(v):
    if pd.isna(v) or v == 0:
        return "background-color: #e0e0e0; color: #555"
    if v >= 6:
        return "background-color: #ffe0b2"
    if v >= 3:
        return "background-color: #c8e6c9"
    if v >= 1.5:
        return "background-color: #fff9c4"
    return "background-color: #ffcdd2"


# ----------------------------------------------------------------------------
# Datos (con caché para no saturar las fuentes)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner="Descargando precios de Nueva York...")
def precios(tickers):
    d = yf.download(list(tickers), period="1y", auto_adjust=True, progress=False)
    return d["Close"].ffill(), d["Volume"]


@st.cache_data(ttl=6 * 3600, show_spinner="Descargando dividendos...")
def dividendos_12m(tickers):
    corte = pd.Timestamp.today() - pd.DateOffset(years=1)
    out = {}
    for t in tickers:
        try:
            d = yf.Ticker(t).dividends
            if len(d) and d.index.tz is not None:
                d.index = d.index.tz_localize(None)
            out[t] = float(d[d.index > corte].sum()) if len(d) else 0.0
        except Exception:
            out[t] = np.nan
    return out


@st.cache_data(ttl=6 * 3600, show_spinner="Descargando datos fundamentales...")
def fundamentales(tickers):
    filas = []
    for t in tickers:
        try:
            i = yf.Ticker(t).info
            filas.append({"Ticker": t, "Sector": i.get("sector"),
                          "P/E": i.get("trailingPE"), "P/E futuro": i.get("forwardPE"),
                          "P/B": i.get("priceToBook")})
        except Exception:
            filas.append({"Ticker": t})
    df = pd.DataFrame(filas).set_index("Ticker")
    return df.reindex(columns=["Sector", "P/E", "P/E futuro", "P/B"])


API = "https://api.argentinadatos.com/v1/finanzas"
TIPOS_FCI = {"Mercado de dinero": "mercadoDinero", "Renta fija": "rentaFija",
             "Renta variable": "rentaVariable", "Renta mixta": "rentaMixta"}


@st.cache_data(ttl=3600, show_spinner=False)
def fci_dia(tipo, fecha):
    """fecha: 'ultimo' o un date. Devuelve DataFrame (vacío si no hay datos)."""
    path = fecha if isinstance(fecha, str) else fecha.strftime("%Y/%m/%d")
    r = requests.get(f"{API}/fci/{tipo}/{path}", timeout=25)
    r.raise_for_status()
    return pd.DataFrame(r.json())


def fci_cercano(tipo, objetivo):
    """Busca el día hábil con datos más cercano hacia atrás."""
    for k in range(8):
        try:
            df = fci_dia(tipo, objetivo - timedelta(days=k))
            if len(df):
                return df
        except Exception:
            continue
    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner="Armando ranking de FCI...")
def ranking_fci(tipo, dias):
    hoy = fci_dia(tipo, "ultimo")
    if hoy.empty:
        return pd.DataFrame()
    f_hoy = pd.to_datetime(hoy["fecha"]).max()
    antes = fci_cercano(tipo, f_hoy.date() - timedelta(days=dias))
    if antes.empty:
        return pd.DataFrame()
    m = hoy.merge(antes[["fondo", "vcp", "fecha"]], on="fondo", suffixes=("", "_ant"))
    m["dias_reales"] = (pd.to_datetime(m["fecha"]) - pd.to_datetime(m["fecha_ant"])).dt.days
    m = m[(m["dias_reales"] > 0) & (m["vcp_ant"] > 0) & (m["vcp"] > 0)].copy()
    m["Rend. período %"] = (m["vcp"] / m["vcp_ant"] - 1) * 100
    m["TNA equiv. %"] = m["Rend. período %"] * 365 / m["dias_reales"]
    m["Patrimonio (M)"] = m["patrimonio"] / 1e6
    return m


@st.cache_data(ttl=3600, show_spinner=False)
def riesgo_pais():
    r = requests.get(f"{API}/indices/riesgo-pais/ultimo", timeout=15)
    r.raise_for_status()
    return r.json()


# ----------------------------------------------------------------------------
# Pestañas
# ----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 CEDEARs: RSI y dividendos", "⚖️ ¿Cara o barata?", "🏦 Ranking FCI",
    "🧮 Simulador de tasas", "💵 Renta fija",
])

close, vol = precios(tuple(TICKERS))
close = close.dropna(axis=1, how="all")
tabla = pd.DataFrame({
    "Precio USD": close.iloc[-1],
    "Volatilidad %": close.pct_change().tail(60).std() * np.sqrt(252) * 100,
    "Volumen USD (M)": (close * vol[close.columns]).tail(30).mean() / 1e6,
    "RSI (14)": close.apply(rsi).iloc[-1],
})
divs = dividendos_12m(tuple(tabla.index))
tabla["Div. 12m USD"] = pd.Series(divs)
tabla["Yield 12m %"] = tabla["Div. 12m USD"] / tabla["Precio USD"] * 100
tabla["Señal RSI"] = tabla["RSI (14)"].apply(senal_rsi)
tabla.index.name = "Ticker"

# --- 1. CEDEARs --------------------------------------------------------------
with tab1:
    st.write(f"Última rueda con datos: **{close.index[-1].date()}**")
    c1, c2, c3 = st.columns(3)
    top = c1.slider("Mostrar las N más volátiles", 3, len(tabla), len(tabla))
    min_vol = c2.slider("Volumen mínimo diario (USD millones)", 0, 500, 0, step=10)
    filtro = c3.selectbox("Señal RSI", ["Todas", "Sobrecompra", "Sobreventa"])

    v = tabla[tabla["Volumen USD (M)"] >= min_vol].sort_values("Volatilidad %", ascending=False)
    if filtro == "Sobrecompra":
        v = v[v["RSI (14)"] > 70]
    elif filtro == "Sobreventa":
        v = v[v["RSI (14)"] < 30]
    v = v.head(top)

    st.dataframe(
        v.style.map(color_rsi, subset=["RSI (14)"])
        .map(color_yield, subset=["Yield 12m %"])
        .format(precision=2, na_rep="-"),
        width="stretch",
    )
    st.markdown(
        "**RSI:** 🔴 >70 sobrecompra · 🟢 <30 sobreventa. "
        "**Yield:** gris no paga · rojo <1,5% · amarillo 1,5–3% · verde 3–6% · naranja ≥6% (revisar por qué es tan alto).  \n"
        "Volatilidad: desvío de retornos diarios de 60 ruedas, anualizado. "
        "El yield es bruto, sobre la acción en NY; el CEDEAR cobra en pesos y con retención en origen."
    )

# --- 2. Cara o barata --------------------------------------------------------
with tab2:
    st.subheader("Valuación relativa dentro de la lista")
    f = fundamentales(tuple(tabla.index))
    val = tabla[["Precio USD"]].join(f)
    val["Posición rango 52 sem. %"] = (
        (close.iloc[-1] - close.min()) / (close.max() - close.min()) * 100
    )
    val["Dist. a media 200r %"] = (close.iloc[-1] / close.tail(200).mean() - 1) * 100

    pe_ok = val["P/E"].where(val["P/E"] > 0)
    med = pe_ok.groupby(val["Sector"]).transform("median")
    n_sec = pe_ok.groupby(val["Sector"]).transform("count")
    val["P/E vs sector"] = (pe_ok / med).where(n_sec >= 2)

    def veredicto(r):
        if pd.isna(r["P/E"]) or r["P/E"] <= 0:
            return "Sin P/E (pérdidas o sin dato)"
        if pd.isna(r["P/E vs sector"]):
            return "Sin comparables"
        if r["P/E vs sector"] < 0.8:
            return "🟢 Barata vs sector"
        if r["P/E vs sector"] > 1.2:
            return "🔴 Cara vs sector"
        return "⚪ En línea"

    val["Veredicto"] = val.apply(veredicto, axis=1)
    st.dataframe(val.round(2), width="stretch")
    st.info(
        "Esto es una comparación **relativa**: el P/E de cada acción contra la mediana de su sector "
        "dentro de esta lista (barata <0,8× · cara >1,2×). No es un valor intrínseco. "
        "Una acción puede ser 'barata' porque el mercado espera que sus ganancias caigan."
    )

# --- 3. FCI -----------------------------------------------------------------
with tab3:
    st.subheader("Ranking de Fondos Comunes de Inversión")
    c1, c2, c3 = st.columns(3)
    tipo_n = c1.selectbox("Categoría", list(TIPOS_FCI))
    dias = c2.selectbox("Período", [30, 90, 180, 365], index=1, format_func=lambda x: f"{x} días")
    min_pat = c3.number_input("Patrimonio mínimo (millones)", min_value=0, value=1000, step=500)
    try:
        r = ranking_fci(TIPOS_FCI[tipo_n], dias)
        if r.empty:
            st.warning("No se pudieron armar datos para ese período.")
        else:
            r = r[r["Patrimonio (M)"] >= min_pat].sort_values("Rend. período %", ascending=False)
            cols = ["fondo", "horizonte", "Rend. período %", "TNA equiv. %", "Patrimonio (M)", "fecha"]
            st.dataframe(
                r[cols].head(30).rename(columns={"fondo": "Fondo", "horizonte": "Horizonte", "fecha": "Dato al"})
                .reset_index(drop=True).style.format(precision=2, na_rep="-"),
                width="stretch",
            )
    except Exception as e:
        st.error(f"No se pudo consultar la API de FCI ahora: {e}")
    st.caption("Fuente: CNV vía ArgentinaDatos. Rendimiento pasado no garantiza resultados futuros. "
               "Puede haber fondos en dólares mezclados: no comparar directo con fondos en pesos.")

# --- 4. Simulador -----------------------------------------------------------
with tab4:
    st.subheader("Simulador de rentabilidad: la capitalización importa")
    c1, c2, c3, c4 = st.columns(4)
    monto = c1.number_input("Monto inicial", min_value=0.0, value=1_000_000.0, step=100_000.0)
    tna = c2.number_input("TNA %", min_value=0.0, value=30.0, step=1.0) / 100
    plazo = c3.number_input("Plazo (días)", min_value=1, value=365, step=30)
    infl = c4.number_input("Inflación mensual esperada %", min_value=0.0, value=2.0, step=0.5) / 100

    FREC = {"Diaria": 365, "Mensual": 12, "Trimestral": 4, "Semestral": 2, "Anual": 1}
    filas = [{
        "Capitalización": "Sin capitalizar (interés simple)",
        "TEA %": ((1 + tna * plazo / 365) ** (365 / plazo) - 1) * 100,
        "Capital final": monto * (1 + tna * plazo / 365),
    }]
    for nombre, m in FREC.items():
        filas.append({"Capitalización": nombre, "TEA %": tea(tna, m) * 100,
                      "Capital final": monto * (1 + tna / m) ** (m * plazo / 365)})
    sim = pd.DataFrame(filas)
    sim["Ganancia"] = sim["Capital final"] - monto
    sim["Rend. período %"] = sim["Ganancia"] / monto * 100 if monto else 0
    inflacion = (1 + infl) ** (plazo / 30) - 1
    sim["Rend. real %"] = ((1 + sim["Rend. período %"] / 100) / (1 + inflacion) - 1) * 100

    st.dataframe(sim.style.format(precision=2), width="stretch", hide_index=True)
    st.caption(f"Inflación acumulada estimada en {plazo} días: {inflacion * 100:.1f}%. "
               "TEA = (1 + TNA/m)^m − 1. Con 30% de TNA: mensual ≈ 34,5% de TEA, diaria ≈ 35,0%. "
               "Con plazos que no son múltiplos exactos del período, es una aproximación.")

    dias_x = np.arange(0, int(plazo) + 1)
    graf = pd.DataFrame({
        "Simple": monto * (1 + tna * dias_x / 365),
        "Capit. mensual": monto * (1 + tna / 12) ** (12 * dias_x / 365),
        "Capit. diaria": monto * (1 + tna / 365) ** dias_x,
    }, index=dias_x)
    graf.index.name = "Días"
    st.line_chart(graf)

# --- 5. Renta fija ----------------------------------------------------------
with tab5:
    st.subheader("Renta fija: deuda pública y privada")
    try:
        rp = riesgo_pais()
        st.metric("Riesgo país (puntos básicos)", rp.get("valor"), help=f"Dato al {rp.get('fecha')}")
    except Exception:
        st.caption("Riesgo país no disponible en este momento.")

    modo = st.radio("Instrumento", ["Letra / cupón cero (Lecap, etc.)", "Bono u ON con cupones"], horizontal=True)

    if modo.startswith("Letra"):
        c1, c2, c3 = st.columns(3)
        precio = c1.number_input("Precio de compra (por 100 VN)", min_value=0.01, value=105.0, step=0.5)
        pago = c2.number_input("Pago al vencimiento (por 100 VN)", min_value=0.01, value=110.0, step=0.5)
        d = c3.number_input("Días al vencimiento", min_value=1, value=90, step=1)
        rend = pago / precio - 1
        teaz = (pago / precio) ** (365 / d) - 1
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rendimiento al vto.", f"{rend * 100:.2f}%")
        m2.metric("TNA (simple)", f"{rend * 365 / d * 100:.2f}%")
        m3.metric("TEA", f"{teaz * 100:.2f}%")
        m4.metric("TEM", f"{((1 + teaz) ** (30 / 365) - 1) * 100:.2f}%")
        st.caption("Cargá el pago al vencimiento (capital + intereses) que figura en la ficha de la letra.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        precio = c1.number_input("Precio con intereses corridos (por 100 VN)", min_value=0.01, value=95.0, step=0.5)
        cupon = c2.number_input("Cupón anual % (TNA)", min_value=0.0, value=8.0, step=0.25)
        f_pag = c3.selectbox("Pagos por año", [1, 2, 4, 12], index=1)
        anios = c4.number_input("Años al vencimiento", min_value=0.1, value=3.0, step=0.25)

        n = int(np.ceil(anios * f_pag - 1e-9))
        tiempos = [anios - (n - i) / f_pag for i in range(1, n + 1)]
        flujos = [cupon / f_pag] * n
        flujos[-1] += 100.0

        tir = ytm(precio, tiempos, flujos)
        if np.isnan(tir):
            st.warning("No se pudo calcular la TIR con esos datos.")
        else:
            pv = np.array(flujos) / (1 + tir) ** np.array(tiempos)
            dur = float((np.array(tiempos) * pv).sum() / pv.sum())
            m1, m2, m3 = st.columns(3)
            m1.metric("TIR (TEA)", f"{tir * 100:.2f}%")
            m2.metric("Rendimiento corriente", f"{cupon / precio * 100:.2f}%")
            m3.metric("Duración (años)", f"{dur:.2f}")
        with st.expander("Ver flujos de fondos"):
            st.dataframe(pd.DataFrame({"Años desde hoy": np.round(tiempos, 2), "Flujo por 100 VN": flujos}),
                         hide_index=True)
        st.caption("Modelo simple: amortización al final (bullet) y precio sucio. "
                   "Los bonos que amortizan por partes necesitan el cronograma real de pagos.")
    st.warning("La TIR en dólares (bonos y ONs hard dollar) no se compara directo con tasas en pesos.")

st.divider()
st.caption("Proyecto personal con fines informativos. No constituye asesoramiento financiero ni recomendación de inversión.")
