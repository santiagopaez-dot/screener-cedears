import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import re
import json
import altair as alt
import unicodedata
import requests
from pathlib import Path
from datetime import date, timedelta

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


def color_roe(v):
    if pd.isna(v):
        return ""
    if v >= 15:
        return "background-color: #c8e6c9"
    if v >= 8:
        return "background-color: #fff9c4"
    return "background-color: #ffcdd2"


def color_deuda(v):
    if pd.isna(v):
        return ""
    if v <= 2:
        return "background-color: #c8e6c9"
    if v <= 4:
        return "background-color: #fff9c4"
    return "background-color: #ffcdd2"


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
            roe, deuda, ebitda = i.get("returnOnEquity"), i.get("totalDebt"), i.get("ebitda")
            filas.append({"Ticker": t, "Sector": i.get("sector"),
                          "P/E": i.get("trailingPE"), "P/E futuro": i.get("forwardPE"),
                          "P/B": i.get("priceToBook"),
                          "ROE %": roe * 100 if roe is not None else None,
                          "Deuda/EBITDA": deuda / ebitda if deuda and ebitda and ebitda > 0 else None})
        except Exception:
            filas.append({"Ticker": t})
    df = pd.DataFrame(filas).set_index("Ticker")
    return df.reindex(columns=["Sector", "P/E", "P/E futuro", "P/B", "ROE %", "Deuda/EBITDA"])


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
    COMISIONES = {
        "honorarioGerente": ("Honorario de la administradora", "% anual sobre el patrimonio del fondo; se descuenta día a día del valor de la cuotaparte"),
        "honorarioDepositaria": ("Honorario de la depositaria (custodia)", "% anual sobre el patrimonio; se descuenta del valor de la cuotaparte"),
        "gastosOrdinariosGestion": ("Gastos ordinarios de gestión", "% anual sobre el patrimonio; se descuenta del valor de la cuotaparte"),
        "comisionIngreso": ("Comisión de ingreso", "% del monto que suscribís, se cobra al entrar"),
        "comisionEgreso": ("Comisión de rescate (egreso)", "% del monto que rescatás, se cobra al salir"),
        "comisionTransferencia": ("Comisión de transferencia", "Se cobra al transferir cuotapartes a otro agente"),
        "comisionExito": ("Comisión de éxito", "% sobre el rendimiento que supera un objetivo, si el reglamento lo prevé"),
        "otros": ("Otros", "Ver el reglamento de gestión del fondo"),
    }
    hon = {k: v for k, v in (f.get("honorarios") or {}).items() if v}
    if hon:
        with st.expander("Honorarios y comisiones: cómo se cobran"):
            filas = [{"Concepto": COMISIONES.get(k, (k, ""))[0], "Valor": f"{v:g}%",
                      "Cómo se cobra": COMISIONES.get(k, (k, ""))[1]} for k, v in hon.items()]
            st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
            st.caption("Los honorarios anuales **ya están descontados** del rendimiento que muestra la tabla: "
                       "no se cobran aparte ni hay que restarlos de nuevo. Se pagan siempre, haya ganancia o pérdida. "
                       "Las comisiones de ingreso y rescate, en cambio, se pagan una vez, al entrar o salir. "
                       "Valores tal como los informa la CNV; suelen ser topes del reglamento y lo realmente cobrado "
                       "puede ser menor. Confirmalo en el reglamento de gestión.")
    cal = f.get("calificaciones") or []
    if cal:
        st.caption("Calificaciones: " + " · ".join(
            f"{x.get('calificadora', '')}: {x.get('calificacion', '')}" for x in cal))


# ----------------------------------------------------------------------------
# Indicadores macro: tarjetas KPI, inflación y dólar MEP histórico
# ----------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def kpis_macro():
    out = {}
    try:   # dólar MEP (casa "bolsa") y CCL: cotización actual de DolarApi
        r = requests.get("https://dolarapi.com/v1/dolares", timeout=15)
        r.raise_for_status()
        for x in r.json():
            try:
                if x.get("casa") in ("bolsa", "contadoconliqui"):
                    out[x["casa"]] = float(x.get("venta") or x.get("compra"))
            except Exception:
                continue
    except Exception:
        pass
    try:   # riesgo país con variación diaria
        r = requests.get(f"{API}/indices/riesgo-pais", timeout=20)
        r.raise_for_status()
        d = pd.DataFrame(r.json()).dropna()
        d["fecha"] = pd.to_datetime(d["fecha"])
        d = d.sort_values("fecha")
        out["rp"] = (float(d["valor"].iloc[-1]), float(d["valor"].iloc[-1] - d["valor"].iloc[-2]))
    except Exception:
        pass
    try:   # índices de EE.UU. y Merval
        idx = yf.download(["^GSPC", "^IXIC", "^DJI", "^MERV"], period="5d", auto_adjust=True, progress=False)["Close"]
        for sym in idx.columns:
            h = idx[sym].dropna()
            if len(h) >= 2:
                out[sym] = (float(h.iloc[-1]), float((h.iloc[-1] / h.iloc[-2] - 1) * 100))
        if "^MERV" in out and "contadoconliqui" in out:
            out["merv_usd"] = out["^MERV"][0] / out["contadoconliqui"]   # Merval en dólares CCL
    except Exception:
        pass
    return out


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def mep_hist():
    r = requests.get("https://api.argentinadatos.com/v1/cotizaciones/dolares/bolsa", timeout=30)
    r.raise_for_status()
    d = pd.DataFrame(r.json())
    col = "venta" if "venta" in d else "compra"
    d["fecha"] = pd.to_datetime(d["fecha"])
    return d.sort_values("fecha")[["fecha", col]].rename(columns={col: "mep"}).dropna().reset_index(drop=True)


def mep_en(d, fecha):
    sub = d[d["fecha"] <= fecha]
    return float(sub["mep"].iloc[-1]) if len(sub) else np.nan


OBJ = ["Ver todo", "Guardar plata a corto plazo", "Ganarle a la inflación"]


