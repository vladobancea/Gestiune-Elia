import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date, time
import urllib.parse
from fpdf import FPDF

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Manager Elia", layout="wide", initial_sidebar_state="collapsed")

# --- STYLING CSS (FORȚĂM CONTINUITATEA) ---
st.markdown("""
    <style>
    .scroll-container { overflow-x: auto; white-space: nowrap; padding-bottom: 15px; }
    .custom-table { width: 100%; border-collapse: collapse; min-width: 1000px; table-layout: fixed; border: none; }
    .custom-table td { border: none; padding: 0 !important; margin: 0 !important; height: 52px; vertical-align: middle; }
    
    .sticky-col { 
        position: sticky; left: 0; background: #fff; z-index: 10; 
        font-weight: bold; border-right: 2px solid #3498db !important; width: 120px;
        padding: 5px !important; border-top: 1px solid #eee; border-bottom: 1px solid #eee;
    }
    
    .calendar-box { 
        height: 48px; width: 100%; display: flex; align-items: center; justify-content: center; 
        font-size: 14px; font-weight: bold; color: white; margin: 0; padding: 0; line-height: 48px;
    }

    .bg-liber { background: #2ECC71; border: 1px solid #fff; border-radius: 4px; height: 38px; width: 92%; margin: auto; }
    .bg-ocupat { background: #E74C3C; width: 100.5%; }
    .bg-checkin { background: linear-gradient(90deg, #2ECC71 50%, #E74C3C 50%); width: 100.5%; }
    .bg-checkout { background: linear-gradient(90deg, #E74C3C 50%, #2ECC71 50%); width: 100.5%; }
    .bg-schimb { background: linear-gradient(90deg, #E74C3C 48%, #ffffff 50%, #E74C3C 52%); width: 100.5%; }
    
    .info-card { background: white; padding: 20px; border-radius: 12px; border: 2px solid #3498db; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- DB ---
conn = sqlite3.connect('pensiune.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS rezervari (id INTEGER PRIMARY KEY, nume TEXT, telefon TEXT, camera TEXT, checkin DATETIME, checkout DATETIME, status TEXT, pret_total REAL, note TEXT)')
conn.commit()

CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

# --- LOGICĂ ---
def este_disponibila(camera, start, end):
    c.execute("SELECT * FROM rezervari WHERE status != 'Anulat' AND camera = ? AND NOT (checkout <= ? OR checkin >= ?)", (camera, start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')))
    return len(c.fetchall()) == 0

# --- MENIU ---
menu = ["📅 Harta", "📊 Statistici", "➕ Nouă", "👥 Grup", "📋 Listă"]
choice = st.sidebar.radio("Meniu", menu)

if choice == "📅 Harta":
    st.title("Harta Disponibilității")
    d_start = st.date_input("Start:", date.today())
    zile = [d_start + timedelta(days=i) for i in range(14)]
    
    df_rez = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    df_rez['checkin_d'] = pd.to_datetime(df_rez['checkin']).dt.date
    df_rez['checkout_d'] = pd.to_datetime(df_rez['checkout']).dt.date

    html = '<div class="scroll-container"><table class="custom-table"><thead><tr><th class="sticky-col">Cameră</th>'
    for d in zile: html += f'<th>{d.strftime("%d/%m")}</th>'
    html += '</tr></thead><tbody>'

    for cam in CAMERE_INFO.keys():
        html += f'<tr><td class="sticky-col">{cam}</td>'
        for d in zile:
            r_out = df_rez[(df_rez['camera'] == cam) & (df_rez['checkout_d'] == d)]
            r_in = df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] == d)]
            r_stay = df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] < d) & (df_rez['checkout_d'] > d)]
            
            bg, label = "bg-liber", ""
            
            # 1. Prioritate la Schimb (Cineva pleacă, cineva vine)
            if not r_out.empty and not r_in.empty:
                bg = "bg-schimb"
                label = f"{r_out.iloc[0]['id']}|{r_in.iloc[0]['id']}"
            # 2. Check-out
            elif not r_out.empty:
                bg = "bg-checkout"
                # Forțăm ID-ul dacă e rezervare de o noapte sau dacă e mijlocul
                r = r_out.iloc[0]
                if (r['checkout_d'] - r['checkin_d']).days <= 1 or d == (r['checkin_d'] + timedelta(days=(r['checkout_d'] - r['checkin_d']).days // 2)):
                    label = str(r['id'])
            # 3. Check-in
            elif not r_in.empty:
                bg = "bg-checkin"
                r = r_in.iloc[0]
                if (r['checkout_d'] - r['checkin_d']).days <= 1 or d == (r['checkin_d'] + timedelta(days=(r['checkout_d'] - r['checkin_d']).days // 2)):
                    label = str(r['id'])
            # 4. Ocupat Full
            elif not r_stay.empty:
                bg = "bg-ocupat"
                r = r_stay.iloc[0]
                if d == (r['checkin_d'] + timedelta(days=(r['checkout_d'] - r['checkin_d']).days // 2)):
                    label = str(r['id'])

            html += f'<td><div class="calendar-box {bg}">{label}</div></td>'
        html += '</tr>'
    
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

    st.markdown("---")
    id_sel = st.selectbox("🔍 Detalii ID:", ["-"] + sorted([str(i) for i in df_rez['id'].unique()]))
    if id_sel != "-":
        r_det = df_rez[df_rez['id'] == int(id_sel)].iloc[0]
        st.markdown(f'<div class="info-card"><h4>{r_det["nume"]}</h4><p>📅 {r_det["checkin_d"]} -> {r_det["checkout_d"]}</p><p>📱 {r_det["telefon"]} | 💰 {r_det["pret_total"]} RON</p></div>', unsafe_allow_html=True)
        if st.button("🗑️ Șterge Rezervarea"):
            c.execute("DELETE FROM rezervari WHERE id=?", (id_sel,))
            conn.commit()
            st.rerun()

elif choice in ["➕ Nouă", "👥 Grup"]:
    st.title(choice)
    is_g = "Grup" in choice
    with st.form("f"):
        nume = st.text_input("Nume Client"); tel = st.text_input("Telefon")
        cam = "Toate" if is_g else st.selectbox("Cameră", list(CAMERE_INFO.keys()))
        d1 = st.date_input("In", date.today()); d2 = st.date_input("Out", date.today()+timedelta(1))
        pret = st.number_input("Pret", value=float(sum(CAMERE_INFO.values()) if is_g else CAMERE_INFO[cam]))
        if st.form_submit_button("Salvează"):
            # REPARARE FIXĂ: Folosim obiectul time importat separat
            t1, t2 = datetime.combine(d1, time(15, 0)), datetime.combine(d2, time(11, 0))
            cms = list(CAMERE_INFO.keys()) if is_g else [cam]
            if all(este_disponibila(cn, t1, t2) for cn in cms):
                for cn in cms:
                    c.execute("INSERT INTO rezervari (nume, telefon, camera, checkin, checkout, status, pret_total) VALUES (?,?,?,?,?,?,?)", (nume, tel, cn, t1, t2, 'Confirmat', pret/6 if is_g else pret))
                conn.commit(); st.success("Salvat!"); st.rerun()
            else: st.error("Cameră ocupată!")

elif choice == "📋 Listă":
    st.title("Listă Rezervări")
    df_l = pd.read_sql_query("SELECT * FROM rezervari ORDER BY checkin DESC", conn)
    st.dataframe(df_l)

elif choice == "📊 Statistici":
    st.title("📊 Statistici")
    df = pd.read_sql_query("SELECT pret_total FROM rezervari", conn)
    if not df.empty: st.metric("Total", f"{df['pret_total'].sum()} RON")
