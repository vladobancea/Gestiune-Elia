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
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# ==========================================
# 1. CONFIGURARE PAGINĂ & DESIGN
# ==========================================
st.set_page_config(
    page_title="Elia PMS", 
    page_icon="🏔️", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- CACHE & BACKGROUND ---
@st.cache_resource
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f: data = f.read()
    return base64.b64encode(data).decode()

def set_bg_hack(main_bg):
    try:
        bin_str = get_base64_of_bin_file(main_bg)
        st.markdown(f'''<style>.stApp {{background-image: linear-gradient(rgba(255,255,255,0.85), rgba(255,255,255,0.95)), url("data:image/jpg;base64,{bin_str}"); background-size: cover; background-attachment: fixed;}}</style>''', unsafe_allow_html=True)
    except: pass

if os.path.exists("Bucegi National Park 2.jpg"): set_bg_hack("Bucegi National Park 2.jpg")

# --- CSS MODERN (OPTIMIZAT MOBIL) ---
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
# 2. LOGICĂ & DATABASE
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

@st.cache_data(ttl=3600)
def get_data_cached():
    try:
        df = conn.read(worksheet="Rezervari", ttl=0)
        req = ['id', 'nume', 'telefon', 'email', 'camera', 'checkin', 'checkout', 'status', 'pret_total', 'note']
        if df.empty: return pd.DataFrame(columns=req)
        
        for col in req:
            if col not in df.columns: df[col] = ""

        df['checkin'] = pd.to_datetime(df['checkin'], errors='coerce')
        df['checkout'] = pd.to_datetime(df['checkout'], errors='coerce')
        df = df.dropna(subset=['checkin', 'checkout'])
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        df['pret_total'] = pd.to_numeric(df['pret_total'], errors='coerce').fillna(0.0)
        
        # Bug fix telefon
        df['telefon'] = df['telefon'].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', '')
        df['email'] = df['email'].astype(str).replace('nan', '')
        return df
    except: return pd.DataFrame(columns=['id', 'nume', 'telefon', 'email', 'camera', 'checkin', 'checkout', 'status', 'pret_total', 'note'])

def update_data(df):
    try:
        df_s = df.copy()
        df_s['checkin'] = df_s['checkin'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_s['checkout'] = df_s['checkout'].dt.strftime('%Y-%m-%d %H:%M:%S')
        conn.update(worksheet="Rezervari", data=df_s)
        st.cache_data.clear() # Clear cache la update
    except Exception as e: st.error(str(e))

def este_disponibila(df, camera, start, end):
    if df.empty: return True
    mask = (df['status'] != 'Anulat') & (df['camera'] == camera)
    conflict = mask & ~( (df['checkout'] <= start) | (df['checkin'] >= end) )
    return df[conflict].empty

# --- PDF GENERATOR (2 PAGINI) ---
def genereaza_pdf_bytes(r):
    pdf = FPDF(); pdf.add_page()
    if os.path.exists("LOGO final.png"): pdf.image("LOGO final.png", x=10, y=8, w=30); pdf.ln(20)
    
    # Pagina 1
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "CONFIRMARE REZERVARE", ln=True, align='C'); pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"ID Rezervare: {r['id']}", ln=True)
    pdf.cell(0, 10, f"Client: {r['nume']}", ln=True)
    pdf.cell(0, 10, f"Email: {r.get('email', '-')}", ln=True)
    pdf.cell(0, 10, f"Telefon: {r['telefon']}", ln=True)
    pdf.cell(0, 10, f"Camera: {r['camera']}", ln=True)
    try: d1, d2 = r['checkin'].strftime('%d-%m-%Y'), r['checkout'].strftime('%d-%m-%Y')
    except: d1, d2 = str(r['checkin']), str(r['checkout'])
    pdf.cell(0, 10, f"Perioada: {d1} -> {d2}", ln=True)
    pdf.ln(5); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, f"Total de Plata: {r['pret_total']} RON", ln=True)
    if pd.notna(r['note']) and r['note']: pdf.ln(5); pdf.set_font("Arial", '', 10); pdf.multi_cell(0, 10, f"Note: {r['note']}")

    pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
    
    # Pagina 2 (Merge)
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

# --- EMAIL SENDER ---
def trimite_email_cu_pdf(destinatar, r, pdf_bytes):
    try:
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        sender_email = st.secrets["email"]["sender_email"]
        sender_password = st.secrets["email"]["sender_password"]

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = destinatar
        msg['Subject'] = f"Confirmare Rezervare Elia - {r['nume']}"

        body = f"Buna ziua {r['nume']},\n\nVa multumim pentru rezervare!\nAtasat gasiti confirmarea si regulamentul.\n\nEchipa Elia"
        msg.attach(MIMEText(body, 'plain'))

        part = MIMEApplication(pdf_bytes, Name=f"Rezervare_{r['id']}.pdf")
        part['Content-Disposition'] = f'attachment; filename="Rezervare_{r["id"]}.pdf"'
        msg.attach(part)

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True, "Email trimis!"
    except Exception as e: return False, f"Eroare: {str(e)}"

