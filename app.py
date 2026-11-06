"""Dashboard ReverseMilk — Edição Bento Box, Mobile App UX & Sidebar Transição
Rode com: streamlit run app.py
"""
import base64
import os
from datetime import datetime, time, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from agendamento import BUFFER_MIN, agendamento_reverso, reprogramar
from gerar_dados import ROTEIROS, gerar
from indicadores import classificar_etapas, distribuicao_mc, resumo_ops

st.set_page_config(page_title="ReverseMilk", page_icon="🥛", layout="wide", initial_sidebar_state="expanded")

# Injeção de JS para Idioma e Troca de Tema (Logo + Modal)
components.html(r"""<script>
const d = window.parent.document;
d.documentElement.setAttribute('translate', 'no'); 
d.documentElement.lang = 'pt-BR';

function alternarLogoETema() {
    const logoPreta = d.querySelector('.logo-preta');
    const logoBranca = d.querySelector('.logo-branca');
    const modalCard = d.querySelector('.modal-card-inner');
    const sidebar = d.querySelector('[data-testid="stSidebar"]');
    
    const bg = sidebar ? getComputedStyle(sidebar).backgroundColor : getComputedStyle(d.body).backgroundColor;
    let isDark = false;
    
    const match = bg.match(/\d+/g);
    if (match && match.length >= 3) {
        const r = parseInt(match[0]), g = parseInt(match[1]), b = parseInt(match[2]);
        isDark = (0.2126 * r + 0.7152 * g + 0.0722 * b) < 128;
    }

    if (logoPreta && logoBranca) {
        if (isDark) {
            logoPreta.style.setProperty('opacity', '0', 'important');
            logoBranca.style.setProperty('opacity', '1', 'important');
        } else {
            logoPreta.style.setProperty('opacity', '1', 'important');
            logoBranca.style.setProperty('opacity', '0', 'important');
        }
    }

    if (modalCard) {
        if (isDark) {
            modalCard.style.setProperty('background-color', '#1e2029', 'important');
            modalCard.style.setProperty('color', '#ffffff', 'important');
        } else {
            modalCard.style.setProperty('background-color', '#ffffff', 'important');
            modalCard.style.setProperty('color', '#0f172a', 'important');
        }
    }
}

setInterval(alternarLogoETema, 150);
</script>""", height=0)

