import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import re
import json
import tempfile
import altair as alt
import estilo as E
import streamlit.components.v1 as components
from datetime import datetime
from zoneinfo import ZoneInfo
import unicodedata
import requests
from pathlib import Path
from datetime import date, timedelta

st.set_page_config(page_title="Panel de inversiones AR", layout="wide")
def NT(x):
    """Marca el contenido como 'no traducir': Chrome tomaba la página por inglés y traducía mal (ROE -> 'hueva')."""
    return f'<div translate="no" class="notranslate">{x}</div>'


def H(x, **k):
    return st.html(NT(x), **k)


def Hc(col, x):
    return col.html(NT(x))


st.html(E.css())
st.html("<script>(function(){var d=document.documentElement;d.setAttribute('lang','es');d.setAttribute('translate','no');"
        "if(!document.querySelector('meta[name=\"google\"]')){var m=document.createElement('meta');m.name='google';m.content='notranslate';"
        "document.head.appendChild(m);}})();</script>", unsafe_allow_javascript=True)
H(E.hero("Panel de inversiones", "CEDEARs, FCI y renta fija", "Información simple para tomar decisiones con más contexto."))

# Lista amplia de empresas con CEDEAR vigente en BYMA (confirmá siempre contra tu broker,
# BYMA agrega y quita programas seguido). Se filtran por volumen mínimo más abajo, así que
# tener más tickers acá no ensucia el panel: los que no operan quedan afuera solos.
# ticker en Nueva York: (nombre, sector)
INFO = {
    # Tecnología
    "AAPL": ('Apple', 'Tecnología'), "MSFT": ('Microsoft', 'Tecnología'),
    "NVDA": ('NVIDIA', 'Tecnología'), "AMD": ('AMD', 'Tecnología'),
    "PLTR": ('Palantir', 'Tecnología'), "INTC": ('Intel', 'Tecnología'),
    "CRM": ('Salesforce', 'Tecnología'), "ORCL": ('Oracle', 'Tecnología'),
    "IBM": ('IBM', 'Tecnología'), "CSCO": ('Cisco', 'Tecnología'),
    "QCOM": ('Qualcomm', 'Tecnología'), "TXN": ('Texas Instruments', 'Tecnología'),
    "MU": ('Micron', 'Tecnología'), "AVGO": ('Broadcom', 'Tecnología'),
    "NOW": ('ServiceNow', 'Tecnología'), "UBER": ('Uber', 'Tecnología'),
    "SNAP": ('Snap', 'Tecnología'), "SHOP": ('Shopify', 'Tecnología'),
    "SPOT": ('Spotify', 'Tecnología'), "ABNB": ('Airbnb', 'Tecnología'),
    "DELL": ('Dell', 'Tecnología'), "HPQ": ('HP', 'Tecnología'),
    "RBLX": ('Roblox', 'Tecnología'), "ZM": ('Zoom', 'Tecnología'),
    "TSM": ('Taiwan Semiconductor', 'Tecnología'), "SAP": ('SAP', 'Tecnología'),
    "SONY": ('Sony', 'Tecnología'), "SNOW": ('Snowflake', 'Tecnología'),
    "PANW": ('Palo Alto Networks', 'Tecnología'), "CRWD": ('CrowdStrike', 'Tecnología'),
    "ADI": ('Analog Devices', 'Tecnología'), "LRCX": ('Lam Research', 'Tecnología'),
    "AMAT": ('Applied Materials', 'Tecnología'), "MRVL": ('Marvell', 'Tecnología'),
    "ANET": ('Arista Networks', 'Tecnología'), "GLOB": ('Globant', 'Tecnología'),
    "ACN": ('Accenture', 'Tecnología'), "ADP": ('ADP', 'Tecnología'),
    "VRSN": ('Verisign', 'Tecnología'), "SWKS": ('Skyworks', 'Tecnología'),
    "WDC": ('Western Digital', 'Tecnología'), "GLW": ('Corning', 'Tecnología'),
    "TWLO": ('Twilio', 'Tecnología'), "DOCU": ('DocuSign', 'Tecnología'),
    "TEAM": ('Atlassian', 'Tecnología'), "PATH": ('UiPath', 'Tecnología'),
    "UPST": ('Upstart', 'Tecnología'), "GRMN": ('Garmin', 'Tecnología'),
    "INFY": ('Infosys', 'Tecnología'), "CLS": ('Celestica', 'Tecnología'),
    "XYZ": ('Block', 'Tecnología'), "ADBE": ('Adobe', 'Tecnología'),
    "ARM": ('Arm Holdings', 'Tecnología'), "ASML": ('ASML', 'Tecnología'),
    "KLAC": ('KLA Corp', 'Tecnología'), "AI": ('C3.ai', 'Tecnología'),
    "ALAB": ('Astera Labs', 'Tecnología'), "BB": ('BlackBerry', 'Tecnología'),
    "FSLR": ('First Solar', 'Tecnología'), "MSI": ('Motorola Solutions', 'Tecnología'),
    "XROX": ('Xerox', 'Tecnología'), "IBKR": ('Interactive Brokers', 'Tecnología'),
    # Comunicación
    "GOOGL": ('Alphabet (Google)', 'Comunicación'), "META": ('Meta Platforms', 'Comunicación'),
    "NFLX": ('Netflix', 'Comunicación'), "DIS": ('Walt Disney', 'Comunicación'),
    "VZ": ('Verizon', 'Comunicación'), "T": ('AT&T', 'Comunicación'),
    "GOOG": ('Alphabet (clase C)', 'Comunicación'), "BIDU": ('Baidu', 'Comunicación'),
    "VIV": ('Telefônica Brasil', 'Comunicación'), "TMUS": ('T-Mobile', 'Comunicación'),
    "VOD": ('Vodafone', 'Comunicación'), "ROKU": ('Roku', 'Comunicación'),
    "PINS": ('Pinterest', 'Comunicación'), "YELP": ('Yelp', 'Comunicación'),
    "NTES": ('NetEase', 'Comunicación'), "ERIC": ('Ericsson', 'Comunicación'),
    "EA": ('Electronic Arts', 'Comunicación'), "AMX": ('América Móvil', 'Comunicación'),
    "ASTS": ('AST SpaceMobile', 'Comunicación'), "ORAN": ('Orange', 'Comunicación'),
    "TIMB": ('TIM Brasil', 'Comunicación'), "TV": ('Grupo Televisa', 'Comunicación'),
    "JOYY": ('JOYY', 'Comunicación'),
    # Consumo discrecional
    "AMZN": ('Amazon', 'Consumo discrecional'), "TSLA": ('Tesla', 'Consumo discrecional'),
    "MELI": ('MercadoLibre', 'Consumo discrecional'), "MCD": ("McDonald's", 'Consumo discrecional'),
    "BABA": ('Alibaba', 'Consumo discrecional'), "NKE": ('Nike', 'Consumo discrecional'),
    "SBUX": ('Starbucks', 'Consumo discrecional'), "HD": ('Home Depot', 'Consumo discrecional'),
    "TGT": ('Target', 'Consumo discrecional'), "F": ('Ford', 'Consumo discrecional'),
    "GM": ('General Motors', 'Consumo discrecional'), "LVS": ('Las Vegas Sands', 'Consumo discrecional'),
    "EBAY": ('eBay', 'Consumo discrecional'), "RACE": ('Ferrari', 'Consumo discrecional'),
    "BKNG": ('Booking', 'Consumo discrecional'), "ROST": ('Ross Stores', 'Consumo discrecional'),
    "TJX": ('TJX Companies', 'Consumo discrecional'), "TM": ('Toyota', 'Consumo discrecional'),
    "HMC": ('Honda', 'Consumo discrecional'), "STLA": ('Stellantis', 'Consumo discrecional'),
    "JD": ('JD.com', 'Consumo discrecional'), "PDD": ('PDD (Pinduoduo)', 'Consumo discrecional'),
    "NIO": ('NIO', 'Consumo discrecional'), "DAL": ('Delta Air Lines', 'Consumo discrecional'),
    "AAL": ('American Airlines', 'Consumo discrecional'), "UAL": ('United Airlines', 'Consumo discrecional'),
    "ORLY": ("O'Reilly Automotive", 'Consumo discrecional'), "DECK": ('Deckers', 'Consumo discrecional'),
    "ANF": ('Abercrombie & Fitch', 'Consumo discrecional'), "AAP": ('Advance Auto Parts', 'Consumo discrecional'),
    "URBN": ('Urban Outfitters', 'Consumo discrecional'), "HOG": ('Harley-Davidson', 'Consumo discrecional'),
    "CAR": ('Avis Budget', 'Consumo discrecional'), "SE": ('Sea Limited', 'Consumo discrecional'),
    "TCOM": ('Trip.com', 'Consumo discrecional'), "ARCO": ('Arcos Dorados', 'Consumo discrecional'),
    "TTM": ('Tata Motors', 'Consumo discrecional'), "CCL": ('Carnival', 'Consumo discrecional'),
    "ETSY": ('Etsy', 'Consumo discrecional'), "NSAN": ('Nissan', 'Consumo discrecional'),
    "XPEV": ('XPeng', 'Consumo discrecional'), "JMIA": ('Jumia', 'Consumo discrecional'),
    "TRIP": ('Tripadvisor', 'Consumo discrecional'),
    # Consumo básico
    "PEP": ('PepsiCo', 'Consumo básico'), "WMT": ('Walmart', 'Consumo básico'),
    "PG": ('Procter & Gamble', 'Consumo básico'), "PM": ('Philip Morris', 'Consumo básico'),
    "MO": ('Altria', 'Consumo básico'), "COST": ('Costco', 'Consumo básico'),
    "MDLZ": ('Mondelez', 'Consumo básico'), "HSY": ('Hershey', 'Consumo básico'),
    "ABEV": ('Ambev', 'Consumo básico'), "FMX": ('FEMSA', 'Consumo básico'),
    "UL": ('Unilever', 'Consumo básico'), "DEO": ('Diageo', 'Consumo básico'),
    "WBA": ('Walgreens', 'Consumo básico'), "KOFM": ('Coca-Cola FEMSA', 'Consumo básico'),
    "UGP": ('Ultrapar', 'Consumo básico'), "KO": ('Coca-Cola', 'Consumo básico'),
    "CL": ('Colgate-Palmolive', 'Consumo básico'), "KMB": ('Kimberly-Clark', 'Consumo básico'),
    "SYY": ('Sysco', 'Consumo básico'), "BRFS": ('BRF', 'Consumo básico'),
    "LND": ('BrasilAgro', 'Consumo básico'),
    # Salud
    "JNJ": ('Johnson & Johnson', 'Salud'), "PFE": ('Pfizer', 'Salud'),
    "MRK": ('Merck', 'Salud'), "UNH": ('UnitedHealth', 'Salud'),
    "ABBV": ('AbbVie', 'Salud'), "LLY": ('Eli Lilly', 'Salud'),
    "BMY": ('Bristol-Myers Squibb', 'Salud'), "AMGN": ('Amgen', 'Salud'),
    "GILD": ('Gilead Sciences', 'Salud'), "MRNA": ('Moderna', 'Salud'),
    "ABT": ('Abbott', 'Salud'), "TMO": ('Thermo Fisher', 'Salud'),
    "DHR": ('Danaher', 'Salud'), "ISRG": ('Intuitive Surgical', 'Salud'),
    "MDT": ('Medtronic', 'Salud'), "CVS": ('CVS Health', 'Salud'),
    "VRTX": ('Vertex Pharma', 'Salud'), "NVS": ('Novartis', 'Salud'),
    "NVO": ('Novo Nordisk', 'Salud'), "AZN": ('AstraZeneca', 'Salud'),
    "GSK": ('GSK', 'Salud'), "HIMS": ('Hims & Hers', 'Salud'),
    "CAH": ('Cardinal Health', 'Salud'), "PHG": ('Philips', 'Salud'),
    "NTRA": ('Natera', 'Salud'),
    # Financiero
    "JPM": ('JPMorgan Chase', 'Financiero'), "V": ('Visa', 'Financiero'),
    "PYPL": ('PayPal', 'Financiero'), "BAC": ('Bank of America', 'Financiero'),
    "WFC": ('Wells Fargo', 'Financiero'), "GS": ('Goldman Sachs', 'Financiero'),
    "MS": ('Morgan Stanley', 'Financiero'), "MA": ('Mastercard', 'Financiero'),
    "C": ('Citigroup', 'Financiero'), "SCHW": ('Charles Schwab', 'Financiero'),
    "HSBC": ('HSBC', 'Financiero'), "STNE": ('StoneCo', 'Financiero'),
    "USB": ('US Bancorp', 'Financiero'), "BK": ('Bank of NY Mellon', 'Financiero'),
    "SPGI": ('S&P Global', 'Financiero'), "ITUB": ('Itaú Unibanco', 'Financiero'),
    "BBD": ('Banco Bradesco', 'Financiero'), "NU": ('Nu Holdings', 'Financiero'),
    "BX": ('Blackstone', 'Financiero'), "MMC": ('Marsh McLennan', 'Financiero'),
    "ING": ('ING Group', 'Financiero'), "SAN": ('Banco Santander', 'Financiero'),
    "BCS": ('Barclays', 'Financiero'), "MUFG": ('Mitsubishi UFJ', 'Financiero'),
    "MFG": ('Mizuho', 'Financiero'), "NMR": ('Nomura', 'Financiero'),
    "HDB": ('HDFC Bank', 'Financiero'), "IBN": ('ICICI Bank', 'Financiero'),
    "KB": ('KB Financial', 'Financiero'), "PAGS": ('PagSeguro', 'Financiero'),
    "XP": ('XP Inc', 'Financiero'), "HOOD": ('Robinhood', 'Financiero'),
    "AXP": ('American Express', 'Financiero'), "AIG": ('AIG', 'Financiero'),
    "AEG": ('Aegon', 'Financiero'), "BBV": ('BBVA', 'Financiero'),
    "BSBR": ('Santander Brasil', 'Financiero'), "LFC": ('China Life', 'Financiero'),
    # Energía
    "XOM": ('Exxon Mobil', 'Energía'), "CVX": ('Chevron', 'Energía'),
    "SHEL": ('Shell', 'Energía'), "COP": ('ConocoPhillips', 'Energía'),
    "OXY": ('Occidental Petroleum', 'Energía'), "BP": ('BP', 'Energía'),
    "HAL": ('Halliburton', 'Energía'), "PBR": ('Petrobras', 'Energía'),
    "BKR": ('Baker Hughes', 'Energía'), "TTE": ('TotalEnergies', 'Energía'),
    "E": ('Eni', 'Energía'), "EQNR": ('Equinor', 'Energía'),
    "VIST": ('Vista Energy', 'Energía'), "SLB": ('SLB (Schlumberger)', 'Energía'),
    "PSX": ('Phillips 66', 'Energía'), "CCJ": ('Cameco', 'Energía'),
    "GLNG": ('Golar LNG', 'Energía'), "GPRK": ('GeoPark', 'Energía'),
    # Industriales
    "BA": ('Boeing', 'Industriales'), "CAT": ('Caterpillar', 'Industriales'),
    "GE": ('General Electric', 'Industriales'), "HON": ('Honeywell', 'Industriales'),
    "MMM": ('3M', 'Industriales'), "LMT": ('Lockheed Martin', 'Industriales'),
    "DE": ('Deere & Co', 'Industriales'), "RTX": ('RTX (Raytheon)', 'Industriales'),
    "UNP": ('Union Pacific', 'Industriales'), "FDX": ('FedEx', 'Industriales'),
    "EFX": ('Equifax', 'Industriales'), "JCI": ('Johnson Controls', 'Industriales'),
    "HWM": ('Howmet', 'Industriales'), "GEV": ('GE Vernova', 'Industriales'),
    "SNA": ('Snap-on', 'Industriales'), "GT": ('Goodyear', 'Industriales'),
    "PCAR": ('Paccar', 'Industriales'), "ERJ": ('Embraer', 'Industriales'),
    "RKLB": ('Rocket Lab', 'Industriales'), "ASR": ('Grupo Aeroportuario Sureste', 'Industriales'),
    "PAC": ('Grupo Aeroportuario Pacífico', 'Industriales'),
    # Materiales
    "FCX": ('Freeport-McMoRan', 'Materiales'), "NUE": ('Nucor', 'Materiales'),
    "NEM": ('Newmont', 'Materiales'), "DOW": ('Dow Inc.', 'Materiales'),
    "VALE": ('Vale', 'Materiales'), "RIO": ('Rio Tinto', 'Materiales'),
    "BHP": ('BHP Group', 'Materiales'), "LIN": ('Linde', 'Materiales'),
    "SHW": ('Sherwin-Williams', 'Materiales'), "DD": ('DuPont', 'Materiales'),
    "MOS": ('Mosaic', 'Materiales'), "GGB": ('Gerdau', 'Materiales'),
    "SID": ('CSN', 'Materiales'), "PAAS": ('Pan American Silver', 'Materiales'),
    "KGC": ('Kinross Gold', 'Materiales'), "AEM": ('Agnico Eagle', 'Materiales'),
    "GFI": ('Gold Fields', 'Materiales'), "MP": ('MP Materials', 'Materiales'),
    "IP": ('International Paper', 'Materiales'), "IFF": ('Intl Flavors & Fragrances', 'Materiales'),
    "SCCO": ('Southern Copper', 'Materiales'), "CX": ('Cemex', 'Materiales'),
    "HMY": ('Harmony Gold', 'Materiales'), "ECL": ('Ecolab', 'Materiales'),
    "AVY": ('Avery Dennison', 'Materiales'), "BAK": ('Braskem', 'Materiales'),
    "CDE": ('Coeur Mining', 'Materiales'), "HL": ('Hecla Mining', 'Materiales'),
    "NG": ('Novagold', 'Materiales'), "SUZ": ('Suzano', 'Materiales'),
    "BIOX": ('Bioceres', 'Materiales'), "LAC": ('Lithium Americas', 'Materiales'),
    # Utilities
    "NEE": ('NextEra Energy', 'Utilities'), "CEG": ('Constellation Energy', 'Utilities'),
    "VST": ('Vistra', 'Utilities'), "NGG": ('National Grid', 'Utilities'),
    "EBR": ('Eletrobras', 'Utilities'), "ELP": ('Copel', 'Utilities'),
    "SBS": ('Sabesp', 'Utilities'),
    # Real Estate
    "PLD": ('Prologis', 'Real Estate'), "WELL": ('Welltower', 'Real Estate'),
    "O": ('Realty Income', 'Real Estate'),
    # Cripto
    "MSTR": ('MicroStrategy', 'Cripto'), "COIN": ('Coinbase', 'Cripto'),
    "IBIT": ('iShares Bitcoin Trust (BTC)', 'Cripto'), "ETHA": ('iShares Ethereum Trust (ETH)', 'Cripto'),
    "HUT": ('Hut 8 (minería BTC)', 'Cripto'), "RIOT": ('Riot Platforms (minería BTC)', 'Cripto'),
    "IREN": ('IREN (minería BTC)', 'Cripto'), "BMNR": ('Bitmine Immersion', 'Cripto'),
    # ETF / Índices
    "URA": ('Global X Uranium ETF', 'ETF / Índices'), "SPY": ('S&P 500 (SPY)', 'ETF / Índices'),
    "QQQ": ('Nasdaq 100 (QQQ)', 'ETF / Índices'), "DIA": ('Dow Jones (DIA)', 'ETF / Índices'),
    "IWM": ('Russell 2000 (IWM)', 'ETF / Índices'), "XLE": ('Energía / Petroleras (XLE)', 'ETF / Índices'),
    "XLF": ('Bancos / Financiero (XLF)', 'ETF / Índices'), "XLK": ('Tecnología (XLK)', 'ETF / Índices'),
    "XLV": ('Salud (XLV)', 'ETF / Índices'), "XLY": ('Consumo discrecional (XLY)', 'ETF / Índices'),
    "XLP": ('Consumo básico (XLP)', 'ETF / Índices'), "XLI": ('Industriales (XLI)', 'ETF / Índices'),
    "XLB": ('Materiales (XLB)', 'ETF / Índices'), "CIBR": ('Ciberseguridad (CIBR)', 'ETF / Índices'),
    "ARKK": ('Innovación / ARK (ARKK)', 'ETF / Índices'), "GLD": ('Oro (GLD)', 'ETF / Índices'),
    "SLV": ('Plata (SLV)', 'ETF / Índices'), "COPX": ('Cobre / Mineras (COPX)', 'ETF / Índices'),
    "GDX": ('Oro / Mineras (GDX)', 'ETF / Índices'),
}
TICKERS = list(INFO)