def selector_objetivo(key):
    obj = st.radio("¿Qué querés ver?", OBJ, horizontal=True, key=key)
    corto, infl = obj == OBJ[1], obj == OBJ[2]
    if corto:
        st.info("**Corto plazo:** muestra fondos de mercado de dinero (30 días) y letras que vencen pronto. Las cauciones todavía no están "
                "cargadas. Es un filtro informativo, no una recomendación: un fondo de mercado de dinero no garantiza rendimiento y una letra "
                "solo devuelve lo prometido si la mantenés hasta el vencimiento.")
    elif infl:
        st.info("**Inflación:** muestra lo que rinde por encima de la inflación **esperada** (la del REM del BCRA, que podés cambiar). "
                "Los bonos CER (indexados) todavía no están cargados. Es un filtro informativo: lo que pasó no garantiza lo que va a pasar.")
    return corto, infl


def _plano(x):
    return unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower()


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def rem_inflacion():
    """Inflación esperada anual según el último REM del BCRA. Devuelve (valor % anual o None, nota o None)."""
    try:
        r = requests.get(f"{API}/rem/ultimo", timeout=25)
        r.raise_for_status()
        d = pd.DataFrame(r.json())
        if d.empty or "indicador" not in d:
            return None, None
        ind = d["indicador"].map(_plano)
        ipc = d[ind.str.contains("precios minoristas|ipc", regex=True) & ~ind.str.contains("nucleo|core|subyacente", regex=True)].copy()
        if ipc.empty:
            return None, None
        vacio = pd.Series("", index=ipc.index)
        per = ipc["periodo"].map(_plano) if "periodo" in ipc else vacio
        uni = ipc["unidad"].map(_plano) if "unidad" in ipc else vacio
        informe = str(ipc["informe"].iloc[0]) if "informe" in ipc else ""
        med = pd.to_numeric(ipc["mediana"], errors="coerce") if "mediana" in ipc else pd.Series(np.nan, index=ipc.index)
        anual = ipc[per.str.contains("12 meses") & ~uni.str.contains("mensual") & med.notna()]
        if len(anual):
            v = float(med[anual.index[0]])
            v = v * 100 if v < 3 else v
            return v, f"Según el REM ({informe}), la inflación esperada para los próximos 12 meses es **{v:.1f}%** (mediana de los analistas)."
        mens = ipc[uni.str.contains("mensual") & med.notna()]
        if len(mens):
            m = float(med[mens.index[:3]].mean())
            v = ((1 + m / 100) ** 12 - 1) * 100
            return v, (f"Según el REM ({informe}), la inflación mensual esperada ronda **{m:.1f}%** (mediana, próximos meses), "
                       f"equivalente a unos **{v:.0f}%** anual.")
    except Exception:
        pass
    return None, None


# ----------------------------------------------------------------------------
# Simulador de cartera: valor diario, rendimiento ajustado por aportes (TWR) y TIR del dinero (XIRR)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner="Descargando precios de la cartera...")
def precios_cartera(tickers, inicio):
    d = yf.download(list(tickers), start=inicio, auto_adjust=False, progress=False)["Close"]
    if isinstance(d, pd.Series):
        d = d.to_frame(tickers[0])
    return d.ffill()


def calcular_cartera(ops, close, mep=None):
    """Operaciones posteriores al último día con precios (hoy, un fin de semana) se aplican con el último precio disponible.
    ops: Fecha, Operación (Compra/Venta/Depósito/Retiro/Cambio), Ticker, Cantidad, Monto, Moneda, Ticker destino (solo Cambio).
    close: precios diarios en USD por ticker. mep: Serie con pesos por dólar (opcional).
    Compras y ventas al cierre del día (o del primer día de mercado posterior)."""
    ops = ops.copy()
    ops["Fecha"] = pd.to_datetime(ops["Fecha"])
    idx = close.index[close.index >= ops["Fecha"].min()]
    if len(idx) == 0:                      # todas las operaciones son posteriores al último día con precios (fin de semana, feriado)
        idx = close.index[-1:]
    if mep is not None:
        mep = mep.reindex(mep.index.union(idx)).ffill().bfill().reindex(idx)
    qty = pd.DataFrame(0.0, index=idx, columns=close.columns)
    cash = pd.Series(0.0, index=idx)
    flujo = pd.Series(0.0, index=idx)
    for _, o in ops.sort_values("Fecha").iterrows():
        pos = min(idx.searchsorted(o["Fecha"]), len(idx) - 1)   # primer día de mercado en o después; si no hay, el último disponible
        d, tipo = idx[pos], o["Operación"]
        if tipo in ("Compra", "Venta"):
            sg = 1 if tipo == "Compra" else -1
            if o["Ticker"] not in close.columns:
                raise ValueError(f"No hay precios de {o['Ticker']}.")
            p = close.loc[d, o["Ticker"]]
            if pd.isna(p):
                raise ValueError(f"No hay precio de {o['Ticker']} el {d.date()}.")
            qty.loc[d:, o["Ticker"]] += sg * o["Cantidad"]
            cash.loc[d:] -= sg * o["Cantidad"] * p
        elif tipo == "Cambio":
            t1, t2 = o["Ticker"], o.get("Ticker destino")
            for t in (t1, t2):
                if t not in close.columns:
                    raise ValueError(f"No hay precios de {t}.")
            p1, p2 = close.loc[d, t1], close.loc[d, t2]
            if pd.isna(p1) or pd.isna(p2):
                raise ValueError(f"No hay precio de {t1} o {t2} el {d.date()}.")
            qty.loc[d:, t1] -= o["Cantidad"]
            qty.loc[d:, t2] += o["Cantidad"] * p1 / p2      # se compra con lo obtenido de la venta; el efectivo no cambia
        else:
            sg = 1 if tipo == "Depósito" else -1
            if o["Moneda"] == "USD":
                m = o["Monto"]
            elif mep is None:
                raise ValueError("Para operaciones en pesos hace falta el dólar MEP histórico, que no está disponible ahora.")
            else:
                m = o["Monto"] / mep.loc[d]
            cash.loc[d:] += sg * m
            flujo.loc[d] += sg * m
    out = pd.DataFrame({"valor_usd": cash + (qty * close.reindex(idx)).sum(axis=1), "flujo_usd": flujo, "efectivo_usd": cash})
    if mep is not None:
        out["mep"] = mep
        out["valor_ars"] = out["valor_usd"] * mep
        out["flujo_ars"] = out["flujo_usd"] * mep
    return out, qty