# ==========================================
# 3. INTERFAȚĂ PRINCIPALĂ
# ==========================================
if os.path.exists("LOGO final.png"): st.sidebar.image("LOGO final.png", use_container_width=True)
st.sidebar.markdown("### 🏔️ Elia PMS")
if st.sidebar.button("✨ Rezervare Nouă", use_container_width=True, type="primary"): st.session_state['show_add_modal'] = True
menu = {"📅 Harta": "Harta", "🗓️ Calendar": "Calendar", "📊 Statistici": "Statistici", "📋 Registru": "Lista"}
choice = st.sidebar.radio("Meniu", list(menu.keys()), format_func=lambda x: x)
sel_page = menu[choice]
df_master = get_data_cached()

# ==========================================
# 4. MODAL ADĂUGARE
# ==========================================
if st.session_state.get('show_add_modal', False):
    st.markdown("---")
    with st.container():
        st.markdown("<div class='info-card'><h3>✨ Adaugă Rezervare</h3>", unsafe_allow_html=True)
        with st.form("quick_add"):
            c1, c2 = st.columns(2)
            nume = c1.text_input("Nume", placeholder="Client")
            tel = c2.text_input("Tel", placeholder="07xx")
            c_email, c_cam = st.columns(2)
            email_client = c_email.text_input("Email", placeholder="client@email.com")
            cam = c_cam.selectbox("Cameră", list(CAMERE_INFO.keys()) + ["Toate"])
            d1 = c1.date_input("In", date.today()); d2 = c2.date_input("Out", date.today()+timedelta(1))
            pret = st.number_input("Preț Total", value=float(sum(CAMERE_INFO.values()) if "Toate" in cam else CAMERE_INFO.get(cam, 0)))
            note = st.text_area("Note")
            
            if st.form_submit_button("🚀 Salvează"):
                t1, t2 = datetime.combine(d1, time(15,0)), datetime.combine(d2, time(11,0))
                cms = list(CAMERE_INFO.keys()) if "Toate" in cam else [cam]
                if all(este_disponibila(df_master, c, t1, t2) for c in cms):
                    new_rows = []
                    max_id = df_master['id'].max() if not df_master.empty else 0
                    created_reservations = []
                    for i, cn in enumerate(cms):
                        new_r = {"id": int(max_id+1+i), "nume": nume, "telefon": tel, "email": email_client, "camera": cn, "checkin": t1, "checkout": t2, "status": "Confirmat", "pret_total": pret/len(cms), "note": note}
                        new_rows.append(new_r); created_reservations.append(new_r)
                    
                    update_data(pd.concat([df_master, pd.DataFrame(new_rows)], ignore_index=True))
                    
                    # Trimitere Email Automat
                    email_msg = ""
                    if email_client and "@" in email_client:
                        with st.spinner("Trimit email..."):
                            pdf_bytes = genereaza_pdf_bytes(created_reservations[0])
                            r_mail = created_reservations[0].copy()
                            if len(created_reservations) > 1: r_mail['camera'] = "Grup (Toate)"; r_mail['pret_total'] = pret
                            ok, msg = trimite_email_cu_pdf(email_client, r_mail, pdf_bytes)
                            email_msg = f" | {msg}"

                    st.session_state['show_add_modal'] = False; st.toast(f"Salvat!{email_msg}"); st.rerun()
                else: st.error("Perioada este ocupată!")
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

    html = '<div class="scroll-container"><table class="custom-table"><thead><tr><th class="first-col">Cam</th>'
    for d in zile: html += f'<th>{d.strftime("%d")}<br>{d.strftime("%b")}</th>'
    html += '</tr></thead><tbody>'
    for cam in CAMERE_INFO.keys():
        html += f'<tr><td class="first-col">{cam}</td>'
        for d in zile:
            if df_v.empty: html += '<td><div class="bg-liber"></div></td>'; continue
            r_out = df_v[(df_v['camera']==cam) & (df_v['co']==d)]; r_in = df_v[(df_v['camera']==cam) & (df_v['ci']==d)]; r_stay = df_v[(df_v['camera']==cam) & (df_v['ci']<d) & (df_v['co']>d)]
            bg, lbl = "bg-liber", ""
            if not r_out.empty and not r_in.empty: bg, lbl = "bg-schimb", f"{int(r_out.iloc[0]['id'])}↔{int(r_in.iloc[0]['id'])}"
            elif not r_out.empty: bg, lbl = "bg-checkout", str(int(r_out.iloc[0]['id']))
            elif not r_in.empty: bg, lbl = "bg-checkin", str(int(r_in.iloc[0]['id']))
            elif not r_stay.empty: bg, lbl = "bg-ocupat", str(int(r_stay.iloc[0]['id']))
            if bg == "bg-liber": html += f'<td><div class="{bg}"></div></td>'
            else: html += f'<td><div class="calendar-box {bg}">{lbl}</div></td>'
        html += '</tr>'
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

    # CĂUTARE & EDITARE
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='info-card'>", unsafe_allow_html=True)
        c1, c2 = st.columns([1, 2])
        search_id = c1.number_input("🔎 Caută ID (Tastatură):", min_value=0, step=1, value=0)
        
        if search_id > 0 and not df_master.empty:
            found = df_master[df_master['id'] == search_id]
            if not found.empty:
                r = found.iloc[0]
                st.markdown(f"### 👤 {r['nume']}") 
                st.markdown(f"**Cam:** {r['camera']} | **{r['checkin'].strftime('%d.%m')} - {r['checkout'].strftime('%d.%m')}**")
                
                # ZONA DE EDITARE
                with st.expander("✏️ Editează / Modifică Datele", expanded=False):
                    with st.form(key=f"e_{r['id']}"):
                        ce1, ce2 = st.columns(2)
                        nn = ce1.text_input("Nume", r['nume']); nt = ce2.text_input("Tel", r['telefon'])
                        ne = ce1.text_input("Email", r.get('email', '')); np = ce2.number_input("Pret", value=float(r['pret_total']))
                        nno = st.text_area("Note", r['note'])
                        if st.form_submit_button("💾 Salvează"):
                            idx = df_master[df_master['id'] == r['id']].index[0]
                            df_master.at[idx,'nume']=nn; df_master.at[idx,'telefon']=nt; df_master.at[idx,'email']=ne; df_master.at[idx,'pret_total']=np; df_master.at[idx,'note']=nno
                            update_data(df_master); st.toast("Actualizat!"); st.rerun()

                # BUTOANE ACȚIUNE
                col_act1, col_act2 = st.columns(2)
                pdf_bytes = genereaza_pdf_bytes(r)
                
                col_act1.download_button("📄 Descarcă PDF", data=pdf_bytes, file_name=f"Rez_{r['id']}.pdf", mime="application/pdf", use_container_width=True)
                if col_act1.button("📧 Email Manual", use_container_width=True):
                    if r.get('email') and "@" in str(r['email']):
                        with st.spinner("Trimit..."):
                            ok, msg = trimite_email_cu_pdf(r['email'], r, pdf_bytes)
                            if ok: st.success(msg)
                            else: st.error(msg)
                    else: st.error("Fără email!")

                msg_t = f"Salut {r['nume']}, confirmare rezervare Elia.\nCamera: {r['camera']}\nInterval: {r['checkin'].strftime('%d.%m')} - {r['checkout'].strftime('%d.%m')}\nTotal: {r['pret_total']} RON.\nTe rog sa descarci PDF-ul din telefon."
                wa = urllib.parse.quote(msg_t)
                col_act2.markdown(f'<a href="https://api.whatsapp.com/send?phone={r["telefon"]}&text={wa}" target="_blank"><button style="width:100%;background:#25D366;color:white;border:none;padding:10px;border-radius:5px;font-weight:bold;height:38px;margin-bottom:15px">💬 WhatsApp</button></a>', unsafe_allow_html=True)
                if col_act2.button("🗑️ Sterge", use_container_width=True):
                    df_master = df_master[df_master['id'] != r['id']]; update_data(df_master); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 6. CALENDAR & STATISTICI