# Acciones argentinas que cotizan directamente en pesos en BYMA (no son CEDEARs).
# ticker en BYMA (sin .BA): (nombre, sector)
INFO_AR = {
    "GGAL": ("Grupo Financiero Galicia", "Bancos"), "BMA": ("Banco Macro", "Bancos"),
    "SUPV": ("Grupo Supervielle", "Bancos"), "BBAR": ("BBVA Argentina", "Bancos"),
    "VALO": ("Banco de Valores", "Bancos"),
    "YPFD": ("YPF", "Energía"), "PAMP": ("Pampa Energía", "Energía"),
    "CEPU": ("Central Puerto", "Energía"), "TGSU2": ("Transportadora Gas del Sur", "Energía"),
    "TGNO4": ("Transportadora Gas del Norte", "Energía"), "EDN": ("Edenor", "Energía"),
    "CGPA2": ("Central Costanera", "Energía"), "TRAN": ("Transener", "Energía"),
    "CRES": ("Cresud", "Real estate / Agro"), "IRSA": ("IRSA", "Real estate / Agro"),
    "ALUA": ("Aluar", "Materiales"), "TXAR": ("Ternium Argentina", "Materiales"),
    "LOMA": ("Loma Negra", "Materiales"),
    "MIRG": ("Mirgor", "Industriales"), "COME": ("Sociedad Comercial del Plata", "Industriales"),
    "TECO2": ("Telecom Argentina", "Comunicación"), "CVH": ("Cablevisión Holding", "Comunicación"),
    "BYMA": ("BYMA", "Financiero"), "AGRO": ("Agrometal", "Industriales"),
    "MOLI": ("Molinos Río de la Plata", "Consumo básico"), "LEDE": ("Ledesma", "Consumo básico"),
}
TICKERS_AR = list(INFO_AR)

# Ratio de conversión de los CEDEARs (cuántos CEDEARs equivalen a 1 acción en Nueva York).
# Se usa SOLO para el dólar CCL implícito. Fuente: tabla sincronizada con BYMA (sep-2026).
# ¡Verificá contra tu broker! Cambian por splits o ajustes del emisor. Si falta un ratio acá,
# ese CEDEAR simplemente no muestra CCL implícito (no se inventa).
RATIOS_CEDEAR = {
    "AAPL": 20, "MSFT": 30, "NVDA": 24, "AMD": 10, "GOOGL": 58, "META": 24, "AMZN": 144,
    "TSLA": 15, "MELI": 120, "KO": 5, "DIS": 12, "NFLX": 48, "BABA": 9, "JPM": 15, "V": 18,
    "MA": 33, "WMT": 18, "NKE": 12, "SBUX": 12, "MCD": 24, "PBR": 1, "VALE": 2, "JNJ": 15,
    "PFE": 4, "XOM": 10, "CVX": 16, "BA": 24, "INTC": 5, "QCOM": 11, "PYPL": 8, "CAT": 20,
    "IBM": 15, "ORCL": 3, "CSCO": 5, "PG": 15, "HD": 32, "C": 3, "GS": 13, "MU": 5,
    "COIN": 27, "MSTR": 20, "GLOB": 18, "VIST": 3, "TSM": 9, "AVGO": 39,
}

# Parámetros fijos (no se muestran en pantalla)
RSI_BAJO, RSI_ALTO = 30, 70      # verde (sobreventa) / rojo (sobrecompra)
MIN_VOLUMEN_USD_M = 100          # volumen mínimo diario en NY: descarta CEDEARs con poca liquidez
MIN_VOLUMEN_USD_M_AR = 0.3       # volumen mínimo diario equivalente en USD para acciones argentinas
                                   # (el mercado local mueve mucho menos dólares que Nueva York, así
                                   # que usa un piso propio en vez del mismo que los CEDEARs)


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
@st.cache_data(persist="disk", ttl=3600, show_spinner="Descargando precios de Nueva York...")
def precios(tickers):
    d = yf.download(list(tickers), period="1y", auto_adjust=True, progress=False)
    return d["Close"].ffill(), d["Volume"]


@st.cache_data(persist="disk", ttl=1800, show_spinner="Descargando precios de CEDEARs en BYMA...")
def precios_cedear_ars(tickers):
    """Obtiene precio en ARS y volumen del CEDEAR en Buenos Aires (.BA)."""
    ba = [t + ".BA" for t in tickers]
    try:
        d = yf.download(ba, period="5d", auto_adjust=True, progress=False)
        cl = d["Close"].ffill()
        vo = d["Volume"]
        # último precio y volumen promedio 5 días
        precio = {}; volumen = {}
        for t in tickers:
            tba = t + ".BA"
            if tba in cl.columns and cl[tba].dropna().shape[0]:
                precio[t] = float(cl[tba].dropna().iloc[-1])
                volumen[t] = float(vo[tba].tail(5).mean()) if tba in vo.columns else 0.0
            else:
                precio[t] = np.nan; volumen[t] = 0.0
        return pd.Series(precio), pd.Series(volumen)
    except Exception:
        return pd.Series(dtype=float), pd.Series(dtype=float)


@st.cache_data(persist="disk", ttl=3600, show_spinner="Descargando acciones argentinas...")
def precios_ar(tickers):
    """Precio y volumen diarios (1 año) de acciones que cotizan solo en BYMA, en pesos."""
    ba = [t + ".BA" for t in tickers]
    try:
        d = yf.download(ba, period="1y", auto_adjust=True, progress=False)
        cl = d["Close"].ffill()
        vo = d["Volume"]
        cl.columns = [c.replace(".BA", "") for c in cl.columns]
        vo.columns = [c.replace(".BA", "") for c in vo.columns]
        return cl, vo
    except Exception:
        return pd.DataFrame(), pd.DataFrame()


def sesion_eeuu():
    """Estado de la rueda de Nueva York según la hora actual: pre / regular / after / cerrado."""
    now = datetime.now(ZoneInfo("America/New_York"))
    if now.weekday() >= 5:   # sábado/domingo
        return "cerrado", now
    hm = now.hour * 60 + now.minute
    if 4 * 60 <= hm < 9 * 60 + 30:
        return "pre", now
    if 9 * 60 + 30 <= hm < 16 * 60:
        return "regular", now
    if 16 * 60 <= hm < 20 * 60:
        return "after", now
    return "cerrado", now


@st.cache_data(persist="disk", ttl=180, show_spinner="Consultando pre-market / after-hours...")
def precios_extended(tickers):
    """Último precio incluyendo pre-market y after-hours (Yahoo prepost). dict ticker -> (precio, hora ET)."""
    try:
        d = yf.download(list(tickers), period="2d", interval="5m", prepost=True,
                        auto_adjust=True, progress=False)["Close"]
        if isinstance(d, pd.Series):
            d = d.to_frame(list(tickers)[0])
        idx = d.index
        idx = idx.tz_localize("UTC") if idx.tz is None else idx
        d.index = idx.tz_convert("America/New_York")
        out = {}
        for t in d.columns:
            s = d[t].dropna()
            if len(s):
                out[t] = (float(s.iloc[-1]), s.index[-1])
        return out
    except Exception:
        return {}


@st.cache_data(persist="disk", ttl=3600, show_spinner=False)
def retornos_sp500():
    """Retornos diarios del S&P 500 (índice de mercado para la beta de CAPM)."""
    try:
        d = yf.download("^GSPC", period="1y", auto_adjust=True, progress=False)["Close"]
        if isinstance(d, pd.DataFrame):
            d = d.iloc[:, 0]
        return d.pct_change().dropna()
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(persist="disk", ttl=6 * 3600, show_spinner="Descargando dividendos...")
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


@st.cache_data(persist="disk", ttl=300, show_spinner="Descargando datos intradiarios...")
def rsi_45m(tickers, sufijo="", tz="America/New_York", inicio_min=570):
    """RSI(14) sobre velas de 45 min, armadas agrupando de a 3 velas de 15 min por rueda.
    sufijo: se agrega a cada ticker al pedirle a Yahoo (".BA" para BYMA). tz/inicio_min: huso horario
    y minuto de apertura de la rueda (9:30 NY = 570; 11:00 ART = 660) para armar los bloques de 45 min."""
    pedidos = [t + sufijo for t in tickers]
    d = yf.download(pedidos, period="1mo", interval="15m", auto_adjust=True, progress=False)["Close"]
    if isinstance(d, pd.Series):
        d = d.to_frame(pedidos[0])
    out, ultima = {}, None
    for tp in d.columns:
        t = tp[:-len(sufijo)] if sufijo and tp.endswith(sufijo) else tp
        s = d[tp].dropna()
        if len(s) < 60:
            out[t] = np.nan
            continue
        # Yahoo puede entregar la hora en UTC: se pasa siempre al huso horario de la rueda
        idx = s.index.tz_localize("UTC") if s.index.tz is None else s.index
        s.index = idx.tz_convert(tz)
        dia = np.array(s.index.date)
        # Bloque de 45 min según la hora de apertura, no por conteo de velas:
        # así, si Yahoo omite una vela de 15 min, el resto no se desfasa.
        minutos = s.index.hour * 60 + s.index.minute - inicio_min
        bloque = np.asarray(minutos // 45)
        c45 = s.groupby([dia, bloque]).last()
        out[t] = float(rsi(c45).iloc[-1])
        ultima = s.index[-1] if ultima is None or s.index[-1] > ultima else ultima
    return pd.Series(out), ultima


@st.cache_data(persist="disk", ttl=6 * 3600, show_spinner=False)
def _fundamental_uno(t):
    """Datos fundamentales de un ticker. Si Yahoo no devuelve nada (rate limit), LANZA excepción
    para que st.cache_data NO cachee el fallo y se reintente en la próxima recarga."""
    i = yf.Ticker(t).info or {}
    pe, sector = i.get("trailingPE"), i.get("sector")
    # Si la respuesta viene vacía (sin nombre ni tipo), es probable rate limit → lanzar para reintentar.
    # Si viene una respuesta válida (p. ej. un ETF) pero sin P/E, se devuelve igual y se cachea.
    valida = any(i.get(k) for k in ("quoteType", "longName", "shortName", "sector", "trailingPE", "forwardPE"))
    if not valida:
        raise ValueError("sin datos (probable rate limit de Yahoo)")
    roe, deuda, ebitda = i.get("returnOnEquity"), i.get("totalDebt"), i.get("ebitda")
    return {"Sector": sector, "P/E": pe, "P/E futuro": i.get("forwardPE"), "P/B": i.get("priceToBook"),
            "ROE %": roe * 100 if roe is not None else None,
            "Deuda/EBITDA": deuda / ebitda if deuda and ebitda and ebitda > 0 else None}


def fundamentales(tickers):
    """Junta los fundamentales por ticker (cada uno cacheado aparte; los fallidos se reintentan solos)."""
    filas = []
    for t in tickers:
        try:
            d = dict(_fundamental_uno(t))
            d["Ticker"] = t
        except Exception:
            d = {"Ticker": t}
        filas.append(d)
    df = pd.DataFrame(filas).set_index("Ticker")
    return df.reindex(columns=["Sector", "P/E", "P/E futuro", "P/B", "ROE %", "Deuda/EBITDA"])


def _preparar_componente():
    """Escribe el componente de tabla clicable en una carpeta temporal y devuelve su ruta."""
    d = Path(tempfile.gettempdir()) / "panel_tabla_click"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "index.html"
    contenido = E.COMPONENTE_TABLA_HTML
    try:
        existente = open(str(f), encoding="utf-8").read()
    except FileNotFoundError:
        existente = ""
    if existente != contenido:
        with open(str(f), "w", encoding="utf-8") as fh:
            fh.write(contenido)
    return d


tabla_click = components.declare_component("tabla_click", path=str(_preparar_componente()))

API = "https://api.argentinadatos.com/v1/finanzas"
TIPOS_FCI = {"Mercado de dinero": "mercadoDinero", "Renta fija": "rentaFija",
             "Renta variable": "rentaVariable", "Renta mixta": "rentaMixta"}


@st.cache_data(persist="disk", ttl=3600, show_spinner=False)
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


@st.cache_data(persist="disk", ttl=3600, show_spinner="Armando ranking de FCI...")
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


@st.cache_data(persist="disk", ttl=6 * 3600, show_spinner=False)
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


@st.cache_data(persist="disk", ttl=6 * 3600, show_spinner="Cargando detalle de los fondos...")
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


def detalle_completo(f):
    comp = pd.DataFrame(f.get("composicionCartera") or [])
    if comp.empty or "porcentaje" not in comp:
        st.info("El fondo no informa la composición de su cartera.")
    else:
        pc = comp["porcentaje"].astype(float)
        pc = pc * 100 if pc.sum() <= 1.5 else pc
        composicion_st("¿Dónde está invertido tu dinero?", "Distribución de la cartera del fondo según lo informado a la CNV.",
                       list(zip(comp["nombre"].astype(str), pc)), "Composición de cartera", "card_comp_fci")
    hon = {k: v for k, v in (f.get("honorarios") or {}).items() if v}
    if hon:
        filas = [[f'<span class="strong">{E.esc(COMISIONES.get(k, (k, ""))[0])}</span>', E.chip(f"{v:g}%", "pur"),
                  E.esc(COMISIONES.get(k, (k, ""))[1])] for k, v in hon.items()]
        H('<div class="eyebrow m" style="margin-top:18px">Honorarios y comisiones</div><div class="h2" style="font-size:1.8rem">Cómo se cobran</div>'
                + E.tabla([("Concepto", "l"), ("Valor", "l"), ("Cómo se cobra", "w")], filas))
        st.caption("Los honorarios anuales **ya están descontados** del rendimiento: no se cobran aparte ni hay que restarlos de nuevo. "
                   "Se pagan siempre, haya ganancia o pérdida. Las comisiones de ingreso y rescate se pagan una vez, al entrar o salir. "
                   "Valores tal como los informa la CNV; suelen ser topes del reglamento. Confirmalo en el reglamento de gestión.")
    cal = f.get("calificaciones") or []
    if cal:
        st.caption("Calificaciones: " + " · ".join(f"{x.get('calificadora', '')}: {x.get('calificacion', '')}" for x in cal))


@st.cache_data(persist="disk", ttl=3600, show_spinner="Armando el gráfico del fondo...")
def serie_fondo(tipo, nombre, ini, fin, n=10):
    """Valor de la cuotaparte en n fechas entre ini y fin (para el gráfico del fondo)."""
    fechas = pd.date_range(ini, fin, periods=n).normalize()
    vals = []
    for f in fechas:
        df = fci_cercano(tipo, f.date())
        fila = df[df["fondo"] == nombre] if len(df) else df
        vals.append(float(fila["vcp"].iloc[0]) if len(fila) else np.nan)
    return list(fechas), vals


def torta_alt(items, colores, alto=260):
    """Gráfico de torta (dona) nativo de Streamlit, con la cantidad de posiciones en el centro."""
    d = pd.DataFrame({"Activo": [i[0] for i in items], "Valor": [float(i[1]) for i in items], "Color": colores})
    arco = alt.Chart(d).mark_arc(innerRadius=0.58 * alto / 2, outerRadius=alto / 2 - 6, stroke="#FFFEFA", strokeWidth=2).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        color=alt.Color("Activo:N", scale=alt.Scale(domain=list(d["Activo"]), range=colores), legend=None),
        tooltip=["Activo", alt.Tooltip("Valor:Q", format=".1f", title="%")])
    centro = alt.Chart(pd.DataFrame({"t": [str(len(d))]})).mark_text(size=40, color="#26221F", dy=-4).encode(text="t:N")
    chico = alt.Chart(pd.DataFrame({"t": ["posiciones"]})).mark_text(size=12, color="#8A7A6C", dy=24).encode(text="t:N")
    return (arco + centro + chico).properties(height=alto, width=alto).configure_view(strokeWidth=0)


def scatter_curva(df):
    """Dispersión TIR (eje Y) vs duración modificada (eje X), coloreada por tipo de instrumento.
    Traza la 'curva' de rendimientos: lo que queda por encima rinde más para su plazo (a revisar)."""
    base = alt.Chart(df).encode(
        x=alt.X("Duración:Q", title="Duración modificada (años)", scale=alt.Scale(zero=False, nice=True)),
        y=alt.Y("TIR:Q", title="TIR (TEA %)", scale=alt.Scale(zero=False, nice=True)),
        color=alt.Color("Tipo:N", scale=alt.Scale(domain=["Soberano", "ON"], range=["#6A4FA0", "#C98A5E"]),
                        legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("Instrumento:N", title="Instrumento"),
                 alt.Tooltip("TIR:Q", format=".1f", title="TIR %"),
                 alt.Tooltip("Duración:Q", format=".2f", title="Dur. mod.")])
    puntos = base.mark_circle(size=130, opacity=0.85, stroke="#FFFEFA", strokeWidth=1)
    etiquetas = base.mark_text(align="left", dx=7, dy=-4, fontSize=10, color="#2A2420").encode(text="Instrumento:N")
    return (puntos + etiquetas).properties(height=380).configure_view(strokeWidth=0).configure_axis(
        grid=True, gridColor="#E7E0D5", labelColor="#8A7A6C", titleColor="#6A5B4F")


def composicion_st(titulo, descripcion, items, eyebrow, key):
    """Tarjeta con la leyenda a la izquierda y la torta a la derecha."""
    items, colores = E.composicion_datos(items)
    with st.container(key=key):
        c1, c2 = st.columns([1.5, 1], vertical_alignment="center")
        c1.html(NT(E.composicion_texto(titulo, descripcion, items, colores, eyebrow)))
        c2.altair_chart(torta_alt(items, colores), width="content")


def alternar_fav(nombre):
    favs = st.session_state.setdefault("fci_favs", set())
    favs.symmetric_difference_update({nombre})


# ----------------------------------------------------------------------------
# Indicadores macro: tarjetas KPI, inflación y dólar MEP histórico
# ----------------------------------------------------------------------------
def _limpia_fecha(serie):
    idx = pd.to_datetime(serie.index)
    serie.index = (idx.tz_localize(None) if idx.tz is not None else idx).normalize()
    return serie


