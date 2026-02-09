import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
import urllib.parse

# --- CONFIGURARE ---
st.set_page_config(page_title="Pensiune Manager Pro", layout="wide")

# --- DATABASE ---
conn = sqlite3.connect('pensiune.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS rezervari 
             (id INTEGER PRIMARY KEY, nume TEXT, telefon TEXT, camera TEXT, 
              checkin DATETIME, checkout DATETIME, status TEXT, pret_total REAL, note TEXT)''')
conn.commit()

CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

# --- FUNCTII AJUTATOARE ---
def este_disponibila(camera, start, end):
    query = '''SELECT * FROM rezervari 
               WHERE camera = ? AND status != 'Anulat'
               AND NOT (checkout <= ? OR checkin >= ?)'''
    c.execute(query, (camera, start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')))
    return len(c.fetchall()) == 0

# --- INTERFATA ---
st.sidebar.title("🏨 Meniu Control")
choice = st.sidebar.radio("Navigare", ["Calendar Vizual", "Rezervare Nouă", "Rezervare Grup", "Listă Rezervări"])

# 1. CALENDAR VIZUAL (MODIFICAT PENTRU SCHIMBURI)
if choice == "Calendar Vizual":
    st.header("📅 Calendar Disponibilitate")
    
    col_l, col_r = st.columns([1, 3])
    data_start_cal = col_l.date_input("Începând cu data:", date.today())
    zile_vizibile = 14
    interval_zile = [data_start_cal + timedelta(days=i) for i in range(zile_vizibile)]
    
    # Construim matricea pentru tabel
    df_rez = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    df_rez['checkin'] = pd.to_datetime(df_rez['checkin'])
    df_rez['checkout'] = pd.to_datetime(df_rez['checkout'])

    data_matrix = []
    for cam in CAMERE_INFO.keys():
        row = {"Cameră": cam}
        for d in interval_zile:
            # Verificăm ce se întâmplă în această zi
            zi_dt = datetime.combine(d, datetime.min.time())
            
            plecare = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkout'].dt.date == d)].empty
            sosire = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin'].dt.date == d)].empty
            ocupat = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin'].dt.date < d) & (df_rez['checkout'].dt.date > d)].empty
            
            if plecare and sosire: row[d.strftime('%d/%m')] = "🔄 SCHIMB"
            elif plecare: row[d.strftime('%d/%m')] = "📤 PLECARE"
            elif sosire: row[d.strftime('%d/%m')] = "📥 SOSIRE"
            elif ocupat: row[d.strftime('%d/%m')] = "🔴 OCUPAT"
            else: row[d.strftime('%d/%m')] = "🟢 LIBER"
        data_matrix.append(row)

    grid_df = pd.DataFrame(data_matrix)
    
    # Styling pentru culori
    def color_status(val):
        color = 'white'
        if val == "🟢 LIBER": color = '#90ee90'
        elif val == "🔴 OCUPAT": color = '#ffcccb'
        elif val == "🔄 SCHIMB": color = '#f0e68c' # Galben pentru zi ocupata partial
        elif val == "📥 SOSIRE": color = '#add8e6'
        elif val == "📤 PLECARE": color = '#e6e6fa'
        return f'background-color: {color}'

    st.table(grid_df.style.applymap(color_status, subset=grid_df.columns[1:]))
    st.info("Legenda: 🟢 Liber | 🔴 Ocupat | 🔄 Schimb (Check-out 11:00 / Check-in 15:00)")

# 2. REZERVARE NOUA (CU ORE)
elif choice in ["Rezervare Nouă", "Rezervare Grup"]:
    st.header(f"➕ {choice}")
    is_grup = (choice == "Rezervare Grup")
    
    with st.form("form_rez"):
        nume = st.text_input("Nume Client")
        telefon = st.text_input("Telefon (407...)")
        cam_sel = ["Toate"] if is_grup else st.selectbox("Cameră", list(CAMERE_INFO.keys()))
        
        c1, c2 = st.columns(2)
        d_in = c1.date_input("Data Check-in", date.today())
        d_out = c2.date_input("Data Check-out", date.today() + timedelta(days=1))
        
        # Orele solicitate
        t_in = datetime.combine(d_in, datetime.strptime("15:00", "%H:%M").time())
        t_out = datetime.combine(d_out, datetime.strptime("11:00", "%H:%M").time())
        
        pret_sugerat = sum(CAMERE_INFO.values()) if is_grup else CAMERE_INFO[cam_sel]
        pret_final = st.number_input("Preț Total (RON)", value=float(pret_sugerat))
        status = st.selectbox("Status", ["Confirmat", "În așteptare", "Anulat"])
        note = st.text_area("Note informative")
        
        if st.form_submit_button("Salvează Rezervarea"):
            camere_vizate = list(CAMERE_INFO.keys()) if is_grup else [cam_sel]
            conflict = [c for c in camere_vizate if not este_disponibila(c, t_in, t_out)]
            
            if conflict:
                st.error(f"⚠️ Conflict de disponibilitate pentru: {', '.join(conflict)}")
            else:
                for c_name in camere_vizate:
                    p_unit = pret_final / 6 if is_grup else pret_final
                    c.execute("INSERT INTO rezervari (nume, telefon, camera, checkin, checkout, status, pret_total, note) VALUES (?,?,?,?,?,?,?,?)",
                              (nume, telefon, c_name, t_in, t_out, status, p_unit, note))
                conn.commit()
                st.success("Rezervare salvată!")
                st.rerun()

# 3. LISTA REZERVARI
elif choice == "Listă Rezervări":
    st.header("📋 Toate Rezervările")
    df_view = pd.read_sql_query("SELECT * FROM rezervari ORDER BY checkin ASC", conn)
    st.dataframe(df_view)