# ---------------------------------------------------------------- CSS BENTO BOX, TRANSIÇÃO SIDEBAR & RESPONSIVIDADE MOBILE
css_bento = r"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    @import url("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css");

    /* Transição Suave Global de Tema */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], 
    [data-testid="stHeader"], [data-testid="stTabs"] button, div, span, p, h1, h2, h3, i {
        transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease !important;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        -webkit-tap-highlight-color: transparent;
    }
    
    footer {visibility: hidden;}
    
    .block-container {
        padding: 2rem 1.5rem;
        max-width: 1600px;
    }

    /* =========================================================
       TRANSIÇÃO DE ABRIR/FECHAR DA SIDEBAR (SLIDE ANIMATION)
       ========================================================= */
    [data-testid="stSidebar"] {
        transition:
            transform 0.4s cubic-bezier(0.4, 0, 0.2, 1),
            margin-left 0.4s cubic-bezier(0.4, 0, 0.2, 1),
            min-width 0.4s cubic-bezier(0.4, 0, 0.2, 1),
            max-width 0.4s cubic-bezier(0.4, 0, 0.2, 1),
            width 0.4s cubic-bezier(0.4, 0, 0.2, 1),
            background-color 0.3s ease !important;
        will-change: transform, margin-left, width;
    }

    /* Fechada: continua renderizada pra animação de saída acontecer,
       e só some depois que o slide termina */
    [data-testid="stSidebar"][aria-expanded="false"] {
        visibility: visible !important;
        display: flex !important;
        pointer-events: none;
        transition:
            transform 0.4s cubic-bezier(0.4, 0, 0.2, 1),
            margin-left 0.4s cubic-bezier(0.4, 0, 0.2, 1),
            min-width 0.4s cubic-bezier(0.4, 0, 0.2, 1),
            max-width 0.4s cubic-bezier(0.4, 0, 0.2, 1),
            width 0.4s cubic-bezier(0.4, 0, 0.2, 1),
            visibility 0s linear 0.4s,
            background-color 0.3s ease !important;
    }

    [data-testid="stSidebar"][aria-expanded="true"] {
        pointer-events: auto;
    }
    
    [data-testid="stSidebar"] > div:first-child,
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        scrollbar-width: none !important;
        -ms-overflow-style: none !important;
    }
    [data-testid="stSidebar"] > div:first-child::-webkit-scrollbar,
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"]::-webkit-scrollbar {
        display: none !important;
        width: 0px !important;
        background: transparent !important;
    }

    /* =========================================================
       MODAL DE PREMISSAS
       ========================================================= */
    #modal-toggle { display: none !important; }
    #modal-toggle:checked ~ #modal-premissas { display: flex !important; }

    /* =========================================================
       TABS: DESKTOP & MOBILE
       ========================================================= */
    div[data-testid="stTabs"] > div[data-baseweb="tab-list"],
    div[data-testid="stTabs"] > div:first-child {
        display: flex !important;
        justify-content: center !important;
        flex-wrap: wrap !important;
        gap: 16px !important;
        padding-bottom: 24px !important;
        width: 100% !important;
    }

    div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
    div[data-testid="stTabs"] div[data-baseweb="tab-border"] {
        display: none !important;
    }

    div[data-testid="stTabs"] button[role="tab"] {
        background-color: var(--secondary-background-color) !important;
        border: 2px solid rgba(128, 128, 128, 0.3) !important;
        border-radius: 99px !important;
        padding: 14px 28px !important;
        margin: 0 !important;
        min-height: 48px !important;
    }
    
    div[data-testid="stTabs"] button[role="tab"] div[data-testid="stMarkdownContainer"] p {
        font-size: 18px !important;
        font-weight: 800 !important;
        color: var(--text-color) !important;
        margin: 0 !important;
    }

    /* Ícones do Bootstrap nas abas */
    div[data-testid="stTabs"] button[role="tab"]:nth-child(1)::before { content: "\F143"; font-family: "bootstrap-icons"; margin-right: 10px; font-size: 20px; color: var(--text-color) !important; }
    div[data-testid="stTabs"] button[role="tab"]:nth-child(2)::before { content: "\F225"; font-family: "bootstrap-icons"; margin-right: 10px; font-size: 20px; color: var(--text-color) !important; }
    div[data-testid="stTabs"] button[role="tab"]:nth-child(3)::before { content: "\F294"; font-family: "bootstrap-icons"; margin-right: 10px; font-size: 20px; color: var(--text-color) !important; }
    div[data-testid="stTabs"] button[role="tab"]:nth-child(4)::before { content: "\F5EA"; font-family: "bootstrap-icons"; margin-right: 10px; font-size: 20px; color: var(--text-color) !important; }
    div[data-testid="stTabs"] button[role="tab"]:nth-child(5)::before { content: "\F2EE"; font-family: "bootstrap-icons"; margin-right: 10px; font-size: 20px; color: var(--text-color) !important; }

    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background-color: var(--text-color) !important;
        border: 2px solid var(--text-color) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        transform: scale(1.03) !important;
    }
    
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] div[data-testid="stMarkdownContainer"] p {
        color: var(--background-color) !important;
        font-weight: 900 !important;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"]::before {
        color: var(--background-color) !important;
    }

    /* =========================================================
       TABELAS E EXPANSORES
       ========================================================= */
    [data-testid="stDataFrame"] {
        background-color: transparent !important;
        border-radius: 16px !important;
        border: 1px solid rgba(128, 128, 128, 0.25) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        overflow: hidden !important;
    }
    .stExpander {
        background-color: var(--secondary-background-color) !important;
        border-radius: 16px !important;
        border: 2px solid rgba(128, 128, 128, 0.2) !important;
    }

    [data-testid="stFileUploader"] section {
        padding: 0 !important;
        background-color: transparent !important;
        border: none !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        min-height: unset !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }

    [data-testid="stFileUploader"] button {
        width: 100% !important;
        background-color: #2e9e5b !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 800 !important;
        min-height: 48px !important;
    }
    [data-testid="stFileUploader"] button:hover {
        background-color: #257d48 !important;
        color: #ffffff !important;
    }

    /* Fullscreen adjustment */
    [data-testid="stFullScreenFrame"], 
    [data-testid="stFullScreenFrame"] > div {
        height: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        flex: 1 !important;
    }

    [data-testid="stFullScreenFrame"] [data-testid="stDataFrame"],
    [data-testid="stFullScreenFrame"] [data-testid="stDataFrame"] > div {
        height: 100% !important;
        min-height: 100% !important;
        max-height: 100% !important;
        flex: 1 !important;
    }

    /* =========================================================
       EVITANDO SOBREPOSIÇÕES EM MOBILE / TABLET (TIPO APP)
       ========================================================= */
    @media (max-width: 992px) {
        /* Desfaz colunas travadas em dispositivos móveis para evitar esmagamento */
        div[data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            margin-bottom: 12px !important;
        }
    }

    @media (max-width: 768px) {
        .block-container {
            padding: 1rem 0.75rem 95px 0.75rem !important;
        }

        /* Menu de Abas Fixo no Rodapé (Bottom Navigation Dock) */
        div[data-testid="stTabs"] > div[data-baseweb="tab-list"],
        div[data-testid="stTabs"] > div:first-child {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            background-color: var(--secondary-background-color) !important;
            border-top: 1px solid rgba(128, 128, 128, 0.2) !important;
            box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.18) !important;
            z-index: 99999 !important;
            padding: 8px 4px !important;
            gap: 2px !important;
            justify-content: space-around !important;
            flex-wrap: nowrap !important;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }

        div[data-testid="stTabs"] button[role="tab"] {
            padding: 6px 2px !important;
            border: none !important;
            border-radius: 12px !important;
            background: transparent !important;
            flex: 1 !important;
            min-height: 44px !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
        }

        div[data-testid="stTabs"] button[role="tab"]:active {
            transform: scale(0.95) !important;
        }

        div[data-testid="stTabs"] button[role="tab"] div[data-testid="stMarkdownContainer"] p {
            font-size: 10px !important;
            font-weight: 700 !important;
            line-height: 1.1 !important;
            margin-top: 3px !important;
            text-align: center !important;
        }

        div[data-testid="stTabs"] button[role="tab"]::before {
            margin-right: 0 !important;
            font-size: 18px !important;
        }

        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background-color: rgba(37, 99, 235, 0.15) !important;
            border: none !important;
            transform: scale(1) !important;
        }

        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] div[data-testid="stMarkdownContainer"] p {
            color: #2563eb !important;
            font-weight: 800 !important;
        }

        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"]::before {
            color: #2563eb !important;
        }

        /* Toque otimizado em botões e seletores */
        .stSelectbox, .stDateInput, .stTimeInput, .stNumberInput, .stSlider {
            margin-bottom: 12px !important;
        }
        
        button, input, select {
            min-height: 46px !important;
        }
    }
