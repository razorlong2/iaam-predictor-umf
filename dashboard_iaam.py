#!/usr/bin/env python3
"""
EpiMind - IAAM Predictor (Enhanced, single-file)
UMF "Grigore T. Popa" Iași — Dr. Boghian Lucian
- Advanced UI, validation, audit/logging, export, reset, robust handling
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from datetime import datetime
from pathlib import Path
import os

# ---------------- Config ----------------
APP_TITLE = "EpiMind — IAAM Predictor (Enhanced)"
APP_ICON = "🏥"
AUDIT_CSV = "epimind_audit.csv"
LOGO_FILE = "1fc80c62-72a4-49d0-a088-f496b5930eac.png"
SIDEBAR_IMG = "4fbe00b9-c580-463a-8538-5ae75595b360.png"

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide", initial_sidebar_state="expanded")

# ---------------- CSS / Theme (Notion Dark enhanced) ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.stApp { background-color: #0f1214 !important; color: #E6EEF8 !important; font-family: 'Inter', sans-serif !important; }
.main .block-container { padding: 1rem 2rem !important; max-width: 1400px; }
.header { border-radius:12px; padding:14px; margin-bottom:12px; background: linear-gradient(135deg,#0b2b3a,#091f30); border:1px solid rgba(255,255,255,0.03); }
.logo-box { width:80px; height:80px; border-radius:12px; display:flex; align-items:center; justify-content:center; font-weight:800; color:#fff; background: linear-gradient(135deg,#2D4A87,#1E3A5F); }
.title { font-size:20px; font-weight:700; color:#EAF2FF; }
.subtitle { color:#9fb0c6; font-size:13px; margin-top:4px; }

.notion-section { background: rgba(20,20,20,0.6); border:1px solid #1f1f1f; border-radius:10px; padding:14px; margin-bottom:12px; }
.section-title { font-size:15px; font-weight:700; color:#EAF2FF; margin-bottom:8px; display:flex; gap:8px; align-items:center; }

.stTextInput > label, .stNumberInput > label, .stSelectbox > label, .stCheckbox > label { color:#9fb0c6 !important; font-weight:600 !important; }
.stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>select, textarea {
    background:#0b0f10 !important; color:#E6EEF8 !important; border:1px solid #232629 !important; border-radius:8px !important; padding:8px 10px !important;
}
.primary-button { background: linear-gradient(135deg,#2383E2,#1a6bb8) !important; color: white !important; padding:12px 16px !important; border-radius:10px !important; font-weight:700 !important; width:100% !important; }

.metric { background: rgba(14,14,14,0.6); border:1px solid #1f1f1f; border-radius:10px; padding:12px; text-align:center; }
.metric-value { color:#2383E2; font-size:26px; font-weight:800; }

.risk-alert { padding:12px; border-radius:10px; margin:8px 0; font-weight:700; }
.risk-critical { background: rgba(220,38,38,0.09); border-left:4px solid #DC2626; color:#fecaca; }
.risk-high { background: rgba(245,101,101,0.06); border-left:4px solid #F56565; color:#ffd6d6; }
.risk-moderate { background: rgba(251,191,36,0.06); border-left:4px solid #FBBF24; color:#fff4d1; }
.risk-low { background: rgba(34,197,94,0.06); border-left:4px solid #22C55E; color:#d7ffe6; }

.data-item { background: rgba(18,18,18,0.5); border:1px solid #1f1f1f; border-radius:8px; padding:8px; margin:6px 0; color:#cfe6ff; }
.small-muted { color:#9fb0c6; font-size:13px; }

#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ---------------- Domain data ----------------
REZISTENTA_PROFILE = {
    "Escherichia coli": ["ESBL", "CRE", "AmpC", "NDM-1"],
    "Klebsiella pneumoniae": ["ESBL", "CRE", "KPC", "NDM", "OXA-48"],
    "Pseudomonas aeruginosa": ["MDR", "XDR", "PDR", "Carbapenemază"],
    "Acinetobacter baumannii": ["OXA-23", "OXA-24", "OXA-58", "MDR", "XDR"],
    "Staphylococcus aureus": ["MRSA", "VISA", "VRSA", "CA-MRSA"],
    "Enterococcus faecalis": ["VRE", "Ampicilină-R", "HLAR"],
    "Enterococcus faecium": ["VRE", "Ampicilină-R", "Linezolid-R"],
    "Clostridioides difficile": ["NAP1/027", "Ribotip 078", "Binar toxin+"],
    "Stenotrophomonas maltophilia": ["SXT-R", "Levofloxacin-R"],
    "Candida auris": ["Fluconazol-R", "Pan-azol-R", "Echinocandin-R"]
}

ICD_CODES = {
    "Bacteriemie": "A41.9",
    "Pneumonie nosocomiala": "J15.9",
    "ITU nosocomiala": "N39.0",
    "Infecție CVC": "T80.2",
    "Infecție plagă operatorie": "T81.4",
    "Clostridium difficile": "A04.7",
    "Sepsis": "A41.9",
    "Șoc septic": "R57.2"
}

COMORBIDITATI = {
    "Cardiovascular": {
        "Insuficiență cardiacă": {"NYHA II": 5, "NYHA III": 10, "NYHA IV": 15},
        "Cardiopatie ischemică": 8,
        "Aritmii": 5,
        "HTA necontrolată": 6
    },
    "Respirator": {
        "BPOC": {"Gold I-II": 5, "Gold III": 10, "Gold IV": 15},
        "Astm bronșic": 5,
        "Fibroză pulmonară": 12,
        "Pneumopatie interstițială": 10
    },
    "Metabolic": {
        "Diabet zaharat": {"Tip 1": 10, "Tip 2 controlat": 5, "Tip 2 necontrolat": 12},
        "Obezitate": {"BMI 30-35": 3, "BMI 35-40": 5, "BMI >40": 8},
        "Sindrom metabolic": 6
    },
    "Renal": {
        "BCR stadiul 3": 8,
        "BCR stadiul 4": 12,
        "BCR stadiul 5": 15,
        "Dializă": 20
    },
    "Oncologic": {
        "Neoplasm activ": 15,
        "Chimioterapie actuală": 20,
        "Radioterapie": 12,
        "Neutropenie": 25
    },
    "Imunologic": {
        "HIV/SIDA": 20,
        "Transplant organ": 18,
        "Imunosupresie medicamentoasă": 15,
        "Splenectomie": 10
    }
}

# ---------------- Calculators (robuste, comentate) ----------------
def calculeaza_sofa(date):
    scor = 0
    pao2_fio2 = date.get('pao2_fio2', 400)
    if pao2_fio2 < 400: scor += 1
    if pao2_fio2 < 300: scor += 1
    if pao2_fio2 < 200: scor += 1
    if pao2_fio2 < 100: scor += 1

    trombocite = date.get('trombocite', 200)
    if trombocite < 150: scor += 1
    if trombocite < 100: scor += 1
    if trombocite < 50: scor += 1
    if trombocite < 20: scor += 1

    bilirubina = date.get('bilirubina', 1.0)
    if bilirubina > 1.2: scor += 1
    if bilirubina > 2.0: scor += 1
    if bilirubina > 6.0: scor += 1
    if bilirubina > 12.0: scor += 1

    if date.get('hipotensiune'): scor += 2
    if date.get('vasopresoare'): scor += 3

    glasgow = date.get('glasgow', 15)
    if glasgow < 15: scor += 1
    if glasgow < 13: scor += 1
    if glasgow < 10: scor += 1
    if glasgow < 6: scor += 1

    creatinina = date.get('creatinina', 1.0)
    if creatinina > 1.2: scor += 1
    if creatinina > 2.0: scor += 1
    if creatinina > 3.5: scor += 1
    if creatinina > 5.0: scor += 1

    return scor

def calculeaza_qsofa(date):
    scor = 0
    if date.get('tas', 120) < 100: scor += 1
    if date.get('fr', 16) >= 22: scor += 1
    if date.get('glasgow', 15) < 15: scor += 1
    return scor

def analiza_sediment_urinar(date):
    interpretare = []
    risc_itu = 0
    leucocite = date.get('leu_urina', 0)
    eritrocite = date.get('eri_urina', 0)
    bacterii = date.get('bact_urina', 0)
    celule_epiteliale = date.get('cel_epit', 0)
    cilindri = date.get('cilindri', False)
    cristale = date.get('cristale', '')
    nitriti = date.get('nitriti', False)
    esteraza = date.get('esteraza', False)

    if leucocite > 5:
        interpretare.append(f"Leucociturie: {leucocite}/câmp")
        risc_itu += 20
    if leucocite > 10:
        interpretare.append("Piurie semnificativă")
        risc_itu += 15
    if bacterii > 2:
        interpretare.append(f"Bacteriurie: {bacterii}+")
        risc_itu += 15
    if nitriti:
        interpretare.append("Nitriti pozitivi - bacterii Gram negative")
        risc_itu += 25
    if esteraza:
        interpretare.append("Esterază leucocitară pozitivă")
        risc_itu += 20
    if eritrocite > 3:
        interpretare.append(f"Hematurie: {eritrocite}/câmp")
        if eritrocite > 50:
            interpretare.append("⚠️ Hematurie macroscopică - investigații suplimentare")
    if cilindri:
        tip_cilindri = date.get('tip_cilindri', '').lower()
        if 'hialin' in tip_cilindri:
            interpretare.append("Cilindri hialini - posibil normal")
        elif 'granular' in tip_cilindri:
            interpretare.append("Cilindri granulari - afectare tubulară")
            risc_itu += 10
        elif 'leucocitari' in tip_cilindri:
            interpretare.append("Cilindri leucocitari - pielonefrită")
            risc_itu += 30
    if cristale:
        interpretare.append(f"Cristale: {cristale}")
        if 'struvit' in cristale.lower():
            interpretare.append("Cristale struvit - bacterii urează pozitive")
            risc_itu += 15
    if celule_epiteliale > 5:
        interpretare.append("Contaminare probabilă - recoltare necorespunzătoare")
        risc_itu -= 10

    return interpretare, max(0, min(100, risc_itu))

def calculeaza_iaam_avansat(date):
    scor = 0
    detalii = []

    ore = date.get('ore_spitalizare', 0)
    if ore < 48:
        return 0, "NU IAAM", [], []

    # temporal
    if 48 <= ore < 72:
        scor += 5; detalii.append(f"Timp spitalizare {ore}h: +5p")
    elif ore < 168:
        scor += 10; detalii.append(f"Timp spitalizare {ore}h: +10p")
    else:
        scor += 15; detalii.append(f"Timp spitalizare {ore}h: +15p")

    # dispozitive
    dispozitive = date.get('dispozitive', {})
    for disp, info in dispozitive.items():
        if info.get('prezent'):
            zile = info.get('zile', 0)
            punctaj_baza = {
                'CVC': 20, 'Ventilație': 25, 'Sondă urinară': 15,
                'Traheostomie': 20, 'Drenaj': 10, 'PEG': 12
            }.get(disp, 5)
            if zile > 7:
                punctaj_baza += 10
            elif zile > 3:
                punctaj_baza += 5
            scor += punctaj_baza
            detalii.append(f"{disp} ({zile} zile): +{punctaj_baza}p")

    # cultura
    if date.get('cultura_pozitiva'):
        bacterie = date.get('bacterie', '')
        profil_rezistenta = date.get('profil_rezistenta', [])
        if bacterie:
            scor += 15; detalii.append(f"Cultură pozitivă - {bacterie}: +15p")
            for rez in profil_rezistenta:
                punctaj_rezistenta = {
                    'ESBL': 15, 'CRE': 25, 'KPC': 30, 'NDM': 35,
                    'MRSA': 20, 'VRE': 25, 'XDR': 30, 'PDR': 40
                }.get(rez, 10)
                scor += punctaj_rezistenta
                detalii.append(f"Profil {rez}: +{punctaj_rezistenta}p")

    # severitate
    sofa = calculeaza_sofa(date)
    if sofa > 0:
        scor += sofa * 3; detalii.append(f"SOFA {sofa}: +{sofa*3}p")
    qsofa = calculeaza_qsofa(date)
    if qsofa >= 2:
        scor += 15; detalii.append(f"qSOFA {qsofa}: +15p")

    # analiza urina
    if date.get('analiza_urina'):
        _, risc_itu = analiza_sediment_urinar(date.get('sediment', {}))
        if risc_itu > 50:
            scor += 10; detalii.append(f"Risc ITU înalt ({risc_itu}%): +10p")

    # comorbiditati
    for categorie, boli in date.get('comorbiditati', {}).items():
        for boala, severitate in boli.items():
            if severitate:
                punctaj = COMORBIDITATI.get(categorie, {}).get(boala, 5)
                if isinstance(punctaj, dict):
                    punctaj = punctaj.get(severitate, 5)
                try:
                    add = int(punctaj)
                except:
                    add = 5
                scor += add
                detalii.append(f"{boala} ({severitate}): +{add}p")

    # nivel
    if scor >= 100: nivel = "CRITIC"
    elif scor >= 75: nivel = "FOARTE ÎNALT"
    elif scor >= 50: nivel = "ÎNALT"
    elif scor >= 30: nivel = "MODERAT"
    else: nivel = "SCĂZUT"

    # recomandari
    if scor >= 100:
        recomandari = [
            "🚨 ALERTĂ CPIAAM IMEDIATĂ",
            "🧪 Screening MDR complet urgent",
            "🔒 Izolare strictă + precauții contact",
            "💊 Antibioterapie empirică largă urgentă",
            "📋 Formular CNAS tip A - urgență"
        ]
    elif scor >= 75:
        recomandari = [
            "⚠️ Consultare infectionist în 2h",
            "🧪 Culturi complete + antibiogramă",
            "🔒 Izolare preventivă",
            "📋 Raportare INSP în 24h"
        ]
    elif scor >= 50:
        recomandari = [
            "👁️ Supraveghere activă IAAM",
            "🧪 Recoltare culturi țintite",
            "📊 Monitorizare parametri la 8h",
            "📋 Completare fișă supraveghere"
        ]
    else:
        recomandari = [
            "📊 Monitorizare standard",
            "🧤 Precauții standard",
            "📋 Documentare în foaia de observație"
        ]

    return scor, nivel, detalii, recomandari

# ---------------- Helpers: session defaults, payload, audit ----------------
def init_defaults():
    defaults = {
        'nume_pacient': 'Pacient_001', 'cnp': '', 'sectie': 'ATI',
        'ore_spitalizare': 96, 'pao2_fio2': 400, 'trombocite': 200,
        'bilirubina': 1.0, 'glasgow': 15, 'creatinina': 1.0,
        'hipotensiune': False, 'vasopresoare': False,
        'tas': 120, 'fr': 18, 'cultura_pozitiva': False,
        'bacterie': '', 'profil_rezistenta': [], 'tip_infectie': list(ICD_CODES.keys())[0],
        'comorbiditati_selectate': {}, 'analiza_urina': False, 'sediment': {}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'home'
    if 'last_result' not in st.session_state:
        st.session_state['last_result'] = None

def collect_payload():
    payload = {
        'nume_pacient': st.session_state.get('nume_pacient', 'Pacient_001'),
        'cnp': st.session_state.get('cnp', ''),
        'sectie': st.session_state.get('sectie', 'ATI'),
        'ore_spitalizare': st.session_state.get('ore_spitalizare', 96),
    }
    devices = ['CVC', 'Ventilație', 'Sondă urinară', 'Traheostomie', 'Drenaj', 'PEG']
    dispozitive = {}
    for d in devices:
        dispozitive[d] = {'prezent': st.session_state.get(f"disp_{d}", False), 'zile': st.session_state.get(f"zile_{d}", 0)}
    payload['dispozitive'] = dispozitive
    payload.update({
        'pao2_fio2': st.session_state.get('pao2_fio2', 400),
        'trombocite': st.session_state.get('trombocite', 200),
        'bilirubina': st.session_state.get('bilirubina', 1.0),
        'glasgow': st.session_state.get('glasgow', 15),
        'creatinina': st.session_state.get('creatinina', 1.0),
        'hipotensiune': st.session_state.get('hipotensiune', False),
        'vasopresoare': st.session_state.get('vasopresoare', False),
        'tas': st.session_state.get('tas', 120),
        'fr': st.session_state.get('fr', 18),
    })
    payload['cultura_pozitiva'] = st.session_state.get('cultura_pozitiva', False)
    payload['bacterie'] = st.session_state.get('bacterie', '')
    payload['profil_rezistenta'] = st.session_state.get('profil_rezistenta', [])
    payload['tip_infectie'] = st.session_state.get('tip_infectie', list(ICD_CODES.keys())[0])
    payload['comorbiditati'] = st.session_state.get('comorbiditati_selectate', {})
    payload['analiza_urina'] = st.session_state.get('analiza_urina', False)
    payload['sediment'] = st.session_state.get('sediment', {})
    return payload

def append_audit(result):
    # result: dict with payload, scor, nivel, details, recomandari, timestamp
    df_row = {
        'timestamp': result['timestamp'],
        'pacient': result['payload'].get('nume_pacient'),
        'sectie': result['payload'].get('sectie'),
        'ore_spitalizare': result['payload'].get('ore_spitalizare'),
        'scor': result['scor'],
        'nivel': result['nivel'],
        'agent': result['payload'].get('bacterie'),
        'rezistente': ','.join(result['payload'].get('profil_rezistenta', []))
    }
    df = pd.DataFrame([df_row])
    if not Path(AUDIT_CSV).exists():
        df.to_csv(AUDIT_CSV, index=False)
    else:
        df.to_csv(AUDIT_CSV, mode='a', header=False, index=False)

def load_audit_df():
    if Path(AUDIT_CSV).exists():
        try:
            return pd.read_csv(AUDIT_CSV)
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# ---------------- UI: Header, Sidebar, Pages ----------------
def render_header():
    st.markdown('<div class="header">', unsafe_allow_html=True)
    cols = st.columns([1, 5])
    with cols[0]:
        if Path(LOGO_FILE).exists():
            st.image(LOGO_FILE, width=80)
        else:
            st.markdown('<div class="logo-box">UMF</div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f'<div class="title">{APP_TITLE}</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">Platformă demonstrativă • IAAM Predictor • UMF "Grigore T. Popa" Iași</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def sidebar_nav():
    st.sidebar.markdown("<div style='padding:6px 8px'><strong style='font-size:14px;color:#EAF2FF;'>Meniu</strong></div>", unsafe_allow_html=True)
    pages = [
        ("🏠 Pagina principală", "home"),
        ("👤 Date pacient", "patient"),
        ("🔧 Dispozitive invazive", "devices"),
        ("📊 Scoruri severitate", "severity"),
        ("🦠 Microbiologie", "microbio"),
        ("🩺 Comorbidități", "comorbid"),
        ("🔬 Analiză urinară", "urine"),
        ("📈 Rezultate & Istoric", "results")
    ]
    labels = [p[0] for p in pages]
    sel = st.sidebar.radio("Selectează", labels, index=0)
    st.session_state['current_page'] = dict(pages)[sel]

    st.sidebar.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    # prominent button
    if st.sidebar.button("📊 Evaluează riscul IAAM", key='compute'):
        # validate minimal required inputs
        missing = []
        if not st.session_state.get('nume_pacient'):
            missing.append("Nume pacient")
        if st.session_state.get('ore_spitalizare', 0) is None:
            missing.append("Ore spitalizare")
        if missing:
            st.sidebar.error("Completați câmpurile: " + ", ".join(missing))
        else:
            payload = collect_payload()
            scor, nivel, detalii, recomandari = calculeaza_iaam_avansat(payload)
            result = {
                'payload': payload,
                'scor': scor,
                'nivel': nivel,
                'detalii': detalii,
                'recomandari': recomandari,
                'timestamp': datetime.now().isoformat()
            }
            st.session_state['last_result'] = result
            # append to audit CSV
            try:
                append_audit(result)
            except Exception as e:
                st.sidebar.warning("Eroare la scriere audit: " + str(e))
            # route to results page
            st.session_state['current_page'] = 'results'
            # show success
            st.sidebar.success(f"Calcul efectuat — Scor: {scor} • Nivel: {nivel}")
    st.sidebar.markdown("<hr style='border-color:#222'/>", unsafe_allow_html=True)
    if Path(SIDEBAR_IMG).exists():
        st.sidebar.image(SIDEBAR_IMG, use_column_width=True)
    st.sidebar.markdown('<div class="small-muted" style="padding-top:6px;">EpiMind • Demo academic • Datele se salvează local (CSV)</div>', unsafe_allow_html=True)
    st.sidebar.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Reset form", key='reset'):
        # clear relevant keys
        keys_to_clear = [k for k in list(st.session_state.keys()) if not k.startswith('last_result') and k not in ('current_page',)]
        for k in keys_to_clear:
            try:
                del st.session_state[k]
            except:
                pass
        st.experimental_rerun()

# ---------------- Page renderers ----------------
def page_home():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏠 Despre EpiMind</div>', unsafe_allow_html=True)
    st.markdown("""
      <div class="small-muted">
      EpiMind este un prototip academic destinat evaluării predictive a riscului de infecții asociate asistenței medicale (IAAM).
      Scop: identificare timpurie pacienți cu risc crescut (screening MDR, izolare, recomandare antibioterapie).
      </div>
    """, unsafe_allow_html=True)
    # quick metrics from audit
    df = load_audit_df()
    cols = st.columns(3)
    with cols[0]:
        st.markdown(f'<div class="metric"><div class="metric-value">{len(df)}</div><div class="small-muted">Evaluări totale (istoric)</div></div>', unsafe_allow_html=True)
    with cols[1]:
        avg = round(df['scor'].mean(), 1) if not df.empty else 0
        st.markdown(f'<div class="metric"><div class="metric-value">{avg}</div><div class="small-muted">Scor mediu</div></div>', unsafe_allow_html=True)
    with cols[2]:
        high = (df['scor'] >= 75).sum() if not df.empty else 0
        st.markdown(f'<div class="metric"><div class="metric-value">{high}</div><div class="small-muted">Evaluări >=75</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_patient():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">👤 Date pacient</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3,2,2])
    with c1:
        st.text_input("Nume / Cod pacient *", key='nume_pacient', placeholder='Pacient_001', help="Obligatoriu pentru raportare")
        st.text_input("CNP (opțional)", key='cnp', help="Dacă este disponibil")
        st.selectbox("Secția", ["ATI", "Chirurgie", "Medicină Internă", "Pediatrie", "Neonatologie"], key='sectie')
    with c2:
        st.number_input("Ore internare *", min_value=0, max_value=10000, value=st.session_state.get('ore_spitalizare', 96), key='ore_spitalizare', help="Criteriu temporal IAAM >= 48h")
        st.selectbox("Tip internare", ["Programat", "Urgent"], key='tip_internare')
    with c3:
        st.date_input("Data evaluării", key='data_evaluare')
        st.text_input("Cod intern (opțional)", key='cod_intern')
    st.markdown('<div class="small-muted">Câmpurile marcate cu * sunt esențiale pentru calcul.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_devices():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔧 Dispozitive invazive</div>', unsafe_allow_html=True)
    devices = ['CVC', 'Ventilație', 'Sondă urinară', 'Traheostomie', 'Drenaj', 'PEG']
    cols = st.columns(3)
    for i, d in enumerate(devices):
        with cols[i % 3]:
            present = st.checkbox(d, key=f"disp_{d}")
            if present:
                st.number_input("Zile (durată)", 0, 365, 3, key=f"zile_{d}")
    st.markdown('<div class="small-muted">Selectați dispozitivele prezente și durata estimată.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_severity():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Scoruri de severitate (SOFA / qSOFA)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("PaO2/FiO2", 50, 500, value=st.session_state.get('pao2_fio2', 400), key='pao2_fio2')
        st.number_input("Trombocite (x10^3/µL)", 0, 1000, value=st.session_state.get('trombocite', 200), key='trombocite')
        st.number_input("Bilirubină (mg/dL)", 0.0, 30.0, value=st.session_state.get('bilirubina', 1.0), key='bilirubina')
    with c2:
        st.number_input("Glasgow", 3, 15, value=st.session_state.get('glasgow', 15), key='glasgow')
        st.number_input("Creatinină (mg/dL)", 0.1, 20.0, value=st.session_state.get('creatinina', 1.0), key='creatinina')
        st.checkbox("Hipotensiune", key='hipotensiune')
        st.checkbox("Vasopresoare", key='vasopresoare')
    # qSOFA
    st.markdown('<div class="small-muted">Note: qSOFA = TAS<100 OR FR≥22 OR Glasgow<15</div>', unsafe_allow_html=True)
    st.number_input("TAS (mmHg)", 40, 220, value=st.session_state.get('tas', 120), key='tas')
    st.number_input("FR (/min)", 8, 60, value=st.session_state.get('fr', 18), key='fr')
    st.markdown('</div>', unsafe_allow_html=True)

def page_microbio():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🦠 Microbiologie</div>', unsafe_allow_html=True)
    cultura = st.checkbox("Cultură pozitivă", key='cultura_pozitiva')
    if cultura:
        st.selectbox("Agent patogen", [""] + list(REZISTENTA_PROFILE.keys()), key='bacterie')
        sel = st.session_state.get('bacterie', '')
        if sel:
            st.multiselect("Profil rezistență", REZISTENTA_PROFILE.get(sel, []), key='profil_rezistenta')
    st.selectbox("Tip infecție (ICD-10)", list(ICD_CODES.keys()), key='tip_infectie')
    st.markdown('<div class="small-muted">Dacă nu există izolat, lăsați "Cultură pozitivă" neclicat.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_comorbid():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🩺 Comorbidități</div>', unsafe_allow_html=True)
    com_select = {}
    cols = st.columns(3)
    cats = list(COMORBIDITATI.keys())
    for i, cat in enumerate(cats):
        with cols[i % 3]:
            with st.expander(cat, expanded=False):
                for cond, val in COMORBIDITATI[cat].items():
                    key = f"com_{cat}_{cond}"
                    if isinstance(val, dict):
                        choice = st.selectbox(cond, ["Nu"] + list(val.keys()), key=key)
                        if choice and choice != "Nu":
                            com_select.setdefault(cat, {})[cond] = choice
                    else:
                        v = st.checkbox(cond, key=key)
                        if v:
                            com_select.setdefault(cat, {})[cond] = True
    st.session_state['comorbiditati_selectate'] = com_select
    st.markdown('<div class="small-muted">Selectați afecțiunile relevante și severitatea când e cazul.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_urina():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔬 Analiză urinară</div>', unsafe_allow_html=True)
    st.checkbox("Analiză urinară disponibilă", key='analiza_urina')
    if st.session_state.get('analiza_urina', False):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.number_input("Leucocite / câmp", 0, 200, value=st.session_state.get('leu_urina', 5), key='leu_urina')
            st.number_input("Eritrocite / câmp", 0, 200, value=st.session_state.get('eri_urina', 1), key='eri_urina')
            st.slider("Bacterii (0-4+)", 0, 4, value=st.session_state.get('bact_urina', 0), key='bact_urina')
        with c2:
            st.number_input("Celule epiteliale", 0, 50, value=st.session_state.get('cel_epit', 2), key='cel_epit')
            st.checkbox("Nitriti +", key='nitriti')
            st.checkbox("Esterază +", key='esteraza')
        with c3:
            st.checkbox("Cilindri", key='cilindri')
            if st.session_state.get('cilindri', False):
                st.text_input("Tip cilindri", key='tip_cilindri')
            st.text_input("Cristale (descriere)", key='cristale')
        st.session_state['sediment'] = {
            'leu_urina': st.session_state.get('leu_urina', 0),
            'eri_urina': st.session_state.get('eri_urina', 0),
            'bact_urina': st.session_state.get('bact_urina', 0),
            'cel_epit': st.session_state.get('cel_epit', 0),
            'nitriti': st.session_state.get('nitriti', False),
            'esteraza': st.session_state.get('esteraza', False),
            'cilindri': st.session_state.get('cilindri', False),
            'tip_cilindri': st.session_state.get('tip_cilindri', ''),
            'cristale': st.session_state.get('cristale', '')
        }
    st.markdown('</div>', unsafe_allow_html=True)

def page_results_and_history():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📈 Rezultate & Istoric</div>', unsafe_allow_html=True)
    last = st.session_state.get('last_result', None)
    if last:
        payload = last['payload']; scor = last['scor']; nivel = last['nivel']; detalii = last['detalii']; recomandari = last['recomandari']
        # metrics headline
        cols = st.columns(4)
        with cols[0]:
            st.markdown(f'<div class="metric"><div class="metric-value">{scor}</div><div class="small-muted">Scor IAAM</div></div>', unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f'<div class="metric"><div style="font-weight:700;font-size:16px;">{nivel}</div><div class="small-muted">Nivel risc</div></div>', unsafe_allow_html=True)
        with cols[2]:
            sofa_val = calculeaza_sofa(payload); st.markdown(f'<div class="metric"><div class="metric-value">{sofa_val}</div><div class="small-muted">SOFA</div></div>', unsafe_allow_html=True)
        with cols[3]:
            qsofa_val = calculeaza_qsofa(payload); st.markdown(f'<div class="metric"><div class="metric-value">{qsofa_val}</div><div class="small-muted">qSOFA</div></div>', unsafe_allow_html=True)

        # banner
        risk_class = {"CRITIC":"risk-critical","FOARTE ÎNALT":"risk-high","ÎNALT":"risk-high","MODERAT":"risk-moderate","SCĂZUT":"risk-low"}.get(nivel, "risk-low")
        st.markdown(f'<div class="risk-alert {risk_class}">🚨 <strong>RISC {nivel}</strong> — Scor: {scor} • {payload.get("nume_pacient")}</div>', unsafe_allow_html=True)

        # tabs
        t1, t2, t3, t4 = st.tabs(["📊 Analiză","💊 Recomandări","🔬 Laborator","📋 Export"])
        with t1:
            st.markdown("**Componente scor**")
            for d in detalii: st.markdown(f"- {d}")
            # gauge
            fig = go.Figure(go.Indicator(mode="gauge+number", value=scor, domain={'x':[0,1],'y':[0,1]},
                                        gauge={'axis':{'range':[0,150]}, 'bar':{'color': "#DC2626" if scor>=75 else "#F59E0B" if scor>=50 else "#10B981"}}))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
            st.plotly_chart(fig, use_container_width=True)
        with t2:
            st.markdown("**Recomandări**")
            for i, r in enumerate(recomandari, 1): st.markdown(f"{i}. {r}")
            # suggested empiric ATB (example)
            agent = payload.get('bacterie', '')
            if agent:
                st.markdown("**Sugestii empirice (exemplu)**")
                atb_map = {"Escherichia coli":["Meropenem 1g IV q8h"], "Klebsiella pneumoniae":["Meropenem 2g perfuzie"], "Pseudomonas aeruginosa":["Ceftazidim/Avibactam 2.5g"]}
                for a in atb_map.get(agent, ["Consultați antibiograma locală"]): st.markdown(f"- {a}")
        with t3:
            st.markdown("**Microbiologie & Urină**")
            if payload.get('cultura_pozitiva'):
                st.markdown(f"- Agent: **{payload.get('bacterie')}**")
                st.markdown(f"- Rezistențe: {', '.join(payload.get('profil_rezistenta', [])) or '—'}")
            else:
                st.markdown("- Fără izolat")
            if payload.get('analiza_urina'):
                interp, risc_itu = analiza_sediment_urinar(payload.get('sediment', {}))
                st.markdown(f"- Probabilitate ITU: **{risc_itu}%**")
                for it in interp: st.markdown(f"  - {it}")
            else:
                st.markdown("- Analiză urinară nedisponibilă")
        with t4:
            raport = {'meta':{'timestamp':last['timestamp']}, 'pacient':payload, 'result':{'scor':scor,'nivel':nivel,'detalii':detalii,'recomandari':recomandari}}
            st.download_button("📥 Descarcă raport JSON", json.dumps(raport, ensure_ascii=False, indent=2), file_name=f"epimind_{payload.get('nume_pacient')}_{datetime.now().strftime('%Y%m%d')}.json", use_container_width=True)
            df = pd.DataFrame([{
                'data': datetime.now().strftime('%Y-%m-%d'),
                'pacient': payload.get('nume_pacient'),
                'sectie': payload.get('sectie'),
                'ore_spitalizare': payload.get('ore_spitalizare'),
                'scor': scor,
                'nivel': nivel
            }])
            st.download_button("📈 Descarcă CSV scurt", df.to_csv(index=False), file_name=f"epimind_stats_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)

    else:
        st.info("Nu există evaluări recente. Completează datele și apasă 'Evaluează riscul IAAM' în sidebar.")

    st.markdown("<hr style='border-color:#222'/>", unsafe_allow_html=True)
    st.markdown("**Istoric audit (fișier local)**")
    df_audit = load_audit_df()
    if not df_audit.empty:
        st.dataframe(df_audit.sort_values('timestamp', ascending=False).head(200), use_container_width=True)
        st.download_button("Descarcă Istoric (.csv)", df_audit.to_csv(index=False), file_name="epimind_audit.csv", use_container_width=True)
        if st.button("Șterge Istoric (local)", key='clear_audit'):
            try:
                os.remove(AUDIT_CSV)
                st.success("Fișier audit șters.")
            except Exception as e:
                st.error("Eroare la ștergere: " + str(e))
    else:
        st.markdown("Nu există date în auditul local.")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Main ----------------
def main():
    init_defaults()
    render_header()
    sidebar_nav()

    page = st.session_state.get('current_page', 'home')
    # route
    if page == 'home': page_home()
    elif page == 'patient': page_patient()
    elif page == 'devices': page_devices()
    elif page == 'severity': page_severity()
    elif page == 'microbio': page_microbio()
    elif page == 'comorbid': page_comorbid()
    elif page == 'urine': page_urina()
    elif page == 'results': page_results_and_history()
    else: st.info("Pagina nu există")

    # footer / help
    with st.expander("ℹ️ Ghid EpiMind (scurt)", expanded=False):
        st.markdown("""
        • Completați secțiunile din meniul lateral; câmpurile esențiale sunt marcate.  
        • Apăsați **📊 Evaluează riscul IAAM** pentru calcul; rezultatul este salvat local (CSV) pentru audit.  
        • Aceasta este o aplicație demonstrativă; nu înlocuiește deciziile clinice.
        """)

if __name__ == "__main__":
    main()
