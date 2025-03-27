# 1. Imports
import streamlit as st
import json
import os
import math
from datetime import datetime, timedelta
import pandas as pd # Usaremos Pandas para mostrar el historial de forma más agradable

# --- Constantes y Configuración (Igual que antes) ---
ARCHIVO_DATOS = "stock_data_hist.json"
LEAD_TIME_FIJO = 3
DIAS_SEGURIDAD_FIJOS = 3
DIAS_PROMEDIO = 30
DIAS_HISTORIAL_MAX = 90

# --- Funciones Auxiliares (cargar_datos, guardar_datos, calcular_promedio_ventas - SIN CAMBIOS) ---
# (Copia aquí las mismas funciones de la versión final de Tkinter)
def cargar_datos(archivo):
    if os.path.exists(archivo):
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                if not contenido: return {}
                return json.loads(contenido)
        except (json.JSONDecodeError, IOError) as e:
            # Usar st.error para mostrar en la app web
            st.error(f"Error al cargar '{archivo}': {e}. Se empezará vacío.")
            return {}
        except Exception as e:
             st.error(f"Error inesperado al cargar datos: {e}")
             return {}
    else: return {}

def guardar_datos(archivo, datos):
    try:
        hoy = datetime.now().date()
        fecha_limite = hoy - timedelta(days=DIAS_HISTORIAL_MAX)
        for nombre_prod, data_prod in datos.items():
            if not isinstance(data_prod, dict):
                 datos[nombre_prod] = {"ventas_historico": []}; continue
            if "ventas_historico" in data_prod and isinstance(data_prod["ventas_historico"], list):
                historial_nuevo = []
                for venta in data_prod["ventas_historico"]:
                     if isinstance(venta, dict) and isinstance(venta.get("fecha"), str) and len(venta["fecha"]) == 10 and "cantidad" in venta:
                         try:
                             fecha_venta_obj = datetime.strptime(venta["fecha"], "%Y-%m-%d").date()
                             if fecha_venta_obj >= fecha_limite:
                                 if isinstance(venta["cantidad"], (int, float)) and venta["cantidad"] >= 0:
                                     historial_nuevo.append(venta)
                         except (ValueError, TypeError): pass
                # Ordenar antes de guardar
                historial_nuevo.sort(key=lambda x: x.get("fecha", "0000-00-00"), reverse=True)
                datos[nombre_prod]["ventas_historico"] = historial_nuevo
            elif "ventas_historico" not in data_prod:
                 datos[nombre_prod]["ventas_historico"] = []
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        # Usar st.error para mostrar en la app web
        st.error(f"Error al guardar datos en '{archivo}': {e}")
        return False

def calcular_promedio_ventas(historial, dias_ventana):
    # (La lógica interna de esta función es la misma que la versión final de Tkinter)
    if not historial or not isinstance(historial, list): return 0.0
    hoy = datetime.now().date()
    fecha_inicio_ventana = hoy - timedelta(days=dias_ventana)
    total_ventas_ventana = 0
    fechas_validas = []
    for venta in historial:
        if isinstance(venta, dict) and isinstance(venta.get("fecha"), str) and len(venta["fecha"]) == 10:
            try:
                fecha_venta = datetime.strptime(venta["fecha"], "%Y-%m-%d").date()
                fechas_validas.append(fecha_venta)
                if fecha_inicio_ventana <= fecha_venta <= hoy:
                    cantidad = venta.get("cantidad", 0)
                    if isinstance(cantidad, (int, float)) and cantidad >= 0:
                        total_ventas_ventana += cantidad
            except (ValueError, TypeError): continue
    if not fechas_validas: return 0.0
    primera_fecha_venta = min(fechas_validas)
    dias_desde_primera_venta = (hoy - primera_fecha_venta).days + 1
    denominador = min(dias_desde_primera_venta, dias_ventana)
    denominador = max(1, denominador)
    promedio_diario = total_ventas_ventana / denominador
    return promedio_diario

# --- Lógica de la Aplicación Streamlit ---

st.set_page_config(layout="wide", page_title="Stock Óptimo") # Configura layout ancho

st.title("📊 Calculadora de Stock Óptimo")

# --- Inicializar Estado de Sesión (si no existe) ---
# Esto preserva los datos entre interacciones del usuario
if 'productos_data' not in st.session_state:
    st.session_state.productos_data = cargar_datos(ARCHIVO_DATOS)
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = None
if 'show_create_form' not in st.session_state:
     st.session_state.show_create_form = False # Para controlar visibilidad del form