def retorno_diario(valor, flujo):
    """Retorno de cada día sin el efecto de los aportes: valor / (valor anterior + aporte del día) - 1."""
    base = valor.shift(1).fillna(0) + flujo
    return (valor / base - 1).where(base > 0, 0.0)


def xirr(fechas, flujos, valor_final, fecha_final):
    """TIR anual del dinero invertido (cada aporte pesa según cuánto tiempo estuvo invertido)."""
    t = np.array([(f - fechas[0]).days / 365 for f in fechas])
    tf = (fecha_final - fechas[0]).days / 365
    f = lambda r: -np.sum(np.asarray(flujos) / (1 + r) ** t) + valor_final / (1 + r) ** tf
    lo, hi = -0.99, 100.0
    if f(lo) * f(hi) > 0:
        return np.nan
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


# ----------------------------------------------------------------------------
# Renta fija: cronogramas (archivo del repo) y precios en vivo (data912)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_cronogramas():
    return json.loads((Path(__file__).parent / "cronogramas.json").read_text(encoding="utf-8"))


@st.cache_data(ttl=600, show_spinner="Descargando precios de letras, bonos y ONs...")
def precios_renta_fija():
    """Precio por símbolo desde data912 (no es tiempo real). Usa punto medio si el spread es chico, si no el último."""
    out, paneles_ok = {}, []
    for panel in ("arg_notes", "arg_bonds", "arg_corp"):
        try:
            r = requests.get(f"https://data912.com/live/{panel}", timeout=25)
            r.raise_for_status()
            for x in r.json():
                bid, ask, ult = x.get("px_bid") or 0, x.get("px_ask") or 0, x.get("c") or 0
                if bid > 0 and ask > 0 and ask / bid - 1 < 0.05:
                    px = (bid + ask) / 2
                else:
                    px = ult
                if px and px > 0:
                    out[x["symbol"]] = float(px)
            paneles_ok.append(panel)
        except Exception:
            pass
    return out, paneles_ok


def liquidacion():
    """Liquidación T+1: próximo día hábil (no contempla feriados)."""
    d = date.today() + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def metricas_flujos(precio, flujos, liq, reinv=0.04, n_cap=2, nom_cap="semestral"):
    fl = [(date.fromisoformat(f), m) for f, m in flujos if date.fromisoformat(f) > liq]
    if not fl:
        return None
    t = np.array([(f - liq).days / 365 for f, _ in fl])
    cf = np.array([m for _, m in fl])
    tir = ytm(precio, t, cf)
    if np.isnan(tir) or tir > 1.0:
        return None
    pv = cf / (1 + tir) ** t
    # TIR modificada: los cobros intermedios se reinvierten a una tasa explícita (reinv) hasta el vencimiento
    T = t[-1]
    vf = float(np.sum(cf * (1 + reinv) ** (T - t)))
    tirm = (vf / precio) ** (1 / T) - 1
    # Días para recuperar: fecha del primer pago en que lo cobrado acumulado alcanza el precio pagado
    acum = np.cumsum(cf)
    idx = np.argmax(acum >= precio) if (acum >= precio).any() else None
    return {"TIR (TEA) %": tir * 100,
            f"TNA (cap. {nom_cap}) %": n_cap * ((1 + tir) ** (1 / n_cap) - 1) * 100,
            "TIR modificada %": tirm * 100,
            "Duración (años)": float((t * pv).sum() / pv.sum()),
            "Duración modificada": float((t * pv).sum() / pv.sum()) / (1 + tir),
            "Días para recuperar": (fl[idx][0] - liq).days if idx is not None else np.nan,
            "Días al vto.": (fl[-1][0] - liq).days,
            "Próximo pago": str(fl[0][0]), "Vencimiento": str(fl[-1][0])}


def tabla_bonos(filas, flujos_por_id, key, liq, aviso_vacio):
    if not filas:
        st.warning(aviso_vacio)
        return
    df = pd.DataFrame(filas).sort_values("Vencimiento").reset_index(drop=True)
    st.info("**Para ver las fechas de pago de un instrumento:** marcá la casilla a la izquierda de su nombre. "
            "Abajo aparece cuánto paga y cuándo, por cada 100 de valor nominal.")
    ev = st.dataframe(df.style.format(precision=2, na_rep="-"), width="stretch",
                      on_select="rerun", selection_mode="single-row", key=key)
    sel = ev.selection.rows if ev is not None else []
    if sel:
        ident = df.loc[sel[0], "Instrumento"]
        fl = [(f, m) for f, m in flujos_por_id[ident] if date.fromisoformat(f) > liq]
        st.markdown(f"**Fechas de pago de {ident}**")
        st.dataframe(pd.DataFrame({
            "Fecha de pago": [f for f, _ in fl],
            "Pago por 100 VN": [m for _, m in fl],
            "Días desde la liquidación": [(date.fromisoformat(f) - liq).days for f, _ in fl],
        }), hide_index=True, width="stretch")
        st.caption("Para bonos que amortizan, cada pago mezcla cupón y devolución de capital.")


# ----------------------------------------------------------------------------
# Pestañas
# ----------------------------------------------------------------------------
k = kpis_macro()


def tarjeta(col, titulo, clave, formato, delta_fmt=None, ayuda=None):
    v = k.get(clave)
    if v is None:
        col.metric(titulo, "-")
    elif isinstance(v, tuple):
        col.metric(titulo, formato.format(v[0]), delta_fmt.format(v[1]) if delta_fmt else None, help=ayuda)
    else:
        col.metric(titulo, formato.format(v), help=ayuda)


