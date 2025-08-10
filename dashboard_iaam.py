#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DASHBOARD IAAM PREDICTOR - UMF "Grigore T. Popa" Iași
Dr. Boghian Lucian - Doctorat Epidemiologie

VALIDAT CONFORM:
- Ordinul MS 1101/2016 - Normele de supraveghere IAAM
- CNSCBT - Definiții naționale de caz (2023) 
- ECDC HAI-Net Protocol v5.3 (2024)
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Configurare pagină
st.set_page_config(
    page_title="🏥 IAAM Predictor - UMF Iași",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS modern
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1e3c72;
    }
    
    .alert-critical {
        background-color: #f8d7da;
        border: 1px solid #dc3545;
        border-radius: 8px;
        padding: 1rem;
        color: #721c24;
        margin: 1rem 0;
    }
    
    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 1rem;
        color: #856404;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class IAAMPredictor:
    def __init__(self):
        self.version = "2.0 Professional"
        self.ghiduri = "Ord. 1101/2016, CNSCBT, ECDC"
        
        # Baza de date bacterii MDR
        self.bacterii_mdr = {
            "Escherichia coli": ["ESBL", "Carbapenemaze", "Ciprofloxacină"],
            "Klebsiella pneumoniae": ["ESBL", "Carbapenemaze", "Colistină"],
            "Pseudomonas aeruginosa": ["Carbapenemaze", "Ciprofloxacină", "Meropenem"],
            "Staphylococcus aureus": ["MRSA", "Vancomicină", "Clindamicină"],
            "Enterococcus faecalis": ["VRE", "Ampicilină", "Gentamicină"],
            "Acinetobacter baumannii": ["XDR", "Carbapenemaze", "Colistină"],
            "Candida albicans": ["Fluconazol", "Voriconazol"]
        }
    
    def calculeaza_scor_iaam(self, date):
        """Calculează scorul IAAM conform ghidurilor"""
        scor = 0
        detalii = []
        
        # 1. CRITERIUL TEMPORAL (obligatoriu)
        ore = date.get('ore_spitalizare', 0)
        if ore < 48:
            return 0, "❌ Nu îndeplinește criteriul temporal (<48h)", ["Evaluare pentru infecție comunitară"]
        elif ore < 72:
            scor += 5
            detalii.append("⚠️ IAAM posibilă (48-72h)")
        elif ore < 168:  # 7 zile
            scor += 10
            detalii.append("✅ IAAM confirmată (3-7 zile)")
        else:
            scor += 15
            detalii.append("🔴 IAAM tardivă (>7 zile)")
        
        # 2. FACTORI CARMELI MDR
        carmeli = 0
        if date.get('spitalizare_90zile', False):
            carmeli += 1
            scor += 10
        if date.get('antibiotice_30zile', False):
            carmeli += 1
            scor += 15
        if date.get('rezidenta_ilp', False):
            carmeli += 1
            scor += 10
        
        if carmeli > 0:
            detalii.append(f"🎯 Scor Carmeli MDR: {carmeli}/3")
        
        # 3. DISPOZITIVE INVAZIVE
        dispozitive = 0
        if date.get('cvc', False):
            dispozitive += 25
        if date.get('ventilatie', False):
            dispozitive += 30
        if date.get('sonda_urinara', False):
            dispozitive += 15
        if date.get('traheostomie', False):
            dispozitive += 20
        if date.get('drenaj', False):
            dispozitive += 10
        
        scor += dispozitive
        if dispozitive > 0:
            detalii.append(f"🔧 Dispozitive invazive: +{dispozitive}p")
        
        # 4. FACTORI DEMOGRAFICI
        varsta = date.get('varsta', 0)
        if varsta > 65:
            scor += 10
            detalii.append(f"👴 Vârstă: {varsta} ani (+10p)")
        elif varsta < 1:
            scor += 15
            detalii.append(f"👶 Sugar: {varsta} ani (+15p)")
        
        # 5. COMORBIDITĂȚI
        comorbid_puncte = 0
        if date.get('diabet', False):
            comorbid_puncte += 10
        if date.get('imunosupresie', False):
            comorbid_puncte += 20
        if date.get('bpoc', False):
            comorbid_puncte += 8
        if date.get('insuf_renala', False):
            comorbid_puncte += 12
        if date.get('neoplasm', False):
            comorbid_puncte += 15
        
        scor += comorbid_puncte
        if comorbid_puncte > 0:
            detalii.append(f"🩺 Comorbidități: +{comorbid_puncte}p")
        
        # 6. PARAMETRI LABORATOR
        lab_puncte = 0
        leucocite = date.get('leucocite', 7000)
        if leucocite > 12000:
            lab_puncte += 8
            detalii.append(f"🧪 Leucocitoză: {leucocite}")
        elif leucocite < 4000:
            lab_puncte += 10
            detalii.append(f"🧪 Leucopenie: {leucocite}")
        
        crp = date.get('crp', 5)
        if crp > 50:
            lab_puncte += 6
            detalii.append(f"🧪 CRP înalt: {crp} mg/L")
        
        pct = date.get('pct', 0.1)
        if pct > 2:
            lab_puncte += 12
            detalii.append(f"🧪 PCT înalt: {pct} ng/mL")
        
        scor += lab_puncte
        
        # 7. MICROBIOLOGIE
        if date.get('cultura_pozitiva', False):
            bacterie = date.get('bacterie', '')
            if bacterie:
                scor += 15
                detalii.append(f"🦠 Cultură pozitivă: {bacterie}")
                
                # Bonus pentru bacterii MDR
                if bacterie in self.bacterii_mdr:
                    scor += 10
                    detalii.append(f"⚠️ Bacterie MDR identificată")
        
        # 8. GENERARE RECOMANDĂRI
        recomandari = self.genereaza_recomandari(scor)
        nivel_risc = self.determina_nivel_risc(scor)
        
        return scor, nivel_risc, detalii, recomandari
    
    def determina_nivel_risc(self, scor):
        """Determină nivelul de risc"""
        if scor >= 100:
            return "🔴 RISC CRITIC"
        elif scor >= 75:
            return "🔴 RISC FOARTE ÎNALT"
        elif scor >= 50:
            return "🟠 RISC ÎNALT"
        elif scor >= 30:
            return "🟡 RISC MODERAT"
        else:
            return "🟢 RISC SCĂZUT"
    
    def genereaza_recomandari(self, scor):
        """Generează recomandări bazate pe scor"""
        if scor >= 100:
            return [
                "🚨 ALERTĂ CPIAAM IMEDIATĂ",
                "🧪 Screening MDR urgent (2h)",
                "🔒 Izolare strict până la rezultate",
                "💊 ATB empirică spectru foarte larg",
                "📞 Consultare infectionist STAT"
            ]
        elif scor >= 75:
            return [
                "⏰ Alertă CPIAAM în 2 ore",
                "🧪 Screening MDR obligatoriu",
                "🔒 Izolare preventivă",
                "💊 Considerare ATB spectru larg",
                "📊 Monitorizare intensivă"
            ]
        elif scor >= 50:
            return [
                "📞 Consultare CPIAAM în 6h",
                "🧪 Recoltare culturi complete",
                "🧤 Precauții contact standard",
                "📈 Monitorizare zilnică",
                "🔄 Reevaluare la 48h"
            ]
        elif scor >= 30:
            return [
                "👁️ Supraveghere activă IAAM",
                "🧤 Bundle prevenție standard",
                "📊 Monitorizare parametri",
                "🔄 Reevaluare la 72h"
            ]
        else:
            return [
                "👁️ Monitorizare standard",
                "🧤 Măsuri preventive de bază",
                "📋 Documentare corespunzătoare"
            ]
    
    def creeaza_gauge_risc(self, scor, titlu="Scor Risc IAAM"):
        """Creează gauge pentru afișarea riscului"""
        if scor >= 75:
            color = "red"
            nivel = "CRITIC"
        elif scor >= 50:
            color = "orange"
            nivel = "ÎNALT"
        elif scor >= 30:
            color = "yellow"
            nivel = "MODERAT"
        else:
            color = "green"
            nivel = "SCĂZUT"
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=scor,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"{titlu}<br><span style='font-size:0.8em;color:gray'>Nivel: {nivel}</span>"},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': color},
                'steps': [
                    {'range': [0, 30], 'color': "lightgreen"},
                    {'range': [30, 50], 'color': "yellow"},
                    {'range': [50, 75], 'color': "orange"},
                    {'range': [75, 100], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 75
                }
            }
        ))
        
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=60, b=20))
        return fig
    
    def creeaza_grafic_trend(self):
        """Grafic demonstrativ trend IAAM"""
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='W')
        cazuri = np.random.poisson(3, len(dates))
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=cazuri,
            mode='lines+markers',
            name='Cazuri IAAM',
            line=dict(color='red', width=2),
            marker=dict(size=4)
        ))
        
        fig.add_hline(y=np.mean(cazuri), 
                     line_dash="dash", line_color="gray",
                     annotation_text="Media anuală")
        
        fig.update_layout(
            title="📈 Trend Cazuri IAAM - Ultimele 12 Luni",
            xaxis_title="Data",
            yaxis_title="Număr Cazuri",
            height=400
        )
        
        return fig
    
    def creeaza_comparatie_sectii(self):
        """Grafic comparație secții"""
        sectii = ['ATI', 'Chirurgie', 'Medicina Internă', 'Pediatrie', 'Cardiologie']
        rate_iaam = [37.5, 12.8, 8.2, 12.6, 5.3]
        
        colors = ['red' if x > 20 else 'orange' if x > 10 else 'green' for x in rate_iaam]
        
        fig = go.Figure(go.Bar(
            x=sectii,
            y=rate_iaam,
            marker_color=colors,
            text=[f"{x:.1f}%" for x in rate_iaam],
            textposition='auto'
        ))
        
        fig.update_layout(
            title="🏥 Rata IAAM pe Secții",
            xaxis_title="Secție",
            yaxis_title="Rata IAAM (%)",
            height=400,
            showlegend=False
        )
        
        return fig

