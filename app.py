import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, timedelta
from fpdf import FPDF
import base64
import requests  # <--- NUEVA LIBRERÍA NECESARIA

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Calendario Logística | Adidas", layout="wide", page_icon="📅")

# --- ESTILOS CSS (VISTA WEB) ---
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

# --- 1. DATOS (INTEGRACIÓN API) ---
def load_data():
    # A. Datos Manuales (Ej: Selección o eventos especiales fuera de la liga)
    data = [
        {"fecha": "2026-03-10", "equipo": "AFA (Seleccion)", "rival": "Brasil", "torneo": "Eliminatorias"},
    ]
    
    # B. Integración TheSportsDB API
    # ID Liga Argentina: 4351
    # API Key Test Gratuita: 3
    api_key = "3" 
    league_id = "4351"
    season = "2026" # Ojo: Si la API aún no tiene el 2026 cargado, no traerá datos.
    
    url = f"https://www.thesportsdb.com/api/v1/json/{api_key}/eventsseason.php?id={league_id}&s={season}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            result = response.json()
            events = result.get('events') # Puede ser None si no hay datos
            
            if events:
                target_teams = ["River Plate", "Boca Juniors"]
                
                for match in events:
                    home_team = match.get('strHomeTeam', '')
                    away_team = match.get('strAwayTeam', '')
                    date_event = match.get('dateEvent', '')
                    
                    # Filtramos si juega River o Boca
                    if home_team in target_teams or away_team in target_teams:
                        
                        # Definimos cual es "nuestro equipo" para mostrar primero
                        if home_team in target_teams:
                            equipo_principal = home_team
                            rival = away_team
                        else:
                            equipo_principal = away_team
                            rival = home_team
                            
                        # Agregamos a la lista de datos
                        data.append({
                            "fecha": date_event,
                            "equipo": equipo_principal,
                            "rival": rival,
                            "torneo": "Liga Profesional"
                        })
            # Si 'events' es None, simplemente no agrega nada (sin error)
    except Exception as e:
        # Si falla la conexión, mostramos un aviso discreto en la consola/app pero cargamos lo manual
        print(f"Error conectando a API: {e}")
        st.toast("⚠️ No se pudo sincronizar con la API de deportes (verificar conexión o temporada).", icon="⚠️")

    # C. Convertir a DataFrame
    df = pd.DataFrame(data)
    df['fecha'] = pd.to_datetime(df['fecha'])
    return df

# --- 2. LÓGICA DE EVENTOS ---
def get_events(date, df_partidos):
    events = []
    # Partido Hoy
    partido_hoy = df_partidos[df_partidos['fecha'] == date]
    for _, row in partido_hoy.iterrows():
        events.append({
            "text_web": f"⚽ VS {row['rival']}",
            "text_pdf": f"VS {row['rival']}",
            "type": "match", 
            "class": "bg-match", 
            "rgb": (0, 0, 0) # NEGRO PURO
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
            "rgb": (80, 80, 80) # GRIS OSCURO
        })
        
    return events

# --- 3. GENERADOR DE PDF (FIX: ESCALADO DINÁMICO) ---
def create_pdf(year, month, df_partidos):
    # Configuración A4 Landscape
    # Alto total A4 = 210mm. Márgenes seguros ~10mm. Espacio útil ~190mm.
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(False) # IMPORTANTÍSIMO: Evita que salte de página solo
    pdf.add_page()
    
    # Título
    pdf.set_font("Arial", 'B', 20)
    month_name = calendar.month_name[month]
    title = f"PLANIFICACION LOGISTICA - {month_name.upper()} {year}"
    pdf.cell(0, 15, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(2) # Pequeño espacio
    
    cal = calendar.monthcalendar(year, month)
    num_weeks = len(cal) # Puede ser 5 o 6 semanas
    
    # CÁLCULO DINÁMICO DE ALTURA
    # Espacio disponible vertical aprox: 190mm - 25mm (titulo/header) = 165mm
    # Dividimos el espacio por la cantidad de semanas
    available_height = 165
    row_h = available_height / num_weeks 
    
    dias = ["LUN", "MAR", "MIE", "JUE", "VIE", "SAB", "DOM"]
    col_w = 39 # Ancho fijo columna
    
    # Cabecera Gris
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(220, 220, 220) 
    pdf.set_text_color(0, 0, 0)
    for dia in dias:
        pdf.cell(col_w, 8, dia, border=1, align='C', fill=True)
    pdf.ln()
    
    # Cuerpo del calendario
    for week in cal:
        y_start = pdf.get_y()
        x_start = pdf.get_x()
        
        for i, day in enumerate(week):
            current_x = x_start + (i * col_w)
            pdf.set_xy(current_x, y_start)
            
            if day == 0:
                # Celda vacía (Gris muy suave)
                pdf.set_fill_color(250, 250, 250)
                pdf.cell(col_w, row_h, "", border=1, fill=True)
            else:
                # 1. Celda BLANCA limpia
                pdf.set_fill_color(255, 255, 255)
                pdf.cell(col_w, row_h, "", border=1, fill=True)
                
                # 2. Número del día (Arriba Izquierda, Grande)
                pdf.set_font("Arial", 'B', 16) # Aumenté a 16 para que se vea bien grande
                pdf.set_text_color(0, 0, 0)
                pdf.text(current_x + 2, y_start + 7, str(day))
                
                # 3. Eventos
                current_date = datetime(year, month, day)
                events = get_events(current_date, df_partidos)
                
                if events:
                    # Posicionamos eventos pegados al fondo de la celda
                    # row_h - 7mm deja espacio justo
                    event_y = y_start + row_h - 7 
                    
                    for event in events:
                        r, g, b = event['rgb']
                        pdf.set_fill_color(r, g, b)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_font("Arial", 'B', 8)
                        
                        pdf.set_xy(current_x + 1, event_y)
                        safe_text = event['text_pdf'].encode('latin-1', 'replace').decode('latin-1')
                        
                        # Celda del evento
                        pdf.cell(col_w - 2, 6, safe_text, border=0, ln=1, align='C', fill=True)
                        
                        # Si hay más de uno, subimos
                        event_y -= 7

        # Bajar a la siguiente fila
        pdf.set_xy(x_start, y_start + row_h)
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. INTERFAZ ---
def main():
    st.title("🚛 Dashboard de Logística")
    
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
            st.error(f"Error: {e}")

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
                cols[i].markdown("<div class='day-cell day-empty'></div>", unsafe_allow_html=True)
            else:
                current_date = datetime(selected_year, selected_month, day)
                events = get_events(current_date, df)
                html_events = ""
                for e in events:
                    html_events += f"<div class='event-capsule {e['class']}'>{e['text_web']}</div>"
                
                cell_html = f"""
                <div class='day-cell'>
                    <div class='day-number'>{day}</div>
                    {html_events}
                </div>
                """
                cols[i].markdown(cell_html, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