</style>
"""
st.markdown(css_bento, unsafe_allow_html=True)

CORES = {"No prazo": "#2e9e5b", "Em risco": "#f0a30a", "Atrasada": "#d64545",
         "Concluída no prazo": "#1f6f43", "Concluída com atraso": "#8c5a2b"}
ICONES = {"No prazo": "🟢", "Em risco": "🟡", "Atrasada": "🔴",
          "Concluída no prazo": "✅", "Concluída com atraso": "🟤"}
COLS_DATA = ["prazo", "plan_inicio", "plan_fim", "real_inicio", "real_fim"]


# ---------------------------------------------------------------- FUNÇÕES HTML
def bento_kpi(titulo, valor, subtitulo, cor_tema="var(--text-color)"):
    html = f"""<div style="background-color: var(--secondary-background-color); border-radius: 20px; padding: 18px 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid rgba(128, 128, 128, 0.15); border-left: 6px solid {cor_tema}; height: 100%; display: flex; flex-direction: column; justify-content: center; margin-bottom: 8px;">
<div style="color: var(--text-color); font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8;">{titulo}</div>
<div style="display: flex; align-items: baseline; gap: 10px; margin: 6px 0;">
    <div style="color: {cor_tema}; font-size: clamp(28px, 5vw, 42px); font-weight: 900; line-height: 1;">{valor}</div>
    <div style="color: var(--text-color); font-size: 13px; font-weight: 600; opacity: 0.9;">{subtitulo}</div>
