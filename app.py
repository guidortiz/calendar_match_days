import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, timedelta
from fpdf import FPDF
import base64
import requests

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Calendario Logística | Adidas", layout="wide", page_icon="📅")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    
    .day-cell {
        border: 1px solid #d1d1d1;
        background-color: white;
        height: 140px;
        padding: 8px;
        border-radius: 4px;
        position: relative;
    }
    
    .day-number {
        font-size: 1.2rem;
        font-weight: 700;
        color: #333;
        margin-bottom: 5px;
    }

    .event-capsule {
        display: block;
        padding: 4px 6px;
        margin-top: 4px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .header-cell {
        background-color: #000;
        color: white;
        padding: 10px;
        text-align: center;
        font-weight: bold;
        border-radius: 4px 4px 0 0;
        margin-bottom: 5px;
    }
    
    .bg-match { background-color: #000; } 
    .bg-restock { background-color: #555; }
    .day-empty { background-color: #f9f9f9; border: none; }
    </style>
""", unsafe_allow_html=True)

# --- 1. CARGA DE DATOS (FOTMOB + BACKUP) ---
def load_data():
    data = []
    
    # IDs de FotMob: River (10206), Boca (10205)
    equipos_busqueda = [
        {"id": 10206, "nombre": "River Plate"},
        {"id": 10205, "nombre": "Boca Juniors"}
    ]
    
    print("--- INICIANDO CONSULTA A FOTMOB ---")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    partidos_procesados = set() # Para evitar duplicar el Superclásico
    api_success = False

    for equipo_info in equipos_busqueda:
        try:
            # Endpoint público de FotMob
            url = f"https://www.fotmob.com/api/teams?id={equipo_info['id']}&ccode3=ARG"
            
            response = requests.get(url, headers=headers, timeout=4)
            
            if response.status_code == 200:
                json_data = response.json()
                fixtures = json_data.get("fixtures", [])
                
                print(f"API: Analizando {len(fixtures)} partidos de {equipo_info['nombre']}...")

                for match in fixtures:
                    # Buscamos fecha. FotMob usa formato ISO UTC (ej: 2026-02-15T19:00:00.000Z)
                    fecha_raw = match.get("status", {}).get("utcTime") 
                    
                    # Filtro simple: Que contenga "2026"
                    if fecha_raw and "2026" in fecha_raw:
                        fecha = fecha_raw.split("T")[0]
                        match_id = match.get("id")
                        
                        # Evitar duplicados
                        if match_id not in partidos_procesados:
                            home_name = match.get("home", {}).get("name")
                            away_name = match.get("away", {}).get("name")
                            
                            # Definir quién es el equipo principal y quién el rival
                            # (Para que en el calendario diga "VS Rival")
                            if "River" in home_name or "Boca" in home_name:
                                # Si el local es uno de los nuestros
                                if home_name == equipo_info['nombre'] or (equipo_info['nombre'] in home_name):
                                    mi_equipo = home_name
                                    rival = away_name
                                else:
                                    mi_equipo = away_name
                                    rival = home_name
                            else:
                                # Caso raro, asumimos por la búsqueda actual
                                mi_equipo = equipo_info['nombre']
                                rival = away_name if home_name == mi_equipo else home_name

                            data.append({
                                "fecha": fecha,
                                "equipo": mi_equipo,
                                "rival": rival,
                                "torneo": match.get("league", {}).get("name", "Liga")
                            })
                            partidos_procesados.add(match_id)
                            api_success = True
            else:
                print(f"API Error con {equipo_info['nombre']}: {response.status_code}")
                
        except Exception as e:
            print(f"API Excepción: {e}")

    # --- PLAN B: BACKUP MANUAL ---
    # Si la API no trajo NADA del 2026 (común en pretemporada), usamos esto.
    if not api_success or len(data) == 0:
        print("⚠️ API sin datos 2026. Cargando backup manual.")
        st.toast("Usando datos manuales (API sin fixture 2026 aún).", icon="ℹ️")
        
        backup_fixtures = [
            {"fecha": "2026-01-28", "equipo": "Boca Juniors", "rival": "Gimnasia (Backup)", "torneo": "Liga"},
            {"fecha": "2026-02-04", "equipo": "River Plate", "rival": "Talleres (Backup)", "torneo": "Liga"},
            {"fecha": "2026-02-15", "equipo": "River Plate", "rival": "Boca Juniors (Backup)", "torneo": "Superclásico"},
            {"fecha": "2026-03-01", "equipo": "Boca Juniors", "rival": "Independiente (Backup)", "torneo": "Liga"},
            {"fecha": "2026-03-08", "equipo": "River Plate", "rival": "Racing (Backup)", "torneo": "Liga"},
        ]
        data.extend(backup_fixtures)
    else:
        print(f"✅ Éxito: Se cargaron {len(data)} partidos desde FotMob.")

    # Convertir a DataFrame
    df = pd.DataFrame(data)
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha'])
        df = df.sort_values(by='fecha')
    
    return df

# --- 2. LÓGICA DE EVENTOS ---
def get_events(date, df_partidos):
    events = []
    if df_partidos.empty: return events

    # Partido Hoy
    partido_hoy = df_partidos[df_partidos['fecha'] == date]
    for _, row in partido_hoy.iterrows():
        events.append({
            "text_web": f"⚽ VS {row['rival']}",
            "text_pdf": f"VS {row['rival']}",
            "type": "match", 
            "class": "bg-match", 
            "rgb": (0, 0, 0)
        })
    
    # Reposición (2 días antes)
    fecha_futura = date + timedelta(days=2)
    partido_futuro = df_partidos[df_partidos['fecha'] == fecha_futura]
    for _, row in partido_futuro.iterrows():
        events.append({
            "text_web": f"📦 REPONER ({row['equipo']})",
            "text_pdf": f"REPONER ({row['equipo']})",
            "type": "restock", 
            "class": "bg-restock", 
            "rgb": (80, 80, 80)
        })
        
    return events

# --- 3. GENERADOR DE PDF ---
def create_pdf(year, month, df_partidos):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(False)
    pdf.add_page()
    
    # Título
    pdf.set_font("Arial", 'B', 20)
    month_name = calendar.month_name[month]
    title = f"PLANIFICACION LOGISTICA - {month_name.upper()} {year}"
    pdf.cell(0, 15, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(2)
    
    cal = calendar.monthcalendar(year, month)
    num_weeks = len(cal)
    
    available_height = 165
    row_h = available_height / num_weeks 
    
    dias = ["LUN", "MAR", "MIE", "JUE", "VIE", "SAB", "DOM"]
    col_w = 39
    
    # Cabecera
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(220, 220, 220) 
    pdf.set_text_color(0, 0, 0)
    for dia in dias:
        pdf.cell(col_w, 8, dia, border=1, align='C', fill=True)
    pdf.ln()
    
    # Cuerpo
    for week in cal:
        y_start = pdf.get_y()
        x_start = pdf.get_x()
        
        for i, day in enumerate(week):
            current_x = x_start + (i * col_w)
            pdf.set_xy(current_x, y_start)
            
            if day == 0:
                pdf.set_fill_color(250, 250, 250)
                pdf.cell(col_w, row_h, "", border=1, fill=True)
            else:
                pdf.set_fill_color(255, 255, 255)
                pdf.cell(col_w, row_h, "", border=1, fill=True)
                
                pdf.set_font("Arial", 'B', 16)
                pdf.set_text_color(0, 0, 0)
                pdf.text(current_x + 2, y_start + 7, str(day))
                
                current_date = datetime(year, month, day)
                events = get_events(current_date, df_partidos)
                
                if events:
                    event_y = y_start + row_h - 7 
                    for event in events:
                        r, g, b = event['rgb']
                        pdf.set_fill_color(r, g, b)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_font("Arial", 'B', 8)
                        pdf.set_xy(current_x + 1, event_y)
                        safe_text = event['text_pdf'].encode('latin-1', 'replace').decode('latin-1')
                        pdf.cell(col_w - 2, 6, safe_text, border=0, ln=1, align='C', fill=True)
                        event_y -= 7

        pdf.set_xy(x_start, y_start + row_h)
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. INTERFAZ ---
def main():
    st.title("🚛 Dashboard de Logística")
    
    # Cargamos datos (API o Backup)
    df = load_data()
    
    with st.sidebar:
        st.header("Configuración")
        selected_year = st.number_input("Año", value=2026, step=1)
        selected_month_name = st.selectbox("Mes", list(calendar.month_name)[1:])
        selected_month = list(calendar.month_name).index(selected_month_name)
        st.divider()
        
        try:
            pdf_bytes = create_pdf(selected_year, selected_month, df)
            b64 = base64.b64encode(pdf_bytes).decode()
            filename = f"Planificacion_{selected_month_name}_{selected_year}.pdf"
            
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}" style="text-decoration:none;">'
            href += f'<button style="width:100%; padding:15px; background-color:#000; color:white; border:none; border-radius:4px; font-weight:bold; cursor:pointer;">🖨️ IMPRIMIR PDF (1 HOJA)</button></a>'
            st.markdown(href, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error generando PDF: {e}")

    # Vista Web
    st.subheader(f"Vista: {selected_month_name} {selected_year}")
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    cols = st.columns(7)
    for i, dia in enumerate(dias):
        cols[i].markdown(f"<div class='header-cell'>{dia}</div>", unsafe_allow_html=True)
    
    cal = calendar.monthcalendar(selected_year, selected_month)
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].markdown("<div
