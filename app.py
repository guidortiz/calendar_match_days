import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Calendario Logística | Adidas", layout="wide", page_icon="📅")

# --- ESTILOS CSS (Para que se vea profesional y limpio) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stApp { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    
    /* Estilo de las tarjetas del calendario */
    .day-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        height: 140px; /* Altura fija para uniformidad */
        background-color: white;
        transition: transform 0.2s;
        margin-bottom: 10px;
    }
    .day-card:hover { transform: scale(1.02); box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    
    /* Indicadores */
    .date-num { font-weight: bold; font-size: 1.2em; color: #333; margin-bottom: 5px; }
    .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: 600; display: block; margin-top: 4px; color: white; }
    
    /* Colores de Estado */
    .match-day { background-color: #e63946; } /* Rojo River/Intenso */
    .restock-day { background-color: #2a9d8f; } /* Verde Operativo */
    .boca { background-color: #003087; } /* Azul Boca */
    .river { background-color: #e63946; } /* Rojo River */
    .afa { background-color: #74acdf; } /* Celeste AFA */
    </style>
""", unsafe_allow_html=True)

# --- 1. DATOS (Simulados - Esto luego lo podés conectar a tu Excel) ---
# Aquí cargamos los partidos. En el futuro, esto puede leer un pd.read_excel('partidos.xlsx')
def load_data():
    data = [
        {"fecha": "2026-02-15", "equipo": "River Plate", "rival": "Boca Juniors", "torneo": "Liga Profesional"},
        {"fecha": "2026-02-22", "equipo": "Boca Juniors", "rival": "Independiente", "torneo": "Liga Profesional"},
        {"fecha": "2026-03-10", "equipo": "AFA (Selección)", "rival": "Brasil", "torneo": "Eliminatorias"},
        {"fecha": "2026-02-04", "equipo": "River Plate", "rival": "Banfield", "torneo": "Liga Profesional"},
    ]
    df = pd.DataFrame(data)
    df['fecha'] = pd.to_datetime(df['fecha'])
    return df

# --- 2. LÓGICA DE LOGÍSTICA ---
def get_logistics_status(date, df_partidos):
    """Determina si un día es de partido, de reposición o normal."""
    
    # Buscar si hay partido hoy
    partido_hoy = df_partidos[df_partidos['fecha'] == date]
    
    # Buscar si hay partido en 2 días (Día de Reposición)
    fecha_futura = date + timedelta(days=2)
    partido_futuro = df_partidos[df_partidos['fecha'] == fecha_futura]
    
    events = []
    
    # Lógica Partido
    if not partido_hoy.empty:
        for _, row in partido_hoy.iterrows():
            events.append({
                "type": "PARTIDO",
                "text": f"⚽ vs {row['rival']}",
                "team": row['equipo'],
                "color": "match-day"
            })
            
    # Lógica Reposición (2 días antes)
    if not partido_futuro.empty:
        for _, row in partido_futuro.iterrows():
            events.append({
                "type": "REPOSICIÓN",
                "text": f"📦 Reponer p/ {row['equipo']}",
                "team": "Logística",
                "color": "restock-day"
            })
            
    return events

# --- 3. INTERFAZ GRÁFICA ---
def main():
    st.title("🚛 Logística & Calendario Deportivo")
    st.markdown("**Herramienta de planificación de stock basada en cronograma AFA/Clubes.**")
    
    df = load_data()
    
    # Controles en barra lateral
    with st.sidebar:
        st.header("Configuración")
        selected_year = st.number_input("Año", value=2026, step=1)
        selected_month = st.selectbox("Mes", list(calendar.month_name)[1:], index=1) # Empieza en Febrero por defecto
        
        month_idx = list(calendar.month_name).index(selected_month)
        
        st.divider()
        st.info("💡 **Guía de Colores:**\n\n🟢 **Verde:** Reposición Obligatoria\n🔴 **Rojo:** Día de Partido (Bloqueado)")
        
        # Botón de "Imprimir" (Simulación)
        if st.button("🖨️ Generar Reporte PDF"):
            st.toast("Generando PDF para imprimir... (Funcionalidad pendiente de integrar libreria fpdf)")

    # Encabezado del Mes
    st.subheader(f"📅 {selected_month} {selected_year}")

    # Estructura del Calendario Semanal
    cal = calendar.monthcalendar(selected_year, month_idx)
    dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    
    # Renderizar encabezados de días
    cols = st.columns(7)
    for idx, dia in enumerate(dias_semana):
        cols[idx].markdown(f"<div style='text-align:center; font-weight:bold; color:#555;'>{dia}</div>", unsafe_allow_html=True)

    # Renderizar días
    for week in cal:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day == 0:
                cols[idx].markdown("<div class='day-card' style='background-color:#f0f2f6; border:none;'></div>", unsafe_allow_html=True)
                continue
            
            current_date = datetime(selected_year, month_idx, day)
            events = get_logistics_status(current_date, df)
            
            # Construir HTML de la tarjeta
            html_content = f"""
            <div class='day-card'>
                <div class='date-num'>{day}</div>
            """
            
            for event in events:
                html_content += f"<div class='badge {event['color']}'>{event['text']}</div>"
                
            html_content += "</div>"
            
            cols[idx].markdown(html_content, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
