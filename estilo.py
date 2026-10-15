"""Tema visual y componentes HTML del panel (fondo crema, tarjetas redondeadas, terracota y verde).

Todo el texto dinámico pasa por esc() para que un nombre raro de la API no pueda romper la página.
"""
import html as _html
import re
from math import pi

PALETA = ["#6A4FA0", "#D6A64F", "#5B7DB1", "#CDC3B5", "#C98A5E", "#4E8B7A"]
FUENTE_URL = "https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&display=swap"
VERDE, ROJO, GRIS = "#2E7D5B", "#B84A4A", "#8A8F98"


def esc(x):
    return _html.escape(str(x), quote=True)


def compactar(h):
    """Evita que Markdown interprete sangrías o líneas en blanco como bloques de código."""
    return re.sub(r">\s+<", "><", re.sub(r"\s*\n\s*", " ", h)).strip()


def num(x, dec=0, pref="", suf="", signo=False):
    """Formato argentino: 1.234,56"""
    if x is None or x != x:
        return "-"
    s = f"{abs(x):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sg = "-" if x < 0 else ("+" if signo and x > 0 else "")
    return f"{sg}{pref}{s}{suf}"


def color_de(texto):
    return PALETA[sum(ord(c) for c in str(texto)) % len(PALETA)]


