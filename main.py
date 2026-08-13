import pandas as pd
import requests
from datetime import datetime, timedelta
import yfinance as yf
from fredapi import Fred
from bcb import sgs, Expectativas
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib import colors
from io import BytesIO
import os
import time

# ============================================================
# CONFIGURAÇÃO
# ============================================================
FRED_API_KEY = "8fddda411ea6b5c0a1f2f780a3805670"  # https://fred.stlouisfed.org/docs/api/api_key.html
fred = Fred(api_key=FRED_API_KEY)

PASTA_SAIDA = "relatorios_macro"
os.makedirs(PASTA_SAIDA, exist_ok=True)

# ============================================================
# FUNÇÕES DE DADOS - BRASIL
# ============================================================
def get_bcb(codigo, last=None, start=None):
    """Séries oficiais do BCB (respeita limite de 20 no last)"""
    if last is not None:
        last = min(int(last), 20)
        return sgs.get({codigo: codigo}, last=last)
    
    if start is None:
        start = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    
    return sgs.get({codigo: codigo}, start=start)


def get_focus_resumo():
    """Últimas expectativas do Focus (IPCA, Selic, Câmbio, PIB)"""
    em = Expectativas()
    ep = em.get_endpoint("ExpectativasMercadoAnuais")
    
    indicadores = ["IPCA", "Selic", "Câmbio", "PIB Total"]
    resultados = {}
    
    for ind in indicadores:
        try:
            df = (ep.query()
                  .filter(ep.Indicador == ind)
                  .filter(ep.baseCalculo == 0)
                  .orderby(ep.Data.desc())
                  .limit(30)
                  .collect())
            
            ano_atual = str(datetime.now().year)
            ano_prox = str(datetime.now().year + 1)
            
            med_atual = None
            med_prox = None
            
            if not df.empty:
                df_atual = df[df["DataReferencia"] == ano_atual]
                df_prox = df[df["DataReferencia"] == ano_prox]
                
                if not df_atual.empty:
                    med_atual = df_atual["Mediana"].iloc[0]
                if not df_prox.empty:
                    med_prox = df_prox["Mediana"].iloc[0]
            
            resultados[ind] = {
                "atual": med_atual,
                "proximo": med_prox,
                "data": df["Data"].iloc[0] if not df.empty else None
            }
        except Exception as e:
            print(f"  Aviso Focus {ind}: {e}")
            resultados[ind] = {"atual": None, "proximo": None, "data": None}
    
    return resultados


# ============================================================
# FUNÇÕES DE DADOS - MERCADO (mais robusta)
# ============================================================
def get_market():
    """Baixa dados de mercado de forma robusta e trata falhas"""
    tickers = {
        "VIX": "^VIX",
        "WTI": "CL=F",
        "Brent": "BZ=F",
        "DXY": "DX-Y.NYB",
        "SPX": "^GSPC"
    }
    
    data = {}
    print("\nBaixando dados de mercado...")
    
    for name, ticker in tickers.items():
        serie = pd.Series(dtype=float)
        
        # Tentativa 1: period="1y"
        try:
            hist = yf.Ticker(ticker).history(period="1y", auto_adjust=True, timeout=15)
            if not hist.empty and len(hist) >= 5:
                hist.index = hist.index.tz_localize(None)
                serie = hist["Close"]
        except Exception:
            pass
        
        # Tentativa 2: com data explícita (se a primeira falhou)
        if serie.empty:
            try:
                time.sleep(1)  # pequena pausa para evitar rate-limit
                hist = yf.Ticker(ticker).history(start="2025-01-01", auto_adjust=True, timeout=15)
                if not hist.empty:
                    hist.index = hist.index.tz_localize(None)
                    serie = hist["Close"]
            except Exception as e:
                print(f"  ✗ {name}: falhou → {e}")
        
        if not serie.empty:
            data[name] = serie
            print(f"  ✓ {name}: {len(serie)} dias | último = {serie.iloc[-1]:.2f}")
        else:
            data[name] = pd.Series(dtype=float)
            print(f"  ✗ {name}: sem dados")
    
    return pd.DataFrame(data)


def safe_last(series_or_df, casas=2):
    """Retorna o último valor formatado ou 'N/D' se for nan/vazio"""
    try:
        if series_or_df is None:
            return "N/D"
        
        if isinstance(series_or_df, pd.DataFrame):
            if series_or_df.empty:
                return "N/D"
            val = series_or_df.iloc[-1, 0]
        else:
            if series_or_df.empty or pd.isna(series_or_df.iloc[-1]):
                return "N/D"
            val = series_or_df.iloc[-1]
        
        if pd.isna(val):
            return "N/D"
        
        return f"{float(val):.{casas}f}"
    except Exception:
        return "N/D"