# --- Barra Lateral (Sidebar) para Selección y Creación ---
with st.sidebar:
    st.header("📦 Productos")

    # Botón para mostrar/ocultar formulario de creación
    if st.button("➕ Crear Nuevo Producto", key="toggle_create"):
         st.session_state.show_create_form = not st.session_state.show_create_form

    # Formulario de Creación (condicional)
    if st.session_state.show_create_form:
        with st.form("create_form", clear_on_submit=True):
             new_prod_name_input = st.text_input("Nombre del Nuevo Producto:")
             submitted_create = st.form_submit_button("Crear y Seleccionar")
             if submitted_create:
                 new_prod_name = new_prod_name_input.strip()
                 if not new_prod_name:
                     st.warning("El nombre no puede estar vacío.")
                 elif new_prod_name in st.session_state.productos_data:
                     st.warning(f"El producto '{new_prod_name}' ya existe.")
                     # Seleccionar el existente en lugar de dar error?
                     st.session_state.selected_product = new_prod_name
                     st.session_state.show_create_form = False # Ocultar form
                     st.rerun() # Rerun para reflejar la selección
                 else:
                     st.session_state.productos_data[new_prod_name] = {"ventas_historico": []}
                     if guardar_datos(ARCHIVO_DATOS, st.session_state.productos_data):
                         st.success(f"Producto '{new_prod_name}' creado.")
                         st.session_state.selected_product = new_prod_name # Seleccionar el nuevo
                         st.session_state.show_create_form = False # Ocultar form
                         st.rerun() # Rerun para actualizar todo
                     else:
                          # Si falla el guardado, quitarlo del estado de sesión
                          del st.session_state.productos_data[new_prod_name]


    st.divider() # Separador visual

    # --- Selección de Producto Existente ---
    lista_productos_sorted = sorted(st.session_state.productos_data.keys())
    options = ["-- Selecciona un Producto --"] + lista_productos_sorted

    # Determinar índice actual para el selectbox
    current_selection_index = 0
    if st.session_state.selected_product and st.session_state.selected_product in options:
        try:
            current_selection_index = options.index(st.session_state.selected_product)
        except ValueError:
            # Si el producto seleccionado ya no existe (raro), resetear
            st.session_state.selected_product = None

    # Selectbox para elegir producto
    selected = st.selectbox(
        "Selecciona Existente:",
        options=options,
        index=current_selection_index,
        key="product_selector" # Key para mantener estado
    )

    # Actualizar estado de sesión cuando cambia la selección
    if selected == "-- Selecciona un Producto --":
        # Si cambia a "Selecciona...", deseleccionar
        if st.session_state.selected_product is not None:
             st.session_state.selected_product = None
             st.rerun() # Rerun para limpiar el panel principal
    elif selected != st.session_state.selected_product:
        # Si cambia a un producto diferente, actualizar
        st.session_state.selected_product = selected
        st.rerun() # Rerun para cargar datos del nuevo producto