CSS = """
@import url('__FUENTE__');
:root{--bg:#F5F2EC;--card:#FFFEFA;--borde:#EAE3D8;--texto:#26221F;--suave:#7C746B;--terra:#E2704A;
--verde:#2E7D5B;--verde-bg:#E3F2E8;--rojo:#B84A4A;--rojo-bg:#F8DAD8;--neu:#6B7280;--neu-bg:#E8E8EA;--dark:#2A2420}
html,body,.stApp,[class*="css"]{font-family:'Instrument Sans','Hanken Grotesk',system-ui,-apple-system,sans-serif;color:var(--texto)}
.stApp{background:radial-gradient(1100px 520px at 88% -8%,#EEE9F7 0%,transparent 62%),
radial-gradient(900px 520px at -5% 0%,#FBEEE4 0%,transparent 58%),var(--bg)}
header[data-testid="stHeader"]{background:transparent}
.block-container{max-width:1640px;padding:2.4rem 2.6rem 4rem}
h1,h2,h3{letter-spacing:-0.02em;font-weight:500}
/* pestañas */
.stApp [role="tablist"]{gap:6px;filter:hue-rotate(268deg) saturate(.6) brightness(.8)}
.stApp [role="tab"]{font-weight:500;padding:10px 16px;color:var(--suave)}
.stApp [role="tab"][aria-selected="true"]{font-weight:700}
/* El rojo de fábrica de Streamlit se rota a violeta (#6B4F9F): no depende de la estructura interna de cada control */
.stApp [data-testid="stSlider"],.stApp [data-testid="stToggle"],.stApp [data-testid="stCheckbox"],
.stApp [data-testid="stButtonGroup"] button{filter:hue-rotate(268deg) saturate(.6) brightness(.8)}
[data-testid="stButtonGroup"]{background:#E9E3D8;padding:6px;border-radius:18px;width:fit-content;max-width:100%;gap:4px}
[data-testid="stButtonGroup"] button{border:0;border-radius:13px;padding:10px 20px;font-weight:500}
/* campos con fondo propio (antes se confundían con el de la página) */
.stApp [data-baseweb="input"],.stApp [data-baseweb="select"]>div,.stApp [data-baseweb="textarea"],.stApp div:has(>div>input){background-color:#FFFFFF !important;border:1px solid #D6CBBA !important;border-radius:14px !important}
.stApp [data-baseweb="base-input"],.stApp div:has(>input){background-color:transparent !important;border:0 !important}
.stApp [data-baseweb="input"]:focus-within,.stApp [data-baseweb="select"]>div:focus-within{border-color:#6A4FA0 !important}
.stApp [data-baseweb="input"] input,.stApp [data-baseweb="textarea"] textarea{font-weight:500}
.stApp [data-testid="stForm"]{background:#fff;border:1px solid #D9CFC0 !important;border-radius:26px;padding:26px 28px;box-shadow:0 10px 30px rgba(60,40,20,.08)}
.stButton>button,.stDownloadButton>button,[data-testid="stPopover"]>button{border-radius:14px;border:1px solid #D6CBBA;background:#fff;font-weight:500;padding:.55rem 1.1rem}
.stFormSubmitButton>button,.stButton>button[kind="primary"]{background:var(--dark) !important;color:#fff !important;border-color:var(--dark) !important}
[data-testid="stExpander"]{background:#fff;border:1px solid #D9CFC0;border-radius:22px;overflow:hidden;margin-bottom:14px;box-shadow:0 4px 18px rgba(60,40,20,.06)}
[data-testid="stExpander"] summary{padding:16px 22px;background:linear-gradient(90deg,#E6E0F3,#F4F0FA);font-size:1.08rem;font-weight:600;color:#3B2C66}
[data-testid="stExpander"] details>div{padding:0}
[data-testid="stAlert"]{border-radius:18px}
[data-testid="stExpander"] .panel{border:0;border-radius:0;box-shadow:none}
[data-testid="stDataFrame"]{border:1px solid #D9CFC0;border-radius:18px;overflow:hidden}
[data-testid="stMetric"]{background:#fff;border:1px solid #D9CFC0;border-radius:20px;padding:14px 18px}
[class*="st-key-card"]{background:#fff;border:1px solid #D9CFC0;border-radius:26px;padding:20px 24px;box-shadow:0 6px 24px rgba(60,40,20,.05)}
[class*="st-key-grandes"] input{font-size:1.7rem;font-weight:500;padding:.55rem .8rem}
/* textos */
.eyebrow{font-size:.74rem;letter-spacing:.16em;text-transform:uppercase;color:#3B4F8F;font-weight:500}
.eyebrow.m{color:#8A7A6C}
.hero h1{font-size:3rem;line-height:1.04;margin:.35rem 0 .5rem;letter-spacing:-0.035em;font-weight:500}
.hero p{font-size:1.15rem;color:var(--suave);margin:0}
.hero{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:26px}
.hero .upd{text-align:right;font-size:.95rem}.hero .upd small{display:block;color:var(--suave)}
.h2{font-size:2.3rem;line-height:1.1;letter-spacing:-0.03em;font-weight:500;margin:.3rem 0 .4rem}
.sub{color:var(--suave);font-size:1.02rem}
.muted{color:var(--suave)}
/* tarjetas KPI */
.kpis{display:flex;gap:16px;margin:10px 0 6px}
.kpi{flex:1;min-width:0;background:var(--card);border:1px solid var(--borde);border-radius:26px;padding:20px 22px;box-shadow:0 6px 24px rgba(60,40,20,.04)}
.kpi-top{display:flex;justify-content:space-between;align-items:center}
.kpi-top b{font-size:1.02rem;font-weight:600}
.info{width:18px;height:18px;border:1.5px solid #B9B2A8;border-radius:50%;font-size:.65rem;display:inline-flex;align-items:center;justify-content:center;color:#9A9288}
.kpi small{display:block;color:var(--suave);font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;margin-top:2px}
.kpi-mid{display:flex;justify-content:space-between;align-items:center;margin:16px 0 14px}
.kpi .v{white-space:nowrap;font-size:2rem;font-weight:500;letter-spacing:-0.03em}
.chip{display:inline-block;white-space:nowrap;padding:4px 11px;border-radius:10px;font-size:.78rem;font-weight:600}
.ch-up{background:var(--verde-bg);color:var(--verde)}.ch-down{background:var(--rojo-bg);color:var(--rojo)}.ch-flat{background:var(--neu-bg);color:var(--neu)}
.ch-pur{background:#ECE6F6;color:#5A3F94}.ch-sand{background:#EFE8DC;color:#6B5B45}.ch-warn{background:#FBEBD0;color:#9A6A12}.ch-yel{background:#FFF3C9;color:#8A6D00}.ch-org{background:#FFE3C2;color:#A85A00}
/* tablas */
.panel{background:var(--card);border:1px solid var(--borde);border-radius:26px;overflow:hidden;box-shadow:0 6px 24px rgba(60,40,20,.04)}
.panel-top{display:flex;justify-content:space-between;align-items:center;padding:12px 24px 4px}
.tbl{width:100%;border-collapse:collapse}
.tbl th{font-size:.7rem;letter-spacing:.13em;text-transform:uppercase;color:#4B5568;text-align:left;padding:16px 18px;background:#F4F5F9;font-weight:600;white-space:nowrap}
.tbl td{white-space:nowrap;padding:15px 18px;border-top:1px solid #EFEAE1;vertical-align:middle;font-size:.98rem}
.tbl tr:hover td{background:#FAF8F3}.tbl tr.clk{cursor:pointer}
.tbl.cmp th{font-size:.62rem;letter-spacing:.06em;padding:12px 7px;white-space:normal;line-height:1.25}
.tbl.cmp td{padding:10px 7px;font-size:.84rem;white-space:normal}
.tbl.cmp .nm{gap:9px;padding-right:6px}.tbl.cmp .nm b{font-size:.9rem}.tbl.cmp .nm span{font-size:.74rem}
.tbl.cmp .av{width:34px;height:34px;border-radius:11px;font-size:.78rem}.tbl.cmp .chip{padding:3px 8px;font-size:.72rem}
.tbl td.r,.tbl th.r{text-align:right}.tbl td.w{white-space:normal;min-width:260px;color:var(--suave);font-size:.92rem}
.tbl tr.sel td{background:#F1ECFA}.tbl tr.sel td:first-child{box-shadow:inset 4px 0 0 #6A4FA0}
.nm{display:flex;gap:14px;align-items:center;padding-right:14px}
.nm b{display:block;font-size:1.02rem;font-weight:600}.nm span{color:var(--suave);font-size:.84rem}
.av{width:44px;height:44px;border-radius:14px;display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:.95rem;flex:none;background:#ECEEF8;color:#44508A;border:1px solid #DFE2F2}
.av.c{color:#fff;border:0}
.strong{font-weight:600}.pos{color:var(--verde)}.neg{color:var(--rojo)}
/* RSI */
.pill{border-radius:15px;padding:10px 14px 11px;min-width:150px;border:1px solid}
.pt{display:flex;justify-content:space-between;align-items:baseline}
.pl{font-size:.7rem;letter-spacing:.09em;font-weight:700}.pv{font-size:1.1rem;font-weight:700}
.bar{height:6px;border-radius:4px;background:rgba(0,0,0,.09);margin-top:8px;overflow:hidden}.bar i{display:block;height:100%;border-radius:4px}
.p-buy{background:#DDF0E4;border-color:#BFE0CC;color:#1F6B47}.p-buy .bar i{background:#2E8B5E}
.p-sell{background:#F8DAD8;border-color:#EFBDB9;color:#9A3C3C}.p-sell .bar i{background:#C45555}
.p-neu{background:#EAEAEC;border-color:#DADADD;color:#5F6571}.p-neu .bar i{background:#7C8290}
.legend{display:flex;gap:20px;justify-content:flex-end;font-size:.92rem;color:#4B5563;margin:6px 6px 18px}
.legend i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px}
/* banner / detalle */
.hint{display:flex;align-items:center;gap:14px;padding:16px 20px;border-radius:20px;background:linear-gradient(90deg,#F1ECFA,#FBF7F0);border:1px solid #E6DDF3;margin:14px 0 22px}
.hint .ic{width:42px;height:42px;border-radius:13px;background:#8C6FB3;color:#fff;display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex:none}
.detail{min-width:0;background:linear-gradient(180deg,#F1ECFA 0%,#FFFEFA 38%);border:1px solid var(--borde);border-radius:28px;padding:24px;box-shadow:0 6px 24px rgba(60,40,20,.05)}
.detail .eyebrow{color:#6A4FA0;font-weight:600}
.mini-row{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}
.mini{flex:1 1 190px;border:1px solid var(--borde);border-radius:18px;padding:13px 15px;background:#fff}
.mini small{color:var(--suave);font-size:.78rem}.mini div{font-size:1.25rem;font-weight:500;margin-top:5px}
.row-sp{display:flex;justify-content:space-between;align-items:center}
.lg{display:flex;gap:16px;font-size:.78rem;color:var(--suave);margin-top:6px}
.lg i{flex:none;display:inline-block;width:14px;height:3px;border-radius:2px;margin-right:6px;vertical-align:middle}
/* composición */
.comp{display:flex;flex-wrap:wrap;gap:30px;align-items:center;justify-content:space-between;background:var(--card);border:1px solid var(--borde);border-radius:30px;padding:34px 38px;box-shadow:0 6px 24px rgba(60,40,20,.04)}
.comp .izq{flex:1 1 440px;min-width:0}.comp .dona{flex:none;margin:0 auto}
.leg{display:flex;flex-wrap:wrap;gap:0 34px;margin-top:22px}
.leg-i{display:flex;justify-content:space-between;align-items:center;width:calc(50% - 17px);min-width:230px;padding:11px 0;border-bottom:1px solid #EFEAE1;font-size:.97rem}
.leg-i span{display:flex;align-items:center;gap:11px}.leg-i i{width:11px;height:11px;border-radius:50%;display:inline-block;flex:none}
.leg-i b{font-weight:700}
/* tasas */
.dark{background:var(--dark);color:#fff;border-radius:24px;padding:22px 28px;min-width:300px;box-shadow:0 14px 34px rgba(42,36,32,.25)}
.dark small{letter-spacing:.14em;font-size:.7rem;color:#CFC6BB;text-transform:uppercase}
.dark .v{font-size:2.2rem;font-weight:500;margin:6px 0 4px;letter-spacing:-0.02em}.dark .s{color:#F2B49C;font-size:.85rem}
.pillb{display:inline-block;background:#E8E0F5;color:#6A4FA0;border-radius:999px;padding:5px 14px;font-size:.8rem;font-weight:600}
.badge{display:inline-block;background:var(--terra);color:#fff;border-radius:999px;padding:2px 9px;font-size:.62rem;letter-spacing:.06em;font-weight:700;margin-left:8px;vertical-align:middle}
.bars{display:flex;align-items:flex-end;gap:14px;height:210px;margin-top:22px;border-bottom:1px solid #E7E0D5}
.bc{flex:1;text-align:center;display:flex;flex-direction:column;justify-content:flex-end;height:100%}
.bc .b{border-radius:12px 12px 0 0;background:#D3C9BC}
.bc.unif .b{background:linear-gradient(180deg,#6A4FA0,#BBA9DC)}.bc.best .b{background:linear-gradient(180deg,#6A4FA0,#BBA9DC);box-shadow:0 8px 18px rgba(106,79,160,.35)}
.bc .t{font-size:.72rem;color:#8A7A6C;margin-bottom:5px;min-height:15px}
.bl{display:flex;gap:14px;margin-top:9px}.bl div{flex:1;text-align:center;font-size:.72rem;color:#8A7A6C}.bl .best{color:#6A4FA0;font-weight:700}
/* cartera */
.strip{display:flex;background:var(--card);border:1px solid var(--borde);border-radius:24px;overflow:hidden;margin:16px 0}
.cell{flex:1;padding:18px 22px;border-right:1px solid #EFEAE1}.cell:last-child{border-right:0}
.cell small{color:var(--suave);font-size:.8rem;display:block}.cell .v{white-space:nowrap;font-size:1.7rem;font-weight:500;letter-spacing:-0.02em;margin:3px 0}
.cell.hl{background:#F1ECFA}.cell.hl .v{color:#5A3F94}
.mm{display:flex;gap:6px;align-items:flex-end;margin-top:14px}
.mm .col{flex:1;text-align:center;border-bottom:1px solid #E7E0D5;padding-bottom:10px}
.mm .col small{display:block;color:var(--suave);font-size:.78rem}.mm .col .p{font-size:.88rem;font-weight:600;margin:5px 0 14px}
.mm .col .area{height:130px;display:flex;align-items:flex-end;justify-content:center}
.mm .col .bb{width:42px;border-radius:9px 9px 0 0;background:linear-gradient(180deg,#5E9E8B,#A8D0C4)}
.mm .col .bb.n{background:linear-gradient(180deg,#C45555,#E5A9A5)}
.mm .col .vv{font-size:.74rem;color:var(--suave);margin-top:8px}
@media (max-width:900px){.kpis{flex-wrap:wrap}.kpi{flex:1 1 45%}.hero h1{font-size:2.3rem}.comp{flex-direction:column}.hero{flex-direction:column;align-items:flex-start}.strip{flex-wrap:wrap}.cell{flex:1 1 45%}}
@media (max-width:600px){
  .block-container{padding:1rem .8rem 2.4rem !important}
  .kpi{flex:1 1 100% !important}.cell{flex:1 1 100% !important}
  .hero h1{font-size:1.9rem}
  /* En celular las tablas compactas no se aplastan: letra chica + scroll horizontal */
  .tbl.cmp th,.tbl.cmp td{white-space:nowrap}
  .tbl td,.tbl th{padding:11px 12px;font-size:.9rem}
  .tbl.cmp td,.tbl.cmp th{padding:8px 6px;font-size:.78rem}
  /* Trading: ocultar columnas accesorias (Vol. BYMA y Volatilidad) para que entren Activo/Precio/RSI */
  .t-trading th:nth-child(3),.t-trading td:nth-child(3),
  .t-trading th:nth-child(4),.t-trading td:nth-child(4){display:none}
  /* Dividendos: ocultar P/E, P/E vs sector, ROE, Deuda/EBITDA y Rango; dejar lo esencial */
  .t-div th:nth-child(5),.t-div td:nth-child(5),
  .t-div th:nth-child(6),.t-div td:nth-child(6),
  .t-div th:nth-child(7),.t-div td:nth-child(7),
  .t-div th:nth-child(8),.t-div td:nth-child(8),
  .t-div th:nth-child(9),.t-div td:nth-child(9){display:none}
}
"""