</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)

def bento_alerta(op, produto, etapa, hora, margem, critico=True):
    cor_borda = "#dc2626" if critico else "#d97706"
    html = f"""<div style="background-color: var(--secondary-background-color); border-left: 6px solid {cor_borda}; border-radius: 16px; padding: 18px; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-top: 1px solid rgba(128,128,128,0.15); border-right: 1px solid rgba(128,128,128,0.15); border-bottom: 1px solid rgba(128,128,128,0.15);">
<div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; margin-bottom: 8px; gap: 6px;">
<div style="color: var(--text-color); font-weight: 900; font-size: 16px;">OP {op} • {produto}</div>
<div style="background-color: {cor_borda}; color: #ffffff; padding: 5px 12px; border-radius: 99px; font-size: 12px; font-weight: 800; white-space: nowrap;">{margem:.0f} min margem</div>
</div>
<div style="color: var(--text-color); font-size: 14px; font-weight: 600;">Etapa atual: <span style="font-weight: 800;">{etapa}</span></div>
<div style="color: var(--text-color); font-size: 14px; font-weight: 600; margin-top: 4px;">Projeção de término: <span style="font-weight: 800;">{hora}</span></div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------- DADOS
@st.cache_data
def dados_sinteticos(n, seed):
    return gerar(int(n), int(seed), base=datetime(2026, 10, 5, 6, 0))

@st.cache_data
def calcular(df, agora, tol, limite, n_sim):
    d = classificar_etapas(df, agora, tol)
    return d, resumo_ops(d, agora, limite, n_sim=n_sim)


# ---------------------------------------------------------------- SIDEBAR COM CROSS-FADE DE LOGOS
def get_base64_image(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

logo_preta_b64 = get_base64_image("logo_preta.png")
logo_branca_b64 = get_base64_image("logo_branca.png")

if logo_preta_b64 and logo_branca_b64:
    st.sidebar.markdown(f"""
    <style>
        .logo-box {{
            position: relative;
            width: 100%;
            min-height: 80px;
            margin-bottom: 24px;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .logo-preta, .logo-branca {{
            width: 80% !important;
            height: auto !important;
            position: absolute;
            left: 10%;
            top: 0;
            transition: opacity 0.3s ease-in-out !important;
        }}
        .logo-preta {{ opacity: 1; }}
        .logo-branca {{ opacity: 0; }}
    </style>
    <div class="logo-box">
        <img src="data:image/png;base64,{logo_preta_b64}" class="logo-preta" alt="ReverseMilk Logo Dark">
        <img src="data:image/png;base64,{logo_branca_b64}" class="logo-branca" alt="ReverseMilk Logo Light">
    </div>
    """, unsafe_allow_html=True)
else:
    st.sidebar.markdown("<h2 style='font-weight: 900; color: var(--text-color); text-align: center; margin-bottom: 24px;'>ReverseMilk</h2>", unsafe_allow_html=True)

st.sidebar.markdown("<p style='font-weight: 800; color: var(--text-color); margin-bottom: 10px;'>Usar CSV próprio</p>", unsafe_allow_html=True)

arq = st.sidebar.file_uploader("Upload", type="csv", label_visibility="collapsed")

st.sidebar.markdown("""
<div style="color: var(--text-color); font-size: 12px; font-weight: 700; margin-top: -2px; margin-bottom: 20px; text-align: center;">
    200MB max • CSV
</div>
""", unsafe_allow_html=True)

n_ops = st.sidebar.number_input("Nº de ordens (sintéticos)", 10, 200, 40, 5)
seed = st.sidebar.number_input("Monte Carlo", 0, 9999, 42)

df = pd.read_csv(arq, parse_dates=COLS_DATA) if arq else dados_sinteticos(n_ops, seed)
dmin = df.plan_inicio.min().floor("30min").to_pydatetime()
dmax = df.prazo.max().ceil("30min").to_pydatetime()
padrao = min(dmin + timedelta(hours=24), dmax)

st.sidebar.markdown("---")
agora = pd.Timestamp(st.sidebar.slider(
    "Horário atual (simulado)", min_value=dmin, max_value=dmax, value=padrao, step=timedelta(minutes=30), format="DD/MM HH:mm"))
tol = st.sidebar.slider("Tolerância (min)", 5, 120, 30)
limite = st.sidebar.slider("Margem alerta (min)", 15, 240, 30)
n_sim = st.sidebar.select_slider("Simulações", [200, 500, 1000, 2000], 1000)

d, r = calcular(df, agora, tol, limite, n_sim)

# ---------------------------------------------------------------- CABEÇALHO COM BOTÃO "!" E MODAL SÓLIDO
st.markdown(f"""
<div style="position: relative; margin-bottom: 30px; display: flex; flex-direction: column; align-items: center; text-align: center; width: 100%;">
<input type="checkbox" id="modal-toggle">
<div style="display: inline-flex; align-items: center; justify-content: center; gap: 10px; position: relative; max-width: 100%;">
<span style="font-size: clamp(24px, 4.5vw, 48px); font-weight: 900; letter-spacing: -1px; line-height: 1.2; color: var(--text-color);">Planejamento Reverso & Cenários</span>
<label for="modal-toggle" title="Entenda as Premissas" style="width: 28px; height: 28px; border-radius: 50%; background-color: var(--secondary-background-color); border: 2px solid rgba(128, 128, 128, 0.3); color: var(--text-color); font-weight: 900; font-size: 15px; font-family: 'Inter', sans-serif; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: all 0.2s ease; flex-shrink: 0;">!</label>
</div>
<div style="font-size: 15px; font-weight: 600; margin-top: 8px; color: var(--text-color);">Status simulado: <b>{agora:%d/%m/%Y às %H:%M}</b></div>
<div id="modal-premissas" style="display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); z-index: 999999; align-items: center; justify-content: center;">
<div class="modal-card-inner" style="background-color: #ffffff; color: #0f172a; border-radius: 20px; padding: 26px 28px; max-width: 500px; width: 92%; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); border: 2px solid rgba(128,128,128,0.3); position: relative; text-align: left; opacity: 1 !important;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
<h3 style="margin: 0; font-weight: 900; font-size: 20px; display: flex; align-items: center; gap: 10px;"><i class="bi bi-info-circle-fill" style="color: #2563eb;"></i> Entenda as Premissas</h3>
<label for="modal-toggle" style="background: transparent; border: none; font-size: 24px; font-weight: 800; cursor: pointer; opacity: 0.7; transition: opacity 0.2s;">✕</label>
</div>
<div style="font-size: 14px; line-height: 1.6;">
<p style="margin-bottom: 8px;"><strong style="font-size: 15px;">Critérios de Alertas:</strong></p>
<ul style="padding-left: 20px; margin-bottom: 16px;">
<li style="margin-bottom: 6px;">🔴 <strong>Atrasada:</strong> Margem < 0.</li>
<li style="margin-bottom: 6px;">🟡 <strong>Em Risco:</strong> Margem positiva, mas abaixo do limite.</li>
<li style="margin-bottom: 6px;">🟢 <strong>No Prazo:</strong> Margem segura.</li>
</ul>
<p style="margin-bottom: 6px;"><strong style="font-size: 15px;">Simulação Monte Carlo:</strong></p>
<p style="margin: 0; opacity: 0.85;">Simula centenas de cenários aplicando distribuição Lognormal nos tempos, prevendo probabilidade de atraso.</p>
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- ABAS

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Visão geral", "Linha do tempo", "Agendamento reverso", "Simular atraso", "Dados"
]) 