# ============================================================
# GERAÇÃO DE GRÁFICOS
# ============================================================
def criar_graficos(dados):
    figs = []
    
    # 1. IPCA
    fig, ax = plt.subplots(figsize=(10, 4))
    if "ipca" in dados and not dados["ipca"].empty:
        dados["ipca"].plot(ax=ax, color="green", linewidth=2)
        ax.set_title("IPCA mensal (%)")
    else:
        ax.text(0.5, 0.5, "IPCA sem dados", ha="center", va="center", transform=ax.transAxes)
        ax.set_title("IPCA mensal")
    ax.grid(True, alpha=0.3)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    buf.seek(0)
    figs.append(buf)
    plt.close()
    
    # 2. Dólar
    fig, ax = plt.subplots(figsize=(10, 4))
    if "dolar" in dados and not dados["dolar"].empty:
        dados["dolar"].tail(150).plot(ax=ax, color="blue", linewidth=2)
        ax.set_title("Dólar PTAX (últimos meses)")
    else:
        ax.text(0.5, 0.5, "Dólar sem dados", ha="center", va="center", transform=ax.transAxes)
        ax.set_title("Dólar PTAX")
    ax.grid(True, alpha=0.3)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    buf.seek(0)
    figs.append(buf)
    plt.close()
    
    # 3. VIX + Petróleo
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    
    # VIX
    vix_ok = ("market" in dados and "VIX" in dados["market"].columns 
              and not dados["market"]["VIX"].dropna().empty)
    if vix_ok:
        dados["market"]["VIX"].dropna().plot(ax=axes[0], color="red", linewidth=1.5)
        axes[0].set_title("VIX")
    else:
        axes[0].text(0.5, 0.5, "VIX sem dados\n(rode novamente em alguns minutos)", 
                     ha="center", va="center", transform=axes[0].transAxes, fontsize=9)
        axes[0].set_title("VIX")
    
    # WTI
    wti_ok = ("market" in dados and "WTI" in dados["market"].columns 
              and not dados["market"]["WTI"].dropna().empty)
    if wti_ok:
        dados["market"]["WTI"].dropna().plot(ax=axes[1], color="orange", linewidth=1.5)
        axes[1].set_title("Petróleo WTI (US$)")
    else:
        axes[1].text(0.5, 0.5, "WTI sem dados\n(rode novamente em alguns minutos)", 
                     ha="center", va="center", transform=axes[1].transAxes, fontsize=9)
        axes[1].set_title("Petróleo WTI (US$)")
    
    for ax in axes:
        ax.grid(True, alpha=0.3)
    
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    buf.seek(0)
    figs.append(buf)
    plt.close()
    
    return figs