@st.cache_data(persist="disk", ttl=600, show_spinner=False)
def panorama_mercado():
    """Lista de tarjetas (dict) para el carrusel: valor, variación y mini gráfico de ~30 puntos."""
    items, live, hist = [], {}, {}
    try:
        r = requests.get("https://dolarapi.com/v1/dolares", timeout=15)
        r.raise_for_status()
        for x in r.json():
            try:
                if x.get("casa") in ("bolsa", "contadoconliqui"):
                    live[x["casa"]] = float(x.get("venta") or x.get("compra"))
            except Exception:
                continue
    except Exception:
        pass
    for casa in ("bolsa", "contadoconliqui"):
        try:
            hist[casa] = _limpia_fecha(dolar_hist(casa).set_index("fecha")["valor"].copy())
        except Exception:
            pass

    def pct(titulo, sub, valor, serie, fmt, ayuda=""):
        s_ = [x for x in serie if x == x]
        d = (s_[-1] / s_[-2] - 1) * 100 if len(s_) >= 2 and s_[-2] else None
        tipo = "flat" if d is None or abs(d) < 0.005 else ("up" if d > 0 else "down")
        items.append(dict(titulo=titulo, sub=sub, valor=fmt(valor), tipo=tipo, ayuda=ayuda, serie=s_[-30:],
                          delta=E.num(abs(d), 2, suf="%") if d is not None else None,
                          flecha="↑" if tipo == "up" else ("↓" if tipo == "down" else "")))

    for casa, nombre, sub in (("bolsa", "Dólar MEP", "MEP"), ("contadoconliqui", "Dólar CCL", "CCL")):
        h = hist.get(casa, pd.Series(dtype=float))
        v = live.get(casa) or (float(h.iloc[-1]) if len(h) else None)
        if v:
            pct(nombre, sub, v, list(h.tail(30)), lambda x: E.num(x, 0, "$ "), "Cotización de venta.")
    try:
        rp = requests.get(f"{API}/indices/riesgo-pais", timeout=20)
        rp.raise_for_status()
        d = pd.DataFrame(rp.json()).dropna()
        d["fecha"] = pd.to_datetime(d["fecha"])
        v = list(d.sort_values("fecha")["valor"].astype(float).tail(30))
        dif = v[-1] - v[-2]
        items.append(dict(titulo="Riesgo país", sub="EMBI", valor=E.num(v[-1], 0, suf=" pb"), serie=v,
                          delta=E.num(abs(dif), 0, suf=" pb"), tipo="flat" if dif == 0 else ("up" if dif < 0 else "down"),
                          flecha="↓" if dif < 0 else ("↑" if dif > 0 else ""),
                          ayuda="Sobretasa de los bonos argentinos sobre los del Tesoro de EE.UU. Si baja, el mercado ve menos riesgo (en verde)."))
    except Exception:
        pass
    try:
        idx = yf.download(["^GSPC", "^IXIC", "^DJI", "^MERV", "^VIX"], period="2mo", auto_adjust=True, progress=False)["Close"]
        merv = _limpia_fecha(idx["^MERV"].dropna().copy()) if "^MERV" in idx else None
        if merv is not None and len(merv) > 2:
            if "contadoconliqui" in hist:
                ccl = hist["contadoconliqui"]
                m_usd = (pd.concat([merv.rename("m"), ccl.rename("c")], axis=1, sort=True).ffill().reindex(merv.index).dropna())
                m_usd = m_usd["m"] / m_usd["c"]
                pct("Merval en USD", "CCL", float(m_usd.iloc[-1]), list(m_usd.tail(30)), lambda x: E.num(x, 0, "US$ "),
                    "Merval en pesos dividido el dólar CCL de cada día.")
            elif "contadoconliqui" in live:
                pct("Merval en USD", "CCL", float(merv.iloc[-1]) / live["contadoconliqui"], [], lambda x: E.num(x, 0, "US$ "),
                    "Merval en pesos dividido el dólar CCL de hoy.")
        for sym, nombre, sub in (("^GSPC", "S&P 500", "EE.UU."), ("^IXIC", "Nasdaq", "EE.UU."), ("^DJI", "Dow Jones", "EE.UU."),
                                 ("^MERV", "Merval", "En pesos")):
            if sym in idx:
                h = idx[sym].dropna()
                if len(h) >= 2:
                    pct(nombre, sub, float(h.iloc[-1]), list(h.tail(30)), lambda x: E.num(x, 0))
        if "^VIX" in idx:
            hv = idx["^VIX"].dropna()
            if len(hv) >= 2:
                pct("VIX", "Índice del miedo", float(hv.iloc[-1]), list(hv.tail(30)), lambda x: E.num(x, 2),
                    "Volatilidad esperada del S&P 500. Sube con el miedo y las caídas; baja con la calma.")
    except Exception:
        pass
    # Commodities y cripto
    try:
        com = yf.download(["GC=F", "SI=F", "HG=F", "CL=F", "BTC-USD", "ETH-USD"], period="2mo",
                          auto_adjust=True, progress=False)["Close"]
        for sym, nombre, sub, dec in (("GC=F", "Oro", "US$/onza", 0), ("SI=F", "Plata", "US$/onza", 2),
                                      ("HG=F", "Cobre", "US$/libra", 2), ("CL=F", "Petróleo WTI", "US$/barril", 2),
                                      ("BTC-USD", "Bitcoin", "USD", 0), ("ETH-USD", "Ethereum", "USD", 0)):
            if sym in com:
                h = com[sym].dropna()
                if len(h) >= 2:
                    pct(nombre, sub, float(h.iloc[-1]), list(h.tail(30)), (lambda d: lambda x: E.num(x, d, "US$ "))(dec))
    except Exception:
        pass
    return items


@st.cache_data(persist="disk", ttl=6 * 3600, show_spinner=False)
def dolar_hist(casa):
    r = requests.get(f"https://api.argentinadatos.com/v1/cotizaciones/dolares/{casa}", timeout=30)
    r.raise_for_status()
    d = pd.DataFrame(r.json())
    col = "venta" if "venta" in d else "compra"
    d["fecha"] = pd.to_datetime(d["fecha"])
    return d.sort_values("fecha")[["fecha", col]].rename(columns={col: "valor"}).dropna().reset_index(drop=True)


def mep_hist():
    return dolar_hist("bolsa").rename(columns={"valor": "mep"})


def mep_en(d, fecha):
    sub = d[d["fecha"] <= fecha]
    return float(sub["mep"].iloc[-1]) if len(sub) else np.nan


@st.cache_data(persist="disk", ttl=600, show_spinner=False)
def ccl_referencia():
    """Dólar CCL de referencia (contado con liquidación) para comparar contra el CCL implícito."""
    try:
        r = requests.get("https://dolarapi.com/v1/dolares/contadoconliqui", timeout=15)
        r.raise_for_status()
        d = r.json()
        return float(d.get("venta") or d.get("compra"))
    except Exception:
        try:
            h = dolar_hist("contadoconliqui")
            return float(h["valor"].iloc[-1]) if len(h) else None
        except Exception:
            return None


@st.cache_data(persist="disk", ttl=600, show_spinner=False)
def cauciones_ars():
    """Tasas de cauciones en pesos por plazo (TNA). Devuelve dict plazo(días) -> TNA %."""
    try:
        r = requests.get(f"{API}/finanzas/cauciones/ars", timeout=20)
        r.raise_for_status()
        out = {}
        for x in r.json():
            try:
                pl = int(x["plazo"]); ta = float(x["tasaActual"])
                if ta > 0:
                    out[pl] = ta
            except Exception:
                continue
        return out
    except Exception:
        return {}


@st.cache_data(persist="disk", ttl=1800, show_spinner=False)
def bonos_cer():
    """Bonos CER (ajustan por inflación): ticker, precio ARS, TIR real % y vencimiento (ArgentinaDatos)."""
    try:
        r = requests.get(f"{API}/finanzas/bonos-cer", timeout=25)
        r.raise_for_status()
        d = r.json()
        filas = []
        for b in d.get("bonos", []):
            try:
                filas.append({"Instrumento": b["ticker"], "Precio ARS": float(b["precioArs"]),
                              "TIR real %": float(b["tirPorcentaje"]), "Vencimiento": b["fechaVencimiento"],
                              "Volumen": float(b.get("volumen") or 0)})
            except Exception:
                continue
        return pd.DataFrame(filas), d.get("fechaActualizacion", "")
    except Exception:
        return pd.DataFrame(), ""


OBJ = ["Ver todo", "Guardar a corto plazo", "Ganarle a la inflación"]


def hint_objetivo(corto, infl, pista=None):
    if corto:
        H(E.hint("<b>Corto plazo:</b> fondos de mercado de dinero (30 días) y letras que vencen pronto. Las cauciones todavía no están "
                       "cargadas. Es un filtro informativo, no una recomendación: un fondo de mercado de dinero no garantiza rendimiento y una "
                       "letra solo devuelve lo prometido si la mantenés hasta el vencimiento."))
    elif infl:
        H(E.hint("<b>Inflación:</b> muestra lo que rinde por encima de la inflación <b>esperada</b> (la del REM del BCRA, que podés cambiar). "
                       "Los bonos CER (indexados) todavía no están cargados. Es un filtro informativo: lo que pasó no garantiza lo que va a pasar."))
    elif pista:
        H(E.hint(pista))


def selector_objetivo(key, pista=None, con_hint=True):
    H('<div class="eyebrow m" style="margin-bottom:6px">¿Qué querés lograr?</div>')
    obj = st.segmented_control("¿Qué querés lograr?", OBJ, default=OBJ[0], key=key, label_visibility="collapsed") or OBJ[0]
    corto, infl = obj == OBJ[1], obj == OBJ[2]
    if con_hint:
        hint_objetivo(corto, infl, pista)
    return corto, infl


def _plano(x):
    return unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower()


@st.cache_data(persist="disk", ttl=6 * 3600, show_spinner=False)
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
@st.cache_data(persist="disk", ttl=3600, show_spinner="Descargando precios de la cartera...")
def precios_cartera(tickers, inicio):
    d = yf.download(list(tickers), start=inicio, auto_adjust=False, progress=False)["Close"]
    if isinstance(d, pd.Series):
        d = d.to_frame(tickers[0])
    return d.ffill()


ACT_FCI, ACT_BONO = "FCI|", "BONO|"


def nombre_activo(k):
    k = str(k)
    if k.startswith(ACT_FCI):
        return "FCI · " + k[len(ACT_FCI):]
    if k.startswith(ACT_BONO):
        return k[len(ACT_BONO):] + " (bono/letra)"
    return k


def catalogo_bonos():
    """Letras, bonos soberanos y ONs del archivo cronogramas.json: clave -> etiqueta, ticker de precio, moneda y pagos."""
    c = cargar_cronogramas()
    cat = {}
    for l in c["letras"]:
        cat[l["ticker"]] = {"etq": f"{l['ticker']} · Letra en pesos", "px": l["ticker"], "ars": True,
                            "flujos": [(l["vencimiento"], l["pago_final"])]}
    for k, v in c["soberanos"].items():
        cat[k] = {"etq": f"{k} · Bono soberano en USD", "px": k + "D", "ars": False, "flujos": v["flujos"]}
    for k, v in c["ons"].items():
        cat[k] = {"etq": f"{k} · {v['nombre']} (ON en USD)", "px": v["precio_ticker"], "ars": False, "flujos": v["flujos"]}
    return cat


@st.cache_data(persist="disk", ttl=6 * 3600, show_spinner=False)
def historial_data912(ticker):
    """Cierre diario por 100 VN (data912, no tiempo real)."""
    r = requests.get(f"https://data912.com/historical/bonds/{ticker}", timeout=40)
    r.raise_for_status()
    d = pd.DataFrame(r.json())
    d["date"] = pd.to_datetime(d["date"])
    return d.drop_duplicates("date").set_index("date")["c"].astype(float).sort_index()


def tipo_api_fci(fd):
    t = _plano((fd or {}).get("tipoRenta", ""))
    for k, v in (("mercado de dinero", "mercadoDinero"), ("renta fija", "rentaFija"),
                 ("renta variable", "rentaVariable"), ("renta mixta", "rentaMixta")):
        if k in t:
            return v
    return "rentaFija"


@st.cache_data(persist="disk", ttl=3600, show_spinner="Descargando la evolución del fondo...")
def vcp_fondo(tipos, nombre, ini, fin):
    """Valor de la cuotaparte en fechas semanales entre ini y fin (se interpola entre fechas)."""
    fechas = sorted({f.normalize() for f in list(pd.date_range(ini, fin, freq="7D")) + [pd.Timestamp(fin)]})
    for tipo in tipos:
        vals = []
        for f in fechas:
            df = fci_cercano(tipo, f.date())
            fila = df[df["fondo"] == nombre] if len(df) else df
            vals.append(float(fila["vcp"].iloc[0]) if len(fila) else np.nan)
        if sum(v == v for v in vals) >= 2:
            return fechas, vals
    return fechas, [np.nan] * len(fechas)


def datos_cartera(keys, inicio, mep):
    """Precios en USD por unidad (acción, cuotaparte o VN) y pagos de bonos en USD por VN, indexados por día hábil."""
    idx = pd.bdate_range(inicio, pd.Timestamp.today().normalize())
    mep_i = None if mep is None else mep.reindex(mep.index.union(idx)).ffill().bfill().reindex(idx)
    cols, pagos = {}, pd.DataFrame(0.0, index=idx, columns=list(keys))
    acciones = [k for k in keys if "|" not in k]
    if acciones:
        c = precios_cartera(tuple(acciones), inicio)
        for t in acciones:
            if t in c.columns and not c[t].dropna().empty:
                cols[t] = c[t].reindex(c.index.union(idx)).ffill().reindex(idx)
    for k in [k for k in keys if k.startswith(ACT_FCI)]:
        nombre = k[len(ACT_FCI):]
        fd = buscar_fondo(detalle_fondos(), nombre)
        tipos = [tipo_api_fci(fd)] + [t for t in TIPOS_FCI.values() if t != tipo_api_fci(fd)]
        fechas, vals = vcp_fondo(tuple(tipos), nombre, str(idx[0].date()), str(idx[-1].date()))
        sv = pd.Series(vals, index=fechas).dropna()
        if sv.empty:
            continue
        sv = sv.reindex(sv.index.union(idx)).interpolate(method="time").reindex(idx).ffill().bfill()
        en_usd = "dolar" in _plano((fd or {}).get("moneda", ""))
        if not en_usd and mep_i is None:
            raise ValueError("Para un fondo en pesos hace falta el dólar MEP histórico, que no está disponible ahora.")
        cols[k] = sv if en_usd else sv / mep_i
    cat = catalogo_bonos() if any(k.startswith(ACT_BONO) for k in keys) else {}
    for k in [k for k in keys if k.startswith(ACT_BONO)]:
        info = cat.get(k[len(ACT_BONO):])
        if info is None:
            continue
        if info["ars"] and mep_i is None:
            raise ValueError("Para una letra en pesos hace falta el dólar MEP histórico, que no está disponible ahora.")
        h = historial_data912(info["px"])
        sb = h.reindex(h.index.union(idx)).ffill().reindex(idx) / 100
        sb = sb / mep_i if info["ars"] else sb
        pos_venc = idx.searchsorted(pd.Timestamp(max(f for f, _ in info["flujos"])))
        if pos_venc < len(idx):
            sb.iloc[pos_venc:] = 0.0                      # vencido: ya no vale nada, el último pago se acreditó como efectivo
        cols[k] = sb
        for f, m in info["flujos"]:
            fd_ = pd.Timestamp(f)
            if fd_ < idx[0] or fd_ > idx[-1]:
                continue
            pos = idx.searchsorted(fd_)
            pagos.iloc[pos, pagos.columns.get_loc(k)] += (m / 100) / (mep_i.iloc[pos] if info["ars"] else 1.0)
    return pd.DataFrame(cols, index=idx), pagos


def calcular_cartera(ops, close, mep=None, pagos=None):
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
    if pagos is not None:   # cupones y amortizaciones de bonos: entran como efectivo, no como aporte
        p = pagos.reindex(index=idx, columns=close.columns).fillna(0.0)
        cash = cash + (qty.shift(1).fillna(0.0) * p).sum(axis=1).cumsum()
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


@st.cache_data(persist="disk", ttl=3600, show_spinner=False)
def precios_indice(inicio):
    d = yf.download("^GSPC", start=inicio, auto_adjust=True, progress=False)["Close"].squeeze().dropna()
    return _limpia_fecha(d.copy())


def benchmark_sp(res, spx, usd=True):
    """Qué habría pasado invirtiendo los mismos aportes y retiros en el S&P 500: (valor, rendimiento acumulado %)."""
    px = spx.reindex(res.index.union(spx.index)).ffill().reindex(res.index).bfill()
    flujo = res["flujo_usd"]
    val = (flujo / px).cumsum() * px
    if not usd and "mep" in res:
        val, flujo = val * res["mep"], flujo * res["mep"]
    return val, ((1 + retorno_diario(val, flujo)).cumprod() - 1) * 100


def resumen_cartera(v, f):
    r = retorno_diario(v, f)
    fl = f[f != 0]
    tir = xirr(list(fl.index), list(fl.values), v.iloc[-1], v.index[-1]) if len(fl) and (v.index[-1] - fl.index[0]).days >= 60 else np.nan
    return r, {"Valor actual": v.iloc[-1], "Aportes netos (depósitos − retiros)": f.sum(), "Ganancia": v.iloc[-1] - f.sum(),
               "Rendimiento ajustado por aportes (TWR) %": ((1 + r).prod() - 1) * 100, "TIR anual del dinero %": tir * 100}


def area_alt(df, c1="#6A4FA0", c2="#B3A58F", cero=False):
    d = df.copy()
    d.index.name = "Fecha"
    cols = list(d.columns)
    largo = d.reset_index().melt("Fecha", var_name="Serie", value_name="Valor")
    base = alt.Chart(largo).encode(
        x=alt.X("Fecha:T", axis=alt.Axis(title=None, format="%b", grid=False, labelColor="#8A7A6C", tickCount=6)),
        y=alt.Y("Valor:Q", axis=alt.Axis(title=None, gridColor="#EFEAE1", labelColor="#8A7A6C"), scale=alt.Scale(zero=cero)),
        color=alt.Color("Serie:N", scale=alt.Scale(domain=cols, range=[c1, c2][:len(cols)]),
                        legend=alt.Legend(orient="bottom", title=None, labelColor="#7C746B", symbolType="stroke")))
    uno = base.transform_filter(alt.datum.Serie == cols[0])
    out = uno.mark_area(opacity=0.14, line=False) + uno.mark_line(strokeWidth=2.6)
    if len(cols) > 1:
        out = out + base.transform_filter(alt.datum.Serie == cols[1]).mark_line(strokeWidth=2, strokeDash=[5, 5])
    return out.properties(height=210).configure_view(strokeWidth=0)


MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def historial_html(ed):
    """Tabla de solo lectura con los últimos movimientos."""
    d = ed.dropna(subset=["Fecha", "Operación"]).copy()
    if d.empty:
        return '<div class="sub">Todavía no cargaste movimientos.</div>'
    d["_f"] = pd.to_datetime(d["Fecha"])
    d = d.sort_values("_f", ascending=False)
    txt = lambda x: "" if pd.isna(x) else str(x)
    rows = []
    for _, o in d.head(20).iterrows():
        op = o["Operación"]
        if op in ("Depósito", "Retiro"):
            det, tipo = E.num(o["Monto"], 2, "US$ " if o["Moneda"] == "USD" else "$ "), "pur"
        elif op == "Cambio":
            det, tipo = f"{E.num(o['Cantidad'], 2)} {E.esc(nombre_activo(txt(o['Ticker'])))} → {E.esc(nombre_activo(txt(o['Ticker destino'])))}", "sand"
        else:
            det, tipo = f"{E.num(o['Cantidad'], 2)} {E.esc(nombre_activo(txt(o['Ticker'])))}", "sand"
        rows.append([E.esc(o["_f"].strftime("%d/%m/%Y")), E.chip(op, tipo), f'<span class="strong">{det}</span>'])
    pie = f'<div class="sub" style="font-size:.85rem;margin-top:8px">Mostrando los últimos {min(20, len(d))} de {len(d)} movimientos.</div>'
    return E.tabla([("Fecha", "l"), ("Operación", "l"), ("Detalle", "l")], rows) + pie