# --- Panel Principal (Mostrar Detalles si hay selección) ---
if st.session_state.selected_product:
    st.header(f"📈 Detalles: {st.session_state.selected_product}")

    producto_actual = st.session_state.productos_data.get(st.session_state.selected_product, {"ventas_historico": []})
    historial_actual = producto_actual.get("ventas_historico", [])
    if not isinstance(historial_actual, list): historial_actual = [] # Asegurar que sea lista

    # --- Formulario para Agregar Venta y Calcular ---
    with st.form("venta_form"):
        st.subheader("➕ Agregar Venta")
        col1, col2 = st.columns([1, 2]) # Columna fecha más pequeña
        with col1:
            input_fecha = st.date_input("Fecha Venta", value=datetime.now().date(), key="fecha_venta")
        with col2:
            # Usamos session state para intentar recordar el último valor ingresado
            if 'last_cantidad' not in st.session_state: st.session_state.last_cantidad = 0
            input_cantidad = st.number_input(
                 "Cantidad Vendida",
                 min_value=0,
                 step=1,
                 # value=st.session_state.last_cantidad, # Opcional: recordar último valor
                 key="cantidad_venta"
             )

        submitted_venta = st.form_submit_button("💾 Guardar Venta y Recalcular Stock")

        if submitted_venta:
            fecha_str = input_fecha.strftime('%Y-%m-%d')
            cantidad = input_cantidad
            st.session_state.last_cantidad = cantidad # Recordar para la próxima vez

            # Lógica para agregar/reemplazar venta (similar a Tkinter)
            entrada_modificada = False
            indice_existente = -1
            for i, venta in enumerate(historial_actual):
                 if isinstance(venta, dict) and venta.get("fecha") == fecha_str:
                     indice_existente = i; break

            if indice_existente != -1:
                 cantidad_anterior = historial_actual[indice_existente].get("cantidad", "?")
                 if cantidad_anterior != cantidad:
                     # En Streamlit, es más directo reemplazar, no necesitamos confirmación modal
                     historial_actual[indice_existente]["cantidad"] = cantidad
                     st.info(f"Venta del {fecha_str} actualizada a {cantidad} unidades.")
                     entrada_modificada = True
                 else:
                      st.info(f"Venta para {fecha_str} ya registrada con {cantidad} unidades (sin cambios).")
                      # Marcamos como modificada para forzar recálculo si el usuario lo espera
                      entrada_modificada = True # O False si no queremos recalcular si no hay cambio
            else:
                 historial_actual.append({"fecha": fecha_str, "cantidad": cantidad})
                 historial_actual.sort(key=lambda x: x.get("fecha", "0000-00-00"), reverse=True)
                 st.success(f"Venta del {fecha_str} ({cantidad} uds) agregada.")
                 entrada_modificada = True

            if entrada_modificada:
                 # Actualizar el diccionario principal en session_state
                 st.session_state.productos_data[st.session_state.selected_product]["ventas_historico"] = historial_actual
                 # Guardar en el archivo JSON
                 if guardar_datos(ARCHIVO_DATOS, st.session_state.productos_data):
                      # Los cálculos se harán automáticamente en el rerun de Streamlit más abajo
                      # Limpiar cantidad input? No, st.form lo hace con clear_on_submit=True si no lo ponemos en session state
                      st.rerun() # Forzar rerun para mostrar cálculos actualizados y limpiar form
                 else:
                      # Error ya mostrado por guardar_datos
                      # Podríamos intentar revertir el cambio en historial_actual si falló, pero es complejo
                      pass


    st.divider()

    # --- Mostrar Resultados (Calculados en cada ejecución) ---
    st.subheader("📊 Recomendaciones de Stock")
    promedio = calcular_promedio_ventas(historial_actual, DIAS_PROMEDIO)
    demanda_lt = promedio * LEAD_TIME_FIJO
    stock_seg = promedio * DIAS_SEGURIDAD_FIJOS
    optimo = math.ceil(demanda_lt + stock_seg)
    pedido = math.ceil(demanda_lt + stock_seg) # Mismo en este modelo

    col_res1, col_res2, col_res3 = st.columns(3)
    with col_res1:
        st.metric(label=f"Prom. Diario ({DIAS_PROMEDIO}d)", value=f"{promedio:.2f}")
    with col_res2:
        st.metric(label="Stock Óptimo Sugerido", value=f"{optimo}")
    with col_res3:
        st.metric(label="Punto de Pedido", value=f"{pedido}")

    st.caption(f"Cálculos basados en Lead Time={LEAD_TIME_FIJO}d y Seguridad={DIAS_SEGURIDAD_FIJOS}d.")

    st.divider()

    # --- Mostrar Historial ---
    st.subheader("📜 Historial Reciente")
    if not historial_actual:
        st.info("No hay ventas registradas para este producto.")
    else:
        # Crear un DataFrame de Pandas para mejor visualización
        try:
            df_historial = pd.DataFrame(historial_actual)
            # Asegurar que cantidad sea numérica por si hay errores en el JSON
            df_historial['cantidad'] = pd.to_numeric(df_historial['cantidad'], errors='coerce').fillna(0).astype(int)
            # Ordenar por fecha (aunque ya debería estarlo por guardar_datos)
            df_historial['fecha'] = pd.to_datetime(df_historial['fecha'])
            df_historial = df_historial.sort_values(by='fecha', ascending=False)
            # Formatear fecha para mostrar
            df_historial['fecha'] = df_historial['fecha'].dt.strftime('%Y-%m-%d')
            # Mostrar tabla (solo las últimas N filas)
            st.dataframe(df_historial[['fecha', 'cantidad']].head(30), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error al mostrar el historial: {e}")
            # Fallback a texto plano si falla Pandas
            hist_texto = "\n".join([f"{v.get('fecha', '??')}: {v.get('cantidad', '??')} uds" for v in historial_actual[:30]])
            st.text_area("Ventas", hist_texto, height=200, disabled=True)


else:
    # Mensaje si no hay producto seleccionado
    st.info("⬅️ Selecciona un producto de la barra lateral o crea uno nuevo para empezar.")
