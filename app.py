import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, timedelta
from fpdf import FPDF
import base64

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Calendario Logística | Adidas", layout="wide", page_icon="📅")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .day-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px; height: 120px; background-color: white; }
    .match-day { background-color: #e63946; color: white; padding: 2px 5px; border-radius: 4px; font-size: 0.8em; margin-top: 5px; }
    .restock-day { background-color: #2a9d8f; color: white; padding: 2px 5px; border-radius: 4px; font-size: 0.8em; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 1. DATOS ---
def load_data():
    # Aquí podés agregar más partidos
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
        events.append({"text": f"VS {row['rival']}", "type": "match", "color": (230, 57, 70)}) # Rojo
    
    # Reposición (2 días antes)
    fecha_futura = date + timedelta(days=2)
    partido_futuro = df_partidos[df_partidos['fecha'] == fecha_futura]
    for _, row in partido_futuro.iterrows():
        events.append({"text": f"REPONER ({row['equipo']})", "type": "restock", "color": (42, 157, 143)}) # Verde
        
    return events

# --- 3. GENERADOR DE PDF (A4 HORIZONTAL - UNA HOJA) ---
def create_pdf(year, month, df_partidos):
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
    dias = ["LUN", "MAR", "MIE", "JUE", "VIE", "SAB", "DOM"]
    
    # Ancho total A4 apaisado es ~297mm. Márgenes default ~10mm. 
    # Usable ~275mm. 275 / 7 columnas = ~39mm por columna.
    col_w = 39 
    row_h = 30 # Altura de cada celda (día)
    
    # Cabecera de días
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(200, 200, 200) # Gris clarito
    for dia in dias:
        pdf.cell(col_w, 8, dia, border=1, align='C', fill=True)
    pdf.ln()
    
    # Cuerpo del calendario
    pdf.set_font("Arial", '', 8)
    
    for week in cal:
        # Guardamos la posición Y actual para volver a ella en cada celda de la fila
        y_start = pdf.get_y()
        x_start = pdf.get_x()
        
        for i, day in enumerate(week):
            # Posición actual de la celda
            current_x = x_start + (i * col_w)
            pdf.set_xy(current_x, y_start)
            
            if day == 0:
                # Celda vacía (mes anterior/siguiente)
                pdf.set_fill_color(245, 245, 245)
                pdf.cell(col_w, row_h, "", border=1, fill=True)
            else:
                current_date = datetime(year, month, day)
                events = get_events(current_date, df_partidos)
                
                # Determinamos color de fondo de la celda SI hay evento importante
                fill = False
                if events:
                    # Si hay partido es rojo, si es reposición es verde
                    if any(e['type'] == 'match' for e in events):
                        pdf.set_fill_color(255, 200, 200) # Rojo muy claro fondo
                        fill = True
                    elif any(e['type'] == 'restock' for e in events):
                        pdf.set_fill_color(200, 255, 200) # Verde muy claro fondo
                        fill = True
                
                # Dibujamos el recuadro de la celda
                pdf.cell(col_w, row_h, str(day), border=1, align='L', fill=fill)
                
                # Dibujamos los eventos DENTRO de la celda
                if events:
                    # Movemos el cursor un poco hacia adentro y abajo del número
                    pdf.set_xy(current_x + 1, y_start + 5)
                    for event in events:
                        # Cuadradito de color intenso para el texto
                        r, g, b = event['color']
                        pdf.set_fill_color(r, g, b)
                        pdf.set_text_color(255, 255, 255) # Texto blanco
                        pdf.set_font("Arial", 'B', 7)
                        
                        # Texto del evento
                        pdf.cell(col_w - 2, 5, event['text'], border=0, ln=1, align='C', fill=True)
                        
                        # Reset color texto
                        pdf.set_text_color(0, 0, 0)
            
        # Al terminar la semana, bajamos de línea con la altura de la fila
        pdf.set_xy(x_start, y_start + row_h)

    return pdf.output(dest='S').encode('latin-1')

# --- 4. INTERFAZ ---
def main():
    st.title("🚛 Logística & Calendario Deportivo")
    
    df = load_data()
    
    with st.sidebar:
        st.header("Configuración")
        selected_year = st.number_input("Año", value=2026, step=1)
        selected_month_name = st.selectbox("Mes", list(calendar.month_name)[1:])
        selected_month = list(calendar.month_name).index(selected_month_name)
        
        st.divider()
        
        # --- BOTÓN DE DESCARGA PDF ---
        # Generamos el PDF en memoria
        pdf_bytes = create_pdf(selected_year, selected_month, df)
        b64 = base64.b64encode(pdf_bytes).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="Logistica_{selected_month_name}_{selected_year}.pdf" style="text-decoration:none;">'
        href += f'<button style="width:100%; padding:10px; background-color:#FF4B4B; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">🖨️ DESCARGAR PDF (1 HOJA)</button></a>'
        st.markdown(href, unsafe_allow_html=True)

    # Vista Web (Simplificada para mostrar que funciona)
    st.subheader(f"Vista Previa: {selected_month_name} {selected_year}")
    
    cal = calendar.monthcalendar(selected_year, selected_month)
    cols = st.columns(7)
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    for i, d in enumerate(dias):
        cols[i].markdown(f"**{d}**")
        
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                current_date = datetime(selected_year, selected_month, day)
                events = get_events(current_date, df)
                
                content = f"**{day}**"
                for e in events:
                    color = "red" if e['type'] == 'match' else "green"
                    content += f"<br><span style='color:{color}; font-size:0.8em'>{e['text']}</span>"
                
                cols[i].markdown(content, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