# ==========================================
elif sel_page == "Calendar":
    st.markdown("### 🗓️ Calendar")
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

elif sel_page == "Statistici":
    st.markdown("### 📊 Statistici")
    if not df_master.empty:
        df_s = df_master[df_master['status'] != 'Anulat'].copy()
        occ_dates = []
        for _, row in df_s.iterrows(): occ_dates.extend(pd.date_range(row['checkin'], row['checkout'] - timedelta(days=1)))
        
        df_stats = pd.DataFrame()
        if occ_dates:
            s = pd.Series(occ_dates); occ = s.groupby(s.dt.to_period("M")).count()
            data = [{"Luna": p.strftime("%b %Y"), "Grad %": round((n/(p.days_in_month*6))*100,1)} for p,n in occ.items()]
            df_stats = pd.DataFrame(data)

        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='info-card'><h2 style='color:#059669;margin:0'>{df_s['pret_total'].sum():,.0f} RON</h2><small>Total</small></div>", unsafe_allow_html=True)
        avg = df_stats["Grad %"].mean() if not df_stats.empty else 0
        c2.markdown(f"<div class='info-card'><h2 style='color:#2563eb;margin:0'>{avg:.1f}%</h2><small>Grad Mediu</small></div>", unsafe_allow_html=True)
        if not df_stats.empty: st.bar_chart(df_stats.set_index("Luna")); df_s['l'] = df_s['checkin'].dt.strftime('%Y-%m'); st.bar_chart(df_s.groupby('l')['pret_total'].sum())
    else: st.info("Fără date.")

elif sel_page == "Lista":
    st.markdown("### 📋 Registru")
    if not df_master.empty: st.dataframe(df_master[['id','nume','camera','checkin','pret_total']].sort_values(by='checkin', ascending=False), use_container_width=True)