f1 = st.columns(4)
tarjeta(f1[0], "Dólar MEP", "bolsa", "$ {:,.0f}")
tarjeta(f1[1], "Dólar CCL", "contadoconliqui", "$ {:,.0f}")
if "rp" in k:
    f1[2].metric("Riesgo país", f"{k['rp'][0]:,.0f} pb", f"{k['rp'][1]:+.0f} pb", delta_color="inverse",
                 help="Variación respecto de la rueda anterior. Si sube, el mercado ve más riesgo (en rojo).")
else:
    f1[2].metric("Riesgo país", "-")
tarjeta(f1[3], "Merval en USD (CCL)", "merv_usd", "US$ {:,.0f}", ayuda="Merval en pesos dividido el dólar CCL de hoy.")
f2 = st.columns(4)
tarjeta(f2[0], "S&P 500", "^GSPC", "{:,.0f}", "{:+.2f}%")
tarjeta(f2[1], "Nasdaq", "^IXIC", "{:,.0f}", "{:+.2f}%")
tarjeta(f2[2], "Dow Jones", "^DJI", "{:,.0f}", "{:+.2f}%")
tarjeta(f2[3], "Merval (en pesos)", "^MERV", "{:,.0f}", "{:+.2f}%")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 CEDEARs: Trading (RSI)", "💰 CEDEARs: Dividendos y ¿cara o barata?", "🏦 Ranking FCI",
    "🧮 Simulador de tasas", "💵 Renta fija", "💼 Simulador de cartera",
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
    val = val.join(f[["P/E", "P/E futuro", "ROE %", "Deuda/EBITDA"]])
    val.loc[val["Sector"] == "Financiero", "Deuda/EBITDA"] = np.nan   # no aplica a bancos y financieras
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
              "P/E", "P/E vs sector", "ROE %", "Deuda/EBITDA", "Posición rango 52 sem. %", "Veredicto"]
    st.caption(f"{len(v)} de {len(val)} CEDEARs pasan los filtros, agrupados por sector.")
    for sector in sorted(v["Sector"].unique()):
        sub = v[v["Sector"] == sector].sort_values("Yield 12m %", ascending=False)[cols_v]
        with st.expander(f"{sector} ({len(sub)})", expanded=True):
            st.dataframe(
                sub.style.map(color_yield, subset=["Yield 12m %"]).map(color_roe, subset=["ROE %"])
                .map(color_deuda, subset=["Deuda/EBITDA"]).format(precision=2, na_rep="-"),
                width="stretch",
            )
    st.markdown(
        "**Yield:** gris no paga · rojo <1,5% · amarillo 1,5–3% · verde 3–6% · naranja ≥6% (revisar por qué es tan alto). "
        "Es bruto, sobre la acción en NY; el CEDEAR cobra en pesos y con retención en origen.  \n"
        "**ROE %** (ganancia sobre el patrimonio de los accionistas): 🟢 15% o más · 🟡 entre 8% y 15% · 🔴 menos de 8% o negativo. "
        "Un patrimonio muy chico (por recompras de acciones) lo infla.  \n"
        "**Deuda/EBITDA** (años de ganancia operativa para pagar la deuda): 🟢 hasta 2 · 🟡 entre 2 y 4 · 🔴 más de 4. "
        "No se muestra para el sector financiero, donde no aplica. Los cortes son convenciones generales: varían por sector.  \n"
        "**¿Cara o barata?** Compara el P/E contra la mediana de su sector en esta lista (barata <0,8× · cara >1,2×). "
        "Es una comparación **relativa**, no un valor intrínseco: una acción puede ser barata porque se esperan ganancias menores."
    )

# --- 3. FCI -----------------------------------------------------------------
with tab3:
    st.subheader("Ranking de Fondos Comunes de Inversión")
    modo_corto, modo_infl = selector_objetivo("obj_fci")
    rem_val, rem_nota = rem_inflacion()
    c1, c2, c3, c4 = st.columns(4)
    tipo_n = c1.selectbox("Categoría", ["Mercado de dinero"] if modo_corto else list(TIPOS_FCI))
    dias = c2.selectbox("Período", [30, 90, 180, 365], index=0 if modo_corto else (3 if modo_infl else 1),
                        format_func=lambda x: f"{x} días")
    min_pat = c3.number_input("Patrimonio mínimo (millones)", min_value=0, value=1000, step=500)
    infl_esp = c4.number_input("Inflación esperada anual (%)", min_value=0.0, max_value=500.0,
                               value=float(round(rem_val, 1)) if rem_val else 25.0, step=0.5,
                               help="Se usa para calcular el rendimiento real esperado. Por defecto, la del REM del BCRA; podés poner la tuya.")
    st.caption(rem_nota if rem_nota else "No se pudo leer el REM: ingresá tu propia estimación de inflación anual.")
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
            r["TEA real vs infl. esperada %"] = ((1 + r["TEA %"] / 100) / (1 + infl_esp / 100) - 1) * 100
            cols.append("TEA real vs infl. esperada %")
            try:
                mep = mep_hist()
                ini, fin = pd.to_datetime(r["fecha_ant"]), pd.to_datetime(r["fecha"])
                var = {(a, b): mep_en(mep, b) / mep_en(mep, a) - 1 for a, b in set(zip(ini, fin))}
                r["Rend. en USD (MEP) %"] = [((1 + x / 100) / (1 + var[(a, b)]) - 1) * 100
                                             for x, a, b in zip(r["Rend. período %"], ini, fin)]
                cols.append("Rend. en USD (MEP) %")
            except Exception:
                st.caption("Dólar MEP histórico no disponible en este momento.")
            cols += ["Patrimonio (M)", "fecha"]
            if modo_infl:
                r = r[r["TEA real vs infl. esperada %"] > 0].sort_values("TEA real vs infl. esperada %", ascending=False)
                if r.empty:
                    st.info("Ningún fondo de esta categoría supera la inflación esperada con el rendimiento del período elegido.")
            mostrar = (r[cols].head(30)
                       .rename(columns={"fondo": "Fondo", "horizonte": "Horizonte", "fecha": "Dato al"})
                       .reset_index(drop=True))
            st.info("**Para ver en qué invierte un fondo:** marcá la casilla que está a la izquierda de su nombre. "
                    "Abajo de la tabla aparece su cartera, el plazo de rescate, la inversión mínima y las comisiones.")
            ev = st.dataframe(
                mostrar.style.format(precision=2, na_rep="-"),
                width="stretch", on_select="rerun", selection_mode="single-row",
                key=f"fci_{tipo_n}_{dias}_{min_pat}",
            )
            filas_sel = ev.selection.rows if ev is not None else []
            if filas_sel:
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
               "no comparar directo con fondos en pesos. 'TEA real vs infl. esperada' compara la TEA del fondo con la inflación "
               "esperada que figura arriba; 'Rend. en USD (MEP)' mide cuánto rindió en dólares en el período. Un valor positivo es ganancia real.")

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

