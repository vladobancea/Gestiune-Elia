import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
import urllib.parse

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Pensiune Manager Pro", layout="wide", initial_sidebar_state="collapsed")

# --- STYLING CSS PENTRU LOOK PREMIUM ---
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .calendar-box {
        display: inline-block;
        width: 100%;
        padding: 10px 0;
        text-align: center;
        border-radius: 5px;
        font-weight: bold;
        font-size: 12px;
        color: #fff;
    }
    .status-liber { background-color: #2ECC71; }
    .status-ocupat { background-color: #E74C3C; }
    .status-schimb { background-color: #F1C40F; color: #000; }
    .status-sosire { background-color: #3498DB; }
    .status-plecare { background-color: #9B59B6; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE SETUP ---
conn = sqlite3.connect('pensiune.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS rezervari 
             (id INTEGER PRIMARY KEY, nume TEXT, telefon TEXT, camera TEXT, 
              checkin DATETIME, checkout DATETIME, status TEXT, pret_total REAL, note TEXT)''')
conn.commit()

CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

# --- LOGICĂ ---
def este_disponibila(camera, start, end):
    query = "SELECT * FROM rezervari WHERE camera = ? AND status != 'Anulat' AND NOT (checkout <= ? OR checkin >= ?)"
    c.execute(query, (camera, start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')))
    return len(c.fetchall()) == 0

# --- SIDEBAR NAV ---
st.sidebar.title("🏨 Pensiunea Mea")
menu = ["📅 Harta Disponibilității", "➕ Rezervare Nouă", "👥 Rezervare Grup", "📋 Listă Rezervări"]
choice = st.sidebar.radio("Navigare", menu)

# --- 1. HARTA DISPONIBILITĂȚII (HEATMAP) ---
if choice == "📅 Harta Disponibilității":
    st.title("Harta Disponibilității")
    
    col_date, col_stat = st.columns([1, 2])
    data_start = col_date.date_input("Vezi de la data:", date.today())
    
    # Generăm 14 zile
    zile = [data_start + timedelta(days=i) for i in range(14)]
    
    # Header zile
    header_cols = st.columns([1.5] + [1]*14)
    header_cols[0].write("**Cameră**")
    for i, d in enumerate(zile):
        header_cols[i+1].write(f"**{d.strftime('%d/%m')}**")

    # Date rezervări
    df_rez = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    df_rez['checkin'] = pd.to_datetime(df_rez['checkin']).dt.date
    df_rez['checkout'] = pd.to_datetime(df_rez['checkout']).dt.date

    for cam in CAMERE_INFO.keys():
        row_cols = st.columns([1.5] + [1]*14)
        row_cols[0].markdown(f"**{cam}**")
        
        for i, d in enumerate(zile):
            plecare = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkout'] == d)].empty
            sosire = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin'] == d)].empty
            ocupat = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin'] < d) & (df_rez['checkout'] > d)].empty
            
            if plecare and sosire: label, clasa = "🔄", "status-schimb"
            elif plecare: label, clasa = "📤", "status-plecare"
            elif sosire: label, clasa = "📥", "status-sosire"
            elif ocupat: label, clasa = "🔴", "status-ocupat"
            else: label, clasa = "🟢", "status-liber"
            
            row_cols[i+1].markdown(f'<div class="calendar-box {clasa}">{label}</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption("Legenda: 🟢 Liber | 🔴 Ocupat | 🔄 Schimb (In/Out) | 📥 Sosire | 📤 Plecare")

# --- 2. REZERVARE NOUĂ ---
elif choice in ["➕ Rezervare Nouă", "👥 Rezervare Grup"]:
    st.title(choice)
    is_grup = "Grup" in choice
    
    with st.expander("📝 Formular Rezervare", expanded=True):
        with st.form("my_form"):
            nume = st.text_input("👤 Nume Client")
            telefon = st.text_input("📱 Telefon (ex: 40722123456)")
            cam_sel = "Toate" if is_grup else st.selectbox("🛏️ Camera", list(CAMERE_INFO.keys()))
            
            c1, c2 = st.columns(2)
            d_in = c1.date_input("📥 Data Check-in",