def css_texto():
    """CSS sin la etiqueta <style> (para el componente de tabla clicable)."""
    return CSS.replace("__FUENTE__", FUENTE_URL)


def css():
    return "<style>" + CSS.replace("__FUENTE__", FUENTE_URL) + "</style>"


# ------------------------------------------------------------------ componentes
def hero(eyebrow, titulo, subtitulo, actualizado=None):
    upd = f'<div class="upd"><small>Actualizado</small><b>{esc(actualizado)}</b></div>' if actualizado else ""
    return compactar(f'<div class="hero"><div><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(titulo)}</h1>'
                     f'<p>{esc(subtitulo)}</p></div>{upd}</div>')


def spark(vals, color, w=96, h=38):
    v = [float(x) for x in vals if x is not None and x == x]
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v)
    rng = (hi - lo) or 1.0
    pts = " ".join(f"{i * (w - 4) / (len(v) - 1) + 2:.1f},{h - 4 - (x - lo) / rng * (h - 8):.1f}" for i, x in enumerate(v))
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><polyline points="{pts}" fill="none" stroke="{color}" '
            f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>')


def chip(texto, tipo="flat", flecha=""):
    f = f"{esc(flecha)} " if flecha else ""
    return f'<span class="chip ch-{tipo}">{f}{esc(texto)}</span>'