# ----------------------------------------------------------------------------
# Renta fija: cronogramas (archivo del repo) y precios en vivo (data912)
# ----------------------------------------------------------------------------
@st.cache_data(persist="disk", ttl=3600)
def cargar_cronogramas():
    return json.loads((Path(__file__).parent / "cronogramas.json").read_text(encoding="utf-8"))


@st.cache_data(persist="disk", ttl=600, show_spinner="Descargando precios de letras, bonos y ONs...")
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


def f_num(d, pref="", suf=""):
    return lambda v: E.num(v, d, pref, suf)


def f_strong(d, suf=""):
    return lambda v: f'<span class="strong">{E.num(v, d, suf=suf)}</span>'


def f_fecha(v):
    return E.esc(pd.to_datetime(v).strftime("%d/%m/%Y"))


def f_chip_real(v):
    return E.chip(E.num(v, 2, suf="%", signo=True), "up" if v >= 0 else "down")


def tabla_bonos(filas, flujos_por_id, key, liq, aviso_vacio, columnas):
    """columnas: lista de (encabezado, clave, función de formato). Un clic sobre el instrumento muestra sus fechas de pago."""
    if not filas:
        st.warning(aviso_vacio)
        return
    df = pd.DataFrame(filas).sort_values("Vencimiento").reset_index(drop=True)
    ids = list(df["Instrumento"])
    sel = st.session_state.get(key + "_sel_id")
    if sel not in ids:
        sel = ids[0]
    rows = []
    for _, r in df.iterrows():
        celdas = [E.activo(r["Instrumento"], r.get("Sub", ""), str(r["Instrumento"])[:2])]
        celdas += [fmt(r[clave]) if clave in r.index else "-" for _, clave, fmt in columnas]
        rows.append(celdas)
    cols = [("Instrumento", "l")] + [(h, "l") for h, _, _ in columnas]
    izq, der = st.columns([2.3, 1.1], gap="medium")
    with izq:
        H('<div class="sub" style="font-size:.9rem;margin:0 0 6px 4px">Hacé clic en un instrumento para ver sus fechas de pago.</div>')
        clic = tabla_click(html=E.tabla(cols, rows, compacta=True, ids=ids), css=E.css_texto(), selected=sel,
                           key=key + "_tabla", default=None)
        if clic in ids:
            sel = clic
        st.session_state[key + "_sel_id"] = sel
    with der:
        fl = [(f, m) for f, m in flujos_por_id[sel] if date.fromisoformat(f) > liq]
        cron = [[f_fecha(f), E.num((date.fromisoformat(f) - liq).days, 0, ""), f'<span class="strong">{E.num(m, 2)}</span>'] for f, m in fl]
        H(E.cronograma_card(sel, df.loc[df["Instrumento"] == sel, "Sub"].iloc[0], cron))
        st.caption("Para bonos que amortizan, cada pago mezcla cupón y devolución de capital. Días: desde la liquidación estimada.")

    # Bonos similares: mismo tipo (= misma clase de riesgo) y duración parecida, para evaluar un cambio
    if "Duración (años)" in df.columns and "TIR (TEA) %" in df.columns:
        fila_sel = df[df["Instrumento"] == sel].iloc[0]
        sdur, stir = fila_sel["Duración (años)"], fila_sel["TIR (TEA) %"]
        otros = df[(df["Instrumento"] != sel) & df["Duración (años)"].notna()].copy()
        if len(otros) and not pd.isna(sdur):
            otros["dd"] = (otros["Duración (años)"] - sdur).abs()
            sim = otros.sort_values("dd").head(4)
            st.markdown(f"**Bonos parecidos a {sel}** (misma clase de riesgo, duración similar)")
            filas_sim = []
            for _, b in sim.iterrows():
                dtir = b["TIR (TEA) %"] - stir
                chip = E.chip(E.num(dtir, 2, suf=" p.p.", signo=True), "up" if dtir > 0.05 else ("down" if dtir < -0.05 else "flat"))
                filas_sim.append([E.activo(b["Instrumento"], b.get("Sub", ""), str(b["Instrumento"])[:2]),
                                  E.num(b["Duración (años)"], 2, suf=" a"),
                                  f'<span class="strong">{E.num(b["TIR (TEA) %"], 2, suf="%")}</span>', chip])
            H(E.tabla([("Instrumento", "l"), ("Duración", "l"), ("TIR", "l"), (f"vs. {sel}", "l")], filas_sim, compacta=True))
            st.caption(f"Comparado con {sel} (duración {E.num(sdur, 2)} años, TIR {E.num(stir, 2)}%). "
                       "Si otro bono de **duración parecida** rinde más (verde), puede convenir cambiarte: tomás más tasa "
                       "sin cambiar casi la sensibilidad a las tasas ni el tipo de riesgo. Igual mirá el volumen y el spread antes.")


# ----------------------------------------------------------------------------
# Pestañas
# ----------------------------------------------------------------------------
panel_mercado = panorama_mercado()
VENTANA = 4
if "pano_i" not in st.session_state:
    st.session_state.pano_i = 0
max_i = max(0, len(panel_mercado) - VENTANA)
st.session_state.pano_i = min(st.session_state.pano_i, max_i)


def mover_panorama(d):
    st.session_state.pano_i = max(0, min(max_i, st.session_state.pano_i + d))


h1, h2, h3, h4 = st.columns([10, 1.3, 0.8, 0.8], vertical_alignment="center")
Hc(h1, '<div style="font-size:1.4rem;font-weight:500;letter-spacing:-0.02em">Panorama de mercado</div>'
        '<div class="muted" style="font-size:.85rem">Datos informativos, no constituyen recomendación de inversión</div>')
Hc(h2, f'<div class="muted" style="text-align:right">{st.session_state.pano_i + 1} / {max_i + 1}</div>')
h3.button("‹", key="pano_prev", on_click=mover_panorama, args=(-1,), disabled=st.session_state.pano_i == 0)
h4.button("›", key="pano_next", on_click=mover_panorama, args=(1,), disabled=st.session_state.pano_i >= max_i)
if panel_mercado:
    vis = panel_mercado[st.session_state.pano_i:st.session_state.pano_i + VENTANA]
    H(E.kpis([E.kpi_card(i["titulo"], i["sub"], i["valor"], i["delta"], i["tipo"], i["flecha"], i["serie"], i["ayuda"])
                    for i in vis]))
else:
    st.caption("No se pudieron cargar los indicadores del mercado en este momento.")
H('<div style="height:10px"></div>')

def chip_yield(v):
    if pd.isna(v) or v == 0:
        return E.chip("No paga", "flat")
    t = "org" if v >= 6 else ("up" if v >= 3 else ("yel" if v >= 1.5 else "down"))
    return E.chip(E.num(v, 2, suf="%"), t)


def chip_roe(v):
    return "-" if pd.isna(v) else E.chip(E.num(v, 1, suf="%"), "up" if v >= 15 else ("yel" if v >= 8 else "down"))


def chip_deuda(v):
    return "-" if pd.isna(v) else E.chip(E.num(v, 1, suf="x"), "up" if v <= 2 else ("yel" if v <= 4 else "down"))


def chip_veredicto(t):
    if t.startswith("Barata"):
        return E.chip(t, "up")
    if t.startswith("Cara"):
        return E.chip(t, "down")
    return E.chip(t, "flat") if t == "En línea" else f'<span class="muted">{E.esc(t)}</span>'


def barra_rango(p):
    if pd.isna(p):
        return "-"
    return (f'<div style="display:flex;align-items:center;gap:7px"><div class="bar" style="width:50px;margin:0;background:#E7E0D5">'
            f'<i style="width:{max(2, min(100, p)):.0f}%;background:#8C6FB3"></i></div><span>{p:.0f}%</span></div>')


def filtro_busqueda(df, texto):
    """Filtra un DataFrame de activos (índice=ticker, col 'Nombre') por nombre o ticker."""
    if not texto or not texto.strip():
        return df
    t = texto.strip().upper()
    mask = df.index.to_series().str.upper().str.contains(t, regex=False) | \
           df["Nombre"].str.upper().str.contains(t, regex=False)
    return df[mask]


def controles_busqueda_fav(tabla, pref, gestionar=True):
    """Buscador + (opcional) multiselect de favoritas. Devuelve (texto_busqueda, set_favoritas).
    Las favoritas viven en session_state['fav_acciones'] y se comparten entre pestañas; se
    gestionan (agregar/quitar) solo donde gestionar=True, para no tener dos selectores en conflicto."""
    favs = st.session_state.setdefault("fav_acciones", set())
    if not gestionar:
        busqueda = st.text_input("Buscar", placeholder="🔍 Nombre o ticker (ej: Apple, AAPL)",
                                 label_visibility="collapsed", key=f"{pref}_busq")
        return busqueda, set(favs)
    cb1, cb2 = st.columns([2, 3], vertical_alignment="bottom")
    busqueda = cb1.text_input("Buscar", placeholder="🔍 Nombre o ticker (ej: Apple, AAPL)",
                              label_visibility="collapsed", key=f"{pref}_busq")
    # Solo ofrecer como favoritas las que realmente tienen CEDEAR/cotización local
    elegibles = tabla[tabla["Tiene CEDEAR"]] if "Tiene CEDEAR" in tabla.columns else tabla
    opciones = list(elegibles.index)
    nombres = {tk: elegibles.loc[tk, "Nombre"] for tk in opciones}
    fav_sel = cb2.multiselect("★ Favoritas (aparecen primero)",
                              options=sorted(opciones, key=lambda k: nombres[k]),
                              default=sorted(favs & set(opciones)),
                              format_func=lambda tk: f"★ {nombres[tk]} ({tk})",
                              key=f"{pref}_fav", label_visibility="collapsed",
                              placeholder="★ Elegí tus favoritas para fijarlas arriba")
    st.session_state["fav_acciones"] = set(fav_sel)
    return busqueda, set(fav_sel)


tab1, tab2, tab_rv, tab3, tab4, tab5, tab6 = st.tabs([
    "Análisis técnico", "Análisis fundamental", "Cartera acciones", "Fondos (FCI)", "Simulador de tasas", "Renta fija", "Mi cartera",
])

close, vol = precios(tuple(TICKERS))
close = close.dropna(axis=1, how="all")
if close.empty:
    st.warning("No se pudieron obtener precios de Yahoo Finance en este momento. Recargá la página en unos minutos.")
    st.stop()

# Dólar MEP, para convertir las acciones argentinas (que cotizan solo en pesos) a un equivalente en USD
try:
    _mep_df = mep_hist()
    MEP_HOY = float(_mep_df["mep"].iloc[-1]) if len(_mep_df) else None
except Exception:
    MEP_HOY = None

# Precios de CEDEARs en BYMA (ARS + volumen local)
cedear_ars, cedear_vol_local = precios_cedear_ars(tuple(close.columns))

tabla = pd.DataFrame({
    "Nombre": [INFO[t][0] for t in close.columns],
    "Sector": [INFO[t][1] for t in close.columns],
    "Precio USD": close.iloc[-1].values,
    "Precio ARS": cedear_ars.reindex(close.columns).values,
    "Vol. BYMA": cedear_vol_local.reindex(close.columns).values,
    "Volatilidad %": (close.pct_change().tail(60).std() * np.sqrt(252) * 100).values,
    "Volumen USD (M)": ((close * vol[close.columns]).tail(30).mean() / 1e6).values,
    "RSI diario": close.apply(rsi).iloc[-1].values,
}, index=close.columns)
tabla.index.name = "Ticker"
tabla["Var. diaria %"] = ((close.iloc[-1] / close.iloc[-2] - 1) * 100).values

try:
    r45, ult_intra = rsi_45m(tuple(tabla.index))
    tabla["RSI 45 min"] = r45.reindex(tabla.index)
except Exception:
    ult_intra = None
    tabla["RSI 45 min"] = np.nan

# Acciones argentinas (cotizan solo en pesos en BYMA, no tienen contraparte en Nueva York)
close_ar, vol_ar = precios_ar(tuple(TICKERS_AR))
close_ar = close_ar.dropna(axis=1, how="all")
if not close_ar.empty and MEP_HOY:
    tabla_ar = pd.DataFrame({
        "Nombre": [INFO_AR[t][0] for t in close_ar.columns],
        "Sector": ["🇦🇷 " + INFO_AR[t][1] for t in close_ar.columns],
        "Precio USD": (close_ar.iloc[-1] / MEP_HOY).values,
        "Precio ARS": close_ar.iloc[-1].values,
        "Vol. BYMA": vol_ar[close_ar.columns].tail(5).mean().values,
        "Volatilidad %": (close_ar.pct_change().tail(60).std() * np.sqrt(252) * 100).values,
        "Volumen USD (M)": ((close_ar * vol_ar[close_ar.columns]).tail(30).mean() / MEP_HOY / 1e6).values,
        "RSI diario": close_ar.apply(rsi).iloc[-1].values,
    }, index=close_ar.columns)
    tabla_ar.index.name = "Ticker"
    tabla_ar["Var. diaria %"] = ((close_ar.iloc[-1] / close_ar.iloc[-2] - 1) * 100).values
    try:
        r45_ar, ult_intra_ar = rsi_45m(tuple(tabla_ar.index), sufijo=".BA",
                                        tz="America/Argentina/Buenos_Aires", inicio_min=660)
        tabla_ar["RSI 45 min"] = r45_ar.reindex(tabla_ar.index)
    except Exception:
        ult_intra_ar = None
        tabla_ar["RSI 45 min"] = np.nan
    tabla = pd.concat([tabla, tabla_ar], sort=True)
    tabla.index.name = "Ticker"
else:
    ult_intra_ar = None

# Liquidez: cada mercado tiene su propio piso de volumen (ver MIN_VOLUMEN_USD_M_AR)
tabla["Es AR"] = tabla["Sector"].str.startswith("🇦🇷")
# Un CEDEAR solo tiene sentido mostrarlo si cotiza localmente (Yahoo tiene su precio en BYMA).
# Si no hay precio en pesos, es una acción sin CEDEAR vigente o sin dato local: se oculta.
tabla["Tiene CEDEAR"] = tabla["Es AR"] | tabla["Precio ARS"].notna()
tabla["Liquida"] = tabla["Tiene CEDEAR"] & np.where(
    tabla["Es AR"], tabla["Volumen USD (M)"] >= MIN_VOLUMEN_USD_M_AR,
    tabla["Volumen USD (M)"] >= MIN_VOLUMEN_USD_M)

# Dólar CCL implícito por CEDEAR = Precio ARS × ratio / Precio USD. Solo para los que tienen ratio
# cargado y no son acciones argentinas. Desvío = cuánto se aparta del CCL de referencia.
CCL_REF = ccl_referencia()
tabla["Ratio"] = [np.nan if es_ar else RATIOS_CEDEAR.get(t, np.nan)
                  for t, es_ar in zip(tabla.index, tabla["Es AR"])]
tabla["CCL implícito"] = tabla["Precio ARS"] * tabla["Ratio"] / tabla["Precio USD"]
tabla["Desvío CCL %"] = (tabla["CCL implícito"] / CCL_REF - 1) * 100 if CCL_REF else np.nan

# Distancia del precio a sus medias móviles de 30, 50 y 200 ruedas (%). Positivo = precio por
# encima de la media (tendencia alcista); negativo = por debajo. Sirve para ver tendencia.
for _n in (30, 50, 200):
    _partes = [(close.iloc[-1] / close.rolling(_n).mean().iloc[-1] - 1) * 100]
    if not close_ar.empty:
        _partes.append((close_ar.iloc[-1] / close_ar.rolling(_n).mean().iloc[-1] - 1) * 100)
    tabla[f"MA{_n} %"] = pd.concat(_partes).reindex(tabla.index)

