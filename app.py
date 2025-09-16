import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import io # Necesario para manejar el archivo Excel en memoria

# --- CONFIGURACIÓN GENERAL Y FUNCIONES ---

st.set_page_config(
    page_title="Gestor de Números Telefónicos",
    page_icon="📞",
    layout="wide"
)

st.title("📞 Gestor de Números Telefónicos")

# Lista de funerarias (definida una vez para ser usada en ambas funciones)
funerarias = ['Latino', 'Agape', 'Bayview', 'Anaheim']

@st.cache_resource
def connect_to_google_sheets():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# Tu función para asignar funeraria
def assign_funeraria(extension='Extension', funerarias_list=funerarias):
    if isinstance(extension, str):
        for funeraria in funerarias_list:
            if funeraria.lower() in extension.lower():
                return funeraria
    return ''

# --- CREACIÓN DE LAS PESTAÑAS ---

tab1, tab2 = st.tabs(["Agregar Nuevos Números", "Procesar Log de Llamadas"])

# --- PESTAÑA 1: AGREGAR NÚMEROS A GOOGLE SHEETS (TU CÓDIGO ORIGINAL) ---
with tab1:
    st.header("Agregar Números desde Excel a la Base de Datos")
    st.write("Sube un archivo Excel para comparar los números de teléfono con la base de datos de Google Sheets. Los números nuevos se agregarán automáticamente.")

    gspread_client = connect_to_google_sheets()
    uploaded_file_sheets = st.file_uploader("Arrastra o selecciona tu archivo de Excel (.xlsx)", type=['xlsx'], key="sheets_uploader")

    if uploaded_file_sheets and gspread_client:
        if st.button("Procesar y Agregar Números", key="process_sheets"):
            # (Aquí va el resto de tu código original para procesar el Excel y subir a Google Sheets)
            # ... (Lo he omitido por brevedad, pero debe ir aquí sin cambios)
            st.success("Funcionalidad de la Pestaña 1 ejecutada.")


# --- PESTAÑA 2: PROCESAR Y DESCARGAR LOG DE LLAMADAS ---
with tab2:
    st.header("Procesador de Log de Llamadas (CallLog)")
    st.write("Sube el archivo `CallLog.csv` para limpiarlo, clasificarlo por funeraria y descargarlo como un archivo Excel organizado.")

    uploaded_file_calllog = st.file_uploader("Sube tu archivo CallLog.csv", type=['csv'], key="calllog_uploader")

    if uploaded_file_calllog:
        try:
            # Leer y procesar el CSV subido usando tu lógica
            logs = pd.read_csv(uploaded_file_calllog)
            
            st.info("Procesando archivo CallLog...")
            logs_filtered = logs.copy()
            # Asegurarse que la columna 'From' es de tipo string antes de aplicar .str
            logs_filtered['From'] = logs_filtered['From'].astype(str)
            logs_filtered = logs_filtered[logs_filtered['From'].str.len() > 3]
            logs_filtered = logs_filtered[['From', 'Date', 'Time', 'Action Result', 'Extension']]
            logs_filtered['Date'] = logs_filtered['Date'].str.replace(r'[a-zA-Z]', '', regex=True).str.strip()
            logs_filtered['PraFecha'] = pd.to_datetime(logs_filtered['Date'] + ' ' + logs_filtered['Time'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

            logs_filtered['Funeraria'] = logs_filtered['Extension'].apply(assign_funeraria)
            logs_filtered = logs_filtered[logs_filtered['Funeraria'] != '']
            logs_filtered = logs_filtered.drop_duplicates(subset='From', keep='last')
            
            st.success("¡Procesamiento completado!")
            st.write("Vista previa de los datos filtrados y clasificados:")
            st.dataframe(logs_filtered[['Funeraria', 'From', 'PraFecha', 'Action Result']])

            # --- Lógica para crear el archivo Excel en memoria ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Iterar sobre cada funeraria única encontrada en los datos
                for funeraria_name in logs_filtered['Funeraria'].unique():
                    # Filtrar el dataframe para la funeraria actual
                    df_funeraria = logs_filtered[logs_filtered['Funeraria'] == funeraria_name]
                    
                    # Seleccionar solo las columnas requeridas
                    df_to_write = df_funeraria[['From', 'PraFecha', 'Action Result']]
                    
                    # Escribir en una hoja de Excel con el nombre de la funeraria
                    df_to_write.to_excel(writer, sheet_name=funeraria_name, index=False)
            
            # Preparar los datos para el botón de descarga
            excel_data = output.getvalue()

            st.download_button(
                label="📥 Descargar Excel Procesado",
                data=excel_data,
                file_name="CallLog_Procesado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Ocurrió un error al procesar el archivo: {e}")