def kpi_card(titulo, sub, valor, delta=None, tipo="flat", flecha="", serie=None, ayuda=""):
    col = {"up": VERDE, "down": ROJO}.get(tipo, GRIS)
    ch = chip(delta, tipo, flecha) if delta else ""
    return (f'<div class="kpi"><div class="kpi-top"><b>{esc(titulo)}</b><span class="info" title="{esc(ayuda)}">i</span></div>'
            f'<small>{esc(sub)}</small><div class="kpi-mid"><span class="v">{esc(valor)}</span>{spark(serie or [], col)}</div>{ch}</div>')


def kpis(cards_html):
    return compactar('<div class="kpis">' + "".join(cards_html) + "</div>")


def avatar(texto, color=None):
    if color:
        return f'<span class="av c" style="background:{color}">{esc(texto)}</span>'
    return f'<span class="av">{esc(texto)}</span>'


def activo(nombre, sub, av_txt, color=None, var_pct=None):
    v = ""
    if var_pct is not None and var_pct == var_pct:
        flecha = "↑" if var_pct > 0.005 else ("↓" if var_pct < -0.005 else "~")
        cls = "up" if var_pct > 0.005 else ("down" if var_pct < -0.005 else "flat")
        v = f' <span class="chip ch-{cls}" style="font-size:11px;padding:1px 5px;vertical-align:middle">{flecha} {num(abs(var_pct), 2, suf="%")}</span>'
    return f'<div class="nm">{avatar(av_txt, color)}<div><b>{esc(nombre)}</b>{v}<span>{esc(sub)}</span></div></div>'


