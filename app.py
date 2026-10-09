import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import re
import unicodedata
import requests
from datetime import timedelta

st.set_page_config(page_title="Panel de inversiones AR", layout="wide")
st.title("📊 Panel de inversiones: CEDEARs, FCI y renta fija")
st.caption("Versión resumida. Datos de Yahoo Finance (NY) y ArgentinaDatos. "
           "Informativo, no es recomendación de inversión.")

# Lista de ejemplo: confirmá en BYMA / tu broker cuáles tienen CEDEAR vigente.
# ticker: (nombre, sector)
INFO = {
    "AAPL": ("Apple", "Tecnología"), "MSFT": ("Microsoft", "Tecnología"),
    "NVDA": ("NVIDIA", "Tecnología"), "AMD": ("AMD", "Tecnología"),
    "PLTR": ("Palantir", "Tecnología"), "INTC": ("Intel", "Tecnología"),
    "GOOGL": ("Alphabet (Google)", "Comunicación"), "META": ("Meta Platforms", "Comunicación"),
    "NFLX": ("Netflix", "Comunicación"), "DIS": ("Walt Disney", "Comunicación"),
    "VZ": ("Verizon", "Comunicación"),
    "AMZN": ("Amazon", "Consumo discrecional"), "TSLA": ("Tesla", "Consumo discrecional"),
    "MELI": ("MercadoLibre", "Consumo discrecional"), "MCD": ("McDonald's", "Consumo discrecional"),
    "BABA": ("Alibaba", "Consumo discrecional"), "NKE": ("Nike", "Consumo discrecional"),
    "KO": ("Coca-Cola", "Consumo básico"), "PEP": ("PepsiCo", "Consumo básico"),
    "WMT": ("Walmart", "Consumo básico"),
    "JNJ": ("Johnson & Johnson", "Salud"), "PFE": ("Pfizer", "Salud"), "MRK": ("Merck", "Salud"),
    "JPM": ("JPMorgan Chase", "Financiero"), "V": ("Visa", "Financiero"),
    "COIN": ("Coinbase", "Financiero"), "PYPL": ("PayPal", "Financiero"),
    "XOM": ("Exxon Mobil", "Energía"), "CVX": ("Chevron", "Energía"),
    "BA": ("Boeing", "Industriales"),
}
TICKERS = list(INFO)

# Parámetros fijos (no se muestran en pantalla)
RSI_BAJO, RSI_ALTO = 30, 70      # verde (sobreventa) / rojo (sobrecompra)
MIN_VOLUMEN_USD_M = 100          # volumen mínimo diario en NY: descarta CEDEARs con poca liquidez


# ----------------------------------------------------------------------------
# Funciones de cálculo
# ----------------------------------------------------------------------------
def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


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


def color_rsi(v, lo=30, hi=70):
    if pd.isna(v):
        return ""
    if v < lo:
        return "background-color: #a5d6a7; font-weight: 600"
    if v > hi:
        return "background-color: #ef9a9a; font-weight: 600"
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