# --- 5. Renta fija ----------------------------------------------------------
with tab5:
    st.subheader("Renta fija: deuda pública y privada")
    modo_corto, modo_infl = selector_objetivo("obj_rf")
    if modo_infl:
        rem_val2, rem_nota2 = rem_inflacion()
        infl_rf = st.number_input("Inflación esperada anual (%)", min_value=0.0, max_value=500.0,
                                  value=float(round(rem_val2, 1)) if rem_val2 else 25.0, step=0.5,
                                  help="Por defecto, la del REM del BCRA; podés poner la tuya.")
        st.caption(rem_nota2 if rem_nota2 else "No se pudo leer el REM: ingresá tu propia estimación de inflación anual.")
    st.caption("Precios en vivo de data912 (no es tiempo real). La TIR es lo que rinde el instrumento **si lo mantenés hasta el "
               "vencimiento y el emisor paga todo**; no es una predicción.")
    liq = liquidacion()
    c1, c2 = st.columns(2)
    CAPS = {"Mensual": 12, "Trimestral": 4, "Semestral": 2, "Anual": 1, "Diaria": 365}
    nom_cap = c1.selectbox("TNA de bonos y ONs con capitalización", list(CAPS), index=2,
                           help="La TNA es la misma tasa expresada con otra frecuencia de capitalización. Semestral es la convención de los bonos.")
    n_cap = CAPS[nom_cap]
    reinv = c2.number_input("Tasa de reinversión de los cobros intermedios (TEA %)", min_value=0.0, max_value=50.0,
                            value=4.0, step=0.5,
                            help="Se usa para la TIR modificada. Es un supuesto tuyo: ¿a qué tasa podrías reinvertir cupones y amortizaciones en dólares?") / 100
    with st.expander("¿Cómo leer las columnas?"):
        st.markdown(
            "- **TIR (TEA):** tasa efectiva anual que iguala el precio con todos los pagos descontados en su fecha. "
            "**Supone que lo que cobrás en el medio (cupones y amortizaciones) se reinvierte a esa misma tasa.**  \n"
            "- **TNA (cap. X):** *la misma* TIR expresada como tasa nominal anual con capitalización X. No es otro rendimiento, "
            "es otra forma de expresarlo: con TEA 10%, la TNA semestral es 9,76%.  \n"
            "- **TIR modificada:** corrige ese supuesto. Reinvierte los cobros intermedios a la tasa que elegís arriba. "
            "En bonos que amortizan, o con TIR muy alta, es más realista que la TIR.  \n"
            "- **Duración modificada:** cuánto cambia el precio, aproximadamente en %, si la TIR sube o baja 1 punto. "
            "Con duración modificada 3, una suba de 1 punto en la TIR baja el precio cerca de 3%. Es la medida de sensibilidad a la tasa.  \n"
            "- **Duración (años):** plazo promedio ponderado en que cobrás el dinero. En bonos que amortizan es menor que el plazo al vencimiento.  \n"
            "- **Días para recuperar:** días hasta el primer pago en que lo cobrado acumulado (sin descontar) iguala lo que pagaste. "
            "Vacío si nunca lo recuperás con los pagos que quedan.  \n"
            "- **Días al vto.:** días desde la liquidación hasta el **último** pago del instrumento.  \n"
            "- En **letras** hay un solo pago, así que días para recuperar y días al vencimiento son lo mismo.")
    sub_l, sub_s, sub_o, sub_m = st.tabs(["Letras (pesos)", "Bonos soberanos (USD)", "ONs (USD)", "Calculadora manual"])
    try:
        crono = cargar_cronogramas()
        px, paneles = precios_renta_fija()
        hay_datos = True
    except Exception as e:
        hay_datos = False
        st.warning(f"No se pudieron cargar los datos de instrumentos: {e}")

    if hay_datos:
        if not paneles:
            st.warning("No se pudo conectar con la fuente de precios (data912) en este momento.")
        st.caption(f"Cronogramas de pago actualizados al **{crono['actualizado']}** (archivo cronogramas.json del repositorio). "
                   f"Liquidación estimada: {liq:%d/%m/%Y} (T+1, sin contar feriados).")

        with sub_l:
            if modo_corto:
                tope = st.slider("Mostrar letras que vencen en hasta (días)", 7, 90, 30)
            filas = []
            for l in crono["letras"]:
                p = px.get(l["ticker"])
                dias = (date.fromisoformat(l["vencimiento"]) - liq).days
                if not p or dias <= 0:
                    continue
                rend = l["pago_final"] / p - 1
                filas.append({"Instrumento": l["ticker"], "Vencimiento": l["vencimiento"], "Días": dias, "Precio": p,
                              "Pago final": l["pago_final"], "Rend. al vto. %": rend * 100,
                              "TNA %": rend * 365 / dias * 100, "TEA %": ((1 + rend) ** (365 / dias) - 1) * 100,
                              "TEM %": ((1 + rend) ** (30 / dias) - 1) * 100})
            if modo_corto:
                filas = [f for f in filas if f["Días"] <= tope]
            if modo_infl:
                for f in filas:
                    f["TEA real vs infl. esperada %"] = ((1 + f["TEA %"] / 100) / (1 + infl_rf / 100) - 1) * 100
                st.caption(f"Se compara la TEA de cada letra con una inflación esperada de {infl_rf:.1f}% anual. Las letras son a tasa fija: "
                           "si la inflación real termina por encima de ese número, el rendimiento real es menor.")
            tabla_bonos(filas, {f["Instrumento"]: [(f["Vencimiento"], f["Pago final"])] for f in filas},
                        "rf_letras", liq, "No hay precios disponibles para las letras cargadas.")
            st.caption(f"{len(filas)} de {len(crono['letras'])} letras con precio. Si falta una letra reciente, hay que agregarla "
                       "a cronogramas.json (ticker, vencimiento y pago final por 100).")

        with sub_s:
            filas, flujos = [], {}
            for k, v in ({} if modo_corto else crono["soberanos"]).items():
                p = px.get(k + "D")
                m = metricas_flujos(p, v["flujos"], liq, reinv, n_cap, nom_cap.lower()) if p else None
                if m:
                    filas.append({"Instrumento": k, "Ley": v["ley"], "Precio USD": p, **m})
                    flujos[k] = v["flujos"]
            tabla_bonos(filas, flujos, "rf_sob", liq, "En el modo corto plazo no se muestran bonos: sus plazos son largos y su precio varía." if modo_corto else "No hay precios disponibles para los bonos soberanos.")
            if modo_infl:
                st.caption("Estos bonos están en dólares y a tasa fija: no están indexados por CER.")
            st.caption("Precio en dólares MEP (símbolo terminado en D), por 100 de valor nominal original. "
                       "La TIR usa el precio de pantalla sin ajustar intereses corridos.")

        with sub_o:
            filas, flujos = [], {}
            for k, v in ({} if modo_corto else crono["ons"]).items():
                p = px.get(v["precio_ticker"])
                m = metricas_flujos(p, v["flujos"], liq, reinv, n_cap, nom_cap.lower()) if p else None
                if m:
                    filas.append({"Instrumento": k, "Emisor": v["nombre"], "Precio USD": p, **m})
                    flujos[k] = v["flujos"]
            tabla_bonos(filas, flujos, "rf_ons", liq, "En el modo corto plazo no se muestran ONs: sus plazos son largos y su precio varía." if modo_corto else "No hay precios disponibles para las ONs cargadas.")
            if modo_infl:
                st.caption("Estas ONs están en dólares y a tasa fija: no están indexadas por CER.")
            st.caption("Las ONs con poca operación pueden tener precios poco representativos: mirá el spread y el volumen "
                       "en tu broker antes de usar la TIR. La TIR usa el precio de pantalla sin ajustar intereses corridos.")

    with sub_m:

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

