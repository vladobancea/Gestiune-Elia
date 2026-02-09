import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date, time
import calendar
from fpdf import FPDF

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Pensiunea Elia - Manager", layout="wide", initial_sidebar_state="expanded")

# --- STYLING CSS ---
st.markdown("""
    <style>
    .scroll-container { overflow-x: auto; white-space: nowrap; padding-bottom: 15px; }
    .custom-table { width: 100%; border-collapse: collapse; min-width: 1000px; table-layout: fixed; border: none; }
    .custom-table td { border: none; padding: 0 !important; margin: 0 !important; height: 52px; vertical-align: middle; }
    .sticky-col { position: sticky; left: 0; background: #fff; z-index: 10; font-weight: bold; border-right: 2px solid #3498db !important; width: 120px; padding: 5px !important; }
    .calendar-box { height: 48px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: bold; color: white; margin: 0; padding: 0; }
    .bg-liber { background: #2ECC71; border: 1px solid #fff; border-radius: 4px; height: 38px; width: 92%; margin: auto; }
    .bg-ocupat { background: #E74C3C; width: 100.5%; }
    .bg-checkin { background: linear-gradient(90deg, #2ECC71 50%, #E74C3C 50%); width: 100.5%; }
    .bg-checkout { background: linear-gradient(90deg, #E74C3C 50%, #2ECC71 50%); width: 100.5%; }
    .bg-schimb { background: linear-gradient(90deg, #E74C3C 48%, #ffffff 50%, #E74C3C 52%); width: 100.5%; }
    .info-card { background: white; padding: 20px; border-radius: 12px; border: 2px solid #3498db; margin-top: 10px; }
    /* Buton + in sidebar */
    .stButton>button { width: 100%; border-radius: 20px; }
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

# --- FUNCȚII ---
def este_disponibila(camera, start, end, exclude_id=None):
    query = "SELECT * FROM rezervari WHERE status != 'Anulat' AND camera = ? AND NOT (checkout <= ? OR checkin >= ?)"
    params = [camera, start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')]
    if exclude_id:
        query += " AND id != ?"
        params.append(exclude_id)
    c.execute(query, params)
    return len(c.fetchall()) == 0

def genereaza_pdf(r):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "CONFIRMARE REZERVARE - ELIA", ln=True, align='C'); pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Client: {r['nume']}", ln=True)
    pdf.cell(0, 10, f"Telefon: {r['telefon']}", ln=True)
    pdf.cell(0, 10, f"Camera: {r['camera']}", ln=True)
    pdf.cell(0, 10, f"Check-in: {r['checkin']}", ln=True)
    pdf.cell(0, 10, f"Check-out: {r['checkout']}", ln=True)
    pdf.cell(0, 10, f"Pret: {r['pret_total']} RON", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR & BUTON + ---
st.sidebar.title("🏨 Pensiunea Elia")
if st.sidebar.button("➕ ADĂUGARE REZERVARE", type="primary"):
    st.session_state.show_add_form = True

menu = ["📅 Harta (14 zile)", "🗓️ Calendar Lunar", "📊 Statistici", "📋 Listă Rezervări"]
choice = st.sidebar.selectbox("Navigare", menu)

# --- FORMULAR ADĂUGARE UNIVERSAL (Modal-like) ---
if st.session_state.get('show_add_form', False):
    with st.expander("📝 Rezervare Nouă", expanded=True):
        with st.form("form_universal"):
            col1, col2 = st.columns(2)
            nume = col1.text_input("Nume Client")
            tel = col2.text_input("Telefon (40...)")
            cam_sel = col1.selectbox("Cameră", list(CAMERE_INFO.keys()) + ["Grup (Toate)"])
            d1 = col2.date_input("Check-in", date.today())
            d2 = col2.date_input("Check-out", date.today() + timedelta(days=1))
            pret = col1.number_input("Preț", value=0.0)
            note = st.text_area("Note")
            
            c1, c2 = st.columns(2)
            if c1.form_submit_button("Salvează"):
                t1, t2 = datetime.combine(d1, time(15, 0)), datetime.combine(d2, time(11, 0))
                cms = list(CAMERE_INFO.keys()) if "Grup" in cam_sel else [cam_sel]
                if all(este_disponibila(cn, t1, t2) for cn in cms):
                    for cn in cms:
                        c.execute("INSERT INTO rezervari (nume, telefon, camera, checkin, checkout, status, pret_total, note) VALUES (?,?,?,?,?,?,?,?)", (nume, tel, cn, t1, t2, 'Confirmat', pret/len(cms), note))
                    conn.commit()
                    st.session_state.show_add_form = False
                    st.success("Rezervare adăugată!")
                    st.rerun()
                else: st.error("Conflict de date!")
            if c2.form_submit_button("Anulează"):
                st.session_state.show_add_form = False
                st.rerun()

# --- 1. HARTA (14 ZILE) ---
if choice == "📅 Harta (14 zile)":
    st.title("Harta Disponibilității")
    d_start = st.date_input("Data Start:", date.today())
    zile = [d_start + timedelta(days=i) for i in range(14)]
    
    df_rez = pd.read_sql_query("SELECT * FROM rezervari", conn)
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
            if not r_out.empty and not r_in.empty: bg, label = "bg-schimb", f"{r_out.iloc[0]['id']}|{r_in.iloc[0]['id']}"
            elif not r_out.empty:
                bg = "bg-checkout"
                r = r_out.iloc[0]
                if (r['checkout_d'] - r['checkin_d']).days <= 1 or d == (r['checkin_d'] + timedelta(days=(r['checkout_d']-r['checkin_d']).days//2)): label = str(r['id'])
            elif not r_in.empty:
                bg = "bg-checkin"
                r = r_in.iloc[0]
                if (r['checkout_d'] - r['checkin_d']).days <= 1 or d == (r['checkin_d'] + timedelta(days=(r['checkout_d']-r['checkin_d']).days//2)): label = str(r['id'])
            elif not r_stay.empty:
                bg = "bg-ocupat"
                r = r_stay.iloc[0]
                if d == (r['checkin_d'] + timedelta(days=(r['checkout_d'] - r['checkin_d']).days // 2)): label = str(r['id'])
            html += f'<td><div class="calendar-box {bg}">{label}</div></td>'
        html += '</tr>'
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

    # --- EDITARE REZERVARE ---
    st.markdown("---")
    id_sel = st.selectbox("🔍 Caută/Editează ID:", ["-"] + sorted([str(i) for i in df_rez['id'].unique()]))
    if id_sel != "-":
        r_det = df_rez[df_rez['id'] == int(id_sel)].iloc[0]
        with st.container():
            st.markdown(f'<div class="info-card"><h3>👤 {r_det["nume"]}</h3>', unsafe_allow_html=True)
            col_e1, col_e2 = st.columns(2)
            n_tel = col_e1.text_input("Telefon nou", r_det['telefon'])
            n_pret = col_e2.number_input("Pret nou", value=float(r_det['pret_total']))
            n_note = st.text_area("Note noi", r_det['note'])
            
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("💾 Salvează Modificări"):
                c.execute("UPDATE rezervari SET telefon=?, pret_total=?, note=? WHERE id=?", (n_tel, n_pret, n_note, id_sel))
                conn.commit(); st.success("Modificat!"); st.rerun()
            
            c2.download_button("📄 Descarcă PDF", genereaza_pdf(r_det), f"Rez_{id_sel}.pdf")
            
            wa_link = f"https://api.whatsapp.com/send?phone={r_det['telefon']}&text=Salut {r_det['nume']}, confirmam rezervarea la Elia!"
            c3.markdown(f'<a href="{wa_link}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; padding:8px; border-radius:5px;">📱 WhatsApp</button></a>', unsafe_allow_html=True)
            
            if c4.button("🗑️ Șterge Rezervarea"):
                c.execute("DELETE FROM rezervari WHERE id=?", (id_sel,)); conn.commit(); st.rerun()

# --- 2. CALENDAR LUNAR ---
elif choice == "🗓️ Calendar Lunar":
    st.title("Calendar Lunar")
    col_l1, col_l2 = st.columns(2)
    an = col_l1.selectbox("An", [2024, 2025, 2026], index=1)
    luna = col_l2.selectbox("Luna", list(range(1, 13)), index=datetime.now().month-1)
    
    cal = calendar.monthcalendar(an, luna)
    df_rez = pd.read_sql_query("SELECT * FROM rezervari", conn)
    df_rez['checkin_d'] = pd.to_datetime(df_rez['checkin']).dt.date
    df_rez['checkout_d'] = pd.to_datetime(df_rez['checkout']).dt.date

    # Grid vizual
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0: cols[i].write("")
            else:
                current_date = date(an, luna, day)
                rez_zi = df_rez[(df_rez['checkin_d'] <= current_date) & (df_rez['checkout_d'] >= current_date)]
                num_rez = len(rez_zi['camera'].unique())
                color = "#2ECC71" if num_rez == 0 else "#E74C3C" if num_rez >= 6 else "#F39C12"
                cols[i].markdown(f"""
                    <div style="background:{color}; color:white; padding:10px; border-radius:5px; text-align:center;">
                        <b>{day}</b><br><small>{num_rez} Cam.</small>
                    </div>
                """, unsafe_allow_html=True)

# --- STATISTICI SI LISTA ---
elif choice == "📊 Statistici":
    st.title("Statistici Financiare")
    df = pd.read_sql_query("SELECT pret_total, checkin FROM rezervari", conn)
    if not df.empty:
        st.metric("Total Încasări", f"{df['pret_total'].sum()} RON")
        df['luna'] = pd.to_datetime(df['checkin']).dt.strftime('%B')
        st.bar_chart(df.groupby('luna')['pret_total'].sum())

elif choice == "📋 Listă Rezervări":
    st.title("Toate Rezervările")
    df_l = pd.read_sql_query("SELECT id, nume, camera, checkin, checkout, pret_total FROM rezervari ORDER BY checkin DESC", conn)
    st.dataframe(df_l, use_container_width=True)
