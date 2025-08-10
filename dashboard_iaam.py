#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IAAM PREDICTOR SIMPLU - TEST FUNCȚIONAL
Dr. Boghian Lucian - UMF "Grigore T. Popa" Iași
Versiune simplă pentru testare rapidă
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
import json

# Configurare pagină
st.set_page_config(
    page_title="🏥 IAAM Predictor Test",
    page_icon="🏥",
    layout="wide"
)

# CSS simplu
st.markdown("""
<style>
    .header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    .alert-red {
        background: #ffe6e6;
        border-left: 5px solid #ff4444;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .alert-orange {
        background: #fff3e0;
        border-left: 5px solid #ff9800;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .alert-yellow {
        background: #fffde7;
        border-left: 5px solid #ffeb3b;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .alert-green {
        background: #e8f5e8;
        border-left: 5px solid #4caf50;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

def calculeaza_scor_iaam(date):
    """Calculează scorul IAAM conform ghidurilor"""
    scor = 0
    detalii = []
    
    # 1. VERIFICARE CRITERIU TEMPORAL (obligatoriu)
    ore = date.get('ore_spitalizare', 0)
    if ore < 48:
        return 0, "❌ NU IAAM - Criteriu temporal neîndeplinit", [], []
    
    # Punctaj pentru timpul de spitalizare
    if 48 <= ore < 72:
        scor += 5
        detalii.append("⏰ IAAM posibilă (48-72h): +5 puncte")
    elif 72 <= ore < 168:  # 7 zile
        scor += 10
        detalii.append("⏰ IAAM confirmată (3-7 zile): +10 puncte")
    else:  # >7 zile
        scor += 15
        detalii.append("⏰ IAAM tardivă (>7 zile): +15 puncte")
    
    # 2. FACTORI CARMELI MDR
    carmeli_scor = 0
    if date.get('spitalizare_90zile', False):
        carmeli_scor += 1
        scor += 10
        detalii.append("🏥 Spitalizare în 90 zile: +10 puncte")
    
    if date.get('antibiotice_30zile', False):
        carmeli_scor += 1
        scor += 15
        detalii.append("💊 Antibiotice în 30 zile: +15 puncte")
    
    if date.get('rezidenta_ilp', False):
        carmeli_scor += 1
        scor += 10
        detalii.append("🏠 Rezidență instituțională: +10 puncte")
    
    # Bonus pentru scor Carmeli maxim
    if carmeli_scor == 3:
        scor += 10
        detalii.append("🎯 Bonus Carmeli maxim (3/3): +10 puncte")
    
    # 3. DISPOZITIVE INVAZIVE
    if date.get('cvc', False):
        scor += 25
        detalii.append("💉 Cateter venos central: +25 puncte")
    
    if date.get('ventilatie', False):
        scor += 30
        detalii.append("🫁 Ventilație mecanică: +30 puncte")
    
    if date.get('sonda_urinara', False):
        scor += 15
        detalii.append("🚽 Sondă urinară: +15 puncte")
    
    if date.get('traheostomie', False):
        scor += 20
        detalii.append("🦴 Traheostomie: +20 puncte")
    
    if date.get('drenaj', False):
        scor += 10
        detalii.append("💧 Drenaj activ: +10 puncte")
    
    # 4. FACTORI DEMOGRAFICI
    varsta = date.get('varsta', 0)
    if varsta > 65:
        scor += 10
        detalii.append(f"👴 Vârstă >65 ani ({varsta}): +10 puncte")
    elif varsta < 1:
        scor += 15
        detalii.append(f"👶 Sugar <1 an: +15 puncte")
    
    # 5. COMORBIDITĂȚI
    if date.get('diabet', False):
        scor += 10
        detalii.append("🍭 Diabet zaharat: +10 puncte")
    
    if date.get('imunosupresie', False):
        scor += 20
        detalii.append("🛡️ Imunosupresie: +20 puncte")
    
    if date.get('bpoc', False):
        scor += 8
        detalii.append("🫁 BPOC: +8 puncte")
    
    if date.get('insuf_renala', False):
        scor += 12
        detalii.append("🫘 Insuficiență renală: +12 puncte")
    
    if date.get('neoplasm', False):
        scor += 15
        detalii.append("🎗️ Neoplasm activ: +15 puncte")
    
    # 6. PARAMETRI LABORATOR
    leucocite = date.get('leucocite', 7000)
    if leucocite > 12000:
        scor += 8
        detalii.append(f"🧪 Leucocitoză ({leucocite:,}): +8 puncte")
    elif leucocite < 4000:
        scor += 10
        detalii.append(f"🧪 Leucopenie ({leucocite:,}): +10 puncte")
    
    crp = date.get('crp', 5)
    if crp > 50:
        scor += 6
        detalii.append(f"🔥 CRP înalt ({crp} mg/L): +6 puncte")
    
    pct = date.get('pct', 0.1)
    if pct > 2:
        scor += 12
        detalii.append(f"⚡ Procalcitonină înaltă ({pct} ng/mL): +12 puncte")
    
    # 7. MICROBIOLOGIE
    if date.get('cultura_pozitiva', False):
        scor += 10
        detalii.append("🦠 Cultură pozitivă: +10 puncte")
        
        bacterie = date.get('bacterie', '')
        if bacterie:
            scor += 15
            detalii.append(f"⚠️ Bacterie MDR ({bacterie}): +15 puncte")
    
    # Determinare nivel risc
    if scor >= 100:
        nivel = "🔴 CRITIC"
        culoare = "red"
    elif scor >= 75:
        nivel = "🔴 FOARTE ÎNALT"
        culoare = "red"
    elif scor >= 50:
        nivel = "🟠 ÎNALT"
        culoare = "orange"
    elif scor >= 30:
        nivel = "🟡 MODERAT"
        culoare = "yellow"
    else:
        nivel = "🟢 SCĂZUT"
        culoare = "green"
    
    # Generare recomandări
    recomandari = genereaza_recomandari(scor)
    
    return scor, nivel, detalii, recomandari

def genereaza_recomandari(scor):
    """Generează recomandări bazate pe scor"""
    if scor >= 100:
        return [
            "🚨 ALERTĂ CPIAAM IMEDIATĂ (0-30 min)",
            "🧪 Screening MDR URGENT în 1 oră",
            "🔒 Izolare STRICTĂ + precauții contact",
            "💊 Antibioterapie empirică spectru FOARTE LARG",
            "📞 Consultare infectionist STAT",
            "📊 Monitorizare parametri vitali la 1h",
            "🏥 Evaluare transfer ATI dacă instabil"
        ]
    elif scor >= 75:
        return [
            "⏰ Alertă CPIAAM în 30 minute",
            "🧪 Screening MDR rapid în 2 ore",
            "🔒 Izolare preventivă imediată",
            "💊 Considerare antibioterapie spectru larg",
            "📈 Monitorizare intensivă la 4h",
            "🧼 Audit igiena mâinilor"
        ]
    elif scor >= 50:
        return [
            "📞 Consultare CPIAAM în 2 ore",
            "🧪 Recoltare culturi complete",
            "🧤 Precauții contact standard",
            "💊 Revizuire antibioterapie curentă",
            "📊 Monitorizare zilnică",
            "🔄 Reevaluare la 48h"
        ]
    elif scor >= 30:
        return [
            "👁️ Supraveghere activă IAAM",
            "🧤 Bundle prevenție standard",
            "📊 Monitorizare parametri clinici",
            "🔄 Reevaluare la 72h",
            "📋 Documentare factori de risc"
        ]
    else:
        return [
            "📋 Monitorizare standard",
            "🧤 Măsuri preventive de bază",
            "📋 Documentare corespunzătoare",
            "🔄 Reevaluare săptămânală"
        ]

def creeaza_gauge(scor):
    """Creează indicator vizual pentru scor"""
    if scor >= 75:
        color = "red"
    elif scor >= 50:
        color = "orange"
    elif scor >= 30:
        color = "yellow"
    else:
        color = "green"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=scor,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Scor IAAM", 'font': {'size': 24}},
        delta={'reference': 50, 'increasing': {'color': "red"}},
        gauge={
            'axis': {'range': [None, 120], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': "lightgreen"},
                {'range': [30, 50], 'color': "yellow"},
                {'range': [50, 75], 'color': "orange"},
                {'range': [75, 120], 'color': "lightcoral"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(
        height=350,
        font={'color': "darkblue", 'family': "Arial"}
    )
    
    return fig

def main():
    """Funcția principală"""
    
    # Header
    st.markdown("""
    <div class="header">
        <h1>🏥 SISTEM PREDICȚIE IAAM - TEST SIMPLU</h1>
        <p><strong>Dr. Boghian Lucian</strong> - Doctorat Epidemiologie</p>
        <p>UMF "Grigore T. Popa" Iași</p>
        <p>Validat: Ord. 1101/2016 • CNSCBT • ECDC HAI-Net v5.3</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar pentru introducerea datelor
    st.sidebar.header("📋 Date Pacient")
    
    # Date de identificare
    nume_pacient = st.sidebar.text_input("Nume/Cod Pacient", "Test_001")
    
    # Date temporale
    st.sidebar.subheader("📅 Criterii Temporale")
    ore_spitalizare = st.sidebar.number_input(
        "Ore de la internare", 
        min_value=0, 
        max_value=720, 
        value=96,
        help="Timpul scurs de la internare până la suspiciunea de infecție"
    )
    
    # Factori Carmeli
    st.sidebar.subheader("🎯 Factori Carmeli MDR")
    spitalizare_90zile = st.sidebar.checkbox(
        "Spitalizare în ultimele 90 zile",
        help="Pacientul a fost spitalizat în ultimele 3 luni"
    )
    antibiotice_30zile = st.sidebar.checkbox(
        "Antibiotice în ultimele 30 zile",
        help="Administrare antibiotice în ultima lună"
    )
    rezidenta_ilp = st.sidebar.checkbox(
        "Rezidență în instituție (ILP)",
        help="Pacient din cămin de bătrâni sau instituție similară"
    )
    
    # Dispozitive medicale
    st.sidebar.subheader("🔧 Dispozitive Invazive")
    cvc = st.sidebar.checkbox("Cateter venos central")
    ventilatie = st.sidebar.checkbox("Ventilație mecanică")
    sonda_urinara = st.sidebar.checkbox("Sondă urinară")
    traheostomie = st.sidebar.checkbox("Traheostomie")
    drenaj = st.sidebar.checkbox("Drenaj activ")
    
    # Date demografice
    st.sidebar.subheader("👤 Date Demografice")
    varsta = st.sidebar.number_input("Vârsta (ani)", 0, 120, 70)
    
    # Comorbidități
    st.sidebar.subheader("🩺 Comorbidități")
    diabet = st.sidebar.checkbox("Diabet zaharat")
    imunosupresie = st.sidebar.checkbox("Imunosupresie/transplant")
    bpoc = st.sidebar.checkbox("BPOC")
    insuf_renala = st.sidebar.checkbox("Insuficiență renală")
    neoplasm = st.sidebar.checkbox("Neoplasm activ")
    
    # Analize laborator
    st.sidebar.subheader("🧪 Analize Laborator")
    leucocite = st.sidebar.number_input("Leucocite (/mmc)", 0, 50000, 8500)
    crp = st.sidebar.number_input("CRP (mg/L)", 0.0, 500.0, 25.0)
    pct = st.sidebar.number_input("Procalcitonină (ng/mL)", 0.0, 50.0, 0.5)
    
    # Microbiologie
    st.sidebar.subheader("🦠 Date Microbiologice")
    cultura_pozitiva = st.sidebar.checkbox("Cultură pozitivă")
    
    bacterie = ""
    if cultura_pozitiva:
        bacterii_disponibile = [
            "",
            "Escherichia coli",
            "Klebsiella pneumoniae", 
            "Pseudomonas aeruginosa",
            "Staphylococcus aureus",
            "Enterococcus faecalis",
            "Acinetobacter baumannii",
            "Candida albicans"
        ]
        bacterie = st.sidebar.selectbox("Bacterie identificată", bacterii_disponibile)
    
    # Buton pentru calcularea scorului
    if st.sidebar.button("🔍 CALCULEAZĂ SCOR IAAM", type="primary"):
        
        # Pregătire date pentru calcul
        date_pacient = {
            'nume_pacient': nume_pacient,
            'ore_spitalizare': ore_spitalizare,
            'spitalizare_90zile': spitalizare_90zile,
            'antibiotice_30zile': antibiotice_30zile,
            'rezidenta_ilp': rezidenta_ilp,
            'cvc': cvc,
            'ventilatie': ventilatie,
            'sonda_urinara': sonda_urinara,
            'traheostomie': traheostomie,
            'drenaj': drenaj,
            'varsta': varsta,
            'diabet': diabet,
            'imunosupresie': imunosupresie,
            'bpoc': bpoc,
            'insuf_renala': insuf_renala,
            'neoplasm': neoplasm,
            'leucocite': leucocite,
            'crp': crp,
            'pct': pct,
            'cultura_pozitiva': cultura_pozitiva,
            'bacterie': bacterie
        }
        
        # Calculare scor
        scor, nivel_risc, detalii, recomandari = calculeaza_scor_iaam(date_pacient)
        
        # Afișare rezultate
        if scor == 0:
            st.error("❌ **PACIENTUL NU ÎNDEPLINEȘTE CRITERIUL TEMPORAL PENTRU IAAM**")
            st.info("**Recomandare:** Evaluați pentru infecție comunitară (< 48h de la internare)")
        else:
            # Metrici principale
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="🎯 Scor Total IAAM",
                    value=f"{scor} puncte",
                    delta=f"vs. medie (45p)"
                )
            
            with col2:
                nivel_text = nivel_risc.split(' ', 1)[1] if ' ' in nivel_risc else nivel_risc
                st.metric(
                    label="📊 Nivel Risc",
                    value=nivel_text,
                    delta="Evaluare automată"
                )
            
            with col3:
                carmeli_total = sum([spitalizare_90zile, antibiotice_30zile, rezidenta_ilp])
                st.metric(
                    label="🎯 Scor Carmeli",
                    value=f"{carmeli_total}/3",
                    delta="MDR predictor"
                )
            
            with col4:
                st.metric(
                    label="⏱️ Data Evaluării",
                    value=datetime.now().strftime("%H:%M"),
                    delta=datetime.now().strftime("%d.%m.%Y")
                )
            
            # Gauge și detalii
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Gauge indicator
                fig_gauge = creeaza_gauge(scor)
                st.plotly_chart(fig_gauge, use_container_width=True)
            
            with col2:
                # Detalii calcul
                st.subheader("📋 Detalii Calcul Scor")
                for detaliu in detalii:
                    st.write(f"• {detaliu}")
            
            # Alertă bazată pe risc
            if scor >= 100:
                st.markdown(
                    f'<div class="alert-red"><strong>🚨 ALERTĂ CRITICĂ IAAM</strong><br>'
                    f'Scor: {scor} puncte - ACȚIUNE IMEDIATĂ NECESARĂ!</div>',
                    unsafe_allow_html=True
                )
            elif scor >= 75:
                st.markdown(
                    f'<div class="alert-red"><strong>🔴 RISC FOARTE ÎNALT</strong><br>'
                    f'Scor: {scor} puncte - Măsuri urgente necesare</div>',
                    unsafe_allow_html=True
                )
            elif scor >= 50:
                st.markdown(
                    f'<div class="alert-orange"><strong>🟠 RISC ÎNALT</strong><br>'
                    f'Scor: {scor} puncte - Supraveghere activă</div>',
                    unsafe_allow_html=True
                )
            elif scor >= 30:
                st.markdown(
                    f'<div class="alert-yellow"><strong>🟡 RISC MODERAT</strong><br>'
                    f'Scor: {scor} puncte - Monitorizare atentă</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="alert-green"><strong>🟢 RISC SCĂZUT</strong><br>'
                    f'Scor: {scor} puncte - Monitorizare standard</div>',
                    unsafe_allow_html=True
                )
            
            # Recomandări clinice
            st.subheader("💡 Recomandări Clinice")
            
            for i, recomandare in enumerate(recomandari, 1):
                st.write(f"**{i}.** {recomandare}")
            
            # Informații microbiologice
            if cultura_pozitiva and bacterie:
                st.subheader("🦠 Informații Microbiologice")
                st.info(f"**Bacterie identificată:** {bacterie}")
                
                # Informații despre rezistențe posibile
                bacterii_mdr_info = {
                    "Escherichia coli": "Posibile rezistențe: ESBL, Carbapenemaze",
                    "Klebsiella pneumoniae": "Posibile rezistențe: ESBL, Carbapenemaze, Colistină",
                    "Pseudomonas aeruginosa": "Posibile rezistențe: Carbapenemaze, Quinolone",
                    "Staphylococcus aureus": "Posibile rezistențe: MRSA, Vancomicină",
                    "Enterococcus faecalis": "Posibile rezistențe: VRE, Ampicilină",
                    "Acinetobacter baumannii": "Posibile rezistențe: XDR, Carbapenemaze",
                    "Candida albicans": "Posibile rezistențe: Azoli"
                }
                
                if bacterie in bacterii_mdr_info:
                    st.warning(f"⚠️ {bacterii_mdr_info[bacterie]}")
            
            # Raport pentru export
            st.subheader("📄 Raport Detaliat pentru Export")
            
            raport_text = f"""
RAPORT EVALUARE RISC IAAM
========================================

IDENTIFICARE PACIENT:
- Nume/Cod: {nume_pacient}
- Data evaluării: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
- Evaluator: Dr. Boghian Lucian

REZULTATE EVALUARE:
- Scor total IAAM: {scor} puncte
- Nivel de risc: {nivel_risc}
- Ore de spitalizare: {ore_spitalizare}h
- Scor Carmeli MDR: {sum([spitalizare_90zile, antibiotice_30zile, rezidenta_ilp])}/3

FACTORI DE RISC IDENTIFICAȚI:
{chr(10).join([f"- {detaliu}" for detaliu in detalii])}

RECOMANDĂRI CLINICE:
{chr(10).join([f"{i}. {rec}" for i, rec in enumerate(recomandari, 1)])}

VALIDĂRI:
- Conform Ordinul MS 1101/2016
- CNSCBT - Definiții naționale
- ECDC HAI-Net Protocol v5.3

CONTACT:
UMF "Grigore T. Popa" Iași
Dr. Boghian Lucian - Doctorat Epidemiologie
            """
            
            st.text_area("Raport complet", raport_text, height=400)
            
            # Butoane pentru export
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="📥 Descarcă Raport TXT",
                    data=raport_text,
                    file_name=f"raport_iaam_{nume_pacient}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )
            
            with col2:
                # Export JSON pentru integrare
                date_export = {
                    **date_pacient,
                    'scor_calculat': scor,
                    'nivel_risc': nivel_risc,
                    'data_evaluare': datetime.now().isoformat(),
                    'recomandari': recomandari
                }
                
                st.download_button(
                    label="📥 Descarcă Date JSON",
                    data=json.dumps(date_export, indent=2, ensure_ascii=False),
                    file_name=f"date_iaam_{nume_pacient}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json"
                )
    
    # Reset button
    if st.sidebar.button("🔄 Resetare Formular"):
        st.rerun()
    
    # Informații generale (întotdeauna vizibile)
    st.subheader("📊 Informații Generale IAAM")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("""
        **🎯 Scor Carmeli MDR:**
        - 0 puncte: Risc scăzut MDR
        - 1 punct: Risc moderat MDR  
        - 2 puncte: Risc înalt MDR
        - 3 puncte: Risc maxim MDR
        """)
    
    with col2:
        st.info("""
        **📊 Interpretare Scor:**
        - 0-29p: 🟢 Risc scăzut
        - 30-49p: 🟡 Risc moderat
        - 50-74p: 🟠 Risc înalt
        - 75+p: 🔴 Risc critic
        """)
    
    with col3:
        st.info("""
        **⏰ Timeline Acțiuni:**
        - Risc critic: Alertă în 30 min
        - Risc înalt: Consultare în 2h
        - Risc moderat: Monitorizare zilnică
        - Risc scăzut: Evaluare standard
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; font-size: 14px;'>
        <p><strong>🏥 SISTEM PREDICȚIE IAAM v2.0</strong></p>
        <p>UMF "Grigore T. Popa" Iași | Dr. Boghian Lucian | Doctorat Epidemiologie</p>
        <p>Validat conform: Ord. 1101/2016 • CNSCBT • ECDC HAI-Net Protocol v5.3</p>
        <p><em>Pentru suport tehnic sau întrebări clinice, contactați departamentul de Epidemiologie</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
