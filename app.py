import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, timedelta
from fpdf import FPDF
import base64

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Calendario Logística | Adidas", layout="wide", page_icon="📅")

# --- ESTILOS CSS (DISEÑO MATRIZ PROFESIONAL) ---
st.markdown("""
    <style>
    /* Estilos generales */
    .block-container { padding-top: 2rem; }
    
    /* Estilo de la Tarjeta del Día (La celda de la matriz) */
    .day-cell {
        border: 1px solid #d1d1d1; /* Borde gris consolidado */
        background-color: white;
        height: 140px; /* Altura fija para que todos sean iguales */
        padding: 8px;
        border-radius: 4px; /* Bordes levemente redondeados */
        position: relative;
        transition: all 0.2s ease;
    }
    
    .day-cell:hover {
        border-color: #000; /* Se oscurece el borde al pasar el mouse */
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        z-index: 10;
    }

    /* Número del día */
    .day-number {
        font-size: 1.2rem;
        font-weight: 700;
        color: #333;
        margin-bottom: 5px;
    }

    /* Cápsulas de eventos */
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

    /* Encabezados de Días (Lunes, Martes...) */
    .header-cell {
        background-color: #000; /* Negro Adidas */
        color: white;
        padding: 10px;
        text-align: center;
        font-weight: bold;
        border-radius: 4px 4px 0 0;
        margin-bottom: 5px;
    }
    
    /* Colores Específicos */
    .bg-match { background-color: #e63946; } /* Rojo */
    .bg-restock { background-color: #2a9d8f; } /* Verde */
    .day-empty { background-color: #f9f9f9; border: none; } /* Días de otro mes */
    </style>
""", unsafe_allow_html=True)

# --- 1. DATOS ---
def load_data():
    data = [
        {"fecha": "2026-03-10", "equipo": "AFA (Selección)", "rival": "Brasil", "torneo": "Eliminatorias"},
        {"fecha": "2026-03-15", "equipo": "Boca Juniors", "rival": "Racing", "torneo": "Liga"},
        {"fecha": "2026-03-22", "equipo": "River Plate", "rival": "Independiente", "torneo": "Liga"},
        {"fecha": "2026-02-15", "equipo": "River Plate", "rival": "Boca Juniors", "torneo": "Liga"},
    ]
    df = pd.DataFrame(data)
    df['fecha'] = pd.to_datetime(df['fecha'])
    return df

# --- 2. LÓGICA DE EVENTOS ---
def get_events(date, df_partidos):
    events = []
    # Partido Hoy
    partido_hoy = df_partidos[df_partidos['fecha'] == date]
    for _, row in partido_hoy.iterrows():
        events.append({"text": f"⚽ VS {row['rival']}", "type": "match", "class": "bg-match", "rgb": (230, 57, 70)})
    
    # Reposición (2 días antes)
    fecha_futura = date + timedelta(days=2)
    partido_futuro = df_partidos[df_partidos['fecha'] == fecha_futura]
    for _, row in partido_futuro.iterrows():
        events.append({"text": f"📦 REPONER ({row['equipo']})", "type": "restock", "class": "bg-restock", "rgb": (42, 157, 143)})
        
    return events

# --- 3. GENERADOR DE PDF (Manteniendo el que ya funciona) ---
def create_pdf(year, month, df_partidos):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    month_name = calendar.month_name[month]
    pdf.cell(0, 10, f"Planificacion Logistica - {month_name} {year}", ln=True, align='C')
    pdf.ln(5)
    
    cal = calendar.monthcalendar(year, month)
    dias = ["LUN", "MAR", "MIE", "JUE", "VIE", "SAB", "DOM"]
    col_w = 39 
    row_h = 30
    
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(220, 220, 220)
    for dia in dias:
        pdf.cell(col_w, 8, dia, border=1, align='C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 8)
    for week in cal:
        y_start = pdf.get_y()
        x_start = pdf.get_x()
        for i, day in enumerate(week):
            current_x = x_start + (i * col_w)
            pdf.set_xy(current_x, y_start)
            if day == 0:
                pdf.set_fill_color(245, 245, 245)
                pdf.cell(col_w, row_h, "", border=1, fill=True)
            else:
                current_date = datetime(year, month, day)
                events = get_events(current_date, df_partidos)
                fill = False
                if events:
                    if any(e['type'] == 'match' for e in events):
                        pdf.set_fill_color(255, 220, 220)
                        fill = True
                    elif any(e['type'] == 'restock' for e in events):
                        pdf.set_fill_color(220, 255, 220)
                        fill = True
                pdf.cell(col_w, row_h, str(day), border=1, align='L', fill=fill)
                if events:
                    pdf.set_xy(current_x + 1, y_start + 5)
                    for event in events:
                        r, g, b = event['rgb']
                        pdf.set_fill_color(r, g, b)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_font("Arial", 'B', 7)
                        pdf.cell(col_w - 2, 5, event['text'], border=0, ln=1, align='C', fill=True)
                        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(x_start, y_start + row_h)
    return pdf.output(dest='S').encode('latin-1')

# --- 4. INTERFAZ WEB PROFESIONAL ---
def main():
    st.title("🚛 Dashboard de Logística & Eventos")
    
    df = load_data()
    
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/2/20/Adidas_Logo.svg", width=100)
        st.header("Configuración")
        selected_year = st.number_input("Año", value=2026, step=1)
        selected_month_name = st.selectbox("Mes", list(calendar.month_name)[1:])
        selected_month = list(calendar.month_name).index(selected_month_name)
        st.divider()
        
        # Botón PDF
        pdf_bytes = create_pdf(selected_year, selected_month, df)
        b64 = base64.b64encode(pdf_bytes).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="Logistica_{selected_month_name}_{selected_year}.pdf" style="text-decoration:none;">'
        href += f'<button style="width:100%; padding:10px; background-color:#333; color:white; border:none; border-radius:4px; cursor:pointer;">📥 DESCARGAR PDF</button></a>'
        st.markdown(href, unsafe_allow_html=True)

    # --- MATRIZ DE CALENDARIO ---
    st.subheader(f"📅 Vista Mensual: {selected_month_name} {selected_year}")
    
    # Encabezados de columnas (Lunes, Martes...)
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    cols = st.columns(7)
    for i, dia in enumerate(dias):
        cols[i].markdown(f"<div class='header-cell'>{dia}</div>", unsafe_allow_html=True)
    
    # Filas del calendario
    cal = calendar.monthcalendar(selected_year, selected_month)
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                # Celda vacía
                cols[i].markdown("<div class='day-cell day-empty'></div>", unsafe_allow_html=True)
            else:
                # Celda con día
                current_date = datetime(selected_year, selected_month, day)
                events = get_events(current_date, df)
                
                # Construcción del HTML interno de la celda
                html_events = ""
                for e in events:
                    html_events += f"<div