# ------------------------------------------------------------ VISÃO GERAL
with tab1:
    produtos = sorted(r.produto.unique())
    r1 = r.copy()
    d1 = d.copy()
    em_and = r1[~r1.status.str.startswith("Concluída")]
    conc = r1[r1.status.str.startswith("Concluída")]
    impacto = (-em_and.margem_min).clip(lower=0)

    # GRID ASSIMÉTRICO DE KPIS (RESPONSIVO PARA COLUNA ÚNICA EM MÓVEIS)
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2], gap="large")
    
    with c1: 
        bento_kpi("OPs Ativas", str(len(em_and)), "Em andamento", cor_tema="#2563eb")
    with c2: 
        bento_kpi("Críticas", str(int((r1.status.isin(["Atrasada", "Em risco"])).sum())), "Atraso ou Risco", cor_tema="#dc2626")
    with c3: 
        taxa = f"{(conc.status == 'Concluída no prazo').mean() * 100:.0f}%" if len(conc) else "—"
        bento_kpi("Sucesso", taxa, "Entregas no prazo", cor_tema="#2e9e5b")
    with c4: 
        bento_kpi("Desvio Médio", f"{impacto.mean():.0f} min" if len(em_and) else "0 min", "Atraso projetado", cor_tema="#d97706")
    
    st.write("")

    col_alertas, col_gargalos = st.columns([1, 1.3], gap="large")
    
    with col_alertas:
        st.markdown("<h3 style='font-weight: 900; font-size: 20px; margin-bottom: 16px; color: var(--text-color);'><i class='bi bi-exclamation-octagon-fill' style='color: var(--text-color); margin-right: 10px;'></i>Alertas Preventivos</h3>", unsafe_allow_html=True)
        crit = em_and[em_and.status.isin(["Atrasada", "Em risco"])].sort_values("margem_min")
        if crit.empty:
            st.success("Tudo sob controle. Nenhuma OP crítica.")
        for _, x in crit.head(3).iterrows():
            bento_alerta(x.op, x.produto, x.etapa_atual, f"{x.projecao_conclusao:%H:%M}", x.margem_min, critico=(x.status=="Atrasada"))
        if len(crit) > 3:
            with st.expander(f"Ver mais {len(crit) - 3} alertas"):
                for _, x in crit.iloc[3:].iterrows():
                    bento_alerta(x.op, x.produto, x.etapa_atual, f"{x.projecao_conclusao:%H:%M}", x.margem_min, critico=(x.status=="Atrasada"))

    with col_gargalos:
        st.markdown("<h3 style='font-weight: 900; font-size: 20px; margin-bottom: 16px; color: var(--text-color);'><i class='bi bi-search' style='color: var(--text-color); margin-right: 10px;'></i>Análise de Gargalos</h3>", unsafe_allow_html=True)
        
        iniciadas = d1[d1.situacao != "Pendente"].copy()
        iniciadas["gargalo"] = iniciadas.produto + " - " + iniciadas.etapa
        garg = (iniciadas.assign(atraso=iniciadas.atraso_min.clip(lower=0))
                .groupby("gargalo", as_index=False).atraso.mean().sort_values("atraso", ascending=True).tail(5))
        
        fig_garg = px.bar(garg, x="atraso", y="gargalo", orientation="h", title="Etapas de maior atraso (min)")
        fig_garg.update_traces(marker_color="#2563eb")
        fig_garg.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='var(--text-color)', family="Inter"),
            margin=dict(l=0, r=0, t=30, b=0),
            title_font=dict(size=15, family="Inter"),
            xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
            yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig_garg, use_container_width=True, theme="streamlit")

    st.write("")
    with st.expander("Ver Tabela Completa de Ordens de Produção", expanded=False):
        st_sel = st.multiselect("Filtrar por status", list(CORES), default=list(CORES)) or list(CORES)
        tab = r1[r1.status.isin(st_sel)].copy()
        tab["prob_atraso"] = tab.prob_atraso * 100
        tab["status"] = tab.status.map(lambda s: f"{ICONES[s]} {s}")
        tab["progresso"] = tab.etapas_concluidas.astype(str) + "/" + tab.total_etapas.astype(str)
        st.dataframe(
            tab[["op", "produto", "status", "etapa_atual", "progresso", "prazo",
                 "projecao_conclusao", "p90_conclusao", "margem_min", "prob_atraso"]].sort_values("margem_min"),
            hide_index=True, use_container_width=True, height=300,
            column_config={
                "op": "OP", "produto": "Produto", "status": "Status", "etapa_atual": "Etapa atual",
                "progresso": "Etapas", "prazo": st.column_config.DatetimeColumn("Prazo", format="DD/MM HH:mm"),
                "projecao_conclusao": st.column_config.DatetimeColumn("Projeção", format="DD/MM HH:mm"),
                "p90_conclusao": st.column_config.DatetimeColumn("Pessimista (P90)", format="DD/MM HH:mm"),
                "margem_min": st.column_config.NumberColumn("Margem", format="%.0f"),
                "prob_atraso": st.column_config.ProgressColumn("Risco", min_value=0, max_value=100, format="%.0f%%"),
            })