# ============================================================
# GERAÇÃO DO PDF
# ============================================================
def gerar_pdf(resumo, focus, figs, nome_arquivo):
    doc = SimpleDocTemplate(
        nome_arquivo,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Titulo", fontSize=18, alignment=TA_CENTER, spaceAfter=12, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Subtitulo", fontSize=11, alignment=TA_CENTER, spaceAfter=18, textColor=colors.grey))
    styles.add(ParagraphStyle(name="Secao", fontSize=13, spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold", textColor=colors.HexColor("#1a5276")))
    styles.add(ParagraphStyle(name="Normal2", fontSize=10, spaceAfter=3, leading=14))
    
    story = []
    
    # Cabeçalho
    story.append(Paragraph("PAINEL MACROECONÔMICO SEMANAL", styles["Titulo"]))
    story.append(Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}", styles["Subtitulo"]))
    
    # BRASIL
    story.append(Paragraph("🇧🇷 BRASIL", styles["Secao"]))
    texto_br = f"""
    <b>IPCA (último mês):</b> {resumo.get('ipca_ultimo', 'N/D')}<br/>
    <b>IPCA acumulado 12 meses:</b> {resumo.get('ipca_12m', 'N/D')}<br/>
    <b>Selic meta atual:</b> {resumo.get('selic', 'N/D')}<br/>
    <b>Dólar PTAX (último):</b> R$ {resumo.get('dolar', 'N/D')}<br/>
    """
    story.append(Paragraph(texto_br, styles["Normal2"]))
    
    # Focus
    story.append(Paragraph("Expectativas Focus (mediana)", styles["Secao"]))
    focus_txt = ""
    for ind, vals in focus.items():
        if vals.get("atual") is not None:
            atual = f"{vals['atual']:.2f}"
            prox = f"{vals['proximo']:.2f}" if vals.get("proximo") is not None else "N/D"
            focus_txt += f"<b>{ind}:</b> {atual} (ano atual) → {prox} (próximo ano)<br/>"
    story.append(Paragraph(focus_txt or "Dados Focus indisponíveis no momento.", styles["Normal2"]))
    
    # EUA
    story.append(Paragraph("🇺🇸 ESTADOS UNIDOS", styles["Secao"]))
    texto_eua = f"""
    <b>CPI:</b> {resumo.get('cpi', 'N/D')}<br/>
    <b>Core PCE:</b> {resumo.get('pce', 'N/D')}<br/>
    <b>Desemprego:</b> {resumo.get('unemp', 'N/D')}%<br/>
    <b>Fed Funds:</b> {resumo.get('fedfunds', 'N/D')}%<br/>
    """
    story.append(Paragraph(texto_eua, styles["Normal2"]))
    
    # MERCADO
    story.append(Paragraph("📈 MERCADO", styles["Secao"]))
    texto_mkt = f"""
    <b>VIX:</b> {resumo.get('vix', 'N/D')}<br/>
    <b>Petróleo WTI:</b> US$ {resumo.get('wti', 'N/D')}<br/>
    <b>DXY (Dólar Index):</b> {resumo.get('dxy', 'N/D')}<br/>
    <b>S&P 500:</b> {resumo.get('spx', 'N/D')}<br/>
    """
    story.append(Paragraph(texto_mkt, styles["Normal2"]))
    
    # Gráficos
    story.append(PageBreak())
    story.append(Paragraph("GRÁFICOS", styles["Secao"]))
    
    for fig_buf in figs:
        img = Image(fig_buf, width=17*cm, height=6.8*cm)
        story.append(img)
        story.append(Spacer(1, 8))
    
    story.append(Spacer(1, 15))
    story.append(Paragraph(
        "<i>Relatório gerado automaticamente com dados públicos do Banco Central do Brasil, FRED e Yahoo Finance. "
        "Uso educacional e de acompanhamento pessoal.</i>",
        ParagraphStyle(name="Rodape", fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))
    
    doc.build(story)
    print(f"\n✅ PDF gerado: {nome_arquivo}")


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================
def rodar_painel():
    print("=" * 55)
    print("Coletando dados do painel macro...")
    print("=" * 55)
    
    # ---------- BRASIL ----------
    print("\nBrasil (BCB)...")
    ipca = get_bcb(433, last=20)
    ipca_12m = get_bcb(13522, last=6)
    selic = get_bcb(432, last=8)
    dolar = get_bcb(1, start="2025-01-01")
    
    print(f"  IPCA último: {safe_last(ipca)}%")
    print(f"  Dólar último: R$ {safe_last(dolar, 4)}")
    
    # Focus
    print("\nFocus...")
    focus = get_focus_resumo()
    
    # ---------- EUA ----------
    print("\nEstados Unidos (FRED)...")
    try:
        cpi = fred.get_series("CPIAUCSL", observation_start="2023-01-01")
        pce = fred.get_series("PCEPILFE", observation_start="2023-01-01")
        unemp = fred.get_series("UNRATE", observation_start="2023-01-01")
        fedfunds = fred.get_series("FEDFUNDS", observation_start="2023-01-01")
    except Exception as e:
        print(f"  Erro FRED: {e}")
        cpi = pce = unemp = fedfunds = pd.Series(dtype=float)
    
    # ---------- MERCADO ----------
    market = get_market()
    
    # ---------- RESUMO (sem nan) ----------
    resumo = {
        "ipca_ultimo": f"{safe_last(ipca)}%",
        "ipca_12m": f"{safe_last(ipca_12m)}%",
        "selic": f"{safe_last(selic)}% a.a.",
        "dolar": safe_last(dolar, 4),
        "cpi": safe_last(cpi),
        "pce": safe_last(pce),
        "unemp": safe_last(unemp, 1),
        "fedfunds": safe_last(fedfunds),
        "vix": safe_last(market["VIX"]) if "VIX" in market.columns else "N/D",
        "wti": safe_last(market["WTI"]) if "WTI" in market.columns else "N/D",
        "dxy": safe_last(market["DXY"]) if "DXY" in market.columns else "N/D",
        "spx": safe_last(market["SPX"], 0) if "SPX" in market.columns else "N/D",
    }
    
    dados = {
        "ipca": ipca.iloc[:, 0] if not ipca.empty else pd.Series(dtype=float),
        "dolar": dolar.iloc[:, 0] if not dolar.empty else pd.Series(dtype=float),
        "market": market
    }
    
    # Gráficos
    print("\nGerando gráficos...")
    figs = criar_graficos(dados)
    
    # PDF
    data_str = datetime.now().strftime("%Y-%m-%d")
    pdf_path = os.path.join(PASTA_SAIDA, f"painel_macro_{data_str}.pdf")
    gerar_pdf(resumo, focus, figs, pdf_path)
    
    # CSVs
    try:
        if not ipca.empty:
            ipca.to_csv(os.path.join(PASTA_SAIDA, "historico_ipca.csv"))
        if not dolar.empty:
            dolar.to_csv(os.path.join(PASTA_SAIDA, "historico_dolar.csv"))
        if not market.empty:
            market.to_csv(os.path.join(PASTA_SAIDA, "historico_mercado.csv"))
    except Exception:
        pass
    
    print("\n" + "=" * 55)
    print("✅ Painel concluído com sucesso!")
    print(f"📁 Pasta: {os.path.abspath(PASTA_SAIDA)}")
    print("=" * 55)
    
    return pdf_path


# ============================================================
if __name__ == "__main__":
    rodar_painel()