import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
import urllib.parse

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Pensiune Manager Pro", layout="wide")

# --- STYLING CSS PENTRU CELULE ÎMPĂRȚITE ---
st.markdown("""
    <style>
    .calendar-box {
        height: 40px;
        width: 100%;
        border-radius: 4px;
        border: 1px solid #ddd;
    }
    /* Celulă complet Liberă (Verde) */
    .bg-liber { background: #2ECC71; }
    
    /* Celulă complet Ocupată (Roșu) */
    .bg-ocupat { background: #E74C3C; }
    
    /* Check-out (Stânga Roșu - pleacă clientul, Dreapta Verde - liber pentru curățenie/venire) */
    .bg-checkout { background: linear-gradient(90deg, #E74C3C 50%, #2ECC71 50%); }
    
    /* Check-in (Stânga Verde - liber înainte, Dreapta Roșu - vine clientul) */
    .bg-checkin { background: linear-gradient(90deg, #2ECC71 50%, #E74C3C 50%); }
    
    /* Schimb în aceeași zi (Roșu complet, dar vizualizat ca două rezervări care se ating) */
    .bg-schimb { background: linear-gradient(90deg, #E74C3C 48%, #ffffff 50%, #E74C3C 52%); }
    
    .cam-name { font-weight: bold; padding-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE SETUP ---
conn = sqlite3.connect('pensiune.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS rezervari 
             (id INTEGER PRIMARY KEY, nume TEXT, telefon TEXT, camera TEXT, 
              checkin DATETIME, checkout DATETIME, status TEXT, pret_total REAL, note TEXT)''')
conn.commit()

# Asigurare coloană 'note'
try:
    c.execute("ALTER TABLE rezervari ADD COLUMN note TEXT")
    conn.commit()
except:
    pass

CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

# --- LOGICĂ ---
def este_disponibila(camera, start, end):
    query = "SELECT * FROM rezervari WHERE camera = ? AND status != 'Anulat' AND NOT (checkout <= ? OR checkin >= ?)"
    c.execute(query, (camera, start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')))
    return len(c.fetchall()) == 0

# --- NAVIGARE ---
menu = ["📅 Harta Disponibilității", "➕ Rezervare Nouă", "👥 Rezervare Grup", "📋 Listă Rezervări"]
choice = st.sidebar.radio("Navigare", menu)

if choice == "📅 Harta Disponibilității":
    st.title("Harta Disponibilității")
    data_start = st.date_input("Vezi de la data:", date.today())
    zile = [data_start + timedelta(days=i) for i in range(14)]
    
    # Header Zile
    cols = st.columns([1.5] + [1]*14)
    cols[0].write("**Cameră**")
    for i, d in enumerate(zile):
        cols[i+1].write(f"**{d.strftime('%d/%m')}**")

    # Date rezervări
    df_rez = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    df_rez['checkin_d'] = pd.to_datetime(df_rez['checkin']).dt.date
    df_rez['checkout_d'] = pd.to_datetime(df_rez['checkout']).dt.date

    for cam in CAMERE_INFO.keys():
        row = st.columns([1.5] + [1]*14)
        row[0].markdown(f"<div class='cam-name'>{cam}</div>", unsafe_allow_html=True)
        
        for i, d in enumerate(zile):
            plecare = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkout_d'] == d)].empty
            sosire = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] == d)].empty
            ocupat = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] < d) & (df_rez['checkout_d'] > d)].empty
            
            # Aplicare stil în funcție de starea zilei
            clasa = "bg-liber"
            if plecare and sosire: clasa = "bg-schimb"
            elif plecare: clasa = "bg-checkout"
            elif sosire: clasa = "bg-checkin"
            elif ocupat: clasa = "bg-ocupat"
            
            row[i+1].markdown(f'<div class="calendar-box {clasa}"></div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:20px; font-size: 14px;">
        <b>Legendă:</b> 
        <span style="color:#2ECC71">■</span> Liber | 
        <span style="color:#E74C3C">■</span> Ocupat | 
        <span style="background:linear-gradient(90deg, #E74C3C 50%, #2ECC71 50%); padding: 0 5px; border:1px solid #ddd;">&nbsp;</span> Check-out (eliberare 11:00) | 
        <span style="background:linear-gradient(90deg, #2ECC71 50%, #E74C3C 50%); padding: 0 5px; border:1px solid #ddd;">&nbsp;</span> Check-in (ocupare 15:00)
    </div>
    """, unsafe_allow_html=True)

# (Păstrează restul funcțiilor pentru Rezervare Nouă și Listă din versiunea anterioară)
# --- SECȚIUNE REZERVARE (Identică cu ultima variantă, dar asigură-te că include orele 15:00/11:00) ---
elif choice in ["➕ Rezervare Nouă", "👥 Rezervare Grup"]:
    st.title(choice)
    is_grup = "Grup" in choice
    with st.form("form_add"):
        nume = st.text_input("Nume Client")
        telefon = st.text_input("Telefon")
        cam_sel = "Toate" if is_grup else st.selectbox("Cameră", list(CAMERE_INFO.keys()))
        c1, c2 = st.columns(2)
        d_in = c1.date_input("Check-in", date.today())
        d_out = c2.date_input("Check-out", date.today() + timedelta(days=1))
        pret_final = st.number_input("Preț Total", value=float(CAMERE_INFO[cam_sel] if not is_grup else sum(CAMERE_INFO.values())))
        status = st.selectbox("Status", ["Confirmat", "În așteptare", "Anulat"])
        note = st.text_area("Note")
        
        if st.form_submit_button("Salvează"):
            t_in = datetime.combine(d_in, datetime.strptime("15:00", "%H:%M").time())
            t_out = datetime.combine(d_out, datetime.strptime("11:00", "%H:%M").time())
            camere_vizate = list(CAMERE_INFO.keys()) if is_grup else [cam_sel]
            
            if all(este_disponibila(c, t_in, t_out) for c in camere_vizate):
                for cv in camere_vizate:
                    p_u = pret_final/6 if is_grup else pret_final
                    c.execute("INSERT INTO rezervari (nume, telefon, camera, checkin, checkout, status, pret_total, note) VALUES (?,?,?,?,?,?,?,?)",
                              (nume, telefon, cv, t_in, t_out, status, p_u, note))
                conn.commit()
                st.success("Salvat!")
                st.rerun()
            else:
                st.error("Conflict detectat!")

elif choice == "📋 Listă Rezervări":
    st.title("Listă Rezervări")
    df = pd.read_sql_query("SELECT * FROM rezervari ORDER BY checkin DESC", conn)
    for i, r in df.iterrows():
        with st.container():
            st.markdown(f"<div style='background:white; padding:10px; border-radius:5px; border-left:5px solid #3498DB; margin-bottom:5px;'><b>{r['camera']} - {r['nume']}</b><br>{r['checkin'][:10]} -> {r['checkout'][:10]}</div>", unsafe_allow_html=True)
            if st.button(f"Șterge {r['id']}", key=f"del_{r['id']}"):
                c.execute("DELETE FROM rezervari WHERE id=?", (r['id'],))
                conn.commit()
                st.rerun()