# --- 1. CEDEARs: trading ------------------------------------------------------
with tab1:
    H('<div class="eyebrow m">Análisis técnico</div><div class="h2">RSI, medias móviles y pre-market</div>')
    estado_ny, ahora_ny = sesion_eeuu()
    etiqueta_ses = {"pre": "🌅 Pre-market abierto", "regular": "🟢 Mercado abierto",
                    "after": "🌙 After-hours", "cerrado": "⏸️ Mercado cerrado"}[estado_ny]
    tabla["Pre %"] = np.nan
    tabla["Pre precio"] = np.nan
    tabla["RSI prov"] = np.nan
    precios_en_vivo = False
    # Con el mercado ABIERTO, el "cierre diario" todavía es el de ayer. Usamos el precio en vivo de hoy
    # para el precio mostrado y la variación del día (solo CEDEARs; las acciones argentinas van por BYMA).
    if estado_ny == "regular":
        try:
            cedear_vivo = tuple(sorted(tabla.index[(~tabla["Es AR"]) & tabla["Liquida"]]))
            ext_vivo = precios_extended(cedear_vivo)
            hoy_ny = ahora_ny.date()
            for tk, (p, ts) in ext_vivo.items():
                if tk in tabla.index and tk in close.columns:
                    s = close[tk].dropna()
                    if len(s) >= 2:
                        base = s.iloc[-2] if s.index[-1].date() == hoy_ny else s.iloc[-1]
                        tabla.loc[tk, "Precio USD"] = p
                        tabla.loc[tk, "Var. diaria %"] = (p / base - 1) * 100
                        precios_en_vivo = True
            if precios_en_vivo and CCL_REF:
                tabla["CCL implícito"] = tabla["Precio ARS"] * tabla["Ratio"] / tabla["Precio USD"]
                tabla["Desvío CCL %"] = (tabla["CCL implícito"] / CCL_REF - 1) * 100
        except Exception:
            pass

    if precios_en_vivo:
        txt = f"🟢 Precios de CEDEARs **en vivo** ({ahora_ny:%H:%M} hora de Nueva York). Acciones argentinas y datos diarios al {close.index[-1].date()}"
    else:
        txt = f"Datos diarios al {close.index[-1].date()}"
    txt += (f" · intradiario hasta {ult_intra:%d/%m %H:%M} (NY)" if ult_intra is not None
            else " · RSI de 45 min no disponible ahora")
    if ult_intra_ar is not None:
        txt += f" · acciones argentinas hasta {ult_intra_ar:%d/%m %H:%M} (Argentina)"
    st.caption(txt)

    lo, hi = RSI_BAJO, RSI_ALTO
    busqueda, favs = controles_busqueda_fav(tabla, "trad")
    c1, c2 = st.columns([2, 3], vertical_alignment="bottom")
    vol_min = c1.slider("Volatilidad mínima % (descarta las que casi no se mueven)", 0, 100, 30, step=5)
    filtro = c2.segmented_control("Mostrar", ["Todas", "Sobreventa", "Sobrecompra"], default="Todas", key="rsi_filtro") or "Todas"
    OPC_MA = ["Todas", "Por encima de MA30", "Por debajo de MA30", "Por encima de MA50",
              "Por debajo de MA50", "Por encima de MA200", "Por debajo de MA200"]
    filtro_ma = st.selectbox("Filtrar por media móvil", OPC_MA, index=0, key="ma_filtro",
                             help="Mostrá solo las que cotizan por encima (tendencia alcista) o por debajo (bajista) "
                                  "de su promedio de 30, 50 o 200 ruedas.")

    ver_pre = st.toggle(f"Ver pre-market / after-hours de EE.UU.  ·  {etiqueta_ses} ({ahora_ny:%H:%M} NY)",
                        value=False, key="ver_pre",
                        help="Muestra cómo se mueve la acción en Nueva York fuera del horario regular (pre-market y after-hours) "
                             "y un RSI diario provisorio como si la rueda cerrara a ese precio. Solo aplica a CEDEARs.")
    if ver_pre:
        if estado_ny == "cerrado":
            st.info("Ahora mismo no hay operaciones en Nueva York (ni pre-market ni after-hours). "
                    "El pre-market suele arrancar a las 5:00 hora de Argentina.")
        else:
            cedear_liq = tuple(sorted(tabla.index[(~tabla["Es AR"]) & tabla["Liquida"]]))
            ext = precios_extended(cedear_liq)
            for tk, (p, ts) in ext.items():
                if tk not in close.columns:
                    continue
                prev = close[tk].dropna()
                if not len(prev):
                    continue
                tabla.loc[tk, "Pre precio"] = p
                tabla.loc[tk, "Pre %"] = (p / prev.iloc[-1] - 1) * 100
                s = prev.copy()
                if ts.date() == s.index[-1].date():
                    s.iloc[-1] = p            # reemplaza el cierre de hoy por el precio en curso
                else:
                    s.loc[pd.Timestamp(ts.date())] = p   # agrega la rueda en curso (provisoria)
                try:
                    tabla.loc[tk, "RSI prov"] = float(rsi(s).iloc[-1])
                except Exception:
                    pass
            n_pre = int(tabla["Pre %"].notna().sum())
            st.caption(f"{etiqueta_ses}. Mostrando el precio de {n_pre} CEDEARs fuera del horario regular y, al lado del RSI diario, "
                       "un **RSI provisorio** (RSI) como si la rueda cerrara a ese precio. El pre-market tiene poco volumen: "
                       "los movimientos pueden revertirse cuando abre el mercado.")

    # --- Dólar CCL implícito y brecha ---
    ccl_tab = tabla[tabla["Ratio"].notna() & tabla["CCL implícito"].notna() & tabla["Liquida"]].copy()
    if CCL_REF and len(ccl_tab):
        with st.expander(f"💱 Dólar CCL implícito y brecha · referencia CCL ${E.num(CCL_REF, 0)}", expanded=False):
            st.caption("El CCL implícito es el dólar que te queda comprando la acción afuera y vendiendo el CEDEAR acá "
                       "(Precio ARS × ratio ÷ Precio USD). Si está **por encima** del CCL de referencia, el CEDEAR está caro "
                       "(conviene vender CEDEAR / comprar afuera); si está **por debajo**, está barato. Ordenado por desvío. "
                       "Los ratios están cargados a mano (sincronizados con BYMA a sep-2026): verificalos en tu broker.")
            orden_ccl = st.radio("Ordenar", ["Mayor sobreprecio", "Mayor descuento", "Alfabético"],
                                 horizontal=True, key="ccl_orden", label_visibility="collapsed")
            cc = ccl_tab.sort_values("Desvío CCL %", ascending=(orden_ccl != "Mayor sobreprecio"))
            if orden_ccl == "Alfabético":
                cc = ccl_tab.sort_values("Nombre")
            def _desvio_chip(d):
                if pd.isna(d):
                    return "-"
                tipo = "down" if d > 0.3 else ("up" if d < -0.3 else "flat")  # caro=rojo, barato=verde
                signo = "+" if d > 0 else ""
                return E.chip(f"{signo}{E.num(d, 2, suf='%')}", tipo)
            filas_ccl = [[E.activo(r["Nombre"], tk, tk[:2]),
                          E.num(r["Precio USD"], 2, "US$ "), E.num(r["Precio ARS"], 0, "AR$ "),
                          E.num(r["Ratio"], 0, suf=":1"), E.num(r["CCL implícito"], 0, "$ "),
                          _desvio_chip(r["Desvío CCL %"])]
                         for tk, r in cc.iterrows()]
            H(E.tabla([("Activo", "l"), ("Precio USD", "l"), ("Precio CEDEAR", "l"), ("Ratio", "l"),
                       ("CCL implícito", "l"), ("Desvío vs CCL", "l")], filas_ccl, compacta=True))

    def _aplicar_filtro_ma(df):
        if filtro_ma == "Todas":
            return df
        n = 30 if "MA30" in filtro_ma else (50 if "MA50" in filtro_ma else 200)
        col = f"MA{n} %"
        if "encima" in filtro_ma:
            return df[df[col] > 0]
        return df[df[col] < 0]

    if busqueda.strip():
        # Si buscás algo puntual, mostramos todo lo que coincida (ignora volatilidad y sobreventa,
        # para que siempre lo encuentres aunque se mueva poco).
        t = filtro_busqueda(tabla[tabla["Liquida"]], busqueda)
    else:
        t = tabla[(tabla["Volatilidad %"] >= vol_min) & tabla["Liquida"]]
        if filtro == "Sobreventa":
            t = t[(t["RSI diario"] < lo) | (t["RSI 45 min"] < lo)]
        elif filtro == "Sobrecompra":
            t = t[(t["RSI diario"] > hi) | (t["RSI 45 min"] > hi)]
        t = _aplicar_filtro_ma(t)

    def _precio_cel(r):
        if r["Es AR"]:
            principal = f'<span class="strong">AR$ {E.num(r["Precio ARS"], 0)}</span>'
            secund = f'<br><span class="muted" style="font-size:12px">≈ US$ {E.num(r["Precio USD"], 2)}</span>' if not pd.isna(r["Precio USD"]) else ""
        else:
            principal = f'<span class="strong">{E.num(r["Precio USD"], 2, "US$ ")}</span>'
            secund = f'<br><span class="muted" style="font-size:12px">AR$ {E.num(r["Precio ARS"], 0)}</span>' if not pd.isna(r["Precio ARS"]) else ""
        extra = ""
        if ver_pre and not r["Es AR"] and not pd.isna(r.get("Pre %", np.nan)):
            d = r["Pre %"]
            cls = "up" if d > 0.05 else ("down" if d < -0.05 else "flat")
            fl = "↑" if d > 0.05 else ("↓" if d < -0.05 else "~")
            etq = {"pre": "PRE", "after": "AFT", "regular": "LIVE", "cerrado": "EXT"}[estado_ny]
            extra = (f'<br><span class="chip ch-{cls}" style="font-size:11px;padding:1px 6px">{etq} {fl} '
                     f'{E.num(abs(d), 2, suf="%")}</span> <span class="muted" style="font-size:11px">US$ {E.num(r["Pre precio"], 2)}</span>')
        return principal + secund + extra

    def _rsi_diario_cel(r):
        base = E.rsi_pill(r["RSI diario"], lo, hi)
        if ver_pre and not pd.isna(r.get("RSI prov", np.nan)):
            base += f'<div class="muted" style="font-size:11px;margin-top:3px">RSI prov. {r["RSI prov"]:.0f}</div>'
        return base

    def _vol_byma(r):
        v = r["Vol. BYMA"]
        if pd.isna(v) or v == 0:
            return '<span class="muted">-</span>'
        if v >= 1e6:
            return E.num(v / 1e6, 1, suf=" M")
        if v >= 1e3:
            return E.num(v / 1e3, 0, suf=" K")
        return E.num(v, 0)

    def _medias_cel(r):
        # Tres líneas apiladas: media (30/50/200) y % del precio respecto a ella.
        # Verde si el precio está por encima de la media; rojo si está por debajo.
        lineas = []
        for n in (30, 50, 200):
            d = r.get(f"MA{n} %", np.nan)
            if pd.isna(d):
                lineas.append(f'<div style="font-size:11.5px;line-height:1.5"><b style="color:#8A7A6C">{n}</b> '
                              f'<span class="muted">—</span></div>')
                continue
            cls = "up" if d >= 0 else "down"
            signo = "+" if d > 0 else ""
            lineas.append(f'<div style="font-size:11.5px;line-height:1.5"><b style="color:#8A7A6C">{n}</b> '
                          f'<span class="chip ch-{cls}" style="font-size:11px;padding:1px 6px">{signo}{E.num(d, 1, suf="%")}</span></div>')
        return "".join(lineas)

    COLS_TRAD = [("Activo", "l"), ("Precio", "l"), ("Vol. BYMA", "l"), ("Volatilidad", "l"),
                 ("Medias móviles", "l"), ("RSI diario", "l"), ("RSI 45 min", "l")]

    def _grupo_trad(titulo, sub, abierto):
        with st.expander(f"{titulo} · {len(sub)} activo" + ("s" if len(sub)!=1 else ""), expanded=abierto):
            filas = [[E.activo(r["Nombre"], tk, tk[:2], var_pct=r["Var. diaria %"]),
                      _precio_cel(r), _vol_byma(r),
                      E.num(r["Volatilidad %"], 2, suf="%"), _medias_cel(r), _rsi_diario_cel(r), E.rsi_pill(r["RSI 45 min"], lo, hi)]
                     for tk, r in sub.iterrows()]
            H(E.variacion_chip(sub["Var. diaria %"].mean()) + E.tabla(COLS_TRAD, filas, clase="t-trading"))

    # Favoritas primero (respetan la búsqueda, pero no el resto de filtros: siempre visibles,
    # salvo las que no tienen CEDEAR/cotización local, que nunca se muestran)
    fav_df = filtro_busqueda(tabla[tabla.index.isin(favs) & tabla["Tiene CEDEAR"]], busqueda)
    if len(fav_df):
        _grupo_trad("★ Favoritas", fav_df.sort_values("Var. diaria %", ascending=False), abierto=True)

    cuerpo = t[~t.index.isin(favs)]
    st.caption(f"{len(t)} de {len(tabla)} activos pasan los filtros, agrupados por sector.")
    if cuerpo.empty and not len(fav_df):
        st.info("Ningún activo pasa los filtros elegidos.")
    for sector in sorted(cuerpo["Sector"].unique()):
        sub = cuerpo[cuerpo["Sector"] == sector].sort_values("Volatilidad %", ascending=False)
        _grupo_trad(sector, sub, abierto=bool(busqueda.strip()))
    H(E.leyenda_rsi(lo, hi))
    st.caption("Medias móviles: % del precio respecto a su promedio de 30, 50 y 200 ruedas. Verde = precio por encima de la media "
               "(tendencia alcista); rojo = por debajo (bajista). Cuanto más largo el plazo (200), más de fondo es la tendencia. "
               "RSI 45 min: velas de 45 minutos armadas desde datos de 15 min (Yahoo, pueden tener demora); fuera del horario de mercado muestra la última rueda. "
               "Volatilidad: desvío de retornos diarios de 60 ruedas, anualizado; descartar las de baja volatilidad evita activos que casi no se mueven. "
               "Las acciones argentinas (🇦🇷) tienen su propio piso de volumen mínimo, porque el mercado local mueve muchos menos dólares que Nueva York. "
               "La barra de cada RSI muestra su valor de 0 a 100. Informativo, no es una recomendación de inversión.")

# --- 2. CEDEARs: dividendos + cara o barata -----------------------------------
with tab2:
    H('<div class="eyebrow m">Análisis fundamental</div><div class="h2">Dividendos y valuación</div>')
    busqueda_d, favs_d = controles_busqueda_fav(tabla, "div", gestionar=False)
    st.caption("Tus favoritas (★) se eligen en la pestaña «CEDEARs · Trading» y también aparecen primero acá.")
    # Para no pedirle datos fundamentales a Yahoo de los 250+ tickers (lento), solo traemos los de
    # las que pasan el filtro de volumen más las favoritas. El resto no se muestra en esta pestaña.
    necesarios = sorted(set(tabla.index[tabla["Liquida"]]) | (favs_d & set(tabla.index)))
    base = tabla.loc[necesarios]
    tickers_yahoo = tuple(tk + ".BA" if base.loc[tk, "Es AR"] else tk for tk in base.index)
    f = fundamentales(tickers_yahoo)
    f.index = base.index
    # Aviso si Yahoo limitó las consultas y faltan fundamentales (se completan al recargar)
    con_pe = int(f["P/E"].notna().sum())
    if con_pe < max(1, int(0.6 * len(f))):
        c_av1, c_av2 = st.columns([4, 1], vertical_alignment="bottom")
        c_av1.warning(f"Yahoo limitó las consultas: por ahora hay datos fundamentales (P/E, ROE, etc.) de "
                      f"{con_pe} de {len(f)} acciones. Se completan solos al recargar la página en un minuto "
                      "(los que ya se bajaron quedan guardados).")
        if c_av2.button("🔄 Reintentar ahora", key="fund_retry"):
            st.rerun()
    divs_raw = dividendos_12m(tickers_yahoo)
    divs = {tk: divs_raw.get(ytk, np.nan) for tk, ytk in zip(base.index, tickers_yahoo)}
    val = base[["Nombre", "Sector", "Precio USD", "Precio ARS", "Volumen USD (M)", "Var. diaria %", "Es AR", "Liquida"]].copy()
    # Para CEDEARs el dividendo que trae Yahoo viene en USD (de la acción en NY); para acciones
    # argentinas viene en pesos (de la acción en BYMA), así que el yield se calcula contra el
    # precio en la misma moneda en la que se pagó el dividendo.
    val["Div. 12m"] = pd.Series(divs)
    val["Yield 12m %"] = np.where(val["Es AR"], val["Div. 12m"] / val["Precio ARS"] * 100,
                                   val["Div. 12m"] / val["Precio USD"] * 100)
    val = val.join(f[["P/E", "P/E futuro", "ROE %", "Deuda/EBITDA"]])
    val.loc[val["Sector"].isin(["Financiero", "🇦🇷 Bancos"]), "Deuda/EBITDA"] = np.nan   # no aplica a bancos y financieras
    rango = pd.concat([
        (close.iloc[-1] - close.min()) / (close.max() - close.min()) * 100,
        (close_ar.iloc[-1] - close_ar.min()) / (close_ar.max() - close_ar.min()) * 100 if not close_ar.empty else pd.Series(dtype=float),
    ])
    val["Posición rango 52 sem. %"] = rango.reindex(val.index)

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
            return "Barata vs sector"
        if r["P/E vs sector"] > 1.2:
            return "Cara vs sector"
        return "En línea"

    val["Veredicto"] = val.apply(veredicto, axis=1)

    solo_pagan = st.toggle("Solo las que pagan dividendos", value=True)

    v = val[val["Liquida"]]
    if solo_pagan and not busqueda_d.strip():   # al buscar algo puntual, no escondas por "paga dividendos"
        v = v[v["Yield 12m %"] > 0]
    v = filtro_busqueda(v, busqueda_d)

    def _precio_div(r):
        if r["Es AR"]:
            principal = f'<span class="strong">AR$ {E.num(r["Precio ARS"], 0)}</span>'
            secund = f'<br><span class="muted" style="font-size:12px">≈ US$ {E.num(r["Precio USD"], 2)}</span>' if not pd.isna(r["Precio USD"]) else ""
        else:
            principal = f'<span class="strong">{E.num(r["Precio USD"], 2, "US$ ")}</span>'
            ars_v = r.get("Precio ARS", np.nan)
            secund = f'<br><span class="muted" style="font-size:12px">AR$ {E.num(ars_v, 0)}</span>' if not pd.isna(ars_v) else ""
        return principal + secund

    def _div_cel(r):
        moneda = "AR$ " if r["Es AR"] else "US$ "
        return E.num(r["Div. 12m"], 2, moneda)

    COLS_DIV = [("Activo", "l"), ("Precio", "l"), ("Div. 12m", "l"), ("Yield 12m", "l"), ("P/E", "l"),
                ("P/E vs sector", "l"), ("ROE", "l"), ("Deuda / EBITDA", "l"), ("Rango 52 sem.", "l"), ("Valuación", "l")]

    def _grupo_div(titulo, sub, abierto):
        with st.expander(f"{titulo} · {len(sub)} activo" + ("s" if len(sub)!=1 else ""), expanded=abierto):
            filas = [[E.activo(r["Nombre"], tk, tk[:2], var_pct=r["Var. diaria %"]),
                      _precio_div(r), _div_cel(r), chip_yield(r["Yield 12m %"]), E.num(r["P/E"], 1),
                      E.num(r["P/E vs sector"], 2, suf="x"), chip_roe(r["ROE %"]), chip_deuda(r["Deuda/EBITDA"]),
                      barra_rango(r["Posición rango 52 sem. %"]), chip_veredicto(r["Veredicto"])]
                     for tk, r in sub.iterrows()]
            H(E.tabla(COLS_DIV, filas, compacta=True, clase="t-div"))

    # Favoritas primero (las que pasan el filtro de liquidez y la búsqueda)
    fav_dv = filtro_busqueda(v[v.index.isin(favs_d)], busqueda_d)
    if len(fav_dv):
        _grupo_div("★ Favoritas", fav_dv.sort_values("Yield 12m %", ascending=False), abierto=True)

    cuerpo_d = v[~v.index.isin(favs_d)]
    st.caption(f"{len(v)} de {len(val)} activos líquidos pasan los filtros, agrupados por sector.")
    for sector in sorted(cuerpo_d["Sector"].unique()):
        sub = cuerpo_d[cuerpo_d["Sector"] == sector].sort_values("Yield 12m %", ascending=False)
        _grupo_div(sector, sub, abierto=bool(busqueda_d.strip()))
    st.markdown(
        "**Yield:** gris no paga · rojo <1,5% · amarillo 1,5–3% · verde 3–6% · naranja ≥6% (revisar por qué es tan alto). "
        "Es bruto: para CEDEARs, sobre la acción en Nueva York (el CEDEAR cobra en pesos y con retención en origen); "
        "para acciones argentinas, sobre el precio en BYMA.  \n"
        "**ROE %** (ganancia sobre el patrimonio de los accionistas): 🟢 15% o más · 🟡 entre 8% y 15% · 🔴 menos de 8% o negativo. "
        "Un patrimonio muy chico (por recompras de acciones) lo infla.  \n"
        "**Deuda/EBITDA** (años de ganancia operativa para pagar la deuda): 🟢 hasta 2 · 🟡 entre 2 y 4 · 🔴 más de 4. "
        "No se muestra para el sector financiero, donde no aplica. Los cortes son convenciones generales: varían por sector.  \n"
        "**¿Cara o barata?** Compara el P/E contra la mediana de su sector en esta lista (barata <0,8× · cara >1,2×). "
        "Es una comparación **relativa**, no un valor intrínseco: una acción puede ser barata porque se esperan ganancias menores."
    )