def rsi_pill(v, lo=30, hi=70):
    if v is None or v != v:
        return '<span class="muted">-</span>'
    cls, lab = ("p-buy", "SOBREVENTA") if v < lo else (("p-sell", "SOBRECOMPRA") if v > hi else ("p-neu", "NEUTRAL"))
    ancho = max(3, min(100, v))
    return (f'<div class="pill {cls}"><div class="pt"><span class="pl">{lab}</span><span class="pv">{v:.0f}</span></div>'
            f'<div class="bar"><i style="width:{ancho:.0f}%"></i></div></div>')


def tabla(headers, filas, sel=None, compacta=False, ids=None, clase=""):
    """headers: lista de (texto, 'l'|'r'|'w'). filas: lista de listas de HTML de celda.
    compacta: letra y espacios más chicos. ids: un identificador por fila (para tablas clicables).
    clase: clase CSS extra en la tabla (sirve para ocultar columnas accesorias en celular)."""
    th = "".join(f'<th class="{a if a in ("r", "w") else ""}">{esc(t)}</th>' for t, a in headers)
    trs = ""
    for i, f in enumerate(filas):
        tds = "".join(f'<td class="{headers[j][1] if headers[j][1] in ("r", "w") else ""}">{c}</td>' for j, c in enumerate(f))
        cl = ("sel" if sel == i else "") + (" clk" if ids else "")
        attr = f' data-id="{esc(ids[i])}"' if ids else ""
        trs += f'<tr class="{cl.strip()}"{attr}>{tds}</tr>'
    clases = "tbl" + (" cmp" if compacta else "") + (f" {clase}" if clase else "")
    return compactar(f'<div class="panel" style="overflow-x:auto"><table class="{clases}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')