# --------------------------------------------------------- LINHA DO TEMPO
with tab2:
    st.markdown("<h3 style='font-weight: 900; color: var(--text-color); font-size: 20px;'><i class='bi bi-calendar2-check-fill' style='color: var(--text-color); margin-right: 10px;'></i>Auditoria de Ordem: Planejado vs Realizado</h3>", unsafe_allow_html=True)
    op = st.selectbox("Selecione a Ordem de produção:", r.sort_values("margem_min").op)
    g = d[d.op == op].sort_values("ordem_etapa")
    prazo_op = g.prazo.iloc[0]
    
    plan = g.assign(Tipo="Planejado", ini=g.plan_inicio, fim=g.plan_fim)
    real = g[g.situacao != "Pendente"].assign(Tipo="Realizado", ini=lambda x: x.real_inicio, fim=lambda x: x.real_fim.clip(upper=agora))

    fig_gantt = px.timeline(pd.concat([plan, real]), x_start="ini", x_end="fim", y="etapa", color="Tipo",
                            color_discrete_map={"Planejado": "#9ca3af", "Realizado": "#2563eb"}, category_orders={"etapa": list(g.etapa)})
    fig_gantt.update_yaxes(autorange="reversed", title="")
    fig_gantt.update_traces(width=0.6) 
    fig_gantt.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='var(--text-color)', family="Inter"),
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(showgrid=False)
    )
    for x_val, nome, cor in [(agora, "Agora", "#dc2626"), (prazo_op, "Prazo", "#16a34a")]:
        fig_gantt.add_shape(type="line", x0=x_val, x1=x_val, y0=0, y1=1, yref="paper", line=dict(color=cor, dash="dot", width=2))
        fig_gantt.add_annotation(x=x_val, y=1.05, yref="paper", text=nome, showarrow=False, font=dict(color=cor, weight="bold"))
    st.plotly_chart(fig_gantt, use_container_width=True, theme="streamlit")

    st.write("")
    st.markdown("<h3 style='font-weight: 900; color: var(--text-color); font-size: 20px;'><i class='bi bi-dice-5-fill' style='color: var(--text-color); margin-right: 10px;'></i>Simulação de Monte Carlo</h3>", unsafe_allow_html=True)
    
    t0_mc, tot_mc = distribuicao_mc(d, agora, op)
    if tot_mc is None:
        st.info("Esta ordem já foi concluída — não há o que simular.")
    else:
        concl = t0_mc + pd.to_timedelta(tot_mc, unit="m")
        prob = float(np.mean(concl > prazo_op))
        p50 = t0_mc + pd.Timedelta(minutes=float(np.percentile(tot_mc, 50)))
        p90 = t0_mc + pd.Timedelta(minutes=float(np.percentile(tot_mc, 90)))
        
        mc1, mc2, mc3 = st.columns(3)
        with mc1: bento_kpi("Risco de Atraso", f"{prob:.0%}", "Probabilidade")
        with mc2: bento_kpi("Conclusão Estimada", f"{p50:%H:%M}", "Cenário P50")
        with mc3: bento_kpi("Cenário Pessimista", f"{p90:%H:%M}", "Cenário P90")
        
        st.write("")
        h = px.histogram(x=pd.Series(concl), nbins=40)
        h.update_traces(marker_color="#2563eb")
        h.add_shape(type="line", x0=prazo_op, x1=prazo_op, y0=0, y1=1, yref="paper", line=dict(color="#dc2626", dash="dash", width=2))
        h.add_annotation(x=prazo_op, y=1.05, yref="paper", text="Prazo Limite", showarrow=False, font=dict(color="#dc2626", weight="bold"))
        h.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='var(--text-color)', family="Inter"),
            yaxis_title="Simulações", xaxis_title="Horário de Término", showlegend=False, height=300, margin=dict(l=0, r=0, t=30, b=0),
            xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
            yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
        )
        st.plotly_chart(h, use_container_width=True, theme="streamlit")