@st.cache_data(ttl=300, show_spinner="Descargando datos intradiarios...")
def rsi_45m(tickers):
    """RSI(14) sobre velas de 45 min, armadas agrupando de a 3 velas de 15 min por rueda."""
    d = yf.download(list(tickers), period="1mo", interval="15m", auto_adjust=True, progress=False)["Close"]
    out, ultima = {}, None
    for t in d.columns:
        s = d[t].dropna()
        if len(s) < 60:
            out[t] = np.nan
            continue
        # Yahoo puede entregar la hora en UTC: se pasa siempre a hora de Nueva York
        idx = s.index.tz_localize("UTC") if s.index.tz is None else s.index
        s.index = idx.tz_convert("America/New_York")
        dia = np.array(s.index.date)
        # Bloque de 45 min según la hora (9:30 NY = 570 min), no por conteo de velas:
        # así, si Yahoo omite una vela de 15 min, el resto no se desfasa.
        minutos = s.index.hour * 60 + s.index.minute - 570
        bloque = np.asarray(minutos // 45)
        c45 = s.groupby([dia, bloque]).last()
        out[t] = float(rsi(c45).iloc[-1])
        ultima = s.index[-1] if ultima is None or s.index[-1] > ultima else ultima
    return pd.Series(out), ultima


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
    # TEA: rendimiento anualizado CON capitalización (comparable entre fondos y con otras tasas)
    m["TEA %"] = ((m["vcp"] / m["vcp_ant"]) ** (365 / m["dias_reales"]) - 1) * 100
    m["Patrimonio (M)"] = m["patrimonio"] / 1e6
    return m


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def serie_deposito_30d():
    """Serie de tasas de depósitos a 30 días (promedio de bancos, BCRA): DataFrame con fecha y TNA %."""
    r = requests.get(f"{API}/tasas/depositos30Dias", timeout=20)
    r.raise_for_status()
    df = pd.DataFrame(r.json()).dropna()
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["valor"] = df["valor"].astype(float)
    df["tna"] = np.where(df["valor"] > 1, df["valor"], df["valor"] * 100)   # puede venir en % o fracción
    return df.sort_values("fecha")[["fecha", "tna"]].reset_index(drop=True)


def tea_de_tna30(tna_pct):
    """TEA % de un plazo fijo a 30 días con esa TNA % (interés simple a 30 días, luego reinvertido)."""
    return ((1 + tna_pct / 100 * 30 / 365) ** (365 / 30) - 1) * 100


def tna30_de_tea(tea_pct):
    """TNA % de un plazo fijo a 30 días que rendiría lo mismo que esa TEA %."""
    return ((1 + tea_pct / 100) ** (30 / 365) - 1) * 365 / 30 * 100


def norm_nombre(x):
    """Clave para emparejar nombres de fondos: sin tildes, minúsculas, solo letras y números."""
    x = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", x.lower())


@st.cache_data(ttl=6 * 3600, show_spinner="Cargando detalle de los fondos...")
def detalle_fondos():
    """Todos los fondos con cartera, rescate, mínimo y honorarios (CNV vía ArgentinaDatos)."""
    r = requests.get(f"{API}/fci/fondos", timeout=60)
    r.raise_for_status()
    js = r.json()
    lista = js.get("fondos", []) if isinstance(js, dict) else js
    return {norm_nombre(f.get("nombre", "")): f for f in lista}


def buscar_fondo(dic, nombre):
    k = norm_nombre(nombre)
    if k in dic:
        return dic[k]
    cand = [v for kk, v in dic.items() if k and kk and (k in kk or kk in k)]
    return cand[0] if len(cand) == 1 else None


def mostrar_detalle(f):
    st.markdown(f"#### {f.get('nombre', 'Fondo')}")
    st.caption(" · ".join(str(x) for x in [f.get("administradora"), f.get("tipoRenta"),
                                           f.get("moneda"), f.get("region")] if x))
    plazo, minimo = f.get("plazoLiquidacionDias"), f.get("inversionMinima")
    c = st.columns(4)
    c[0].metric("Rescate", "-" if plazo is None else ("Mismo día" if plazo == 0 else f"{plazo} día(s)"))
    c[1].metric("Inversión mínima", "-" if minimo is None else f"{minimo:,.0f} {f.get('monedaInversion') or ''}".strip())
    c[2].metric("Horizonte", f.get("horizonte") or "-")
    c[3].metric("Duración", f.get("duracion") or "-")

    comp = pd.DataFrame(f.get("composicionCartera") or [])
    if comp.empty or "porcentaje" not in comp:
        st.info("El fondo no informa la composición de su cartera.")
    else:
        comp = comp.sort_values("porcentaje", ascending=False).reset_index(drop=True)
        if comp["porcentaje"].sum() <= 1.5:          # viene como fracción
            comp["porcentaje"] = comp["porcentaje"] * 100
        st.markdown("**En qué invierte** (según lo informado a la CNV)")
        st.dataframe(
            comp.rename(columns={"nombre": "Activo", "porcentaje": "Porcentaje"}),
            width="stretch", hide_index=True,
            column_config={"Porcentaje": st.column_config.ProgressColumn(
                "Porcentaje", min_value=0, max_value=100, format="%.1f%%")},
        )
    hon = {k: v for k, v in (f.get("honorarios") or {}).items() if v}
    if hon:
        with st.expander("Honorarios y comisiones (tal como los informa la CNV)"):
            st.dataframe(pd.DataFrame({"Concepto": list(hon), "Valor": list(hon.values())}),
                         hide_index=True, width="stretch")
    cal = f.get("calificaciones") or []
    if cal:
        st.caption("Calificaciones: " + " · ".join(
            f"{x.get('calificadora', '')}: {x.get('calificacion', '')}" for x in cal))


@st.cache_data(ttl=3600, show_spinner=False)
def riesgo_pais():
    r = requests.get(f"{API}/indices/riesgo-pais/ultimo", timeout=15)
    r.raise_for_status()
    return r.json()


# ----------------------------------------------------------------------------
# Pestañas
# ----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 CEDEARs: Trading (RSI)", "💰 CEDEARs: Dividendos y ¿cara o barata?", "🏦 Ranking FCI",
    "🧮 Simulador de tasas", "💵 Renta fija",
])