# --- 2b. Renta variable: cartera de acciones (riesgo + diversificación + CAPM) ----------------
with tab_rv:
    H('<div class="eyebrow m">Renta variable</div><div class="h2">Armá tu cartera de acciones</div>')
    st.caption("Elegí CEDEARs y la app calcula el riesgo de la cartera, te sugiere cuáles sumar para bajarlo "
               "y estima el rendimiento esperado con CAPM. Todo **en dólares** (así el CCL no ensucia el riesgo). "
               "Informativo, no es recomendación de inversión.")

    # Universo: CEDEARs líquidos con precio diario en USD (las acciones argentinas quedan afuera: distinta moneda)
    universo = [t for t in tabla.index[(~tabla["Es AR"]) & tabla["Liquida"]] if t in close.columns]
    universo = sorted(universo, key=lambda t: tabla.loc[t, "Nombre"])
    nombres_u = {t: tabla.loc[t, "Nombre"] for t in universo}

    favs_rv = sorted(st.session_state.get("fav_acciones", set()) & set(universo))
    sel = st.multiselect("Elegí las acciones de tu cartera (2 o más)", options=universo,
                         default=favs_rv[:5] if favs_rv else universo[:4],
                         format_func=lambda t: f"{nombres_u[t]} ({t})", key="rv_sel")

    cA, cB = st.columns(2)
    rf = cA.number_input("Tasa libre de riesgo anual (%)", min_value=0.0, max_value=20.0, value=4.0, step=0.5,
                         help="Rendimiento de un bono del Tesoro de EE.UU. Base del CAPM.") / 100
    prima = cB.number_input("Prima de mercado esperada anual (%)", min_value=0.0, max_value=20.0, value=5.0, step=0.5,
                            help="Cuánto se espera que las acciones rindan por encima de la tasa libre, en promedio y a largo plazo. "
                                 "Es un supuesto tuyo.") / 100

    if len(sel) < 2:
        st.info("Elegí al menos 2 acciones para calcular el riesgo y la diversificación de la cartera.")
    else:
        # Pesos: por defecto equitativos, editables
        with st.expander("Ajustar pesos (por defecto, equitativos)"):
            pesos_df = st.data_editor(
                pd.DataFrame({"Acción": [nombres_u[t] for t in sel], "Ticker": sel,
                              "Peso %": [round(100 / len(sel), 2)] * len(sel)}),
                hide_index=True, width="stretch", key="rv_pesos",
                column_config={"Acción": st.column_config.TextColumn(disabled=True),
                               "Ticker": st.column_config.TextColumn(disabled=True),
                               "Peso %": st.column_config.NumberColumn(min_value=0.0, step=1.0)})
        pesos = pesos_df.set_index("Ticker")["Peso %"].reindex(sel).fillna(0.0).values.astype(float)
        if pesos.sum() <= 0:
            pesos = np.ones(len(sel))
        w = pesos / pesos.sum()

        # Retornos diarios en USD y covarianza anualizada (pairwise, tolera huecos)
        ret_u = close[universo].pct_change()
        COV = ret_u.cov() * 252
        sub_cov = COV.loc[sel, sel].values
        var_port = float(w @ sub_cov @ w)
        vol_port = float(np.sqrt(max(var_port, 0)))
        vol_ind = np.sqrt(np.diag(sub_cov))
        # Contribución de cada acción al riesgo total
        marg = sub_cov @ w
        contrib = (w * marg) / var_port if var_port > 0 else np.zeros(len(sel))

        # Beta vs S&P 500 y retorno esperado por CAPM
        mkt = retornos_sp500()
        betas = {}
        if len(mkt):
            var_m = float(mkt.var())
            for t in sel:
                r = ret_u[t].dropna()
                al = pd.concat([r.rename("a"), mkt.rename("m")], axis=1, join="inner").dropna()
                betas[t] = float(al["a"].cov(al["m"]) / var_m) if len(al) > 20 and var_m > 0 else np.nan
        else:
            betas = {t: np.nan for t in sel}
        er = {t: (rf + betas[t] * prima) * 100 if not pd.isna(betas[t]) else np.nan for t in sel}
        beta_port = float(np.nansum([w[i] * betas[sel[i]] for i in range(len(sel)) if not pd.isna(betas[sel[i]])]))
        er_port = sum(w[i] * er[sel[i]] for i in range(len(sel)) if not pd.isna(er[sel[i]]))

        k1, k2, k3 = st.columns(3)
        k1.metric("Volatilidad de la cartera", f"{vol_port*100:.1f}%", help="Cuánto oscila la cartera por año (desvío anualizado, en USD).")
        k2.metric("Retorno esperado (CAPM)", f"{er_port:.1f}%", help="Libre de riesgo + beta × prima de mercado, ponderado.")
        k3.metric("Beta de la cartera", f"{beta_port:.2f}", help="Sensibilidad al S&P 500. 1 = se mueve como el mercado.")

        def _contrib_bar(c):
            p = max(0, min(100, c * 100))
            return (f'<div style="display:flex;align-items:center;gap:7px"><div class="bar" style="width:60px;margin:0;background:#E7E0D5">'
                    f'<i style="width:{p:.0f}%;background:#6A4FA0"></i></div><span>{c*100:.0f}%</span></div>')
        filas_rv = []
        for i, t in enumerate(sel):
            filas_rv.append([E.activo(nombres_u[t], t, t[:2]), E.num(w[i] * 100, 1, suf="%"),
                             E.num(vol_ind[i] * 100, 1, suf="%"), _contrib_bar(contrib[i]),
                             E.num(betas[t], 2) if not pd.isna(betas[t]) else "-",
                             f'<span class="strong">{E.num(er[t], 1, suf="%")}</span>' if not pd.isna(er[t]) else "-"])
        H(E.tabla([("Acción", "l"), ("Peso", "l"), ("Volatilidad", "l"), ("Aporte al riesgo", "l"),
                   ("Beta", "l"), ("Retorno esp.", "l")], filas_rv, compacta=True))
        st.caption("**Aporte al riesgo**: cuánto del riesgo total de la cartera viene de cada acción (suma 100%). Puede diferir del peso: "
                   "una acción muy correlacionada con el resto aporta más riesgo del que parece.")

        # Recomendador: qué CEDEARs bajarían el riesgo si se sumaran con un 10%
        st.markdown("#### Para bajar el riesgo")
        cand = [t for t in universo if t not in sel]
        res = []
        for c in cand:
            idx = sel + [c]
            try:
                cv = COV.loc[idx, idx].values
            except Exception:
                continue
            if np.isnan(cv).any():
                continue
            w_new = np.append(w * 0.9, 0.10)
            v_new = float(np.sqrt(max(w_new @ cv @ w_new, 0)))
            if v_new < vol_port:
                res.append((c, v_new))
        res.sort(key=lambda x: x[1])
        if not res:
            st.caption("No se encontraron CEDEARs que, sumados, bajen la volatilidad de esta cartera (ya está bastante diversificada "
                       "o faltan datos).")
        else:
            filas_rec = []
            for c, v_new in res[:8]:
                baja = (vol_port - v_new) * 100
                filas_rec.append([E.activo(nombres_u[c], c, c[:2]),
                                  E.num(tabla.loc[c, "Volatilidad %"], 1, suf="%"),
                                  f'{vol_port*100:.1f}% → <span class="strong">{v_new*100:.1f}%</span>',
                                  E.chip(f"−{baja:.1f} p.p.", "up")])
            H(E.tabla([("Sumar", "l"), ("Su volatilidad", "l"), ("Riesgo cartera", "l"), ("Baja", "l")],
                      filas_rec, compacta=True))
            st.caption("Cada fila muestra cómo quedaría la volatilidad de tu cartera si sumaras ese CEDEAR con un 10% "
                       "(bajando proporcionalmente el resto). Bajan el riesgo los de baja volatilidad y poca correlación con lo que ya tenés.")

        st.caption("Datos: retornos diarios del último año en USD. La covarianza y la beta miran para atrás (no garantizan el futuro); "
                   "el retorno esperado es de largo plazo por CAPM, no un pronóstico. Prima de mercado y tasa libre son supuestos editables arriba.")


# --- 3. FCI -----------------------------------------------------------------
with tab3:
    H('<div class="eyebrow m">Fondos comunes de inversión</div><div class="h2">Ranking de FCI</div>')
    rem_val, rem_nota = rem_inflacion()
    favs = st.session_state.setdefault("fci_favs", set())
    cA, cB = st.columns([4, 1.3], vertical_alignment="bottom")
    with cA:
        modo_corto, modo_infl = selector_objetivo("obj_fci", con_hint=False)
    solo_favs = cB.toggle("★ Mis seleccionados", key="fci_solo_favs")
    s1, s2, s3, s4 = st.columns([3, 1.7, 1.7, 1.2], vertical_alignment="bottom")
    busqueda = s1.text_input("Buscar", placeholder="Buscar por fondo o administradora", label_visibility="collapsed")
    tipo_n = s2.selectbox("Categoría", ["Mercado de dinero"] if modo_corto else list(TIPOS_FCI))
    dias = s3.selectbox("Período", [30, 90, 180, 365], index=0 if modo_corto else (3 if modo_infl else 1),
                        format_func=lambda x: f"Últimos {x} días")
    with s4.popover("Más filtros"):
        min_pat = st.number_input("Patrimonio mínimo (millones)", min_value=0, value=1000, step=500)
        infl_esp = st.number_input("Inflación esperada anual (%)", min_value=0.0, max_value=500.0, key="infl_fci",
                                   value=float(round(rem_val, 1)) if rem_val else 25.0, step=0.5,
                                   help="Por defecto, la del REM del BCRA; podés poner la tuya.")
    hint_objetivo(modo_corto, modo_infl, (f"<b>Una pista para comparar:</b> la inflación esperada es de {E.num(infl_esp, 1)}% anual. "
                                          "Buscá una TEA superior para proteger el valor de tus ahorros."))
    st.caption(rem_nota if rem_nota else "No se pudo leer el REM: ingresá tu propia estimación de inflación anual en «Más filtros».")

    r = pd.DataFrame()
    try:
        r = ranking_fci(TIPOS_FCI[tipo_n], dias)
    except Exception as e:
        st.error(f"No se pudo consultar la API de FCI ahora: {e}")
    if r.empty:
        st.warning("No se pudieron armar datos para ese período.")
    else:
        r = r[r["Patrimonio (M)"] >= min_pat].sort_values("Rend. período %", ascending=False).copy()
        r["eq_tna"] = tna30_de_tea(r["TEA %"])
        r["tna_d"] = ((1 + r["TEA %"] / 100) ** (1 / 365) - 1) * 365 * 100
        tea_ref = None
        try:
            serie = serie_deposito_30d()
            f_fin = pd.to_datetime(r["fecha"]).max()
            ventana = serie[(serie["fecha"] > f_fin - timedelta(days=dias)) & (serie["fecha"] <= f_fin)]
            tea_ref = tea_de_tna30(float((ventana if len(ventana) else serie.tail(1))["tna"].mean()))
        except Exception:
            pass
        r["vs_ref"] = r["TEA %"] - tea_ref if tea_ref is not None else np.nan
        r["vs_infl"] = ((1 + r["TEA %"] / 100) / (1 + infl_esp / 100) - 1) * 100
        try:
            mep = mep_hist()
            ini, fin = pd.to_datetime(r["fecha_ant"]), pd.to_datetime(r["fecha"])
            var = {(a_, b_): mep_en(mep, b_) / mep_en(mep, a_) - 1 for a_, b_ in set(zip(ini, fin))}
            r["usd"] = [((1 + x / 100) / (1 + var[(a_, b_)]) - 1) * 100 for x, a_, b_ in zip(r["Rend. período %"], ini, fin)]
        except Exception:
            r["usd"] = np.nan
        try:
            det = detalle_fondos()
        except Exception:
            det = {}

        def partes(n):
            m = re.match(r"(.+?)\s*[-–]\s*(Clase.*)$", n)
            base, clase = (m.group(1), m.group(2)) if m else (n, "")
            d = buscar_fondo(det, n) if det else None
            adm = (d or {}).get("administradora") or ""
            return base, " · ".join(x for x in (adm, clase) if x) or " "

        pp = r["fondo"].map(partes)
        r["base"], r["sub"] = [p[0] for p in pp], [p[1] for p in pp]
        if modo_infl:
            r = r[r["vs_infl"] > 0].sort_values("vs_infl", ascending=False)
        if solo_favs:
            r = r[r["fondo"].isin(favs)]
        q = _plano(busqueda)
        if q:
            r = r[(r["base"] + " " + r["sub"]).map(_plano).str.contains(q, regex=False)]
        top = r.head(30)

        # Cauciones: piso de costo del dinero en la bolsa (liquidez inmediata), referencia para T+0
        cau = cauciones_ars()
        if cau:
            def _cau_txt(d):
                if d in cau:
                    tna = cau[d]
                    tea = (1 + tna / 100 / 365) ** 365 - 1
                    return f"**{d} día{'s' if d > 1 else ''}:** {tna:.1f}% TNA (≈ {tea*100:.1f}% TEA)"
                return None
            partes_cau = [x for x in (_cau_txt(1), _cau_txt(7)) if x]
            if not partes_cau:  # si no están 1 y 7, mostrar los dos plazos más cortos disponibles
                for d in sorted(cau)[:2]:
                    partes_cau.append(_cau_txt(d))
            if partes_cau:
                st.caption("💵 **Caución bursátil** (piso de liquidez inmediata en la bolsa) — " + " · ".join(partes_cau) +
                           ". Es la tasa a la que se presta plata con garantía en el mercado: sirve de piso para comparar "
                           "con el rendimiento diario de fondos T+0 y billeteras.")

        if top.empty:
            st.info("Ningún fondo cumple los filtros elegidos." if not modo_infl else
                    "Ningún fondo de esta categoría supera la inflación esperada con el rendimiento del período elegido.")
        else:
            izq, der = st.columns([2.2, 1.2], gap="medium")
            nombres = list(top["fondo"])
            filas = []
            for _, x in top.iterrows():
                rc = "pos" if x["Rend. período %"] >= 0 else "neg"
                filas.append([
                    E.activo(x["base"], x["sub"], x["base"][:1].upper(), E.color_de(x["base"])),
                    f'<span class="{rc} strong">{"↑" if x["Rend. período %"] >= 0 else "↓"} {E.num(abs(x["Rend. período %"]), 2, suf="%")}</span>',
                    f'<span class="strong">{E.num(x["TEA %"], 2, suf="%")}</span>',
                    E.chip(E.num(x["vs_infl"], 2, suf="%", signo=True), "up" if x["vs_infl"] > 0 else "down"),
                    E.chip(E.num(x["vs_ref"], 2, suf=" p.p.", signo=True), "up" if x["vs_ref"] > 0 else "down") if x["vs_ref"] == x["vs_ref"] else "-",
                    E.num(x["Patrimonio (M)"], 0, "$ ", " M"),
                ])
            cols_tab = [("Fondo", "l"), (f"Rend. {dias} días", "l"), ("TEA", "l"), ("Vs. inflación", "l"), ("Vs. plazo fijo", "l"), ("Patrimonio", "r")]
            sel = st.session_state.get("fci_sel_id")
            if sel not in nombres:
                sel = nombres[0]
            with izq:
                H(f'<div class="panel-top" style="padding:6px 4px 10px"><div><div class="eyebrow m">Ranking actualizado</div>'
                  f'<div class="h2" style="font-size:1.9rem;margin:2px 0 0">Fondos que mejor encajan</div>'
                  f'<div class="sub" style="font-size:.88rem">Hacé clic en un fondo para ver su detalle.</div></div>'
                  f'<span class="chip ch-flat" style="font-size:.85rem">{len(r)} resultados</span></div>')
                if tabla_click:
                    clic = tabla_click(html=E.tabla(cols_tab, filas, compacta=True, ids=nombres), css=E.css_texto(),
                                       selected=sel, key="fci_tabla", default=None)
                    if clic in nombres:
                        sel = clic
                else:
                    sel = st.selectbox("Fondo seleccionado", nombres, index=nombres.index(sel),
                                       format_func=lambda n: top.loc[top["fondo"] == n, "base"].iloc[0])
                    H(E.tabla(cols_tab, filas, sel=nombres.index(sel), compacta=True))
                st.session_state["fci_sel_id"] = sel
            with der:
                fila = top[top["fondo"] == sel].iloc[0]
                st.button("★ Quitar de mis seleccionados" if sel in favs else "☆ Agregar a mis seleccionados",
                          key="fci_fav", on_click=alternar_fav, args=(sel,))
                fd = buscar_fondo(det, sel) if det else None
                plazo_l = (fd or {}).get("plazoLiquidacionDias")
                resc = "-" if plazo_l is None else ("Mismo día" if plazo_l == 0 else f"{plazo_l} día(s)")
                mn = (fd or {}).get("inversionMinima")
                sim_ = "$" if "peso" in str((fd or {}).get("monedaInversion", "peso")).lower() else "US$"
                minimo = "-" if mn is None else E.num(mn, 0, f"{sim_} ")
                svg = ""
                try:
                    fechas, vals = serie_fondo(TIPOS_FCI[tipo_n], sel, str(pd.to_datetime(fila["fecha_ant"]).date()),
                                               str(pd.to_datetime(fila["fecha"]).date()))
                    vs_ = pd.Series(vals).ffill().bfill()
                    if vs_.notna().sum() >= 3:
                        acum = list((vs_ / vs_.iloc[0] - 1) * 100)
                        ref = [((1 + tea_ref / 100) ** ((f - fechas[0]).days / 365) - 1) * 100 for f in fechas] if tea_ref is not None else None
                        svg = E.area_svg(acum, ref, uid="fci")
                except Exception:
                    pass
                extra = [("TNA del fondo (capitaliza a diario)", E.num(fila["tna_d"], 1, suf="%")),
                         ("Plazo fijo equivalente (capitaliza cada 30 días)", E.num(fila["eq_tna"], 1, suf="%"))]
                if fila["usd"] == fila["usd"]:
                    extra.append((f"En USD (MEP), {dias} días", E.num(fila["usd"], 1, suf="%", signo=True)))
                H(E.detalle_fondo(fila["base"], fila["sub"].strip(), E.color_de(fila["base"]), resc, minimo,
                                  E.num(fila["Rend. período %"], 1, suf="%", signo=True), fila["Rend. período %"] >= 0, svg,
                                  leyenda=("Este fondo", "Depósitos a 30 días" if tea_ref is not None else "Referencia"), extra=extra))
                st.caption("Un fondo capitaliza **todos los días** y un plazo fijo cada 30 días: para igualar el mismo rendimiento, el plazo fijo "
                           "necesita una TNA **mayor** que la TNA diaria del fondo. Por eso la comparación se hace sobre la TEA.")
                ver = st.toggle("Ver detalle completo", key="fci_ver")
            if ver and fd:
                detalle_completo(fd)
            elif ver:
                st.info("No encontré el detalle de este fondo en la base de fondos.")
    st.caption("Fuente: CNV vía ArgentinaDatos. **Rend.** es la variación real de la cuotaparte (ya incluye la capitalización y es neta de honorarios); "
               "**TEA** lo anualiza con interés compuesto, comparable entre fondos y con otras tasas. **Vs. inflación** compara la TEA con la inflación "
               "esperada (REM o la que elijas); **Vs. plazo fijo** con el promedio de depósitos a 30 días en el mismo período. En renta fija y variable, "
               "anualizar períodos cortos exagera. Rendimiento pasado no garantiza resultados futuros. Puede haber fondos en dólares mezclados.")