# --- 6. Simulador de cartera ---------------------------------------------------
COLS_OPS = ["Fecha", "Operación", "Ticker", "Cantidad", "Monto", "Moneda", "Ticker destino"]


def preparar_ops(ed):
    ops = ed.copy()
    for c in COLS_OPS:
        if c not in ops:
            ops[c] = None
    ops = ops.dropna(subset=["Fecha", "Operación"])
    for c in ("Ticker", "Ticker destino"):
        ops[c] = ops[c].fillna("").astype(str).str.upper().str.strip()
    ops["Moneda"] = ops["Moneda"].fillna("USD")
    for c in ("Cantidad", "Monto"):
        ops[c] = pd.to_numeric(ops[c], errors="coerce")
    trade = ops["Operación"].isin(["Compra", "Venta"])
    cambio = ops["Operación"] == "Cambio"
    plata = ops["Operación"].isin(["Depósito", "Retiro"])
    mala = ((trade & ((ops["Ticker"] == "") | ~(ops["Cantidad"] > 0)))
            | (cambio & ((ops["Ticker"] == "") | (ops["Ticker destino"] == "") | ~(ops["Cantidad"] > 0)))
            | (plata & ~(ops["Monto"] > 0)))
    return ops[~mala], int(mala.sum())


with tab6:
    st.subheader("Simulador de cartera")
    st.caption("Registrá tus movimientos y mirá cómo evoluciona la cartera en dólares y en pesos. El rendimiento (TWR) **no se infla ni se "
               "achica por los depósitos y retiros**: mide qué hizo la cartera con el dinero que tenía cada día. Tus datos no se guardan en "
               "la página: descargá el CSV del historial para conservarlos.")
    hoy = date.today()
    if "cart_ops" not in st.session_state:
        d150, d90, d45 = hoy - timedelta(days=150), hoy - timedelta(days=90), hoy - timedelta(days=45)
        st.session_state.cart_ops = pd.DataFrame([
            [d150, "Depósito", "", None, 3000.0, "USD", ""], [d150, "Compra", "AAPL", 8.0, None, "USD", ""],
            [d150, "Compra", "KO", 20.0, None, "USD", ""], [d90, "Depósito", "", None, 1500000.0, "ARS", ""],
            [d90, "Compra", "MSFT", 2.0, None, "USD", ""], [d45, "Retiro", "", None, 300.0, "USD", ""],
        ], columns=COLS_OPS)
        st.session_state.cart_ver = 0

    c_form, c_res, c_hist = st.container(), st.container(), st.container()

    # ---- Historial (se dibuja al final de la página, pero se lee primero) ----
    with c_hist:
        st.markdown("### Historial de movimientos")
        st.caption("Es el **registro de todo lo que hiciste**, en orden. Podés corregir una fila, borrarla (seleccionala y apretá Supr) o "
                   "agregar una a mano. La **tenencia actual** de arriba es el resultado de aplicar todos estos movimientos.")
        up = st.file_uploader("Cargar un historial guardado (CSV)", type="csv", key="cart_up")
        if up is not None and st.session_state.get("cart_up_name") != up.name:
            try:
                nuevo_df = pd.read_csv(up)
                nuevo_df["Fecha"] = pd.to_datetime(nuevo_df["Fecha"]).dt.date
                st.session_state.cart_ops = nuevo_df.reindex(columns=COLS_OPS)
                st.session_state.cart_up_name = up.name
                st.session_state.cart_ver += 1
                st.rerun()
            except Exception:
                st.warning("No se pudo leer el CSV. Tiene que tener las columnas: " + ", ".join(COLS_OPS) + ".")
        ed = st.data_editor(
            st.session_state.cart_ops, num_rows="dynamic", width="stretch", key=f"cart_ed_{st.session_state.cart_ver}",
            column_config={
                "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "Operación": st.column_config.SelectboxColumn("Operación", options=["Depósito", "Retiro", "Compra", "Venta", "Cambio"], required=True,
                                                              help="Cambio: vende 'Ticker' y compra 'Ticker destino' con lo obtenido."),
                "Ticker": st.column_config.TextColumn("Ticker", help="Compras, ventas y cambios (el que se vende)."),
                "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, format="%.4f"),
                "Monto": st.column_config.NumberColumn("Monto", min_value=0.0, help="Para depósitos y retiros."),
                "Moneda": st.column_config.SelectboxColumn("Moneda del monto", options=["USD", "ARS"]),
                "Ticker destino": st.column_config.TextColumn("Cambia por", help="Solo para 'Cambio': la acción que se compra."),
            })
        st.session_state.cart_ops = ed
        st.download_button("Descargar historial (CSV)", ed.to_csv(index=False).encode("utf-8"), "historial_cartera.csv", "text/csv")

    # ---- Cálculo ----
    ops, n_malas = preparar_ops(ed)
    res = qty = close = None
    error = None
    tickers = sorted(set(ops.loc[ops["Operación"].isin(["Compra", "Venta", "Cambio"]), "Ticker"])
                     | set(ops.loc[ops["Operación"] == "Cambio", "Ticker destino"]))
    if not ops.empty and tickers:
        try:
            inicio = (pd.to_datetime(ops["Fecha"]).min() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
            close = precios_cartera(tuple(tickers), inicio)
            faltan = [t for t in tickers if t not in close.columns or close[t].dropna().empty]
            if faltan:
                error = f"No encontré precios para: {', '.join(faltan)}. Usá el ticker de Nueva York (ej. AAPL)."
            else:
                try:
                    mep = mep_hist().set_index("fecha")["mep"]
                except Exception:
                    mep = None
                res, qty = calcular_cartera(ops, close, mep)
        except ValueError as e:
            error = str(e)
        except Exception as e:
            error = f"No se pudo calcular la cartera: {e}"
    ult_qty = qty.iloc[-1] if qty is not None else pd.Series(dtype=float)
    tenidas = [t for t in ult_qty.index if ult_qty[t] > 1e-9]

    # ---- Formulario para registrar movimientos ----
    with c_form:
        st.markdown("### Agregar un movimiento")
        tipo = st.radio("¿Qué querés hacer?", ["Depositar dinero", "Retirar dinero", "Comprar acciones", "Vender acciones",
                                               "Cambiar una acción por otra"], horizontal=True, key="cart_tipo")
        fila, falta = None, None
        with st.form("cart_form", clear_on_submit=True):
            fch = st.date_input("Fecha", value=hoy, max_value=hoy, format="DD/MM/YYYY")
            g1, g2 = st.columns(2)
            if tipo in ("Depositar dinero", "Retirar dinero"):
                monto = g1.number_input("Monto", min_value=0.0, step=100.0)
                mon = g2.selectbox("Moneda", ["USD", "ARS"])
            elif tipo == "Comprar acciones":
                tk = g1.text_input("Ticker (de Nueva York)", placeholder="Ej: TSLA")
                cant = g2.number_input("Cantidad", min_value=0.0, step=1.0)
                st.caption("Se compra al precio de cierre del día. Si no tenés efectivo suficiente, primero depositá dinero.")
            elif tipo == "Vender acciones":
                tk = g1.selectbox("Acción que vendés", tenidas or ["(no tenés acciones)"])
                cant = g2.number_input("Cantidad", min_value=0.0, step=1.0,
                                       help=f"Tenés {ult_qty.get(tk, 0):,.4f}" if tenidas else None)
            else:
                tk = g1.selectbox("Vendo", tenidas or ["(no tenés acciones)"])
                cant = g2.number_input("Cantidad que vendo", min_value=0.0, step=1.0)
                tk2 = st.text_input("Compro (ticker)", placeholder="Ej: TSLA")
                st.caption("La compra se hace con lo que se obtiene de la venta, a los precios de cierre del día. "
                           "Después de agregarlo, la tenencia actual ya aparece cambiada.")
            enviar = st.form_submit_button("Agregar movimiento")
        if enviar:
            base = {"Fecha": fch, "Moneda": "USD"}
            if tipo in ("Depositar dinero", "Retirar dinero"):
                if monto > 0:
                    fila = {**base, "Operación": "Depósito" if tipo.startswith("Dep") else "Retiro", "Monto": monto, "Moneda": mon}
                else:
                    falta = "Ingresá un monto mayor a 0."
            elif tipo == "Comprar acciones":
                if tk.strip() and cant > 0:
                    fila = {**base, "Operación": "Compra", "Ticker": tk.strip().upper(), "Cantidad": cant}
                else:
                    falta = "Ingresá el ticker y una cantidad mayor a 0."
            elif tipo == "Vender acciones":
                if tk in tenidas and cant > 0:
                    fila = {**base, "Operación": "Venta", "Ticker": tk, "Cantidad": cant}
                else:
                    falta = "Elegí una acción que tengas e ingresá una cantidad mayor a 0."
            else:
                if tk in tenidas and cant > 0 and tk2.strip():
                    fila = {**base, "Operación": "Cambio", "Ticker": tk, "Cantidad": cant, "Ticker destino": tk2.strip().upper()}
                else:
                    falta = "Elegí la acción que vendés, la cantidad y el ticker de la que comprás."
            if tipo in ("Vender acciones", "Cambiar una acción por otra") and fila and cant > ult_qty.get(tk, 0) + 1e-9:
                st.warning(f"Estás vendiendo más de lo que tenés hoy de {tk} ({ult_qty.get(tk, 0):,.4f}). Se agrega igual; revisá la fecha.")
            if falta:
                st.error(falta)
            elif fila:
                nueva = pd.DataFrame([{c: fila.get(c) for c in COLS_OPS}])
                st.session_state.cart_ops = pd.concat([ed, nueva], ignore_index=True)
                st.session_state.cart_ver += 1
                st.session_state.cart_msg = "Movimiento agregado. La tenencia actual ya lo incluye."
                st.rerun()

    # ---- Resultados ----
    with c_res:
        if st.session_state.get("cart_msg"):
            st.success(st.session_state.pop("cart_msg"))
        if n_malas:
            st.error(f"{n_malas} fila(s) incompletas del historial se ignoran: las compras, ventas y cambios necesitan ticker y cantidad; "
                     "los depósitos y retiros, un monto.")
        if error:
            st.error(error)
        elif res is None:
            st.info("Cargá al menos un depósito y una compra para ver los resultados.")
        else:
            if (res["efectivo_usd"] < -0.01).any():
                st.warning("En algún momento compraste más de lo que tenías en efectivo (efectivo negativo). Agregá un depósito antes de esa compra, "
                           "o el rendimiento va a reflejar dinero que no pusiste.")
            if (qty < -1e-9).any().any():
                st.warning("Hay ventas por más acciones de las que tenías.")

            st.markdown(f"### Tenencia actual (al {res.index[-1]:%d/%m/%Y})")
            st.caption("Lo que tenés **hoy**, después de aplicar todos los movimientos del historial.")
            px_ult = close.reindex(res.index).iloc[-1]
            ten = pd.DataFrame({"Cantidad": ult_qty, "Precio USD": px_ult[ult_qty.index], "Valor USD": ult_qty * px_ult[ult_qty.index]})
            ten = ten[ten["Cantidad"].abs() > 1e-9]
            ten.loc["Efectivo (USD)"] = [np.nan, np.nan, res["efectivo_usd"].iloc[-1]]
            ten["% de la cartera"] = ten["Valor USD"] / ten["Valor USD"].sum() * 100
            ten.index.name = "Activo"
            h1, h2 = st.columns([2, 3])
            torta = ten[ten["Valor USD"] > 0.005].reset_index()
            if not torta.empty:
                torta["Etiqueta"] = torta["% de la cartera"].map(lambda x: f"{x:.1f}%")
                arco = alt.Chart(torta).encode(
                    theta=alt.Theta("Valor USD:Q", stack=True), color=alt.Color("Activo:N", legend=alt.Legend(title=None, orient="bottom")),
                    tooltip=["Activo", alt.Tooltip("Valor USD:Q", format=",.2f"), "Etiqueta"])
                grafico = (arco.mark_arc(innerRadius=35) + arco.mark_text(radius=82, size=12).encode(text="Etiqueta:N")).properties(height=280)
                h1.altair_chart(grafico, width="stretch")
            h2.dataframe(ten.style.format(precision=2, na_rep="-"), width="stretch")

            def resumen(v, f):
                r = retorno_diario(v, f)
                fl = f[f != 0]
                tir = xirr(list(fl.index), list(fl.values), v.iloc[-1], v.index[-1]) if len(fl) and (v.index[-1] - fl.index[0]).days >= 60 else np.nan
                return r, {"Valor actual": v.iloc[-1], "Aportes netos (depósitos − retiros)": f.sum(), "Ganancia": v.iloc[-1] - f.sum(),
                           "Rendimiento ajustado por aportes (TWR) %": ((1 + r).prod() - 1) * 100, "TIR anual del dinero %": tir * 100}

            r_usd, m_usd = resumen(res["valor_usd"], res["flujo_usd"])
            tabla_res = pd.DataFrame({"USD": m_usd})
            r_ars = None
            if "valor_ars" in res:
                r_ars, m_ars = resumen(res["valor_ars"], res["flujo_ars"])
                tabla_res["Pesos (ARS)"] = pd.Series(m_ars)
            st.markdown(f"### Rendimiento del {res.index[0]:%d/%m/%Y} al {res.index[-1]:%d/%m/%Y}")
            st.dataframe(tabla_res.style.format(precision=2, na_rep="-"), width="stretch")
            st.caption("**TWR** encadena el rendimiento de cada día quitando el efecto de los depósitos y retiros: es la medida para saber si "
                       "elegiste bien las acciones. La **TIR del dinero** sí pesa cuándo pusiste cada monto (se calcula con 60 días o más). "
                       "En pesos, el rendimiento incluye lo que subió o bajó el dólar MEP.")

            mon_v = st.radio("Ver gráficos y detalle mensual en", ["USD"] + (["Pesos (ARS)"] if r_ars is not None else []),
                             horizontal=True, key="cart_mon")
            v, f, r = (res["valor_usd"], res["flujo_usd"], r_usd) if mon_v == "USD" else (res["valor_ars"], res["flujo_ars"], r_ars)
            gA, gB = st.columns(2)
            gA.caption("Valor de la cartera y aportes acumulados")
            gA.line_chart(pd.DataFrame({"Valor de la cartera": v, "Aportes netos acumulados": f.cumsum()}), height=220)
            gB.caption("Rendimiento acumulado % (TWR)")
            gB.line_chart(pd.DataFrame({"Rendimiento acumulado % (TWR)": ((1 + r).cumprod() - 1) * 100}), height=220)
            mes = v.index.to_period("M").astype(str)
            mensual = pd.DataFrame({"Rend. del mes % (TWR)": ((1 + r).groupby(mes).prod() - 1) * 100,
                                    "Aportes netos del mes": f.groupby(mes).sum(), "Valor al cierre": v.groupby(mes).last()})
            mensual.index.name = "Mes"
            st.markdown("**Mes a mes:** el rendimiento de cada mes no cambia aunque hayas depositado o retirado ese mes.")
            st.dataframe(mensual.style.format(precision=2), width="stretch")
            st.caption("Compras, ventas y cambios al precio de cierre del día (o del siguiente día de mercado). Precios de Yahoo Finance en dólares. "
                       "No incluye comisiones, impuestos ni dividendos. La conversión a pesos usa el dólar MEP de cada fecha.")

st.divider()
st.caption("Proyecto personal con fines informativos. No constituye asesoramiento financiero ni recomendación de inversión.")