close, vol = precios(tuple(TICKERS))
close = close.dropna(axis=1, how="all")
tabla = pd.DataFrame({
    "Nombre": [INFO[t][0] for t in close.columns],
    "Sector": [INFO[t][1] for t in close.columns],
    "Precio USD": close.iloc[-1].values,
    "Volatilidad %": (close.pct_change().tail(60).std() * np.sqrt(252) * 100).values,
    "Volumen USD (M)": ((close * vol[close.columns]).tail(30).mean() / 1e6).values,
    "RSI diario": close.apply(rsi).iloc[-1].values,
}, index=close.columns)
tabla.index.name = "Ticker"

try:
    r45, ult_intra = rsi_45m(tuple(tabla.index))
    tabla["RSI 45 min"] = r45.reindex(tabla.index)
except Exception:
    ult_intra = None
    tabla["RSI 45 min"] = np.nan

# --- 1. CEDEARs: trading ------------------------------------------------------
with tab1:
    st.subheader("Trading: RSI diario y de 45 minutos")
    txt = f"Datos diarios al **{close.index[-1].date()}**"
    if ult_intra is not None:
        txt += f" · intradiario hasta **{ult_intra:%d/%m %H:%M}** (hora de Nueva York)"
    else:
        txt += " · RSI de 45 min no disponible ahora"
    st.write(txt)

    lo, hi = RSI_BAJO, RSI_ALTO
    c1, c2 = st.columns(2)
    vol_min = c1.slider("Volatilidad mínima % (descarta las que casi no se mueven)", 0, 100, 30, step=5)
    filtro = c2.selectbox("Mostrar", ["Todas", "Solo sobreventa (RSI verde)", "Solo sobrecompra (RSI rojo)"])

    t = tabla[(tabla["Volatilidad %"] >= vol_min) & (tabla["Volumen USD (M)"] >= MIN_VOLUMEN_USD_M)]
    if filtro.startswith("Solo sobreventa"):
        t = t[(t["RSI diario"] < lo) | (t["RSI 45 min"] < lo)]
    elif filtro.startswith("Solo sobrecompra"):
        t = t[(t["RSI diario"] > hi) | (t["RSI 45 min"] > hi)]

    cols_t = ["Nombre", "Precio USD", "Volatilidad %", "RSI diario", "RSI 45 min"]
    cols_rsi = ["RSI diario", "RSI 45 min"]
    st.caption(f"{len(t)} de {len(tabla)} CEDEARs pasan los filtros, agrupados por sector.")
    for sector in sorted(t["Sector"].unique()):
        sub = t[t["Sector"] == sector].sort_values("Volatilidad %", ascending=False)[cols_t]
        with st.expander(f"{sector} ({len(sub)})", expanded=True):
            st.dataframe(
                sub.style
                .map(lambda v: color_rsi(v, lo, hi), subset=cols_rsi)
                .format(precision=1, na_rep="-", subset=cols_rsi)
                .format(precision=2, na_rep="-", subset=["Precio USD", "Volatilidad %"]),
                width="stretch",
            )
    st.markdown(
        "**RSI:** 🟢 verde = sobreventa (menor a 30) · 🔴 rojo = sobrecompra (mayor a 70).  \n"
        "**RSI 45 min:** velas de 45 minutos armadas desde datos de 15 min (datos de Yahoo, pueden tener demora). "
        "Sirve para operar en el día; fuera del horario de NY muestra la última rueda.  \n"
        "**Volatilidad:** desvío de retornos diarios de 60 ruedas, anualizado. Descartar las de baja volatilidad evita "
        "activos que casi no se mueven y dan pocas señales."
    )