# --- 4. Simulador -----------------------------------------------------------
with tab4:
    c_hero = st.container()
    with st.container(key="grandes_tasas"):
        c1, c2, c3, c4 = st.columns(4)
        monto = c1.number_input("Monto inicial ($)", min_value=0.0, value=1_000_000.0, step=100_000.0)
        tna = c2.number_input("Tasa nominal anual (%)", min_value=0.0, value=30.0, step=1.0) / 100
        plazo = c3.number_input("Plazo (días)", min_value=1, value=365, step=30)
        infl = c4.number_input("Inflación mensual esperada (%)", min_value=0.0, value=2.0, step=0.5) / 100

    FREC = {"Diaria": 365, "Mensual": 12, "Trimestral": 4, "Semestral": 2, "Anual": 1}
    filas = [("Sin capitalizar", "Simple", ((1 + tna * plazo / 365) ** (365 / plazo) - 1) * 100, monto * (1 + tna * plazo / 365))]
    for nombre, m in FREC.items():
        corto = {"Trimestral": "Trim.", "Semestral": "Sem."}.get(nombre, nombre)
        filas.append((nombre, corto, tea(tna, m) * 100, monto * (1 + tna / m) ** (m * plazo / 365)))
    inflacion = (1 + infl) ** (plazo / 30) - 1
    mejor = max(range(len(filas)), key=lambda i: filas[i][3])
    gan = [f[3] - monto for f in filas]
    real = [((1 + g / monto) / (1 + inflacion) - 1) * 100 if monto else 0 for g in gan]

    with c_hero:
        H('<div style="margin-bottom:6px"><div class="eyebrow m">✦ Proyectá tu inversión</div>'
                '<div class="h2" style="font-size:3rem;max-width:680px">La capitalización hace la diferencia.</div>'
                '<div class="sub" style="max-width:600px">Ajustá los valores y compará cuánto puede crecer tu dinero según la frecuencia con la que se '
                'reinvierten los intereses.</div></div>')

    R = st.container()
    with R:
        rows = []
        for i, f in enumerate(filas):
            nombre = f[0]
            rows.append([nombre, E.num(f[2], 2, suf="%"), f'<span class="strong">{E.num(f[3], 0, "$ ")}</span>',
                         f'<span class="pos strong">{E.num(gan[i], 0, "+$ ")}</span>',
                         E.chip(E.num(real[i], 2, suf="%", signo=True), "up" if real[i] >= 0 else "down")])
        H('<div class="eyebrow m" style="margin:2px 0 8px">Comparativa completa</div>' + E.tabla(
            [("Frecuencia", "l"), ("TEA", "l"), ("Capital final", "l"), ("Ganancia", "l"), ("Rend. real", "l")], rows))
    st.caption(f"Inflación acumulada estimada en {plazo} días: {E.num(inflacion * 100, 1, suf='%')}. TEA = (1 + TNA/m)^m − 1. Con 30% de TNA: mensual ≈ 34,5% de TEA, diaria ≈ 35,0%. Rend. real descuenta la inflación acumulada "
               "estimada. Con plazos que no son múltiplos exactos del período, es una aproximación.")