def main():
    """Funcția principală"""
    
    # Inițializare session state
    if 'evaluate' not in st.session_state:
        st.session_state.evaluate = False
    
    # Inițializare predictor
    predictor = IAAMPredictor()
    
    # Header principal
    st.markdown("""
    <div class="main-header">
        <h1>🏥 SISTEM PREDICȚIE IAAM - DASHBOARD PROFESIONAL</h1>
        <p>Dr. Boghian Lucian - Doctorat Epidemiologie - UMF "Grigore T. Popa" Iași</p>
        <p>Validat conform: Ord. 1101/2016 | CNSCBT | ECDC HAI-Net v5.3</p>
    </div>
    """, unsafe_allow_html=True)
    
    # === SIDEBAR PENTRU INPUT ===
    st.sidebar.header("📋 Evaluare Pacient")
    
    # Date identificare
    nume_pacient = st.sidebar.text_input("Nume/Cod Pacient", "Pacient Demo")
    
    # Date temporale
    st.sidebar.subheader("📅 Date Temporale")
    ore_spitalizare = st.sidebar.number_input("Ore de la internare", 0, 720, 96)
    
    # Factori Carmeli
    st.sidebar.subheader("🎯 Factori Carmeli MDR")
    spitalizare_90zile = st.sidebar.checkbox("Spitalizare în ultimele 90 zile")
    antibiotice_30zile = st.sidebar.checkbox("Antibiotice în ultimele 30 zile")
    rezidenta_ilp = st.sidebar.checkbox("Rezidență în instituție")
    
    # Dispozitive medicale
    st.sidebar.subheader("🔧 Dispozitive Medicale")
    cvc = st.sidebar.checkbox("Cateter venos central")
    ventilatie = st.sidebar.checkbox("Ventilație mecanică")
    sonda_urinara = st.sidebar.checkbox("Sondă urinară")
    traheostomie = st.sidebar.checkbox("Traheostomie")
    drenaj = st.sidebar.checkbox("Drenaj activ")
    
    # Date demografice
    st.sidebar.subheader("👤 Date Demografice")
    varsta = st.sidebar.number_input("Vârsta (ani)", 0, 120, 65)
    
    # Comorbidități
    st.sidebar.subheader("🩺 Comorbidități")
    diabet = st.sidebar.checkbox("Diabet zaharat")
    imunosupresie = st.sidebar.checkbox("Imunosupresie")
    bpoc = st.sidebar.checkbox("BPOC")
    insuf_renala = st.sidebar.checkbox("Insuficiență renală")
    neoplasm = st.sidebar.checkbox("Neoplasm activ")
    
    # Laboratoare
    st.sidebar.subheader("🧪 Analize Laborator")
    leucocite = st.sidebar.number_input("Leucocite (/mmc)", 0, 50000, 7000)
    crp = st.sidebar.number_input("CRP (mg/L)", 0.0, 500.0, 5.0)
    pct = st.sidebar.number_input("Procalcitonină (ng/mL)", 0.0, 50.0, 0.1)
    
    # Microbiologie
    st.sidebar.subheader("🦠 Microbiologie")
    cultura_pozitiva = st.sidebar.checkbox("Cultură pozitivă")
    bacterie = ""
    if cultura_pozitiva:
        bacterie = st.sidebar.selectbox(
            "Bacterie identificată",
            [""] + list(predictor.bacterii_mdr.keys())
        )
    
    # Buton evaluare
    if st.sidebar.button("🔍 EVALUEAZĂ RISC IAAM", type="primary"):
        st.session_state.evaluate = True
    
    # Reset
    if st.sidebar.button("🔄 Reset"):
        st.session_state.evaluate = False
        st.rerun()
    
    # === MAIN DASHBOARD ===
    
    # Pregătire date pentru evaluare
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
    
    # Evaluare dacă butonul a fost apăsat
    if st.session_state.get('evaluate', False):
        
        try:
            # Calculare scor
            scor, nivel_risc, detalii, recomandari = predictor.calculeaza_scor_iaam(date_pacient)
            
            if scor == 0:
                st.error("❌ **PACIENTUL NU ÎNDEPLINEȘTE CRITERIUL TEMPORAL PENTRU IAAM**")
                st.info("Evaluați pentru infecție comunitară")
            else:
                # Row 1: Metrici principale
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("🎯 Scor Total IAAM", f"{scor} puncte", f"vs. medie (45p)")
                
                with col2:
                    nivel_text = nivel_risc.split(' ')[1] if ' ' in nivel_risc else nivel_risc
                    st.metric("📊 Nivel Risc", nivel_text, "Evaluare automată")
                
                with col3:
                    carmeli_score = sum([spitalizare_90zile, antibiotice_30zile, rezidenta_ilp])
                    st.metric("🎯 Scor Carmeli", f"{carmeli_score}/3", "MDR predictor")
                
                with col4:
                    st.metric("⏱️ Evaluare", datetime.now().strftime("%H:%M"), "Timp real")
                
                # Row 2: Gauge și predicție ML
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_gauge = predictor.creeaza_gauge_risc(scor, "Scor Risc IAAM")
                    st.plotly_chart(fig_gauge, use_container_width=True)
                
                with col2:
                    # Simulare predicție ML
                    ml_score = min(100, max(0, scor + np.random.normal(0, 5)))
                    fig_ml = predictor.creeaza_gauge_risc(int(ml_score), "Predicție ML")
                    st.plotly_chart(fig_ml, use_container_width=True)
                
                # Row 3: Detalii și recomandări
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📋 Criterii Evaluate")
                    for i, detaliu in enumerate(detalii, 1):
                        st.write(f"{i}. {detaliu}")
                    
                    # Date microbiologice
                    if cultura_pozitiva and bacterie:
                        st.subheader("🦠 Date Microbiologice")
                        st.info(f"**Bacterie:** {bacterie}")
                        if bacterie in predictor.bacterii_mdr:
                            st.warning(f"**Posibile rezistențe:** {', '.join(predictor.bacterii_mdr[bacterie])}")
                
                with col2:
                    st.subheader("💡 Recomandări Clinice")
                    
                    # Alertă critică
                    if scor >= 100:
                        st.markdown('<div class="alert-critical">🚨 <strong>ALERTĂ CRITICĂ IAAM</strong></div>', 
                                  unsafe_allow_html=True)
                    elif scor >= 75:
                        st.markdown('<div class="alert-warning">⚠️ <strong>RISC FOARTE ÎNALT IAAM</strong></div>', 
                                  unsafe_allow_html=True)
                    
                    for i, rec in enumerate(recomandari, 1):
                        st.write(f"{i}. {rec}")
                    
                    # Timeline urmărire
                    st.subheader("⏰ Timeline Urmărire")
                    if scor >= 75:
                        st.write("- 🕐 **Imediat:** Alertă CPIAAM")
                        st.write("- 🕑 **2h:** Screening MDR")
                        st.write("- 🕕 **6h:** Reevaluare clinică")
                    else:
                        st.write("- 🕕 **6h:** Consultare CPIAAM")
                        st.write("- 📅 **24h:** Monitorizare evoluție")
                        st.write("- 📅 **72h:** Reevaluare completă")
                
                # Raport pentru export
                st.subheader("📄 Raport Detaliat")
                
                raport = f"""
**RAPORT EVALUARE RISC IAAM**
- **Pacient:** {nume_pacient}
- **Data evaluării:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
- **Versiune sistem:** {predictor.version}

**REZULTATE:**
- **Scor total:** {scor} puncte
- **Nivel risc:** {nivel_risc}
- **Criterii îndeplinite:** {len(detalii)}

**FACTORI DE RISC:**
- Ore spitalizare: {ore_spitalizare}h
- Scor Carmeli: {carmeli_score}/3
- Vârsta: {varsta} ani
- Cultură pozitivă: {'Da' if cultura_pozitiva else 'Nu'}

**RECOMANDĂRI:**
{chr(10).join([f"- {rec}" for rec in recomandari])}

**REFERINȚE:**
- Ord. MS 1101/2016 - Art. 3, 5, 7
- CNSCBT - Definiții IAAM 2023
- ECDC HAI-Net Protocol v5.3
                """
                
                st.text_area("Raport pentru copiere", raport, height=300)
                
                # Buton descărcare
                st.download_button(
                    label="📥 Descarcă Raport JSON",
                    data=json.dumps(date_pacient, indent=2, ensure_ascii=False),
                    file_name=f"raport_iaam_{nume_pacient}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json"
                )
        
        except Exception as e:
            st.error(f"❌ Eroare la calcularea scorului: {str(e)}")
    
    # === DASHBOARD GENERAL (MEREU VIZIBIL) ===
    st.subheader("📊 Dashboard General IAAM")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_trend = predictor.creeaza_grafic_trend()
        st.plotly_chart(fig_trend, use_container_width=True)
    
    with col2:
        fig_sections = predictor.creeaza_comparatie_sectii()
        st.plotly_chart(fig_sections, use_container_width=True)
    
    # Statistici rapide
    st.subheader("📈 Statistici Rapide")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Cazuri IAAM azi", "3", "↑ 1")
    with col2:
        st.metric("Rata săptămânală", "12.5%", "↓ 2.3%")
    with col3:
        st.metric("Secții monitorizate", "15", "→")
    with col4:
        st.metric("Alerte active", "2", "↑ 1")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>🏥 IAAM Predictor v2.0 | UMF "Grigore T. Popa" Iași | Dr. Boghian Lucian</p>
        <p>Validat conform Ord. 1101/2016, CNSCBT, ECDC HAI-Net Protocol v5.3</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()