def variacion_chip(pct):
    if pct is None or pct != pct:
        return ""
    tipo = "up" if pct > 0.005 else ("down" if pct < -0.005 else "flat")
    return f'<div class="panel-top"><span class="muted strong" style="margin-right:10px">Variación promedio</span>' \
           f'{chip(num(abs(pct), 2, suf="%"), tipo, "↑" if pct > 0 else "↓")}</div>'


def leyenda_rsi(lo=30, hi=70):
    return (f'<div class="legend"><span><i style="background:{VERDE}"></i>Sobreventa (RSI &lt; {lo})</span>'
            f'<span><i style="background:{GRIS}"></i>Neutral</span><span><i style="background:{ROJO}"></i>Sobrecompra (RSI &gt; {hi})</span></div>')


def hint(texto_html, icono="✦"):
    return compactar(f'<div class="hint"><div class="ic">{icono}</div><div>{texto_html}</div></div>')


def area_svg(a, b=None, uid="a", w=380, h=150, c1="#6A4FA0", c2="#B3A58F"):
    """Área con la serie principal y una línea punteada de referencia."""
    a = [float(x) for x in a]
    todas = a + ([float(x) for x in b] if b else [])
    lo, hi = min(todas + [0]), max(todas)
    rng = (hi - lo) or 1.0
    pad = 8

    def pts(s):
        return [(pad + i * (w - 2 * pad) / (len(s) - 1), h - pad - (x - lo) / rng * (h - 2 * pad)) for i, x in enumerate(s)]

    pa = pts(a)
    linea = " ".join(f"{x:.1f},{y:.1f}" for x, y in pa)
    area = f"{pa[0][0]:.1f},{h - pad} " + linea + f" {pa[-1][0]:.1f},{h - pad}"
    ref = ""
    if b and len(b) == len(a):
        ref = f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts([float(x) for x in b]))}" fill="none" stroke="{c2}" stroke-width="2" stroke-dasharray="5 5" opacity=".8" vector-effect="non-scaling-stroke"/>'
    return (f'<svg width="100%" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" style="display:block"><defs><linearGradient id="g{uid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{c1}" stop-opacity=".28"/><stop offset="1" stop-color="{c1}" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon points="{area}" fill="url(#g{uid})"/>{ref}<polyline points="{linea}" fill="none" stroke="{c1}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>')