# --- 5. Renta fija ----------------------------------------------------------
with tab5:
    H('<div class="eyebrow m">Deuda pública y privada</div><div class="h2">Renta fija</div>')
    modo_corto, modo_infl = selector_objetivo("obj_rf")
    if modo_infl:
        rem_val2, rem_nota2 = rem_inflacion()
        infl_rf = st.number_input("Inflación esperada anual (%)", min_value=0.0, max_value=500.0, key="infl_rf",
                                  value=float(round(rem_val2, 1)) if rem_val2 else 25.0, step=0.5,
                                  help="Por defecto, la del REM del BCRA; podés poner la tuya.")
        st.caption(rem_nota2 if rem_nota2 else "No se pudo leer el REM: ingresá tu propia estimación de inflación anual.")
    st.caption("Precios en vivo de data912 (no es tiempo real). La TIR es lo que rinde el instrumento **si lo mantenés hasta el "
               "vencimiento y el emisor paga todo**; no es una predicción. No es la lista completa de todo lo que cotiza en BYMA: "
               "verificá siempre el cronograma exacto contra el prospecto o tu broker antes de invertir. En las ONs agregadas más "
               "recientemente (Petroquímica Comodoro Rivadavia, Capex, Edenor, Telecom TLCV/TLCW, Cresud CS52, Pluspetrol), "
               "las fechas de pago son una aproximación calculada desde el vencimiento con la frecuencia informada por el emisor, "
               "no están confirmadas contra el aviso de pago original — pueden estar corridas por algunos días.")
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
    columnas_bonos = [("Precio USD", "Precio USD", f_num(2, "US$ ")), ("TIR (TEA)", "TIR (TEA) %", f_strong(2, "%")),
                      (f"TNA (cap. {nom_cap.lower()})", f"TNA (cap. {nom_cap.lower()}) %", f_num(2, suf="%")),
                      ("TIR modificada", "TIR modificada %", f_num(2, suf="%")), ("Duración", "Duración (años)", f_num(2)),
                      ("Dur. modificada", "Duración modificada", f_num(2)), ("Días p/ recuperar", "Días para recuperar", f_num(0)),
                      ("Días al vto.", "Días al vto.", f_num(0)), ("Próximo pago", "Próximo pago", f_fecha),
                      ("Vencimiento", "Vencimiento", f_fecha)]
    sub_arm, sub_l, sub_cer, sub_s, sub_o, sub_m = st.tabs(
        ["Armar cartera", "Letras (pesos)", "Bonos CER (inflación)", "Bonos soberanos (USD)", "ONs (USD)", "Calculadora manual"])
    curva_usd = []   # puntos (duración modificada, TIR) para el scatter de la curva hard-dollar
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

        with sub_arm:
            st.caption("Elegí moneda, horizonte y perfil, y la app arma una cartera con los instrumentos que ya cotizan acá, "
                       "muestra el rendimiento esperado, el calendario de pagos y un stress test. Informativo, no es recomendación.")
            ca1, ca2, ca3 = st.columns(3)
            moneda_obj = ca1.selectbox("Moneda de tu objetivo", ["Dólares", "Pesos (tasa fija)", "Pesos + inflación (CER)"])
            horizonte = ca2.slider("Horizonte (años)", 0.5, 10.0, 2.0, step=0.5,
                                   help="En cuánto tiempo pensás usar la plata. La cartera se arma con duración cercana a este plazo.")
            perfil = ca3.selectbox("Perfil", ["Bajo", "Medio", "Alto"],
                                   help="Bajo: menor duración (menos sensible a tasas) y lo más seguro. Alto: permite más duración y más tipos de instrumento.")
            monto = st.number_input("Monto a invertir", min_value=0.0, value=10000.0, step=1000.0,
                                    help="En la moneda del objetivo (dólares o pesos). Solo escala los resultados.")
            dur_cap = {"Bajo": 2.0, "Medio": 4.0, "Alto": 8.0}[perfil]

            # Reunir candidatos con sus flujos y métricas, según la moneda del objetivo
            cands = []  # (nombre, sub, precio, flujos, tir, dur, durmod)
            if moneda_obj == "Dólares":
                for k, v in crono["soberanos"].items():
                    p = px.get(k + "D"); m = metricas_flujos(p, v["flujos"], liq, reinv, n_cap, nom_cap.lower()) if p else None
                    if m:
                        cands.append((k, "Soberano USD", p, v["flujos"], m["TIR (TEA) %"], m["Duración (años)"], m["Duración modificada"]))
                if perfil != "Bajo":   # las ONs entran en perfil medio/alto (más riesgo de crédito)
                    for k, v in crono["ons"].items():
                        p = px.get(v["precio_ticker"]); m = metricas_flujos(p, v["flujos"], liq, reinv, n_cap, nom_cap.lower()) if p else None
                        if m:
                            cands.append((k, "ON · " + v["nombre"], p, v["flujos"], m["TIR (TEA) %"], m["Duración (años)"], m["Duración modificada"]))
            elif moneda_obj == "Pesos (tasa fija)":
                for l in crono["letras"]:
                    p = px.get(l["ticker"]); dias = (date.fromisoformat(l["vencimiento"]) - liq).days
                    if p and dias > 0:
                        rend = l["pago_final"] / p - 1
                        tea = ((1 + rend) ** (365 / dias) - 1) * 100
                        dur = dias / 365
                        cands.append((l["ticker"], "Letra pesos", p, [(l["vencimiento"], l["pago_final"])], tea, dur, dur / (1 + tea / 100)))
            else:  # Pesos + CER
                cer_df, _ = bonos_cer()
                for _, b in cer_df.iterrows():
                    dias = (date.fromisoformat(str(b["Vencimiento"])[:10]) - liq).days
                    if dias > 0:
                        dur = dias / 365   # aproximación: los CER suelen amortizar al final o cerca
                        cands.append((b["Instrumento"], "Bono CER", b["Precio ARS"], None, b["TIR real %"], dur, dur / (1 + b["TIR real %"] / 100)))

            cands = [c for c in cands if c[5] <= dur_cap + 0.5]   # dentro del tope de duración del perfil
            if not cands:
                st.warning("No hay instrumentos de esa moneda y perfil con precio ahora mismo. Probá otro perfil o moneda.")
            else:
                # Elegir los 3-4 con duración más cercana al horizonte (y mejor TIR para desempatar)
                cands.sort(key=lambda c: (abs(c[5] - horizonte), -c[4]))
                elegidos = cands[:4]
                w_rf = np.ones(len(elegidos)) / len(elegidos)   # equitativo
                tir_port = float(np.dot(w_rf, [c[4] for c in elegidos]))
                dur_port = float(np.dot(w_rf, [c[5] for c in elegidos]))
                durmod_port = float(np.dot(w_rf, [c[6] for c in elegidos]))

                sim = "US$ " if moneda_obj == "Dólares" else "AR$ "
                k1, k2, k3 = st.columns(3)
                k1.metric("Rendimiento esperado (TIR)", f"{tir_port:.1f}%",
                          help="TIR promedio ponderada. Es lo que rendiría si mantenés al vencimiento y pagan todo.")
                k2.metric("Duración de la cartera", f"{dur_port:.1f} años")
                k3.metric("Inmunización vs tu horizonte",
                          "✔ alineada" if abs(dur_port - horizonte) <= 0.75 else f"{dur_port - horizonte:+.1f} años",
                          help="Si la duración ≈ tu horizonte, la cartera queda 'inmunizada': una suba de tasas te baja el precio pero te sube "
                               "la reinversión, y se compensan cerca de tu fecha objetivo.")

                filas_arm = [[E.activo(c[0], c[1], c[0][:3]), E.num(monto * w / 100, 0, sim),
                              f'<span class="strong">{E.num(c[4], 1, suf="%")}</span>', E.num(c[5], 1, suf=" a")]
                             for c, w in zip(elegidos, w_rf * 100)]
                H(E.tabla([("Instrumento", "l"), ("Monto", "l"), ("TIR", "l"), ("Duración", "l")], filas_arm, compacta=True))

                # Calendario de pagos agregado (solo para instrumentos con flujos: USD y pesos tasa fija)
                pagos_anio = {}
                for c, w in zip(elegidos, w_rf):
                    if not c[3]:
                        continue
                    nominal = (monto * w) / (c[2] / 100)   # VN que comprás con esa parte del monto
                    for f, pago in c[3]:
                        y = date.fromisoformat(str(f)[:10]).year
                        pagos_anio[y] = pagos_anio.get(y, 0) + nominal / 100 * pago
                if pagos_anio:
                    dfp = pd.DataFrame({"Año": list(pagos_anio.keys()), "Cobrás": list(pagos_anio.values())}).sort_values("Año")
                    ch = alt.Chart(dfp).mark_bar(color="#6A4FA0", cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                        x=alt.X("Año:O", title="Año"),
                        y=alt.Y("Cobrás:Q", title=f"Cobrás ({sim.strip()})"),
                        tooltip=[alt.Tooltip("Año:O"), alt.Tooltip("Cobrás:Q", format=",.0f")])
                    st.markdown("**Calendario de pagos de la cartera**")
                    st.altair_chart(ch.properties(height=220).configure_view(strokeWidth=0), width="stretch")

                # Stress test con la duración modificada de la cartera
                st.markdown("**Stress test** (impacto aproximado en el precio, vía duración modificada)")
                escenarios = [("Tasas +2 pp", -durmod_port * 2.0)]
                if moneda_obj == "Dólares":
                    escenarios.append(("Riesgo país +500 pb", -durmod_port * 5.0))
                else:
                    escenarios.append(("Devaluación 30% (si medís en US$)", (1 / 1.30 - 1) * 100))
                filas_ss = [[nom, E.chip(f"{imp:+.1f}%", "down" if imp < 0 else "up"),
                             E.num(monto * (1 + imp / 100), 0, sim)] for nom, imp in escenarios]
                H(E.tabla([("Escenario", "l"), ("Impacto", "l"), ("Valor resultante", "l")], filas_ss, compacta=True))
                peor = min(imp for _, imp in escenarios)
                st.caption(f"**Peor caso de los escenarios:** {peor:+.1f}% → {sim}{monto * (1 + peor/100):,.0f}. "
                           "El stress test aproxima el cambio de precio con la duración (válido para movimientos chicos). "
                           "No incluye default: es riesgo de precio por tasa/devaluación, no de que el emisor no pague. "
                           + ("Los bonos CER no tienen cronograma de flujos cargado, así que no se muestra el calendario de pagos."
                              if moneda_obj.startswith("Pesos +") else ""))

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
                filas.append({"Instrumento": l["ticker"], "Sub": "Letra en pesos", "Vencimiento": l["vencimiento"], "Días": dias, "Precio": p,
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
                        "rf_letras", liq, "No hay precios disponibles para las letras cargadas.",
                        [("Vencimiento", "Vencimiento", f_fecha), ("Días", "Días", f_num(0)), ("Precio", "Precio", f_num(2)),
                         ("Pago final", "Pago final", f_num(2)), ("Rend. al vto.", "Rend. al vto. %", f_num(2, suf="%")),
                         ("TNA", "TNA %", f_num(2, suf="%")), ("TEA", "TEA %", f_strong(2, "%")), ("TEM", "TEM %", f_num(2, suf="%"))]
                        + ([("TEA real vs infl.", "TEA real vs infl. esperada %", f_chip_real)] if modo_infl else []))
            st.caption(f"{len(filas)} de {len(crono['letras'])} letras con precio. Si falta una letra reciente, hay que agregarla "
                       "a cronogramas.json (ticker, vencimiento y pago final por 100).")

        with sub_cer:
            cer_df, cer_fecha = bonos_cer()
            if cer_df.empty:
                st.warning("No se pudieron obtener los bonos CER ahora (ArgentinaDatos). Probá recargar en unos minutos.")
            else:
                # Curva de tasa fija (letras en pesos) para calcular la inflación de equilibrio (breakeven):
                # para cada bono CER, qué inflación hace que rinda lo mismo que una Lecap del mismo plazo.
                curva_fija = []
                for l in crono["letras"]:
                    p = px.get(l["ticker"])
                    d = (date.fromisoformat(l["vencimiento"]) - liq).days
                    if p and d > 0:
                        tea = ((l["pago_final"] / p) ** (365 / d) - 1) * 100
                        curva_fija.append((d, tea))
                curva_fija.sort()

                def tea_fija_en(dias):
                    """TEA de tasa fija interpolada para ese plazo (o None si no hay curva)."""
                    if not curva_fija:
                        return None
                    ds = [c[0] for c in curva_fija]; ts = [c[1] for c in curva_fija]
                    if dias <= ds[0]:
                        return ts[0]
                    if dias >= ds[-1]:
                        return ts[-1]
                    return float(np.interp(dias, ds, ts))

                cer_df = cer_df.copy()
                cer_df["Días"] = [(date.fromisoformat(str(f)[:10]) - liq).days for f in cer_df["Vencimiento"]]
                cer_df = cer_df[cer_df["Días"] > 0].sort_values("Días")
                be = []
                for _, b in cer_df.iterrows():
                    tf = tea_fija_en(b["Días"])
                    if tf is None:
                        be.append(np.nan)
                    else:
                        # inflación de equilibrio: (1+TEA_fija) = (1+TIR_real)·(1+infl) → infl = (1+TEA_fija)/(1+TIR_real)-1
                        be.append(((1 + tf / 100) / (1 + b["TIR real %"] / 100) - 1) * 100)
                cer_df["Breakeven infl. %"] = be

                infl_be = rem_val2 if modo_infl and rem_val2 else None
                if infl_be is None:
                    rv, _ = rem_inflacion()
                    infl_be = rv
                st.caption("Los bonos CER ajustan el capital por inflación (CER). La **TIR real** es lo que rendís *por encima* de la "
                           "inflación. La **inflación de equilibrio** (breakeven) es la inflación a la que un CER y una letra a tasa fija "
                           "del mismo plazo rinden igual: si esperás **más** inflación que ese número, conviene el CER; si esperás "
                           "**menos**, conviene la tasa fija." +
                           (f" Inflación esperada (REM): **{infl_be:.1f}%** anual." if infl_be else ""))

                def _be_chip(bval):
                    if pd.isna(bval):
                        return "-"
                    if infl_be is None:
                        return E.num(bval, 1, suf="%")
                    # si la inflación esperada supera el breakeven, el CER conviene (verde)
                    tipo = "up" if infl_be > bval else "down"
                    return E.chip(E.num(bval, 1, suf="%"), tipo)

                filas_cer = [[E.activo(b["Instrumento"], f"Vence {str(b['Vencimiento'])[:10]}", b["Instrumento"][:3]),
                              E.num(b["Precio ARS"], 0, "AR$ "),
                              f'<span class="strong">{E.num(b["TIR real %"], 1, suf="%")}</span>',
                              E.num(b["Días"], 0), _be_chip(b["Breakeven infl. %"])]
                             for _, b in cer_df.iterrows()]
                H(E.tabla([("Bono", "l"), ("Precio", "l"), ("TIR real (sobre CER)", "l"),
                           ("Días al vto.", "l"), ("Inflación breakeven", "l")], filas_cer, compacta=True))
                st.caption(f"Datos de ArgentinaDatos actualizados al {str(cer_fecha)[:10]}. La TIR real viene calculada por la fuente. "
                           "El breakeven usa la curva de letras a tasa fija de esta misma página (interpolada por plazo). "
                           "En el chip, verde = a la inflación que esperás, el CER conviene; rojo = conviene la tasa fija.")

        with sub_s:
            filas, flujos = [], {}
            for k, v in ({} if modo_corto else crono["soberanos"]).items():
                p = px.get(k + "D")
                m = metricas_flujos(p, v["flujos"], liq, reinv, n_cap, nom_cap.lower()) if p else None
                if m:
                    filas.append({"Instrumento": k, "Sub": f"Ley {v['ley']}", "Precio USD": p, **m})
                    flujos[k] = v["flujos"]
                    curva_usd.append({"Instrumento": k, "Duración": m["Duración modificada"],
                                      "TIR": m["TIR (TEA) %"], "Tipo": "Soberano"})
            tabla_bonos(filas, flujos, "rf_sob", liq, "En el modo corto plazo no se muestran bonos: sus plazos son largos y su precio varía." if modo_corto else "No hay precios disponibles para los bonos soberanos.", columnas_bonos)
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
                    filas.append({"Instrumento": k, "Sub": v["nombre"], "Precio USD": p, **m})
                    flujos[k] = v["flujos"]
                    curva_usd.append({"Instrumento": k, "Duración": m["Duración modificada"],
                                      "TIR": m["TIR (TEA) %"], "Tipo": "ON"})
            tabla_bonos(filas, flujos, "rf_ons", liq, "En el modo corto plazo no se muestran ONs: sus plazos son largos y su precio varía." if modo_corto else "No hay precios disponibles para las ONs cargadas.", columnas_bonos)
            if modo_infl:
                st.caption("Estas ONs están en dólares y a tasa fija: no están indexadas por CER.")
            st.caption("Las ONs con poca operación pueden tener precios poco representativos: mirá el spread y el volumen "
                       "en tu broker antes de usar la TIR. La TIR usa el precio de pantalla sin ajustar intereses corridos.")

        # --- Curva de rendimientos (scatter): TIR vs duración modificada, hard-dollar ---
        if len(curva_usd) >= 2:
            st.markdown("#### Curva de rendimientos (bonos y ONs en dólares)")
            cdf = pd.DataFrame(curva_usd)
            cdf = cdf[cdf["Duración"].notna() & cdf["TIR"].notna() & (cdf["TIR"] < 100)]
            if len(cdf) >= 2:
                st.altair_chart(scatter_curva(cdf), width="stretch")
                st.caption("Cada punto es un bono/ON en dólares: eje X la duración modificada (sensibilidad a la tasa), eje Y la TIR. "
                           "Los que quedan **por encima** de la nube rinden más para su plazo (candidatos a revisar, puede haber más riesgo); "
                           "los que quedan **por debajo** están más caros. Soberanos y ONs juntos porque comparten moneda (USD).")

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


def importar_csv_cartera(archivo):
    """Lee un CSV de movimientos (formato propio de la app) o una foto de tenencia de Cocos.
    Devuelve (DataFrame con COLS_OPS, mensaje o None). Lanza ValueError si no entiende el formato."""
    import io
    texto = archivo.getvalue().decode("utf-8-sig", errors="replace")
    primera = next((l for l in texto.splitlines() if l.strip()), "")
    sep = ";" if primera.count(";") > primera.count(",") else ","
    df = pd.read_csv(io.StringIO(texto), sep=sep, decimal="," if sep == ";" else ".")
    cols = {str(c).strip().lower(): c for c in df.columns}

    # Formato propio: historial de movimientos (tiene Fecha y Operación)
    if ("fecha" in cols and ("operación" in cols or "operacion" in cols)):
        d = df.rename(columns={c: str(c).strip() for c in df.columns})
        d = d.rename(columns={"Operacion": "Operación"})
        d["Fecha"] = pd.to_datetime(d["Fecha"]).dt.date
        return d.reindex(columns=COLS_OPS), None

    # Formato Cocos: foto de tenencia (instrumento; cantidad; precio; precioAsOf; moneda; total; ...)
    if "instrumento" in cols and ("total" in cols or "cantidad" in cols):
        efectivo = {"ARS", "USD", "EXT"}
        fecha_rep = date.today()
        if "precioasof" in cols:
            fechas = pd.to_datetime(df[cols["precioasof"]], errors="coerce").dropna()
            if len(fechas):
                fecha_rep = fechas.max().date()
        por_moneda = {}
        for _, r in df.iterrows():
            inst = str(r[cols["instrumento"]]).strip()
            if inst.upper() in efectivo:
                cur, val = inst.upper(), pd.to_numeric(r.get(cols.get("cantidad")), errors="coerce")
            else:
                cur = str(r.get(cols.get("moneda"), "")).strip().upper()
                val = pd.to_numeric(r.get(cols.get("total")), errors="coerce")
            if cur in ("ARS", "USD") and pd.notna(val) and val > 0:
                por_moneda[cur] = por_moneda.get(cur, 0.0) + float(val)
        if not por_moneda:
            raise ValueError("no encontré tenencia válida")
        movs = [[fecha_rep, "Depósito", "", None, round(v, 2), cur, ""] for cur, v in por_moneda.items()]
        msg = ("Detecté una **foto de tenencia de Cocos** (no un historial de movimientos). La cargué como un "
               f"depósito inicial por moneda al {fecha_rep:%d/%m/%Y}, así ves tu saldo de partida. "
               "**No tiene rendimiento histórico** (no hay compras/ventas con fechas) y el FCI de Cocos se sumó por su "
               "valor en pesos, porque la app no puede cotizarlo. Para ver rendimiento real, exportá de Cocos el "
               "historial de **movimientos** (con fechas y operaciones).")
        return pd.DataFrame(movs, columns=COLS_OPS), msg

    raise ValueError("formato no reconocido")


def preparar_ops(ed):
    ops = ed.copy()
    for c in COLS_OPS:
        if c not in ops:
            ops[c] = None
    ops = ops.dropna(subset=["Fecha", "Operación"])
    for c in ("Ticker", "Ticker destino"):
        ops[c] = ops[c].fillna("").astype(str).str.strip()
        ops[c] = ops[c].where(ops[c].str.contains("|", regex=False), ops[c].str.upper())
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
        H('<div class="eyebrow m" style="margin-top:18px">Registro</div><div class="h2">Historial de movimientos</div>'
                '<div class="sub" style="margin-bottom:12px">Todo lo que hiciste, en orden. La <b>tenencia actual</b> es el resultado de '
                'aplicar todos estos movimientos.</div>')
        t_hist = st.container()
        with st.expander("Editar, borrar o cargar movimientos"):
            st.caption("Los movimientos que ves son un **ejemplo** para mostrar cómo funciona. Para armar tu propia cartera, apretá "
                       "«Vaciar» y cargá los tuyos. También podés corregir una fila, borrarla (seleccionala y apretá Supr) o agregar "
                       "una a mano, o cargar un historial guardado en CSV.")
            cz1, cz2 = st.columns([1, 3])
            if cz1.button("🗑️ Vaciar (empezar de cero)", key="cart_vaciar",
                          help="Borra todos los movimientos de ejemplo para que cargues los tuyos desde cero."):
                st.session_state.cart_ops = pd.DataFrame(columns=COLS_OPS)
                st.session_state.cart_ver += 1
                st.session_state.pop("cart_up_name", None)
                st.rerun()
            up = st.file_uploader("Cargar un historial guardado (CSV) o una tenencia de Cocos", type="csv", key="cart_up")
            if up is not None and st.session_state.get("cart_up_name") != up.name:
                try:
                    nuevo_df, msg = importar_csv_cartera(up)
                    st.session_state.cart_ops = nuevo_df
                    st.session_state.cart_up_name = up.name
                    st.session_state.cart_ver += 1
                    if msg:
                        st.session_state.cart_import_msg = msg
                    st.rerun()
                except Exception:
                    st.warning("No se pudo leer el CSV. Para el **historial** tiene que tener las columnas: "
                               + ", ".join(COLS_OPS) + ". También acepto la **foto de tenencia de Cocos** "
                               "(el archivo portfolio_report).")
            if st.session_state.get("cart_import_msg"):
                st.info(st.session_state.pop("cart_import_msg"))
            ed = st.data_editor(
                st.session_state.cart_ops, num_rows="dynamic", width="stretch", key=f"cart_ed_{st.session_state.cart_ver}",
                column_config={
                    "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                    "Operación": st.column_config.SelectboxColumn("Operación", options=["Depósito", "Retiro", "Compra", "Venta", "Cambio"],
                                                                  required=True, help="Cambio: vende 'Ticker' y compra 'Ticker destino' con lo obtenido."),
                    "Ticker": st.column_config.TextColumn("Ticker", help="Compras, ventas y cambios (el que se vende)."),
                    "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, format="%.4f"),
                    "Monto": st.column_config.NumberColumn("Monto", min_value=0.0, help="Para depósitos y retiros."),
                    "Moneda": st.column_config.SelectboxColumn("Moneda del monto", options=["USD", "ARS"]),
                    "Ticker destino": st.column_config.TextColumn("Cambia por", help="Solo para 'Cambio': la acción que se compra."),
                })
            st.session_state.cart_ops = ed
            st.download_button("Descargar historial (CSV)", ed.to_csv(index=False).encode("utf-8"), "historial_cartera.csv", "text/csv")
        with t_hist:
            H(historial_html(ed))

    # ---- Cálculo ----
    ops, n_malas = preparar_ops(ed)
    res = qty = close = None
    error = None
    tickers = sorted(set(ops.loc[ops["Operación"].isin(["Compra", "Venta", "Cambio"]), "Ticker"])
                     | set(ops.loc[ops["Operación"] == "Cambio", "Ticker destino"]))
    if not ops.empty and tickers:
        try:
            inicio = (pd.to_datetime(ops["Fecha"]).min() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
            try:
                mep = mep_hist().set_index("fecha")["mep"]
            except Exception:
                mep = None
            close, pagos = datos_cartera(tickers, inicio, mep)
            faltan = [t for t in tickers if t not in close.columns or close[t].dropna().empty]
            if faltan:
                error = (f"No encontré precios para: {', '.join(nombre_activo(t) for t in faltan)}. Para acciones usá el ticker de Nueva York "
                         "(ej. AAPL); los fondos y bonos salen de las listas del formulario.")
            else:
                res, qty = calcular_cartera(ops, close, mep, pagos)
        except ValueError as e:
            error = str(e)
        except Exception as e:
            error = f"No se pudo calcular la cartera: {e}"
    ult_qty = qty.iloc[-1] if qty is not None else pd.Series(dtype=float)
    tenidas = [t for t in ult_qty.index if ult_qty[t] > 1e-9]

    # ---- Formulario para registrar movimientos ----
    with c_form:
        H('<div class="eyebrow m">Mi cartera</div><div class="h2">Agregar un movimiento</div>'
          '<div class="sub" style="margin-bottom:12px">Depositá o retirá dinero, y comprá, vendé o cambiá acciones, fondos (FCI) y bonos. '
          'La tenencia actual se actualiza al instante.</div>')
        tipo = st.segmented_control("¿Qué querés hacer?", ["Depositar dinero", "Retirar dinero", "Comprar", "Vender", "Cambiar uno por otro"],
                                    default="Depositar dinero", key="cart_tipo", label_visibility="collapsed") or "Depositar dinero"
        CLASES = ["Acción / CEDEAR", "Fondo (FCI)", "Bono / Letra / ON"]
        clase = CLASES[0]
        if tipo in ("Comprar", "Cambiar uno por otro"):
            H('<div class="eyebrow m" style="margin:8px 0 6px">¿Qué querés comprar?</div>')
            clase = st.segmented_control("Tipo de activo", CLASES, default=CLASES[0], key="cart_clase", label_visibility="collapsed") or CLASES[0]
        UNIDAD = {CLASES[0]: "Cantidad de acciones", CLASES[1]: "Cantidad de cuotapartes", CLASES[2]: "Valor nominal (VN)"}

        def selector_activo(contenedor, clave):
            """Devuelve la clave interna del activo elegido (o None)."""
            if clase == CLASES[1]:
                try:
                    nombres = sorted({v["nombre"] for v in detalle_fondos().values() if v.get("nombre")})
                except Exception:
                    contenedor.warning("No se pudo cargar la lista de fondos ahora.")
                    return None
                sel = contenedor.selectbox("Fondo", nombres, index=None, placeholder="Escribí para buscar un fondo...", key=clave)
                return None if sel is None else ACT_FCI + sel
            if clase == CLASES[2]:
                try:
                    cat = catalogo_bonos()
                except Exception:
                    contenedor.warning("No se pudo cargar la lista de bonos ahora.")
                    return None
                sel = contenedor.selectbox("Instrumento", list(cat), index=None, format_func=lambda k: cat[k]["etq"],
                                           placeholder="Escribí para buscar un instrumento...", key=clave)
                return None if sel is None else ACT_BONO + sel
            t = contenedor.text_input("Ticker (de Nueva York)", placeholder="Ej: TSLA", key=clave)
            return t.strip().upper() or None

        fila, falta = None, None
        with st.form("cart_form", clear_on_submit=True):
            fch = st.date_input("Fecha", value=hoy, max_value=hoy, format="DD/MM/YYYY")
            g1, g2 = st.columns(2)
            tk = tk2 = None
            cant = monto = 0.0
            if tipo in ("Depositar dinero", "Retirar dinero"):
                monto = g1.number_input("Monto", min_value=0.0, step=100.0)
                mon = g2.selectbox("Moneda", ["USD", "ARS"])
            elif tipo == "Comprar":
                tk = selector_activo(g1, "cart_activo")
                cant = g2.number_input(UNIDAD[clase], min_value=0.0, step=1.0)
                st.caption("Se compra al precio de cierre del día. Si no tenés efectivo suficiente, primero depositá dinero.")
            elif tipo == "Vender":
                tk = g1.selectbox("Activo que vendés", tenidas or [None],
                                  format_func=lambda k: "(todavía no tenés activos)" if k is None else nombre_activo(k))
                cant = g2.number_input("Cantidad (acciones, cuotapartes o VN)", min_value=0.0, step=1.0,
                                       help=f"Tenés {ult_qty.get(tk, 0):,.4f}" if tk is not None else None)
            else:
                tk = g1.selectbox("Vendo", tenidas or [None],
                                  format_func=lambda k: "(todavía no tenés activos)" if k is None else nombre_activo(k))
                cant = g2.number_input("Cantidad que vendo", min_value=0.0, step=1.0)
                tk2 = selector_activo(st, "cart_activo_destino")
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
            elif tipo == "Comprar":
                if tk and cant > 0:
                    fila = {**base, "Operación": "Compra", "Ticker": tk, "Cantidad": cant}
                else:
                    falta = "Elegí el activo e ingresá una cantidad mayor a 0."
            elif tipo == "Vender":
                if tk in tenidas and cant > 0:
                    fila = {**base, "Operación": "Venta", "Ticker": tk, "Cantidad": cant}
                else:
                    falta = "Elegí un activo que tengas e ingresá una cantidad mayor a 0."
            else:
                if tk in tenidas and cant > 0 and tk2:
                    fila = {**base, "Operación": "Cambio", "Ticker": tk, "Cantidad": cant, "Ticker destino": tk2}
                else:
                    falta = "Elegí el activo que vendés, la cantidad y el activo que comprás."
            if tipo in ("Vender", "Cambiar uno por otro") and fila and cant > ult_qty.get(tk, 0) + 1e-9:
                st.warning(f"Estás vendiendo más de lo que tenés hoy de {nombre_activo(tk)} ({ult_qty.get(tk, 0):,.4f}). Se agrega igual; revisá la fecha.")
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

            # --- Tenencia actual ---
            px_ult = close.reindex(res.index).iloc[-1]
            ten = pd.DataFrame({"Cantidad": ult_qty, "Precio USD": px_ult[ult_qty.index], "Valor USD": ult_qty * px_ult[ult_qty.index]})
            ten = ten[ten["Cantidad"].abs() > 1e-9]
            ten.loc["Efectivo (USD)"] = [np.nan, np.nan, res["efectivo_usd"].iloc[-1]]
            ten["% de la cartera"] = ten["Valor USD"] / ten["Valor USD"].sum() * 100
            ten.index = [nombre_activo(i) for i in ten.index]
            ten.index.name = "Activo"
            items = [(i, float(p)) for i, p in ten["% de la cartera"].items() if p > 0.05]
            composicion_st("¿Qué tenés hoy?", f"Tenencia al {res.index[-1]:%d/%m/%Y}: el resultado de aplicar todos los movimientos del historial.",
                           items, "Tenencia actual", "card_comp_cartera")
            with st.expander("Ver la tenencia en detalle"):
                st.dataframe(ten.style.format(precision=2, na_rep="-"), width="stretch")

            # --- Evolución ---
            r_usd, m_usd = resumen_cartera(res["valor_usd"], res["flujo_usd"])
            r_ars, m_ars = (resumen_cartera(res["valor_ars"], res["flujo_ars"]) if "valor_ars" in res else (None, None))
            hA, hB = st.columns([5, 1.1], vertical_alignment="bottom")
            moneda = hB.segmented_control("Moneda", ["USD"] + (["ARS"] if r_ars is not None else []), default="USD",
                                          key="cart_mon", label_visibility="collapsed") or "USD"
            es_usd = moneda == "USD"
            v, f, r, m_ = ((res["valor_usd"], res["flujo_usd"], r_usd, m_usd) if es_usd
                           else (res["valor_ars"], res["flujo_ars"], r_ars, m_ars))
            sym = "US$ " if es_usd else "$ "
            gan = m_["Ganancia"]
            Hc(hA, f'<div class="eyebrow m" style="margin-top:18px">Evolución · {res.index[0]:%d/%m/%Y} a {res.index[-1]:%d/%m/%Y}</div>'
                    f'<div class="h2">Tu estrategia {"ganó" if gan >= 0 else "perdió"} {E.num(abs(gan), 1, sym)}</div>')
            H(E.strip([("Valor actual", E.num(m_["Valor actual"], 1, sym), f"Al {res.index[-1]:%d/%m/%Y}", False),
                             ("Aportes netos", E.num(m_["Aportes netos (depósitos − retiros)"], 1, sym), "Depósitos menos retiros", False),
                             ("Ganancia", E.num(gan, 1, sym, signo=True), "Resultado acumulado", True),
                             ("Rendimiento TWR", E.num(m_["Rendimiento ajustado por aportes (TWR) %"], 2, suf="%", signo=True),
                              "Sin efecto de aportes", False)]))
            try:
                bval, bacum = benchmark_sp(res, precios_indice(str((res.index[0] - pd.Timedelta(days=7)).date())), es_usd)
            except Exception:
                bval = bacum = None
            tw = ((1 + r).cumprod() - 1) * 100
            gA, gB = st.columns(2, gap="large")
            with gA:
                with st.container(key="card_valor"):
                    H(f'<small class="muted">Valor de la cartera</small><div class="h2" style="font-size:1.9rem;margin:2px 0 4px">'
                            f'{E.num(m_["Valor actual"], 1, sym)}</div>')
                    d1 = pd.DataFrame({"Tu cartera": v})
                    if bval is not None:
                        d1["S&P 500 (mismos aportes)"] = bval
                    st.altair_chart(area_alt(d1), width="stretch")
            with gB:
                with st.container(key="card_twr"):
                    H(f'<small class="muted">Rendimiento acumulado (TWR)</small><div class="h2" style="font-size:1.9rem;margin:2px 0 4px">'
                            f'{E.num(tw.iloc[-1], 2, suf="%", signo=True)}</div>')
                    d2 = pd.DataFrame({"Tu cartera": tw})
                    if bacum is not None:
                        d2["S&P 500"] = bacum
                    st.altair_chart(area_alt(d2, cero=True), width="stretch")
            with st.container(key="card_mes"):
                mes = v.index.to_period("M")
                pct_m = ((1 + r).groupby(mes).prod() - 1) * 100
                cierre_m = v.groupby(mes).last()
                H('<div class="eyebrow m">Mes a mes</div><div class="h2" style="font-size:1.7rem">Rendimiento sin efecto de movimientos</div>'
                        '<div class="sub" style="font-size:.85rem">El TWR permite comparar períodos de forma justa, aunque hayas depositado o retirado ese mes.</div>'
                        + E.meses([(MESES_ES[p.month - 1], float(pct_m[p]), E.num(cierre_m[p], 0, sym)) for p in pct_m.index]))
            with st.expander("Ver el resumen completo en dólares y pesos"):
                tabla_res = pd.DataFrame({"USD": m_usd})
                if m_ars is not None:
                    tabla_res["Pesos (ARS)"] = pd.Series(m_ars)
                st.dataframe(tabla_res.style.format(precision=2, na_rep="-"), width="stretch")
                st.caption("**TWR** encadena el rendimiento de cada día quitando el efecto de los depósitos y retiros: mide si elegiste bien las acciones. "
                           "La **TIR del dinero** sí pesa cuándo pusiste cada monto (se calcula con 60 días o más). En pesos, el rendimiento incluye "
                           "lo que subió o bajó el dólar MEP. La línea del S&P 500 muestra qué habría pasado con los mismos aportes y retiros.")
            st.caption("Compras, ventas y cambios al precio de cierre del día (o del siguiente día de mercado). Acciones: Yahoo Finance en dólares. "
                       "Fondos: valor de la cuotaparte según la CNV (datos semanales, interpolados entre fechas). Bonos y letras: cierre de data912 y "
                       "pagos del cronograma cargado, que se acreditan como efectivo; es una aproximación. No incluye comisiones, impuestos ni dividendos. "
                       "La conversión a pesos usa el dólar MEP de cada fecha.")

st.divider()
st.caption("Proyecto personal con fines informativos. No constituye asesoramiento financiero ni recomendación de inversión.")