# ------------------------------------------------------ AGENDAMENTO REVERSO
with tab3:
    st.markdown("<h3 style='font-weight: 900; color: var(--text-color); font-size: 20px;'><i class='bi bi-clock-history' style='color: var(--text-color); margin-right: 10px;'></i>Calculadora de Planejamento Reverso</h3>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    prod = c1.selectbox("Produto", list(ROTEIROS))
    dia = c2.date_input("Data de entrega", datetime(2026, 10, 6).date())
    hora = c3.time_input("Hora de entrega", time(18, 0))
    buf = c4.number_input("Folga (min)", 0, 120, BUFFER_MIN)
    
    prazo = datetime.combine(dia, hora)
    plano = pd.DataFrame(agendamento_reverso(prazo, ROTEIROS[prod], buf))
    inicio_total = plano.plan_inicio.min()
    
    m1, m2, m3 = st.columns([1,1,2])
    with m1: bento_kpi("Início Limite", f"{inicio_total:%H:%M}", f"Dia {inicio_total:%d/%m}")
    with m2: bento_kpi("Duração Total", f"{(prazo - inicio_total).total_seconds() / 3600:.1f} h", "Lead Time")
    
    st.write("")
    f = px.timeline(plano, x_start="plan_inicio", x_end="plan_fim", y="etapa", color="recurso", category_orders={"etapa": list(plano.etapa)})
    f.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='var(--text-color)', family="Inter"),
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(showgrid=False)
    )
    st.plotly_chart(f.update_yaxes(autorange="reversed", title=""), use_container_width=True, theme="streamlit")