def detalle_fondo(nombre, sub, color, rescate, minimo, rend_txt, rend_pos, svg, leyenda=("Este fondo", "Referencia"), extra=None):
    cls = "pos" if rend_pos else "neg"
    extras = ""
    if extra:
        extras = '<div class="mini-row" style="margin-top:-6px">' + "".join(
            f'<div class="mini"><small>{esc(a)}</small><div style="font-size:1.05rem">{esc(b)}</div></div>' for a, b in extra) + "</div>"
    graf = ""
    if svg:
        graf = (f'<div class="row-sp" style="margin-top:6px"><span class="muted">Rendimiento acumulado</span><b class="{cls}">{esc(rend_txt)}</b></div>'
                f'<div style="margin-top:10px">{svg}</div><div class="lg"><span><i style="background:#6A4FA0"></i>{esc(leyenda[0])}</span>'
                f'<span><i style="background:#B3A58F"></i>{esc(leyenda[1])}</span></div>')
    return compactar(f'<div class="detail"><div class="row-sp"><span class="eyebrow">Seleccionado</span></div>'
                     f'<div class="nm" style="margin-top:16px">{avatar(nombre[:1].upper(), color)}<div><b style="font-size:1.25rem;font-weight:500">{esc(nombre)}</b><span>{esc(sub)}</span></div></div>'
                     f'<div class="mini-row"><div class="mini"><small>⏱ Rescate</small><div>{esc(rescate)}</div></div>'
                     f'<div class="mini"><small>▣ Inversión mínima</small><div>{esc(minimo)}</div></div></div>{extras}{graf}</div>')


def cronograma_card(nombre, sub, filas):
    """Tarjeta del instrumento seleccionado con la lista de sus pagos. filas: [fecha, días, pago] en HTML."""
    t = tabla([("Fecha de pago", "l"), ("Días", "r"), ("Pago por 100 VN", "r")], filas, compacta=True)
    return compactar(f'<div class="detail"><span class="eyebrow">Seleccionado</span>'
                     f'<div class="nm" style="margin:14px 0 10px">{avatar(str(nombre)[:2], color_de(nombre))}'
                     f'<div><b style="font-size:1.25rem;font-weight:500">{esc(nombre)}</b><span>{esc(sub)}</span></div></div>'
                     f'<div class="eyebrow m" style="margin:10px 0 8px">Fechas de pago</div>'
                     f'<div style="max-height:460px;overflow:auto">{t}</div></div>')


def donut(items, centro_n, centro_txt, size=270, radio=92, grosor=36):
    """items: lista de (etiqueta, porcentaje, color)."""
    c = size / 2
    circ = 2 * pi * radio
    acc, arcos = 0.0, ""
    for _, pct, col in items:
        largo = max(0.0, pct / 100 * circ)
        arcos += (f'<circle cx="{c}" cy="{c}" r="{radio}" fill="none" stroke="{col}" stroke-width="{grosor}" '
                  f'stroke-dasharray="{max(largo - 2, 0):.2f} {circ - max(largo - 2, 0):.2f}" stroke-dashoffset="{-acc:.2f}" transform="rotate(-90 {c} {c})"/>')
        acc += largo
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">{arcos}'
            f'<text x="{c}" y="{c - 22}" text-anchor="middle" font-size="13" fill="#8A7A6C">Activos</text>'
            f'<text x="{c}" y="{c + 22}" text-anchor="middle" font-size="46" font-weight="500" fill="#26221F">{esc(centro_n)}</text>'
            f'<text x="{c}" y="{c + 44}" text-anchor="middle" font-size="13" fill="#8A7A6C">{esc(centro_txt)}</text></svg>')


def composicion_datos(items, max_items=6):
    """Ordena, agrupa lo que pase de 5 en 'Otros activos' y asigna colores. items: lista de (etiqueta, porcentaje)."""
    items = sorted(items, key=lambda x: -x[1])
    if len(items) > max_items:
        items = items[:max_items - 1] + [("Otros activos", sum(p for _, p in items[max_items - 1:]))]
    return items, [PALETA[i % len(PALETA)] for i in range(len(items))]


def leyenda_comp(items, colores):
    return "".join(f'<div class="leg-i"><span><i style="background:{colores[i]}"></i>{esc(e)}</span><b>{num(p, 0)}%</b></div>'
                   for i, (e, p) in enumerate(items))


def composicion_texto(titulo, descripcion, items, colores, eyebrow="Composición de cartera"):
    return compactar(f'<div class="eyebrow m">{esc(eyebrow)}</div><div class="h2">{esc(titulo)}</div>'
                     f'<div class="sub">{esc(descripcion)}</div><div class="leg">{leyenda_comp(items, colores)}</div>')


