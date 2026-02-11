import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date, time
import urllib.parse
import calendar
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURARE ---
st.set_page_config(page_title="Manager Pensiune Pro", layout="wide", initial_sidebar_state="collapsed")

# --- CSS (Design identic cu cel anterior) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .scroll-container { overflow-x: auto; white-space: nowrap; padding-bottom: 20px; }
    .custom-table { width: 100%; border-collapse: collapse; min-width: 1000px; table-layout: fixed; border: none; }
    .custom-table th { border: 1px solid #ddd; padding: 10px; background: #f1f3f4; font-size: 14px; position: sticky; top: 0; z-index: 5; }
    .custom-table td { border: none; padding: 0 !important; margin: 0 !important; height: 55px; vertical-align: middle; position: relative; }
    .sticky-col { position: sticky; left: 0; background: #fff; z-index: 10; font-weight: bold; border-right: 3px solid #3498db !important; width: 130px; padding: 5px !important; border-top: 1px solid #eee; border-bottom: 1px solid #eee; color: #2c3e50; }
    .calendar-box { height: 46px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: bold; color: white; margin: 0; padding: 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.3); }
    .bg-liber { background: #2ECC71; border: 1px solid #fff; border-radius: 6px; height: 40px; width: 90%; margin: auto; opacity: 0.3; }
    .bg-ocupat { background: #E74C3C; width: 100.5%; border-top: 3px solid #f8f9fa; border-bottom: 3px solid #f8f9fa; }
    .bg-checkin { background: linear-gradient(90deg, #f8f9fa 5%, #2ECC71 5%, #2ECC71 45%, #E74C3C 55%); border-top: 3px solid #f8f9fa; border-bottom: 3px solid #f8f9fa; width: 100.5%; }
    .bg-checkout { background: linear-gradient(90deg, #E74C3C 45%, #2ECC71 55%, #2ECC71 95%, #f8f9fa 95%); border-top: 3px solid #f8f9fa; border-bottom: 3px solid #f8f9fa; width: 100.5%; }
    .bg-schimb { background: linear-gradient(90deg, #E74C3C 45%, #ffffff 50%, #E74C3C 55%); border-top: 3px solid #f8f9fa; border-bottom: 3px solid #f8f9fa; width: 100.5%; color: #333 !important; text-shadow: none; font-size: 11px; }
    .info-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #3498db; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIUNE GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

# --- 3. FUNCȚII UTILITARE (Adaptate pentru Pandas) ---

def get_data():
    # Citim datele din Sheet, forțăm reîmprospătarea (ttl=0)
    try:
        df = conn.read(worksheet="Rezervari", ttl=0)
        # Convertim coloanele de dată la datetime objects
        df['checkin'] = pd.to_datetime(df['checkin'])
        df['checkout'] = pd.to_datetime(df['checkout'])
        # Asigurăm că ID este numeric
        df['id'] = pd.to_numeric(df['id'])
        return df
    except Exception as e:
        # Dacă foaia e goală sau dă eroare, returnăm structura goală
        return pd.DataFrame(columns=['id', 'nume', 'telefon', 'camera', 'checkin', 'checkout', 'status', 'pret_total', 'note'])

def update_data(df):
    # Scriem înapoi în Google Sheets
    conn.update(worksheet="Rezervari", data=df)

def este_disponibila(df, camera, start, end, exclude_id=None):
    # start și end sunt datetime objects
    mask = (df['status'] != 'Anulat') & (df['camera'] == camera)
    
    # Logică de suprapunere intervale
    # Conflict dacă: Nu (Checkout existent <= New Start SAU Checkin existent >= New End)
    # Pandas vectorization
    conflict = mask & ~( (df['checkout'] <= start) | (df['checkin'] >= end) )
    
    if exclude_id:
        conflict = conflict & (df['id'] != exclude_id)
        
    return df[conflict].empty

def genereaza_pdf(r):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "CONFIRMARE REZERVARE", ln=True, align='C'); pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Client: {r['nume']}", ln=True)
    pdf.cell(0, 10, f"Telefon: {r['telefon']}", ln=True)
    pdf.cell(0, 10, f"Camera: {r['camera']}", ln=True)
    pdf.cell(0, 10, f"Perioada: {r['checkin'].strftime('%Y-%m-%d')} -> {r['checkout'].strftime('%Y-%m-%d')}", ln=True)
    pdf.cell(0, 10, f"Total Plata: {r['pret_total']} RON", ln=True)
    if pd.notna(r['note']) and r['note']:
        pdf.ln(5); pdf.multi_cell(0, 10, f"Note: {r['note']}")
    return pdf.output(dest='S').encode('latin-1')

# --- 4. SIDEBAR & NAVIGARE ---
st.sidebar.title("🏨 Manager Pensiune")

if st.sidebar.button("➕ ADAUGĂ REZERVARE", key="btn_add_sidebar", use_container_width=True, type="primary"):
    st.session_state['show_add_modal'] = True

menu = ["📅 Harta Disponibilității", "🗓️ Calendar Lunar", "📊 Statistici", "📋 Listă Rezervări"]
choice = st.sidebar.radio("Meniu", menu)

# Încărcăm datele o singură dată la începutul ciclului
df_master = get_data()

# --- 5. MODAL ADĂUGARE REZERVARE ---
if st.session_state.get('show_add_modal', False):
    st.markdown("---")
    with st.container():
        st.subheader("📝 Rezervare Nouă")
        with st.form("quick_add"):
            c1, c2 = st.columns(2)
            nume = c1.text_input("Nume Client")
            tel = c2.text_input("Telefon (ex: 407...)")
            cam = c1.selectbox("Cameră", list(CAMERE_INFO.keys()) + ["Toate (Grup)"])
            d1 = c2.date_input("Check-in", date.today())
            d2 = c2.date_input("Check-out", date.today() + timedelta(1))
            
            pret_default = sum(CAMERE_INFO.values()) if "Grup" in cam else (CAMERE_INFO[cam] if cam in CAMERE_INFO else 0)
            pret = c1.number_input("Preț Total", value=float(pret_default))
            note = st.text_area("Note")
            
            cols = st.columns(2)
            if cols[0].form_submit_button("✅ Salvează"):
                t1, t2 = datetime.combine(d1, time(15, 0)), datetime.combine(d2, time(11, 0))
                camere_target = list(CAMERE_INFO.keys()) if "Grup" in cam else [cam]
                
                # Verificăm disponibilitatea pe datele locale (df_master)
                if all(este_disponibila(df_master, c, t1, t2) for c in camere_target):
                    new_rows = []
                    # Calculăm noul ID
                    max_id = df_master['id'].max() if not df_master.empty else 0
                    if pd.isna(max_id): max_id = 0
                    
                    for i, c_name in enumerate(camere_target):
                        p_part = pret / 6 if "Grup" in cam else pret
                        new_row = {
                            "id": int(max_id + 1 + i),
                            "nume": nume, "telefon": tel, "camera": c_name,
                            "checkin": t1, "checkout": t2,
                            "status": "Confirmat", "pret_total": p_part, "note": note
                        }
                        new_rows.append(new_row)
                    
                    # Actualizare DataFrame și Google Sheets
                    updated_df = pd.concat([df_master, pd.DataFrame(new_rows)], ignore_index=True)
                    update_data(updated_df)
                    st.session_state['show_add_modal'] = False
                    st.success("Rezervare Salvată pe Google Drive!"); st.rerun()
                else:
                    st.error("⚠️ Conflict! Una dintre camere este ocupată.")
            
            if cols[1].form_submit_button("❌ Închide"):
                st.session_state['show_add_modal'] = False
                st.rerun()
    st.markdown("---")

# --- 6. HARTA ---
if choice == "📅 Harta Disponibilității":
    st.title("Harta Disponibilității")
    d_start = st.date_input("Start:", date.today())
    zile = [d_start + timedelta(days=i) for i in range(14)]
    d_end_view = zile[-1]
    
    # Pregătim datele pentru afișare (doar cele active)
    df_view = df_master[df_master['status'] != 'Anulat'].copy()
    df_view['checkin_d'] = df_view['checkin'].dt.date
    df_view['checkout_d'] = df_view['checkout'].dt.date

    html = '<div class="scroll-container"><table class="custom-table"><thead><tr><th class="sticky-col">Cameră</th>'
    for d in zile: html += f'<th>{d.strftime("%d/%m")}</th>'
    html += '</tr></thead><tbody>'

    for cam in CAMERE_INFO.keys():
        html += f'<tr><td class="sticky-col">{cam}</td>'
        for d in zile:
            # Filtrare cu Pandas
            r_out = df_view[(df_view['camera'] == cam) & (df_view['checkout_d'] == d)]
            r_in = df_view[(df_view['camera'] == cam) & (df_view['checkin_d'] == d)]
            r_stay = df_view[(df_view['camera'] == cam) & (df_view['checkin_d'] < d) & (df_view['checkout_d'] > d)]
            
            bg, label = "bg-liber", ""
            
            if not r_out.empty and not r_in.empty:
                bg = "bg-schimb"
                label = f"{int(r_out.iloc[0]['id'])}|{int(r_in.iloc[0]['id'])}"
            elif not r_out.empty:
                bg = "bg-checkout"
                r = r_out.iloc[0]
                if (r['checkout_d'] - r['checkin_d']).days <= 1: label = str(int(r['id']))
                else:
                     v_start = max(r['checkin_d'], d_start)
                     v_end = min(r['checkout_d'], d_end_view)
                     if d == v_start + timedelta(days=(v_end - v_start).days // 2): label = str(int(r['id']))
            elif not r_in.empty:
                bg = "bg-checkin"
                r = r_in.iloc[0]
                if (r['checkout_d'] - r['checkin_d']).days <= 1: label = str(int(r['id']))
                else:
                     v_start = max(r['checkin_d'], d_start)
                     v_end = min(r['checkout_d'], d_end_view)
                     if d == v_start + timedelta(days=(v_end - v_start).days // 2): label = str(int(r['id']))
            elif not r_stay.empty:
                bg = "bg-ocupat"
                r = r_stay.iloc[0]
                v_start = max(r['checkin_d'], d_start)
                v_end = min(r['checkout_d'], d_end_view)
                if d == v_start + timedelta(days=(v_end - v_start).days // 2): label = str(int(r['id']))
            
            html += f'<td><div class="calendar-box {bg}">{label}</div></td>'
        html += '</tr>'
    
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

    # Detalii & Editare
    st.markdown("### 🔍 Detalii & Editare")
    active_ids = sorted(df_view['id'].unique().tolist())
    id_sel = st.selectbox("Selectează ID-ul de pe hartă:", ["-"] + [str(i) for i in active_ids])
    
    if id_sel != "-":
        r_idx = df_master[df_master['id'] == int(id_sel)].index[0]
        r = df_master.iloc[r_idx]
        
        with st.container():
            st.info(f"Editare rezervare: {r['nume']} ({r['camera']})")
            c1, c2, c3 = st.columns(3)
            new_tel = c1.text_input("Telefon", r['telefon'])
            new_pret = c2.number_input("Preț", value=float(r['pret_total']))
            new_note = c3.text_area("Note", r['note'] if pd.notna(r['note']) else "")
            
            btn_col = st.columns(4)
            if btn_col[0].button("💾 Salvează"):
                df_master.at[r_idx, 'telefon'] = new_tel
                df_master.at[r_idx, 'pret_total'] = new_pret
                df_master.at[r_idx, 'note'] = new_note
                update_data(df_master)
                st.success("Actualizat!"); st.rerun()
            
            btn_col[1].download_button("📄 PDF", genereaza_pdf(r), f"Rez_{id_sel}.pdf")
            
            wa_msg = urllib.parse.quote(f"Salut {r['nume']}, confirmam rezervarea la Elia.")
            btn_col[2].markdown(f'<a href="https://api.whatsapp.com/send?phone={new_tel}&text={wa_msg}" target="_blank"><button style="width:100%; border:none; background:#25D366; color:white; padding:5px; border-radius:5px;">📱 WhatsApp</button></a>', unsafe_allow_html=True)
            
            if btn_col[3].button("🗑️ Șterge"):
                # Ștergem rândul din DataFrame
                df_master = df_master[df_master['id'] != int(id_sel)]
                update_data(df_master)
                st.warning("Șters!"); st.rerun()

# --- 7. CALENDAR LUNAR ---
elif choice == "🗓️ Calendar Lunar":
    st.title("🗓️ Calendar de Ansamblu")
    c1, c2 = st.columns(2)
    an = c1.selectbox("An", [2024, 2025, 2026], index=1)
    luna = c2.selectbox("Luna", list(range(1, 13)), index=datetime.now().month-1)
    
    cal = calendar.monthcalendar(an, luna)
    df_active = df_master[df_master['status'] != 'Anulat'].copy()
    
    st.markdown("### Grad de ocupare")
    cols = st.columns(7)
    for z in ["Lu", "Ma", "Mi", "Jo", "Vi", "Sâ", "Du"]: cols[0].parent.write("") # Hack
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                curr_date = pd.Timestamp(year=an, month=luna, day=day)
                # Count occupied rooms for this specific day
                # Logic: checkin <= day < checkout (stays overnight)
                # Or checkin <= day <= checkout (occupies partially) -> using < checkout for overnight logic
                ocupate = df_active[
                    (df_active['checkin'] <= curr_date) & 
                    (df_active['checkout'] > curr_date)
                ]
                nr_cam = len(ocupate['camera'].unique())
                
                bg = "#e8f8f5"
                txt = "#27ae60"
                if nr_cam >= 6: bg, txt = "#fadbd8", "#c0392b"
                elif nr_cam > 0: bg, txt = "#fdebd0", "#d35400"
                
                cols[i].markdown(f"""
                <div style="background:{bg}; padding:10px; border-radius:8px; text-align:center; border:1px solid {txt}; margin-bottom:5px;">
                    <span style="font-size:16px; font-weight:bold; color:{txt}">{day}</span><br>
                    <span style="font-size:11px;">{nr_cam}/6</span>
                </div>
                """, unsafe_allow_html=True)

# --- 8. STATISTICI ---
elif choice == "📊 Statistici":
    st.title("📊 Statistici Financiare")
    df_active = df_master[df_master['status'] != 'Anulat']
    
    if not df_active.empty:
        df_active['luna_nume'] = df_active['checkin'].dt.strftime('%B')
        
        c1, c2 = st.columns(2)
        c1.metric("Venituri Totale", f"{df_active['pret_total'].sum():,.0f} RON")
        c2.metric("Număr Rezervări", len(df_active))
        
        st.subheader("Venituri Lunare")
        st.bar_chart(df_active.groupby('luna_nume')['pret_total'].sum())
    else:
        st.info("Nu există date.")

# --- 9. LISTĂ ---
elif choice == "📋 Listă Rezervări":
    st.title("📋 Registru Rezervări")
    # Afișăm o versiune curată a tabelului
    st.dataframe(
        df_master[['id', 'nume', 'telefon', 'camera', 'checkin', 'checkout', 'pret_total', 'note']].sort_values(by='checkin', ascending=False),
        use_container_width=True
    )