# --- 2. CEDEARs: dividendos + cara o barata -----------------------------------
with tab2:
    st.subheader("Dividendos (largo plazo) y valuación")
    f = fundamentales(tuple(tabla.index))
    divs = dividendos_12m(tuple(tabla.index))
    val = tabla[["Nombre", "Sector", "Precio USD", "Volumen USD (M)"]].copy()
    val["Div. 12m USD"] = pd.Series(divs)
    val["Yield 12m %"] = val["Div. 12m USD"] / val["Precio USD"] * 100
    val = val.join(f[["P/E", "P/E futuro"]])
    val["Posición rango 52 sem. %"] = (close.iloc[-1] - close.min()) / (close.max() - close.min()) * 100

    # Mediana de P/E por sector, calculada sobre toda la lista (antes de filtrar)
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

    solo_pagan = st.checkbox("Solo las que pagan dividendos", value=True)

    v = val[val["Volumen USD (M)"] >= MIN_VOLUMEN_USD_M]
    if solo_pagan:
        v = v[v["Yield 12m %"] > 0]

    cols_v = ["Nombre", "Precio USD", "Div. 12m USD", "Yield 12m %",
              "P/E", "P/E vs sector", "Posición rango 52 sem. %", "Veredicto"]
    st.caption(f"{len(v)} de {len(val)} CEDEARs pasan los filtros, agrupados por sector.")
    for sector in sorted(v["Sector"].unique()):
        sub = v[v["Sector"] == sector].sort_values("Yield 12m %", ascending=False)[cols_v]
        with st.expander(f"{sector} ({len(sub)})", expanded=True):
            st.dataframe(
                sub.style.map(color_yield, subset=["Yield 12m %"]).format(precision=2, na_rep="-"),
                width="stretch",
            )
    st.markdown(
        "**Yield:** gris no paga · rojo <1,5% · amarillo 1,5–3% · verde 3–6% · naranja ≥6% (revisar por qué es tan alto). "
        "Es bruto, sobre la acción en NY; el CEDEAR cobra en pesos y con retención en origen.  \n"
        "**¿Cara o barata?** Compara el P/E contra la mediana de su sector en esta lista (barata <0,8× · cara >1,2×). "
        "Es una comparación **relativa**, no un valor intrínseco: una acción puede ser barata porque se esperan ganancias menores."
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
            r = r[r["Patrimonio (M)"] >= min_pat].sort_values("Rend. período %", ascending=False).copy()
            r["Equiv. TNA plazo fijo 30d %"] = tna30_de_tea(r["TEA %"])
            cols = ["fondo", "horizonte", "Rend. período %", "TEA %", "Equiv. TNA plazo fijo 30d %"]
            try:
                serie = serie_deposito_30d()
                f_fin = pd.to_datetime(r["fecha"]).max()
                ventana = serie[(serie["fecha"] > f_fin - timedelta(days=dias)) & (serie["fecha"] <= f_fin)]
                if ventana.empty:
                    ventana = serie.tail(1)
                tna_ref = float(ventana["tna"].mean())
                tea_ref = tea_de_tna30(tna_ref)
                r["TEA vs referencia (p.p.)"] = r["TEA %"] - tea_ref
                cols.append("TEA vs referencia (p.p.)")
                st.info(f"Referencia: depósitos a 30 días (promedio de bancos, BCRA), promedio de los últimos {dias} días "
                        f"hasta el {f_fin.date()}: TNA {tna_ref:.1f}% = TEA {tea_ref:.1f}%. "
                        "Un fondo con 'TEA vs referencia' positiva rindió más que depositar a plazo fijo en ese mismo período.")
            except Exception:
                st.caption("Tasa de referencia no disponible en este momento.")
            cols += ["Patrimonio (M)", "fecha"]
            mostrar = (r[cols].head(30)
                       .rename(columns={"fondo": "Fondo", "horizonte": "Horizonte", "fecha": "Dato al"})
                       .reset_index(drop=True))
            ev = st.dataframe(
                mostrar.style.format(precision=2, na_rep="-"),
                width="stretch", on_select="rerun", selection_mode="single-row",
                key=f"fci_{tipo_n}_{dias}_{min_pat}",
            )
            filas_sel = ev.selection.rows if ev is not None else []
            if not filas_sel:
                st.caption("Marcá la casilla a la izquierda de un fondo para ver en qué invierte, su plazo de rescate, la inversión mínima y los honorarios.")
            else:
                nombre_sel = mostrar.loc[filas_sel[0], "Fondo"]
                try:
                    f_det = buscar_fondo(detalle_fondos(), nombre_sel)
                    if f_det is None:
                        st.info(f"No encontré el detalle de «{nombre_sel}» en la base de fondos.")
                    else:
                        mostrar_detalle(f_det)
                except Exception as e:
                    st.warning(f"No se pudo cargar el detalle del fondo: {e}")
    except Exception as e:
        st.error(f"No se pudo consultar la API de FCI ahora: {e}")
    st.caption("Fuente: CNV vía ArgentinaDatos. **Rend. período** es la variación real de la cuotaparte (ya incluye la "
               "capitalización). **TEA** lo anualiza con interés compuesto, así que es comparable entre fondos y con otras "
               "tasas; la TNA no lo es. En fondos de renta fija y variable, anualizar períodos cortos exagera: el valor "
               "sube y baja. 'Equiv. TNA plazo fijo' dice qué TNA a 30 días daría lo mismo que el fondo, para compararlo con "
               "lo que ofrece un banco. Rendimiento pasado no garantiza resultados futuros. Puede haber fondos en dólares mezclados: "
               "no comparar directo con fondos en pesos.")

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