# ------------------------------------------------------------ SIMULAR ATRASO
with tab4:
    st.markdown("<h3 style='font-weight: 900; color: var(--text-color); font-size: 20px;'><i class='bi bi-sliders' style='color: var(--text-color); margin-right: 10px;'></i>Cenário 'What-if' (E se...)</h3>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    op_s = c1.selectbox("Ordem", r.op, key="op_sim")
    plano_op = (df[df.op == op_s].sort_values("ordem_etapa"))
    etapa_s = c2.selectbox("Etapa afetada", list(plano_op.etapa))
    atraso = c3.slider("Atraso inserido (min)", 0, 600, 120, 15)
    
    ordem_s = int(plano_op[plano_op.etapa == etapa_s].ordem_etapa.iloc[0])
    novo = reprogramar(plano_op, ordem_s, atraso)
    prazo_s = plano_op.prazo.iloc[0]
    estouro = (novo.novo_fim.iloc[-1] - prazo_s).total_seconds() / 60
    
    if estouro > 0:
        st.error(f"🛑 O atraso propaga em cascata! Conclusão passa para **{novo.novo_fim.iloc[-1]:%H:%M}** ({estouro:.0f} min após o prazo).")
    else:
        st.success("✅ O atraso é absorvido pelas folgas e não compromete o prazo de entrega.")
        
    st.dataframe(novo[["etapa", "recurso", "plan_inicio", "novo_inicio", "plan_fim", "novo_fim"]].round(1), hide_index=True, use_container_width=True, height=500)

# ------------------------------------------------------------------ DADOS
with tab5:
    st.markdown("<h3 style='font-weight: 900; color: var(--text-color); font-size: 20px;'><i class='bi bi-database-fill' style='color: var(--text-color); margin-right: 10px;'></i>Base de Dados</h3>", unsafe_allow_html=True)
    st.dataframe(d, hide_index=True, use_container_width=True, height=500)
    
    st.markdown("""
    <style>
    div[data-testid="stDownloadButton"] button {
        background-color: #2e9e5b !important;
        color: #ffffff !important;
    }
    div[data-testid="stDownloadButton"] button:hover {
        background-color: #257d48 !important;
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.download_button("Baixar dados (CSV)", d.to_csv(index=False).encode("utf-8"), "dados_reversemilk.csv", "text/csv")
