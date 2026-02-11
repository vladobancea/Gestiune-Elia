import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date, time
import urllib.parse
import calendar
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CONFIGURARE PAGINĂ ȘI STILURI (CSS)
# ==========================================
st.set_page_config(page_title="Manager Pensiune Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Fundal general */
    .main { background-color: #f8f9fa; }
    
    /* Container pentru Harta (Scroll orizontal pe mobil) */
    .scroll-container { 
        overflow-x: auto; 
        white-space: nowrap; 
        padding-bottom: 20px; 
    }
    
    /* Tabel Harta - Optimizat pentru continuitate */
    .custom-table { 
        width: 100%; 
        border-collapse: collapse; 
        min-width: 1000px; 
        table-layout: fixed; 
        border: none; 
    }
    
    /* Header Tabel (Zilele) */
    .custom-table th { 
        border: 1px solid #ddd; 
        padding: 10px; 
        background: #f1f3f4; 
        font-size: 14px; 
        position: sticky; 
        top: 0; 
        z-index: 5; 
    }
    
    /* Celule Tabel */
    .custom-table td { 
        border: none; 
        padding: 0 !important; 
        margin: 0 !important; 
        height: 55px; 
        vertical-align: middle; 
        position: relative; 
    }
    
    /* Coloana Fixă (Numele Camerelor) */
    .sticky-col { 
        position: sticky; 
        left: 0; 
        background: #fff; 
        z-index: 10; 
        font-weight: bold; 
        border-right: 3px solid #3498db !important; 
        width: 130px; 
        padding: 5px !important; 
        border-top: 1px solid #eee; 
        border-bottom: 1px solid #eee; 
        color: #2c3e50; 
    }
    
    /* Stil general cutie calendar */
    .calendar-box { 
        height: 46px; 
        width: 100%; 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        font-size: 13px; 
        font-weight: bold; 
        color: white; 
        margin: 0; 
        padding: 0; 
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3); 
    }

    /* --- CULORI ȘI CONTINUITATE VIZUALĂ --- */
    
    /* Liber */
    .bg-liber { 
        background: #2ECC71; 
        border: 1px solid #fff; 
        border-radius: 6px; 
        height: 40px; 
        width: 90%; 
        margin: auto; 
        opacity: 0.3; 
    }
    
    /* Ocupat (Bandă continuă) */
    .bg-ocupat { 
        background: #E74C3C; 
        width: 100.5%; 
        border-top: 3px solid #f8f9fa; 
        border-bottom: 3px solid #f8f9fa; 
    }
    
    /* Check-in (Gradient Intrare) */
    .bg-checkin { 
        background: linear-gradient(90deg, #f8f9fa 5%, #2ECC71 5%, #2ECC71 45%, #E74C3C 55%); 
        border-top: 3px solid #f8f9fa; 
        border-bottom: 3px solid #f8f9fa; 
        width: 100.5%; 
    }
    
    /* Check-out (Gradient Ieșire) */
    .bg-checkout { 
        background: linear-gradient(90deg, #E74C3C 45%, #2ECC71 55%, #2ECC71 95%, #f8f9fa 95%); 
        border-top: 3px solid #f8f9fa; 
        border-bottom: 3px solid #f8f9fa; 
        width: 100.5%; 
    }
    
    /* Schimb în aceeași zi */
    .bg-schimb { 
        background: linear-gradient(90deg, #E74C3C 45%, #ffffff 50%, #E74C3C 55%); 
        border-top: 3px solid #f8f9fa; 
        border-bottom: 3px solid #f8f9fa; 
        width: 100.5%; 
        color: #333 !important; 
        text-shadow: none; 
        font-size: 11px; 
    }
    
    /* Carduri Informații */
    .info-card { 
        background: white; 
        padding: 20px; 
        border-radius: 12px; 
        border-left: 5px solid #3498db; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
        margin-bottom: 15px; 
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONEXIUNE BAZĂ DE DATE (GOOGLE SHEETS)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

CAMERE_INFO = {
    "Camera 1": 200, "Camera 2": 200, 
    "Camera 3": 250, "Camera 4": 250, 
    "Camera 5": 300, "Camera 6": 350
}

# ==========================================
# 3. FUNCȚII UTILITARE
# ==========================================

def get_data():
    """Citește datele din Google Sheets și repară formatele."""
    try:
        # ttl=0 forțează reîmprospătarea datelor la fiecare acțiune
        df = conn.read(worksheet="Rezervari", ttl=0)
        
        required_cols = ['id', 'nume', 'telefon', 'camera', 'checkin', 'checkout', 'status', 'pret_total', 'note']
        
        # Verificăm dacă foaia e goală sau lipsesc coloane
        if df.empty or not all(col in df.columns for col in required_cols):
            return pd.DataFrame(columns=required_cols)
            
        # Convertim coloanele de dată (tratăm erorile cu 'coerce' -> NaT)
        df['checkin'] = pd.to_datetime(df['checkin'], errors='coerce')
        df['checkout'] = pd.to_datetime(df['checkout'], errors='coerce')
        
        # Eliminăm rândurile cu date invalide
        df = df.dropna(subset=['checkin', 'checkout'])
        
        # Convertim ID și Preț la numere
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        df['pret_total'] = pd.to_numeric(df['pret_total'], errors='coerce').fillna(0.0)
        
        return df
    except Exception as e:
        st.error(f"Eroare la citirea datelor (Verifică dacă foaia se numește 'Rezervari'): {e}")
        return pd.DataFrame(columns=['id', 'nume', 'telefon', 'camera', 'checkin', 'checkout', 'status', 'pret_total', 'note'])

def update_data(df):
    """Salvează datele înapoi în Google Sheets."""
    try:
        df_save = df.copy()
        # Sheets preferă string-uri pentru date ca să nu le strice formatul
        df_save['checkin'] = df_save['checkin'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_save['checkout'] = df_save['checkout'].dt.strftime('%Y-%m-%d %H:%M:%S')
        conn.update(worksheet="Rezervari", data=df_save)
    except Exception as e:
        st.error(f"Eroare la salvare: {e}")

def este_disponibila(df, camera, start, end, exclude_id=None):
    """Verifică suprapunerea rezervărilor."""
    if df.empty: 
        return True
        
    mask = (df['status'] != 'Anulat') & (df['camera'] == camera)
    
    # Logică de conflict: (Start existent < End nou) AND (End existent > Start nou)
    conflict = mask & ~( (df['checkout'] <= start) | (df['checkin'] >= end) )
    
    if exclude_id:
        conflict = conflict & (df['id'] != exclude_id)
        
    return df[conflict].empty

def genereaza_pdf(r):
    """Generează PDF de confirmare."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "CONFIRMARE REZERVARE", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Client: {r['nume']}", ln=True)
    pdf.cell(0, 10, f"Telefon: {r['telefon']}", ln=True)
    pdf.cell(0, 10, f"Camera: {r['camera']}", ln=True)
    
    try:
        c_in = r['checkin'].strftime('%Y-%m-%d')
        c_out = r['checkout'].strftime('%Y-%m-%d')
    except:
        c_in, c_out = str(r['checkin']), str(r['checkout'])
        
    pdf.cell(0, 10, f"Perioada: {c_in} -> {c_out}", ln=True)
    pdf.cell(0, 10, f"Total Plata: {r['pret_total']} RON", ln=True)
    
    if pd.notna(r['note']) and r['note']:
        pdf.ln(5)
        pdf.multi_cell(0, 10, f"Note: {r['note']}")
        
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. INTERFAȚĂ & SIDEBAR
# ==========================================
st.sidebar.title("🏨 Manager Pensiune")

# Butonul Universal de Adăugare
if st.sidebar.button("➕ ADAUGĂ REZERVARE", key="btn_add_sidebar", use_container_width=True, type="primary"):
    st.session_state['show_add_modal'] = True

menu = ["📅 Harta Disponibilității", "🗓️ Calendar Lunar", "📊 Statistici", "📋 Listă Rezervări"]
choice = st.sidebar.radio("Meniu", menu)

# Încărcăm datele (o singură dată pe refresh)
df_master = get_data()

# ==========================================
# 5. MODAL ADĂUGARE REZERVARE
# ==========================================
if st.session_state.get('show_add_modal', False):
    st.markdown("---")
    with st.container():
        st.subheader("📝 Rezervare Nouă")
        with st.form("quick_add"):
            c1, c2 = st.columns(2)
            nume = c1.text_input("Nume Client")
            tel = c2.text_input("Telefon")
            cam = c1.selectbox("Cameră", list(CAMERE_INFO.keys()) + ["Toate (Grup)"])
            d1 = c2.date_input("Check-in", date.today())
            d2 = c2.date_input("Check-out", date.today() + timedelta(1))
            
            pret_def = sum(CAMERE_INFO.values()) if "Grup" in cam else CAMERE_INFO.get(cam, 0)
            pret = c1.number_input("Preț Total", value=float(pret_def))
            note = st.text_area("Note")
            
            cols = st.columns(2)
            if cols[0].form_submit_button("✅ Salvează"):
                # Creăm timpii corecți: Check-in 15:00, Check-out 11:00
                t1 = datetime.combine(d1, time(15, 0))
                t2 = datetime.combine(d2, time(11, 0))
                
                camere_target = list(CAMERE_INFO.keys()) if "Grup" in cam else [cam]
                
                # Verificăm disponibilitatea
                if all(este_disponibila(df_master, c, t1, t2) for c in camere_target):
                    new_rows = []
                    # Calculăm ID-ul următor
                    max_id = df_master['id'].max() if not df_master.empty else 0
                    if pd.isna(max_id): max_id = 0
                    
                    for i, c_name in enumerate(camere_target):
                        p_part = pret / 6 if "Grup" in cam else pret
                        new_rows.append({
                            "id": int(max_id + 1 + i),
                            "nume": nume, 
                            "telefon": tel, 
                            "camera": c_name, 
                            "checkin": t1, 
                            "checkout": t2, 
                            "status": "Confirmat", 
                            "pret_total": p_part, 
                            "note": note
                        })
                    
                    # Adăugăm și salvăm
                    updated_df = pd.concat([df_master, pd.DataFrame(new_rows)], ignore_index=True)
                    update_data(updated_df)
                    st.session_state['show_add_modal'] = False
                    st.success("Salvat cu succes!"); st.rerun()
                else:
                    st.error("⚠️ Conflict! Perioada selectată este indisponibilă.")
            
            if cols[1].form_submit_button("❌ Închide"):
                st.session_state['show_add_modal'] = False
                st.rerun()
    st.markdown("---")

# ==========================================
# 6. PAGINA: HARTA DISPONIBILITĂȚII
# ==========================================
if choice == "📅 Harta Disponibilității":
    st.title("Harta Disponibilității")
    d_start = st.date_input("Start Vizualizare:", date.today())
    zile = [d_start + timedelta(days=i) for i in range(14)]
    d_end_view = zile[-1]
    
    # Pregătim datele pentru vizualizare (convertim în date simple pentru comparație)
    if not df_master.empty:
        df_view = df_master[df_master['status'] != 'Anulat'].copy()
        df_view['checkin_d'] = df_view['checkin'].dt.date
        df_view['checkout_d'] = df_view['checkout'].dt.date
    else:
        df_view = pd.DataFrame(columns=df_master.columns)

    # Construire Tabel HTML
    html = '<div class="scroll-container"><table class="custom-table"><thead><tr><th class="sticky-col">Cameră</th>'
    for d in zile: 
        html += f'<th>{d.strftime("%d/%m")}</th>'
    html += '</tr></thead><tbody>'

    for cam in CAMERE_INFO.keys():
        html += f'<tr><td class="sticky-col">{cam}</td>'
        for d in zile:
            if df_view.empty:
                html += f'<td><div class="calendar-box bg-liber"></div></td>'
                continue

            # Găsim tipurile de rezervări pentru celula curentă
            r_out = df_view[(df_view['camera'] == cam) & (df_view['checkout_d'] == d)]
            r_in = df_view[(df_view['camera'] == cam) & (df_view['checkin_d'] == d)]
            r_stay = df_view[(df_view['camera'] == cam) & (df_view['checkin_d'] < d) & (df_view['checkout_d'] > d)]
            
            bg, label = "bg-liber", ""
            
            # 1. SCHIMB (Out dimineața + In după-amiaza)
            if not r_out.empty and not r_in.empty:
                bg = "bg-schimb"
                label = f"{int(r_out.iloc[0]['id'])}|{int(r_in.iloc[0]['id'])}"
            
            # 2. CHECK-OUT (Plecare)
            elif not r_out.empty:
                bg = "bg-checkout"
                r = r_out.iloc[0]
                # ID-ul apare dacă rezervarea e de 1 noapte SAU dacă ziua curentă e mijlocul vizibil
                if (r['checkout_d'] - r['checkin_d']).days <= 1: 
                    label = str(int(r['id']))
                else:
                    v_start = max(r['checkin_d'], d_start)
                    v_end = min(r['checkout_d'], d_end_view)
                    if d == v_start + timedelta(days=(v_end - v_start).days // 2): 
                        label = str(int(r['id']))

            # 3. CHECK-IN (Sosire)
            elif not r_in.empty:
                bg = "bg-checkin"
                r = r_in.iloc[0]
                if (r['checkout_d'] - r['checkin_d']).days <= 1: 
                    label = str(int(r['id']))
                else:
                    v_start = max(r['checkin_d'], d_start)
                    v_end = min(r['checkout_d'], d_end_view)
                    if d == v_start + timedelta(days=(v_end - v_start).days // 2): 
                        label = str(int(r['id']))

            # 4. OCUPAT COMPLET (Stay)
            elif not r_stay.empty:
                bg = "bg-ocupat"
                r = r_stay.iloc[0]
                v_start = max(r['checkin_d'], d_start)
                v_end = min(r['checkout_d'], d_end_view)
                if d == v_start + timedelta(days=(v_end - v_start).days // 2): 
                    label = str(int(r['id']))
            
            html += f'<td><div class="calendar-box {bg}">{label}</div></td>'
        html += '</tr>'
    
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

    # --- ZONA DE EDITARE ȘI DETALII ---
    if not df_view.empty:
        st.markdown("### 🔍 Detalii & Editare")
        active_ids = sorted(df_view['id'].unique().tolist())
        id_sel = st.selectbox("Selectează ID-ul de pe hartă:", ["-"] + [str(i) for i in active_ids])
        
        if id_sel != "-":
            try:
                # Găsim indexul real în DataFrame-ul master
                r_idx = df_master[df_master['id'] == int(id_sel)].index[0]
                r = df_master.iloc[r_idx]
                
                with st.container():
                    st.info(f"Editare rezervare: {r['nume']} ({r['camera']})")
                    c1, c2, c3 = st.columns(3)
                    
                    new_tel = c1.text_input("Telefon", r['telefon'])
                    new_pret = c2.number_input("Preț", value=float(r['pret_total']))
                    new_note = c3.text_area("Note", r['note'] if pd.notna(r['note']) else "")
                    
                    bc = st.columns(4)
                    
                    # Buton Salvare
                    if bc[0].button("💾 Save"):
                        df_master.at[r_idx, 'telefon'] = new_tel
                        df_master.at[r_idx, 'pret_total'] = new_pret
                        df_master.at[r_idx, 'note'] = new_note
                        update_data(df_master)
                        st.success("Actualizat!")
                        st.rerun()
                    
                    # Buton PDF
                    bc[1].download_button("📄 PDF", genereaza_pdf(r), f"Rez_{id_sel}.pdf")
                    
                    # Buton WhatsApp
                    wa_msg = urllib.parse.quote(f"Salut {r['nume']}, confirmam rezervarea la Elia.")
                    wa_link = f"https://api.whatsapp.com/send?phone={new_tel}&text={wa_msg}"
                    bc[2].markdown(f'<a href="{wa_link}" target="_blank"><button style="width:100%;background:#25D366;color:white;border:none;padding:5px;border-radius:5px">WhatsApp</button></a>', unsafe_allow_html=True)
                    
                    # Buton Ștergere
                    if bc[3].button("🗑️ Del"):
                        df_master = df_master[df_master['id'] != int(id_sel)]
                        update_data(df_master)
                        st.warning("Șters!")
                        st.rerun()
            except IndexError:
                st.warning("Rezervarea nu a fost găsită (posibil ștearsă între timp).")

# ==========================================
# 7. PAGINA: CALENDAR LUNAR (REPARAT)
# ==========================================
elif choice == "🗓️ Calendar Lunar":
    st.title("🗓️ Calendar de Ansamblu")
    c1, c2 = st.columns(2)
    an = c1.selectbox("An", [2024, 2025, 2026], index=1)
    luna = c2.selectbox("Luna", list(range(1, 13)), index=datetime.now().month-1)
    
    cal = calendar.monthcalendar(an, luna)
    
    st.markdown("### Grad de ocupare")
    
    # Header Zile (Fără hack-uri care dau eroare)
    cols = st.columns(7)
    zile_sapt = ["Lu", "Ma", "Mi", "Jo", "Vi", "Sâ", "Du"]
    for i, z in enumerate(zile_sapt):
        cols[i].markdown(f"<div style='text-align:center; font-weight:bold;'>{z}</div>", unsafe_allow_html=True)
    
    if not df_master.empty:
        df_active = df_master[df_master['status'] != 'Anulat'].copy()
        # FIX MAJOR: Eliminăm ora (normalizare) pentru comparație corectă în calendar
        df_active['checkin_norm'] = df_active['checkin'].dt.normalize()
        df_active['checkout_norm'] = df_active['checkout'].dt.normalize()
    else:
        df_active = pd.DataFrame()

    # Generare Calendar Grid
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("") # Zi goală din altă lună
                continue
            
            # Data curentă din calendar (ora 00:00:00)
            curr_date = pd.Timestamp(year=an, month=luna, day=day)
            
            nr_cam = 0
            if not df_active.empty:
                # O cameră e ocupată dacă perioada de ședere include ziua curentă
                # Check-in <= Zi Curentă < Check-out
                ocupate = df_active[
                    (df_active['checkin_norm'] <= curr_date) & 
                    (df_active['checkout_norm'] > curr_date)
                ]
                nr_cam = len(ocupate['camera'].unique())
            
            # Culori în funcție de gradul de ocupare
            bg, txt = "#e8f8f5", "#27ae60" # Verde (Liber)
            if nr_cam >= 6: 
                bg, txt = "#fadbd8", "#c0392b" # Roșu (Plin)
            elif nr_cam > 0: 
                bg, txt = "#fdebd0", "#d35400" # Portocaliu (Parțial)
            
            cols[i].markdown(f"""
                <div style="background:{bg}; padding:10px; border-radius:8px; text-align:center; border:1px solid {txt}; margin-bottom:5px;">
                    <span style="font-size:16px; font-weight:bold; color:{txt}">{day}</span><br>
                    <span style="font-size:11px;">{nr_cam}/6</span>
                </div>
            """, unsafe_allow_html=True)

# ==========================================
# 8. PAGINA: STATISTICI
# ==========================================
elif choice == "📊 Statistici":
    st.title("📊 Statistici Financiare")
    
    if not df_master.empty:
        df_active = df_master[df_master['status'] != 'Anulat'].copy()
        df_active['luna_nume'] = df_active['checkin'].dt.strftime('%B')
        
        c1, c2 = st.columns(2)
        c1.metric("Venituri Totale", f"{df_active['pret_total'].sum():,.0f} RON")
        c2.metric("Număr Rezervări", len(df_active))
        
        st.subheader("Venituri Lunare")
        st.bar_chart(df_active.groupby('luna_nume')['pret_total'].sum())
    else:
        st.info("Nu există date pentru statistici.")

# ==========================================
# 9. PAGINA: LISTĂ REZERVĂRI
# ==========================================
elif choice == "📋 Listă Rezervări":
    st.title("📋 Registru Rezervări")
    
    if not df_master.empty:
        # Afișăm tabelul sortat după data sosirii
        st.dataframe(
            df_master[['id', 'nume', 'telefon', 'camera', 'checkin', 'checkout', 'pret_total', 'note']]
            .sort_values(by='checkin', ascending=False),
            use_container_width=True
        )
    else:
        st.info("Lista de rezervări este goală.")
