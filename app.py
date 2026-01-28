import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Calendario Logística | Adidas", layout="wide", page_icon="📅")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stApp { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    .day-card {
        border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px;
        height: 140px; background-color: white; margin-bottom: 10px;
    }
    .date-num { font-weight: bold; font-size: 1.2em; color: #333; }
    .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: 600; display: block; margin-top: 4px; color: white; }
    .match-day { background-color: #e63946; } 
    .restock-day { background-color: #2a9d8f; } 
    </style>
""", unsafe_allow_html=True)

# --- 1. DATOS ---
def load_data():
    # Aca podes agregar más partidos
    data = [
        {"fecha": "2026-03-10", "equipo": "AFA (Selección)", "rival": "Brasil", "torneo": "Eliminatorias"},
        {"fecha": "2026-03-15", "equipo": "River Plate", "rival": "Boca Juniors", "torneo": "Liga"},
        {"fecha": "2026-03-22", "equipo": "Boca Juniors", "rival": "Racing", "torneo": "Liga"},
        {"fecha": "2026-02-15", "equipo": "River Plate", "rival": "Boca Juniors", "torneo": "Amistoso"},
    ]
    df = pd.DataFrame(data)
    df['fecha'] = pd.to_datetime(df['fecha'])
    return df

# --- 2. LÓGICA LOGÍSTICA ---
def get_logistics_status(date, df_partidos):
    partido_hoy = df_partidos[df_partidos['fecha'] == date]
    fecha_futura = date + timedelta(days=2) # Reposición 2 días antes
    partido_futuro = df_partidos[df_partidos['fecha'] == fecha_futura]
    
    events = []
    if not partido_hoy.empty:
        for _, row in partido_hoy.iterrows():
            events.append({"type": "PARTIDO", "text": f"VS {row['rival']}", "color_pdf": (230, 57, 70), "css": "match-day"}) # Rojo
            
    if not partido_futuro.empty:
        for _, row in partido_futuro.iterrows():
            events.append({"type": "REPOSICIÓN", "text": f"REPONER ({row['equipo']})", "color_pdf": (42, 157, 143), "css": "restock-day"}) # Verde
            
    return events

# --- 3. GENERADOR DE PDF ---
def create_pdf(year, month, df_data):
    # Configuración A4 Horizontal (Landscape)
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # Título
    month_name = calendar.month_name[month]
    pdf.cell(0, 10, f"Planificacion Logistica - {month_name} {year}", ln=True, align='C')
    pdf.ln(5)
    
    # Configuración de la grilla
    cal = calendar.monthcalendar(year, month)
    dias_semana = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
    
    # Anchos y Altos (A4 Landscape es aprox 297mm ancho)
    col_width = 38 
    row_height = 30 
    
    pdf.set_font("Arial", 'B', 10)
    
    # Encabezados (Lunes, Martes...)
    for dia in dias_semana:
        pdf.cell(col_width, 8, dia, border=1, align='C', fill=False)
    pdf.ln()
    
    # Días
    pdf.set_font("Arial", '', 8)
    
    for week in cal:
        # Primera pasada: Dibujar celdas y números
        # Guardamos la posición Y actual
        y_start = pdf.get_y()
        x_start = pdf.get_x()
        
        for i, day in enumerate(week):
            # Movernos a la posición correcta de la columna
            pdf.set_xy(x_start + (i * col_width), y_start)
            
            if day == 0:
                # Día vacío (mes anterior/siguiente)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(col_width, row_height, "", border=1, fill=True)
            else:
                current_date = datetime(year, month, day)
                events = get_logistics_status(current_date, df_data)
                
                # Si hay eventos, pintar el fondo del PRIMER evento importante
                fill = False
                if events:
                    fill = True
                    r, g, b = events[0]['color_pdf']
                    pdf.set_fill_color(r, g, b)
                else:
                    pdf.set_fill_color(255, 255, 255)

                # Celda contenedora
                pdf.cell(col_width, row_height, str(day), border=1, align='L', fill=fill)
                
                # Escribir texto del evento (superpuesto)
                if events:
                    pdf.set_xy(x_start + (i * col_width) + 1, y_start + 5)
                    pdf.set_text_color(255, 255, 255) # Texto blanco para contraste
                    pdf.set_font("Arial", 'B', 7)
                    for event in events:
                        pdf.multi_cell(col_width-2, 4, event['text'], align='C')
                    
                    # Restaurar colores
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", '', 8)

        # Bajar una fila completa
        pdf.ln(row_height)
        
    return pdf.output(dest='S').encode('latin-1')

# --- 4. MAIN APP ---
def main():
    st.title("🚛 Logística & Calendario Deportivo")
    
    df = load_data()
    
    with st.sidebar:
        st.header("Configuración")
        selected_year = st.number_input("Año", value=2026, step=1)
        months = list(calendar.month_name)[1:]
        selected_month_name = st.selectbox("Mes", months, index=2) # Default Marzo
        month_idx = months.index(selected_month_name) + 1
        
        st.divider()
        st.info("🟢 Verde: Reposición\n🔴 Rojo: Partido")
        
        # --- BOTÓN DE DESCARGA PDF ---
        if st.button("🔄 Preparar PDF"):
            pdf_bytes = create_pdf(selected_year, month_idx, df)
            st.download_button(
                label="⬇️ Descargar PDF Mensual",
                data=pdf_bytes,
                file_name=f"Logistica_{selected_month_name}_{selected_year}.pdf",
                mime="application/pdf"
            )

    # Visualización en pantalla (igual que antes)
    st.subheader(f"📅 {selected_month_name} {selected_year}")
    cal = calendar.monthcalendar(selected_year, month_idx)
    
    cols = st.columns(7)
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    for idx, dia in enumerate(dias):
        cols[idx].markdown(f"<div style='text-align:center; font-weight:bold;'>{dia}</div>", unsafe_allow_html=True)

    for week in cal:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day == 0:
                cols[idx].markdown("<div class='day-card' style='background-color:#f0f2f6; border:none;'></div>", unsafe_allow_html=True)
                continue
            
            current_date = datetime(selected_year, month_idx, day)
            events = get_logistics_status(current_date, df)
            
            html_content = f"<div class='day-card'><div class='date-num'>{day}</div>"
            for event in events:
                html_content += f"<div class='badge {event['css']}'>{event['text']}</div>"
            html_content += "</div>"
            cols[idx].markdown(html_content, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
