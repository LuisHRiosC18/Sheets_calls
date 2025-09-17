import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import io

# --- CONFIGURACIÓN DE LA PÁGINA Y TÍTULO ---
st.set_page_config(
    page_title="Gestor de Números Telefónicos",
    page_icon="📞",
    layout="wide"
)

st.title("📞 Gestor de Números Telefónicos")
st.write("Esta pagina sirve para procesar logs de Ring Center y actualizar la base de datos de contactos cada día.")

# --- CONFIGURACIÓN INICIAL Y FUNCIONES AUXILIARES ---

# Lista de funerarias (definida una vez para ser usada globalmente)
funerarias = ['Latino', 'Agape', 'Bayview', 'Anaheim']

# Función para conectar con Google Sheets (cacheada para eficiencia)
@st.cache_resource
def connect_to_google_sheets():
    """
    Establece la conexión con la API de Google Sheets usando las credenciales
    almacenadas en los secrets de Streamlit.
    """
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# Función para asignar el nombre de la funeraria basado en la extensión
def assign_funeraria(extension='Extension', funerarias_list=funerarias):
    """
    Busca el nombre de una funeraria en el string de la extensión de la llamada.
    """
    if isinstance(extension, str):
        for funeraria in funerarias_list:
            if funeraria.lower() in extension.lower():
                return funeraria
    return ''

# --- CREACIÓN DE LA INTERFAZ CON PESTAÑAS ---

tab1, tab2 = st.tabs(["Agregar números", "Procesar Log "])

# --- PESTAÑA 1: AGREGAR NÚMEROS A GOOGLE SHEETS ---
with tab1:
    st.header("Agregar Números desde Excel a la Base de Datos")
    st.write(
        "Sube un archivo Excel para comparar sus números de teléfono con la base de datos "
        "de Google Sheets. Los números nuevos se agregarán automáticamente a la hoja."
    )

    gspread_client = connect_to_google_sheets()
    
    # Cargador de archivos para la funcionalidad de Google Sheets
    uploaded_file_sheets = st.file_uploader(
        "Arrastra o selecciona tu archivo de Excel (.xlsx)", 
        type=['xlsx'], 
        key="sheets_uploader"
    )

    if uploaded_file_sheets and gspread_client:
        if st.button("Procesar y Agregar Números", key="process_sheets"):
            try:
                # Reemplaza 'NOMBRE_DE_TU_HOJA' con el nombre real de tu documento en Google Drive
                spreadsheet = gspread_client.open("Llamadas_totales") 
                worksheet = spreadsheet.sheet1

                st.info("Obteniendo números existentes de la base de datos...")
                existing_phones_raw = worksheet.col_values(1)
                existing_phones = {str(phone).strip() for phone in existing_phones_raw}
                st.success(f"Se encontraron {len(existing_phones)} números en la base de datos.")

                xls = pd.ExcelFile(uploaded_file_sheets)
                new_rows_to_add = []
                
                progress_bar = st.progress(0)
                total_sheets = len(xls.sheet_names)

                for i, sheet_name in enumerate(xls.sheet_names):
                    df_sheet = pd.read_excel(xls, sheet_name=sheet_name)

                    if 'From' not in df_sheet.columns or 'PraFecha' not in df_sheet.columns:
                        st.warning(f"La hoja '{sheet_name}' no contiene las columnas 'From' y/o 'PraFecha'. Se omitirá.")
                        continue

                    for index, row in df_sheet.iterrows():
                        phone_number = str(row['From']).strip()
                        pra_fecha_obj = row['PraFecha']

                        if pd.isna(pra_fecha_obj):
                            pra_fecha_str = ""
                        elif isinstance(pra_fecha_obj, time):
                            pra_fecha_str = pra_fecha_obj.strftime('%H:%M:%S')
                        else:
                            # Intenta convertir a fecha y hora completa
                            dt_obj = pd.to_datetime(pra_fecha_obj, errors='coerce')
                            if pd.notna(dt_obj):
                                pra_fecha_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                            else: # Si no se puede convertir, lo deja como texto
                                pra_fecha_str = str(pra_fecha_obj)
                        # --- FIN DE LA SECCIÓN CORREGIDA ---

                        if phone_number not in existing_phones:
                            new_rows_to_add.append([phone_number, pra_fecha_str])
                            existing_phones.add(phone_number)

                    
                    progress_bar.progress((i + 1) / total_sheets, text=f"Procesando hoja: {sheet_name}")

                if new_rows_to_add:
                    st.info(f"Agregando {len(new_rows_to_add)} nuevos números a Google Sheets...")
                    worksheet.append_rows(new_rows_to_add, value_input_option='USER_ENTERED')
                    st.success("Se agregaron los nuevos números a la base de datos")
                    st.balloons()
                else:
                    st.info("La base no necesitó actualizarse.")

            except Exception as e:
                st.error(f"Ocurrió un error durante el procesamiento: {e}")

# --- PESTAÑA 2: PROCESAR Y DESCARGAR LOG DE LLAMADAS ---
with tab2:
    st.header("Procesador de Log de Llamadas (CallLog)")
    st.write(
        "Sube el archivo `CallLog.csv` para limpiarlo, clasificarlo por funeraria "
        "y descargarlo como un excel."
    )

    # Cargador de archivos para la funcionalidad del CallLog
    uploaded_file_calllog = st.file_uploader(
        "Sube tu archivo CallLog.csv", 
        type=['csv'], 
        key="calllog_uploader"
    )

    if uploaded_file_calllog:
        try:
            logs = pd.read_csv(uploaded_file_calllog)
            
            st.info("Procesando archivo CallLog...")
            logs_filtered = logs.copy()
            logs_filtered['From'] = logs_filtered['From'].astype(str)
            logs_filtered = logs_filtered[logs_filtered['From'].str.len() > 3]
            
            required_cols = ['From', 'Date', 'Time', 'Action Result', 'Extension']
            if not all(col in logs_filtered.columns for col in required_cols):
                st.error(f"El archivo CSV debe contener las siguientes columnas: {', '.join(required_cols)}")
            else:
                logs_filtered = logs_filtered[required_cols]
                logs_filtered['Date'] = logs_filtered['Date'].str.replace(r'[a-zA-Z]', '', regex=True).str.strip()
                logs_filtered['PraFecha'] = pd.to_datetime(
                    logs_filtered['Date'] + ' ' + logs_filtered['Time'], 
                    errors='coerce'
                ).dt.strftime('%Y-%m-%d %H:%M:%S')

                logs_filtered['Funeraria'] = logs_filtered['Extension'].apply(assign_funeraria)
                logs_filtered = logs_filtered[logs_filtered['Funeraria'] != '']
                logs_filtered = logs_filtered.drop_duplicates(subset='From', keep='last')
                
                st.success("Ya lo puede descargar")
                st.write("Vista previa de los datos filtrados y clasificados:")
                st.dataframe(logs_filtered[['Funeraria', 'From', 'PraFecha', 'Action Result']])

                # --- Lógica para crear el archivo Excel en memoria ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    for funeraria_name in sorted(logs_filtered['Funeraria'].unique()):
                        df_funeraria = logs_filtered[logs_filtered['Funeraria'] == funeraria_name]
                        df_to_write = df_funeraria[['From', 'PraFecha', 'Action Result']]
                        df_to_write.to_excel(writer, sheet_name=funeraria_name, index=False)
                
                excel_data = output.getvalue()

                st.download_button(
                    label="📥 Descargar Excel Procesado",
                    data=excel_data,
                    file_name="CallLog_Procesado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"Ocurrió un error al procesar el archivo: {e}")
