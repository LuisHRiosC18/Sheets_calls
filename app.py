import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN DE LA PÁGINA Y CONEXIÓN A GOOGLE SHEETS ---

st.set_page_config(
    page_title="Cargar de Números",
    page_icon="📞"
)

st.title("📞 Cargar números a google sheets")
st.write("""
    Sube un archivo Excel para comparar los números de teléfono con la base de datos.
    Los números nuevos se agregarán automáticamente.
""")

# Función para autenticar y conectar con Google Sheets usando los Secrets de Streamlit
@st.cache_resource
def connect_to_google_sheets():
    try:
        # Define los permisos (scopes) necesarios
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        # Carga las credenciales desde los secrets de Streamlit
        # st.secrets es un diccionario especial que Streamlit maneja para las credenciales
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes,
        )
        # Autoriza y retorna el cliente de gspread
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# Llama a la función de conexión
gspread_client = connect_to_google_sheets()

# --- INTERFAZ DE LA APLICACIÓN ---

# Pídele al usuario que suba el archivo de Excel
uploaded_file = st.file_uploader(
    "Arrastra o selecciona tu archivo de Excel (.xlsx)",
    type=['xlsx']
)

# Botón para iniciar el procesamiento
if uploaded_file and gspread_client:
    if st.button("Procesar Archivo"):
        try:
            # Abre el documento de Google Sheets (reemplaza 'NOMBRE_DE_TU_HOJA')
            spreadsheet = gspread_client.open("Llamadas_totales")
            worksheet = spreadsheet.sheet1 # O la hoja específica que uses como BD

            # Obtener los números existentes de la primera columna para evitar duplicados
            st.info("Obteniendo números existentes de la base de datos...")
            existing_phones_raw = worksheet.col_values(1) # Asume que los teléfonos están en la columna A
            # Convertimos todo a string para una comparación robusta
            existing_phones = {str(phone).strip() for phone in existing_phones_raw}
            st.success(f"Se encontraron {len(existing_phones)} números en la base de datos.")

            # Leer el archivo Excel subido
            xls = pd.ExcelFile(uploaded_file)
            new_rows_to_add = []

            # Iterar por cada hoja del documento Excel
            progress_bar = st.progress(0)
            total_sheets = len(xls.sheet_names)

            for i, sheet_name in enumerate(xls.sheet_names):
                df_sheet = pd.read_excel(xls, sheet_name=sheet_name)

                # Verificar si las columnas necesarias existen en la hoja actual
                if 'From' not in df_sheet.columns or 'PraFecha' not in df_sheet.columns:
                    st.warning(f"La hoja '{sheet_name}' no contiene las columnas 'From' y/o 'PraFecha'. Se omitirá.")
                    continue

                # Iterar por las filas de la hoja actual
                for index, row in df_sheet.iterrows():
                    phone_number = str(row['From']).strip()
                    pra_fecha = row['PraFecha']

                    if pd.isna(pra_fecha_obj):
                        pra_fecha_str = "" # O puedes poner "N/A" si prefieres
                    else:
                        # Formato 'Año-Mes-Día Hora:Minuto:Segundo'. Puedes simplificarlo a '%Y-%m-%d' si no necesitas la hora.
                        pra_fecha_str = pra_fecha_obj.strftime('%Y-%m-%d %H:%M:%S')

                # Si el número no está en la base de datos, lo agregamos a la lista
                    if phone_number not in existing_phones:
                        # ¡Importante! Agregamos la versión en string de la fecha
                        new_rows_to_add.append([phone_number, pra_fecha_str])
                    
                        # Y también al set de control para evitar duplicados del mismo archivo
                        existing_phones.add(phone_number)
            
            # Actualizar la barra de progreso
            progress_bar.progress((i + 1) / total_sheets, text=f"Procesando hoja: {sheet_name}")
            
            # --- AGREGAR LOS NUEVOS DATOS A GOOGLE SHEETS ---
            
            if new_rows_to_add:
                st.info(f"Agregando {len(new_rows_to_add)} nuevos números a Google Sheets...")
                # append_rows es más eficiente que agregar una por una
                worksheet.append_rows(new_rows_to_add, value_input_option='USER_ENTERED')
                st.success("¡Proceso completado! Se agregaron los nuevos números exitosamente. ✅")
                st.balloons()
            else:
                st.info("No se encontraron números nuevos para agregar. La base de datos ya está actualizada. 👍")

        except Exception as e:
            st.error(f"Ocurrió un error durante el procesamiento: {e}")