def composicion(titulo, descripcion, items, eyebrow="Composición de cartera", centro_txt="categorías"):
    items, colores = composicion_datos(items)
    dona = donut([(e, p, colores[i]) for i, (e, p) in enumerate(items)], len(items), centro_txt)
    return compactar(f'<div class="comp"><div class="izq">{composicion_texto(titulo, descripcion, items, colores, eyebrow)}</div>'
                     f'<div class="dona">{dona}</div></div>')


def tarjeta_oscura(etiqueta, valor, sub):
    return compactar(f'<div class="dark"><small>{esc(etiqueta)}</small><div class="v">{esc(valor)}</div><div class="s">{esc(sub)}</div></div>')


def barras(items, mejor=None, alto=190):
    """items: lista de (etiqueta, valor, texto_sobre_barra). Eje desde cero. Si mejor es None, todas las barras se ven igual."""
    mx = max(v for _, v, _ in items) or 1
    cols, labs = "", ""
    for i, (et, v, t) in enumerate(items):
        h = max(4, v / mx * alto)
        cls = "unif" if mejor is None else ("best" if i == mejor else "")
        cols += f'<div class="bc {cls}"><div class="t">{esc(t) if (mejor is None or i == mejor) else ""}</div><div class="b" style="height:{h:.0f}px"></div></div>'
        labs += f'<div class="{"best" if i == mejor else ""}">{esc(et)}</div>'
    return compactar(f'<div class="bars">{cols}</div><div class="bl">{labs}</div>')


def strip(celdas):
    """celdas: lista de (etiqueta, valor, sub, resaltada)."""
    cs = "".join(f'<div class="cell {"hl" if hl else ""}"><small>{esc(e)}</small><div class="v">{esc(v)}</div><small>{esc(s)}</small></div>'
                 for e, v, s, hl in celdas)
    return compactar(f'<div class="strip">{cs}</div>')


def meses(items):
    """items: lista de (mes, porcentaje, texto_valor)."""
    mx = max((abs(p) for _, p, _ in items), default=1) or 1
    cols = ""
    for m, p, v in items:
        h = max(6, abs(p) / mx * 120)
        cls = "n" if p < 0 else ""
        col = "neg" if p < 0 else "pos"
        cols += (f'<div class="col"><small>{esc(m)}</small><div class="p {col}">{num(p, 2, suf="%", signo=True)}</div>'
                 f'<div class="area"><div class="bb {cls}" style="height:{h:.0f}px"></div></div><div class="vv">{esc(v)}</div></div>')
    return compactar(f'<div class="mm">{cols}</div>')


COMPONENTE_TABLA_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style id="css-app"></style>
<style>html,body{margin:0;background:transparent}#raiz{padding:6px 4px 10px}</style>
</head>
<body>
<div id="raiz"></div>
<script>
// Componente mínimo de Streamlit: dibuja una tabla HTML y devuelve el id de la fila donde se hace clic.
function enviar(tipo, extra) {
  window.parent.postMessage(Object.assign({isStreamlitMessage: true, type: tipo}, extra || {}), "*");
}
function ajustarAltura() {
  enviar("streamlit:setFrameHeight", {height: document.documentElement.scrollHeight});
}
var seleccionada = null;
function marcar() {
  document.querySelectorAll("tr[data-id]").forEach(function (tr) {
    tr.classList.toggle("sel", tr.getAttribute("data-id") === seleccionada);
  });
}
function dibujar(args) {
  document.getElementById("css-app").textContent = args.css || "";
  document.getElementById("raiz").innerHTML = args.html || "";
  seleccionada = args.selected;
  marcar();
  document.querySelectorAll("tr[data-id]").forEach(function (tr) {
    tr.addEventListener("click", function () {
      seleccionada = tr.getAttribute("data-id");
      marcar();
      enviar("streamlit:setComponentValue", {value: seleccionada, dataType: "json"});
    });
  });
  ajustarAltura();
  setTimeout(ajustarAltura, 150);
  setTimeout(ajustarAltura, 600);
}
window.addEventListener("message", function (ev) {
  if (ev.data && ev.data.type === "streamlit:render") { dibujar(ev.data.args || {}); }
});
window.addEventListener("resize", ajustarAltura);
enviar("streamlit:componentReady", {apiVersion: 1});
</script>
</body>
</html>
"""
