import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date, time
import urllib.parse
import calendar
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import base64
import os
import io
from pypdf import PdfWriter, PdfReader

# ==========================================
# 1. CONFIGURARE PAGINĂ & DESIGN
# ==========================================
st.set_page_config(
    page_title="Elia PMS", 
    page_icon="🏔️", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- FUNCȚIE BACKGROUND ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f: data = f.read()
    return base64.b64encode(data).decode()

def set_bg_hack(main_bg):
    try:
        bin_str = get_base64_of_bin_file(main_bg)
        st.markdown(f'''<style>.stApp {{background-image: linear-gradient(rgba(255,255,255,0.85), rgba(255,255,255,0.95)), url("data:image/jpg;base64,{bin_str}"); background-size: cover; background-attachment: fixed;}}</style>''', unsafe_allow_html=True)
    except: pass

if os.path.exists("Bucegi National Park 2.jpg"): set_bg_hack("Bucegi National Park 2.jpg")

# --- CSS MODERN ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; color: #1f2937; }

    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e5e7eb; }
    [data-testid="stSidebar"] * { color: #1f2937 !important; }
    
    .info-card { background: rgba(255, 255, 255, 0.95); padding: 20px; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #f1f5f9; }

    .scroll-container { overflow-x: auto; padding-bottom: 10px; background: rgba(255, 255, 255, 0.9); border-radius: 15px; }
    .custom-table { width: 100%; border-collapse: separate; border-spacing: 0; min-width: 800px; } 
    .custom-table th { background: #f8fafc; color: #475569; padding: 10px; border-bottom: 2px solid #e2e8f0; font-size: 11px; text-transform: uppercase; }
    .custom-table td { border-bottom: 1px solid #f1f5f9; height: 50px; vertical-align: middle; padding: 0 !important; }
    .first-col { background: #ffffff; font-weight: 600; color: #1e293b; width: 80px; padding-left: 5px !important; }

    .calendar-box { height: 35px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: white; }
    .bg-liber { background: #f1f5f9; border-radius: 50%; height: 8px; width: 8px; margin: auto; }
    .bg-ocupat { background: #ef4444; width: 100.5%; }
    .bg-checkin { background: linear-gradient(90deg, transparent 0%, #10b981 15%, #ef4444 85%); width: 100.5%; border-radius: 8px 0 0 8px; }
    .bg-checkout { background: linear-gradient(90deg, #ef4444 15%, #10b981 85%, transparent 100%); width: 100.5%; border-radius: 0 8px 8px 0; }
    .bg-schimb { background: linear-gradient(90deg, #ef4444 45%, #ffffff 50%, #10b981 50%, #ef4444 55%); width: 100.5%; color: #000; }

    .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; margin-top: 10px; }
    .cal-day-header { text-align: center; font-weight: bold; font-size: 12px; color: #64748b; margin-bottom: 5px; }
    .cal-day-cell { background: white; border-radius: 8px; padding: 5px; min-height: 50px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid #e2e8f0; font-size: 14px; font-weight: bold; }
    .occ-low { background: #ecfdf5; border-color: #10b981; color: #065f46; }
    .occ-med { background: #ffedd5; border-color: #f97316; color: #9a3412; }
    .occ-high { background: #fee2e2; border-color: #ef4444; color: #991b1b; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. LOGICĂ & DB
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

def get_data():
    try:
        df = conn.read(worksheet="Rezervari", ttl=0)
        req = ['id', 'nume', 'telefon', 'camera', 'checkin', 'checkout', 'status', 'pret_total', 'note']
        if df.empty or not all(c in df.columns for c in req): return pd.DataFrame(columns=req)
        
        # Conversii Date
        df['checkin'] = pd.to_datetime(df['checkin'], errors='coerce')
        df['checkout'] = pd.to_datetime(df['checkout'], errors='coerce')
        df = df.dropna(subset=['checkin', 'checkout'])
        
        # Conversii Numere
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        df['pret_total'] = pd.to_numeric(df['pret_total'], errors='coerce').fillna(0.0)
        
        # --- FIX TELEFON (Eliminare .0) ---
        df['telefon'] = df['telefon'].astype(str).str.replace(r'\.0$', '', regex=True)
        # Înlocuim "nan" cu spațiu gol dacă nu există telefon
        df['telefon'] = df['telefon'].replace('nan', '')
        
        return df
    except: return pd.DataFrame(columns=['id', 'nume', 'telefon', 'camera', 'checkin', 'checkout', 'status', 'pret_total', 'note'])

def update_data(df):
    try:
        df_s = df.copy()
        df_s['checkin'] = df_s['checkin'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_s['checkout'] = df_s['checkout'].dt.strftime('%Y-%m-%d %H:%M:%S')
        conn.update(worksheet="Rezervari", data=df_s)
    except Exception as e: st.error(str(e))

def este_disponibila(df, camera, start, end):
    if df.empty: return True
    mask = (df['status'] != 'Anulat') & (df['camera'] == camera)
    conflict = mask & ~( (df['checkout'] <= start) | (df['checkin'] >= end) )
    return df[conflict].empty

# --- FUNCȚIE PDF MERGE (PAGINA 2 FIXĂ) ---
def genereaza_pdf(r):
    pdf = FPDF(); pdf.add_page()
    if os.path.exists("LOGO final.png"): pdf.image("LOGO final.png", x=10, y=8, w=30); pdf.ln(20)
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "CONFIRMARE REZERVARE", ln=True, align='C'); pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"ID Rezervare: {r['id']}", ln=True)
    pdf.cell(0, 10, f"Client: {r['nume']}", ln=True)
    pdf.cell(0, 10, f"Telefon: {r['telefon']}", ln=True)
    pdf.cell(0, 10, f"Camera: {r['camera']}", ln=True)
    try: d1, d2 = r['checkin'].strftime('%d-%m-%Y'), r['checkout'].strftime('%d-%m-%Y')
    except: d1, d2 = str(r['checkin']), str(r['checkout'])
    pdf.cell(0, 10, f"Check-in: {d1} (dupa 15:00)", ln=True); pdf.cell(0, 10, f"Check-out: {d2} (pana la 11:00)", ln=True)
    pdf.ln(5); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, f"Total de Plata: {r['pret_total']} RON", ln=True)
    if pd.notna(r['note']) and r['note']: pdf.ln(5); pdf.set_font("Arial", '', 10); pdf.multi_cell(0, 10, f"Note: {r['note']}")

    pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
    pdf1_buffer = io.BytesIO(pdf_bytes)
    output_writer = PdfWriter()
    output_writer.add_page(PdfReader(pdf1_buffer).pages[0])
    
    if os.path.exists("General pag2.pdf"):
        try:
            doc2 = PdfReader("General pag2.pdf")
            for page in doc2.pages: output_writer.add_page(page)
        except: pass
    
    final_buffer = io.BytesIO()
    output_writer.write(final_buffer)
    return final_buffer.getvalue()

# ==========================================
# 3. SIDEBAR & NAV
# ==========================================
if os.path.exists("LOGO final.png"): st.sidebar.image("LOGO final.png", use_container_width=True)
st.sidebar.markdown("### 🏔️ Elia PMS")
if st.sidebar.button("✨ Rezervare Nouă", use_container_width=True, type="primary"): st.session_state['show_add_modal'] = True
menu = {"📅 Harta": "Harta", "🗓️ Calendar": "Calendar", "📊 Statistici": "Statistici", "📋 Registru": "Lista"}
choice = st.sidebar.radio("Meniu", list(menu.keys()), format_func=lambda x: x)
sel_page = menu[choice]
df_master = get_data()

# ==========================================
# 4. MODAL ADAUGARE
# ==========================================
if st.session_state.get('show_add_modal', False):
    st.markdown("---")
    with st.container():
        st.markdown("<div class='info-card'><h3>✨ Adaugă Rezervare</h3>", unsafe_allow_html=True)
        with st.form("quick_add"):
            c1, c2 = st.columns(2)
            nume = c1.text_input("Nume", placeholder="Client")
            tel = c2.text_input("Tel", placeholder="07xx")
            cam = c1.selectbox("Cameră", list(CAMERE_INFO.keys()) + ["Toate"])
            d1 = c2.date_input("In", date.today()); d2 = c2.date_input("Out", date.today()+timedelta(1))
            pret = st.number_input("Preț Total", value=float(sum(CAMERE_INFO.values()) if "Toate" in cam else CAMERE_INFO.get(cam, 0)))
            note = st.text_area("Note")
            if st.form_submit_button("🚀 Salvează"):
                t1, t2 = datetime.combine(d1, time(15,0)), datetime.combine(d2, time(11,0))
                cms = list(CAMERE_INFO.keys()) if "Toate" in cam else [cam]
                if all(este_disponibila(df_master, c, t1, t2) for c in cms):
                    new_rows = []
                    max_id = df_master['id'].max() if not df_master.empty else 0
                    for i, cn in enumerate(cms):
                        new_rows.append({"id": int(max_id+1+i), "nume": nume, "telefon": tel, "camera": cn, "checkin": t1, "checkout": t2, "status": "Confirmat", "pret_total": pret/len(cms), "note": note})
                    update_data(pd.concat([df_master, pd.DataFrame(new_rows)], ignore_index=True))
                    st.session_state['show_add_modal'] = False; st.toast("Salvat!"); st.rerun()
                else: st.error("Ocupat!")
            if st.form_submit_button("Închide"): st.session_state['show_add_modal'] = False; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 5. HARTA & ADMINISTRARE
# ==========================================
if sel_page == "Harta":
    st.markdown("<h2 style='text-align:center'>🗺️ Harta</h2>", unsafe_allow_html=True)
    d_start = st.date_input("Data:", date.today())
    zile = [d_start + timedelta(days=i) for i in range(14)]
    
    df_v = df_master[df_master['status']!='Anulat'].copy() if not df_master.empty else pd.DataFrame(columns=df_master.columns)
    if not df_v.empty: df_v['ci'] = df_v['checkin'].dt.date; df_v['co'] = df_v['checkout'].dt.date

    # Tabel Harta
    html = '<div class="scroll-container"><table class="custom-table"><thead><tr><th class="first-col">Cam</th>'
    for d in zile: html += f'<th>{d.strftime("%d")}<br>{d.strftime("%b")}</th>'
    html += '</tr></thead><tbody>'

    for cam in CAMERE_INFO.keys():
        html += f'<tr><td class="first-col">{cam}</td>'
        for d in zile:
            if df_v.empty: html += '<td><div class="bg-liber"></div></td>'; continue
            r_out = df_v[(df_v['camera']==cam) & (df_v['co']==d)]
            r_in = df_v[(df_v['camera']==cam) & (df_v['ci']==d)]
            r_stay = df_v[(df_v['camera']==cam) & (df_v['ci']<d) & (df_v['co']>d)]
            
            bg, lbl = "bg-liber", ""
            if not r_out.empty and not r_in.empty: bg, lbl = "bg-schimb", f"{int(r_out.iloc[0]['id'])}↔{int(r_in.iloc[0]['id'])}"
            elif not r_out.empty: bg, lbl = "bg-checkout", str(int(r_out.iloc[0]['id']))
            elif not r_in.empty: bg, lbl = "bg-checkin", str(int(r_in.iloc[0]['id']))
            elif not r_stay.empty: bg, lbl = "bg-ocupat", str(int(r_stay.iloc[0]['id']))
            
            if bg == "bg-liber": html += f'<td><div class="{bg}"></div></td>'
            else: html += f'<td><div class="calendar-box {bg}">{lbl}</div></td>'
        html += '</tr>'
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

    # --- ZONA CĂUTARE & EDITARE ---
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='info-card'>", unsafe_allow_html=True)
        c1, c2 = st.columns([1, 2])
        search_id = c1.number_input("🔎 Caută ID (Tastatură):", min_value=0, step=1, value=0)
        
        selected_r = None
        if search_id > 0 and not df_master.empty:
            found = df_master[df_master['id'] == search_id]
            if not found.empty: selected_r = found.iloc[0]
        
        if selected_r is not None:
            r = selected_r
            # Header Rezervare
            st.markdown(f"### 👤 {r['nume']}") 
            st.markdown(f"**Camera:** {r['camera']} | **Perioada:** {r['checkin'].strftime('%d.%m')} - {r['checkout'].strftime('%d.%m')}")
            
            # --- ZONA DE EDITARE ---
            with st.expander("✏️ Editează / Modifică Datele", expanded=False):
                with st.form(key=f"edit_form_{r['id']}"):
                    ce1, ce2 = st.columns(2)
                    new_nume = ce1.text_input("Nume", r['nume'])
                    new_tel = ce2.text_input("Telefon", r['telefon'])
                    new_pret = ce1.number_input("Preț Total", value=float(r['pret_total']))
                    new_note = ce2.text_area("Note", r['note'] if pd.notna(r['note']) else "")
                    
                    if st.form_submit_button("💾 Salvează Modificările", use_container_width=True):
                        idx = df_master[df_master['id'] == r['id']].index[0]
                        df_master.at[idx, 'nume'] = new_nume
                        df_master.at[idx, 'telefon'] = new_tel
                        df_master.at[idx, 'pret_total'] = new_pret
                        df_master.at[idx, 'note'] = new_note
                        update_data(df_master)
                        st.toast("Date actualizate cu succes!"); st.rerun()

            # --- BUTOANE ACȚIUNE RAPIDĂ ---
            st.markdown("---")
            col_act1, col_act2, col_act3 = st.columns(3)
            
            # 1. Download PDF
            col_act1.download_button("📄 PDF", data=genereaza_pdf(r), file_name=f"Rezervare_{r['id']}.pdf", mime="application/pdf", use_container_width=True)
            
            # 2. WhatsApp
            wa = urllib.parse.quote(f"Salut {r['nume']}, confirmare rezervare.")
            col_act2.markdown(f'<a href="https://api.whatsapp.com/send?phone={r["telefon"]}&text={wa}" target="_blank"><button style="width:100%;background:#25D366;color:white;border:none;padding:10px;border-radius:5px;font-weight:bold; height: 38px;">WhatsApp</button></a>', unsafe_allow_html=True)
            
            # 3. Sterge
            if col_act3.button("🗑️ Sterge", use_container_width=True):
                df_master = df_master[df_master['id'] != r['id']]; update_data(df_master); st.rerun()

        elif search_id > 0:
            st.warning("ID inexistent.")
        else:
            st.info("Tastează ID-ul pentru editare și opțiuni.")
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 6. CALENDAR LUNAR
# ==========================================
elif sel_page == "Calendar":
    st.markdown("### 🗓️ Calendar General")
    c1, c2 = st.columns([1,3]); an = c1.selectbox("An", [2024, 2025, 2026], index=1); luna = c2.selectbox("Luna", range(1, 13), index=datetime.now().month-1)
    cal = calendar.monthcalendar(an, luna)
    html_cal = '<div class="calendar-grid">'
    for z in ["Lu", "Ma", "Mi", "Jo", "Vi", "Sâ", "Du"]: html_cal += f'<div class="cal-day-header">{z}</div>'
    df_act = df_master[df_master['status']!='Anulat'].copy() if not df_master.empty else pd.DataFrame()
    if not df_act.empty: df_act['cin'] = df_act['checkin'].dt.normalize(); df_act['con'] = df_act['checkout'].dt.normalize()
    for week in cal:
        for day in week:
            if day == 0: html_cal += '<div></div>'; continue
            curr = pd.Timestamp(an, luna, day); nr = 0
            if not df_act.empty: nr = len(df_act[(df_act['cin'] <= curr) & (df_act['con'] > curr)]['camera'].unique())
            cls = "occ-low"
            if nr >= 6: cls = "occ-high"
            elif nr > 0: cls = "occ-med"
            html_cal += f'<div class="cal-day-cell {cls}">{day}<span style="font-size:10px; font-weight:normal">{nr}/6</span></div>'
    html_cal += '</div>'; st.markdown(html_cal, unsafe_allow_html=True)

# ==========================================
# 7. STATISTICI
# ==========================================
elif sel_page == "Statistici":
    st.markdown("### 📊 Performanță")
    if not df_master.empty:
        df_s = df_master[df_master['status'] != 'Anulat'].copy()
        occupied_dates = []
        for _, row in df_s.iterrows():
            d_range = pd.date_range(row['checkin'], row['checkout'] - timedelta(days=1))
            occupied_dates.extend(d_range)
        
        if occupied_dates:
            occ_series = pd.Series(occupied_dates)
            occ_by_month = occ_series.groupby(occ_series.dt.to_period("M")).count()
            stats_data = []
            for period, occupied_nights in occ_by_month.items():
                rate = (occupied_nights / (period.days_in_month * 6)) * 100
                stats_data.append({"Luna": period.strftime("%b %Y"), "Grad Ocupare %": round(rate, 1)})
            df_stats = pd.DataFrame(stats_data)
        else: df_stats = pd.DataFrame()

        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='info-card'><h2 style='color:#059669; margin:0'>{df_s['pret_total'].sum():,.0f} RON</h2><small>Total Încasări</small></div>", unsafe_allow_html=True)
        avg_occ = df_stats["Grad Ocupare %"].mean() if not df_stats.empty else 0
        c2.markdown(f"<div class='info-card'><h2 style='color:#2563eb; margin:0'>{avg_occ:.1f}%</h2><small>Grad Mediu</small></div>", unsafe_allow_html=True)
        
        if not df_stats.empty:
            st.subheader("Grad de Ocupare Lunar (%)")
            st.bar_chart(df_stats.set_index("Luna"))
            st.subheader("Încasări Lunare")
            df_s['luna'] = df_s['checkin'].dt.strftime('%Y-%m')
            st.bar_chart(df_s.groupby('luna')['pret_total'].sum())
    else: st.info("Nu există date.")

elif sel_page == "Lista":
    st.markdown("### 📋 Registru")
    if not df_master.empty: st.dataframe(df_master[['id','nume','camera','checkin','pret_total']].sort_values(by='checkin', ascending=False), use_container_width=True)
