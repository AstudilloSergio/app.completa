import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from PIL import Image

# Configuración de la página
st.set_page_config(page_title="TradeAnalytics Pro", page_icon="📈", layout="wide")

# Estilos CSS premium
st.markdown(
    """
<style>
    .stAlert, .stWarning, .stException { 
        display: none !important; 
    }
    
    div[data-testid="stNumberInput"] label {
        display: none !important;
    }
    
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap');
    
    .main-header-premium {
        font-family: 'Montserrat', sans-serif;
        font-size: 4rem;
        background: linear-gradient(45deg, #1a2a6c, #0047ab, #0066cc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        letter-spacing: 3px;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .dolar-box-premium {
        background: linear-gradient(135deg, #e8f4f8 0%, #ffffff 100%);
        padding: 16px;
        border-radius: 12px;
        border: 2px solid #1a2a6c;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    .stButton>button {
        background: linear-gradient(45deg, #1a2a6c, #0047ab);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background: linear-gradient(45deg, #0047ab, #0066cc);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Mejor responsividad para móviles */
    @media (max-width: 768px) {
        .stNumberInput, .stTextInput, .stSelectbox {
            margin-bottom: 10px;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)


# FUNCIONES MEJORADAS
def format_currency(value):
    """Formato de moneda argentino mejorado"""
    try:
        value = float(value)
        if value >= 1000:
            return (
                f"${value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        else:
            return (
                f"${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
    except:
        return f"${value}"


def convertir_a_numero(valor):
    try:
        if isinstance(valor, str):
            valor = (
                valor.replace("$", "")
                .replace(" ", "")
                .replace(".", "")
                .replace(",", ".")
            )
        return float(valor)
    except:
        return 0.0


def sugerir_sl_tp_inteligente(precio_compra, activo):
    """Sugiere SL y TP basado en análisis técnico del activo"""
    activo = activo.upper()

    if any(coin in activo for coin in ["BTC", "ETH", "XRP", "SOL", "ADA"]):
        # Criptomonedas: alta volatilidad
        stop_loss = precio_compra * 0.92  # -8%
        take_profit = precio_compra * 1.18  # +18%
    elif any(stock in activo for stock in ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]):
        # Tech stocks: volatilidad media-alta
        stop_loss = precio_compra * 0.94  # -6%
        take_profit = precio_compra * 1.12  # +12%
    elif any(stock in activo for stock in ["KO", "PG", "JNJ", "WMT", "XOM"]):
        # Blue chips: baja volatilidad
        stop_loss = precio_compra * 0.96  # -4%
        take_profit = precio_compra * 1.08  # +8%
    elif "ARS" in activo or "PESO" in activo:
        # Activos en pesos: mayor volatilidad
        stop_loss = precio_compra * 0.90  # -10%
        take_profit = precio_compra * 1.20  # +20%
    else:
        # Default: volatilidad moderada
        stop_loss = precio_compra * 0.93  # -7%
        take_profit = precio_compra * 1.15  # +15%

    return round(stop_loss, 2), round(take_profit, 2)


# Lista de brokers predefinidos
BROKERS_PREDEFINIDOS = [
    "BALANZ",
    "IOL",
    "BULL MARKET",
    "ECO VALORES",
    "BINANCE",
    "PPI",
    "COINBASE",
    "RAVA",
    "BYMA",
    "BROU",
    "BANCO GALICIA",
    "BANCO SANTANDER",
    "BANCO ICBC",
    "MERCADO PAGO",
    "RIPIO",
    "LETSRIPO",
]


# Inicializar la base de datos
def init_db():
    conn = sqlite3.connect("trade_analytics.db")
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS portafolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Tipo_Activo TEXT, Broker TEXT, Monto_Invertido REAL,
            Moneda TEXT, Renta TEXT
        )
    """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS operaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Fecha_Entrada TEXT, Fecha_Salida TEXT, Activo TEXT,
            Operacion TEXT, Cantidad REAL, Precio_Entrada REAL,
            Precio_Salida REAL, Inversion_Total REAL, Resultado REAL,
            ROI REAL, Duracion INTEGER, Estrategia TEXT, Notas TEXT
        )
    """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS cotizaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT, valor_usd REAL
        )
    """
    )

    # Cargar datos existentes
    try:
        portafolio_db = pd.read_sql_query("SELECT * FROM portafolio", conn)
        st.session_state.portafolio = (
            portafolio_db.drop("id", axis=1)
            if not portafolio_db.empty
            else pd.DataFrame(
                columns=["Tipo_Activo", "Broker", "Monto_Invertido", "Moneda", "Renta"]
            )
        )
    except:
        st.session_state.portafolio = pd.DataFrame(
            columns=["Tipo_Activo", "Broker", "Monto_Invertido", "Moneda", "Renta"]
        )

    try:
        operaciones_db = pd.read_sql_query("SELECT * FROM operaciones", conn)
        st.session_state.libro_trading = (
            operaciones_db.drop("id", axis=1)
            if not operaciones_db.empty
            else pd.DataFrame(
                columns=[
                    "Fecha_Entrada",
                    "Fecha_Salida",
                    "Activo",
                    "Operacion",
                    "Cantidad",
                    "Precio_Entrada",
                    "Precio_Salida",
                    "Inversion_Total",
                    "Resultado",
                    "ROI",
                    "Duracion",
                    "Estrategia",
                    "Notas",
                ]
            )
        )
    except:
        st.session_state.libro_trading = pd.DataFrame(
            columns=[
                "Fecha_Entrada",
                "Fecha_Salida",
                "Activo",
                "Operacion",
                "Cantidad",
                "Precio_Entrada",
                "Precio_Salida",
                "Inversion_Total",
                "Resultado",
                "ROI",
                "Duracion",
                "Estrategia",
                "Notas",
            ]
        )

    try:
        cotizacion_db = pd.read_sql_query(
            "SELECT valor_usd FROM cotizaciones ORDER BY fecha DESC LIMIT 1", conn
        )
        st.session_state.cotizacion_usd = (
            cotizacion_db["valor_usd"].iloc[0] if not cotizacion_db.empty else 1000.0
        )
    except:
        st.session_state.cotizacion_usd = 1000.0

    conn.commit()
    conn.close()


# Inicializar la aplicación
if "portafolio" not in st.session_state:
    st.session_state.portafolio = pd.DataFrame(
        columns=["Tipo_Activo", "Broker", "Monto_Invertido", "Moneda", "Renta"]
    )

if "libro_trading" not in st.session_state:
    st.session_state.libro_trading = pd.DataFrame(
        columns=[
            "Fecha_Entrada",
            "Fecha_Salida",
            "Activo",
            "Operacion",
            "Cantidad",
            "Precio_Entrada",
            "Precio_Salida",
            "Inversion_Total",
            "Resultado",
            "ROI",
            "Duracion",
            "Estrategia",
            "Notas",
        ]
    )

if "cotizacion_usd" not in st.session_state:
    st.session_state.cotizacion_usd = 1000.0

# Inicializar base de datos
init_db()

# ============================================================
# LOGO + INFO PRINCIPAL
# ============================================================
col_logo, col_info = st.columns([3, 1])

with col_info:
    try:
        logo = Image.open("logo.png")
        st.image(logo, width=220)
    except:
        st.markdown(
            """
            <div style="text-align: center; margin: 10px 0;">
                <div style="width: 80px; height: 80px; margin: 0 auto;
                            background: linear-gradient(135deg, #1a2a6c 0%, #0047ab 100%);
                            border-radius: 12px; display: flex; align-items: center; justify-content: center;
                            box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
                    <span style="color: white; font-size: 1.2rem; font-weight: bold;">TAP</span>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )

with col_logo:
    if not st.session_state.portafolio.empty:
        portafolio_copy = st.session_state.portafolio.copy()
        portafolio_copy["Monto_Invertido"] = portafolio_copy["Monto_Invertido"].apply(
            convertir_a_numero
        )
        portafolio_copy["Monto_ARS"] = portafolio_copy.apply(
            lambda x: (
                x["Monto_Invertido"] * st.session_state.cotizacion_usd
                if x["Moneda"] in ["USD", "USDT"]
                else x["Monto_Invertido"]
            ),
            axis=1,
        )
        total_invertido_ars = portafolio_copy["Monto_ARS"].sum()

        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #e8f4f8 0%, #ffffff 100%);
                        padding: 15px; border-radius: 12px; border-left: 4px solid #1a2a6c;
                        margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <h3 style="color: #1a2a6c; margin: 0; font-family: 'Montserrat', sans-serif; font-size: 1.1rem;">
                    💰 INVERSIÓN TOTAL
                </h3>
                <p style="font-size: 1.8rem; font-weight: bold; color: #0047ab; margin: 5px 0;">
                    {format_currency(total_invertido_ars)}
                </p>
                <p style="color: #2c3e50; margin: 0; font-size: 0.9rem;">
                    {len(st.session_state.portafolio)} activos en cartera
                </p>
            </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                        padding: 15px; border-radius: 12px; border-left: 4px solid #1a2a6c;
                        margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <h3 style="color: #1a2a6c; margin: 0; font-family: 'Montserrat', sans-serif; font-size: 1.1rem;">
                    💰 INVERSIÓN TOTAL
                </h3>
                <p style="font-size: 1.1rem; color: #2c3e50; margin: 5px 0;">Agrega tu primer activo</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

st.markdown("---")

# Pestañas principales
tab1, tab2, tab3 = st.tabs(["💼 Portafolio", "📈 Trading", "🎯 TP/SL Calculator"])

# Pestaña 1: Portafolio de Inversiones
with tab1:
    st.header("💼 Portafolio de Inversiones")

    col1, col2 = st.columns([3, 1])

    with col2:
        st.markdown('<div class="dolar-box-premium">', unsafe_allow_html=True)
        st.markdown("**💵 Cotización USD**")
        nueva_cotizacion = st.number_input(
            "Valor USD → ARS",
            min_value=1.0,
            value=float(st.session_state.cotizacion_usd),
            step=1.0,
            format="%.0f",
            label_visibility="collapsed",
        )
        if st.button("💱 Actualizar Cotización", use_container_width=True):
            st.session_state.cotizacion_usd = nueva_cotizacion
            conn = sqlite3.connect("trade_analytics.db")
            conn.execute(
                "INSERT INTO cotizaciones (fecha, valor_usd) VALUES (?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nueva_cotizacion),
            )
            conn.commit()
            conn.close()
            st.success("✅ Cotización actualizada!")
        st.markdown("</div>", unsafe_allow_html=True)

    with col1:
        st.info("💡 Agregá tus activos de inversión a largo plazo")

    edited_df = st.data_editor(
        st.session_state.portafolio,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Tipo_Activo": st.column_config.SelectboxColumn(
                "Tipo de Activo",
                options=[
                    "CEDEARs",
                    "Acciones",
                    "Bonos",
                    "Fondos",
                    "Cripto",
                    "Letras",
                    "ONs",
                    "Otros",
                    "Causión",
                    "Dolar",
                ],
                required=True,
            ),
            "Broker": st.column_config.SelectboxColumn(
                "Broker", options=BROKERS_PREDEFINIDOS, required=True
            ),
            "Monto_Invertido": st.column_config.NumberColumn(
                "Monto Invertido", format="%.0f", required=True, min_value=0
            ),
            "Moneda": st.column_config.SelectboxColumn(
                "Moneda", options=["ARS", "USD", "USDT"], required=True
            ),
            "Renta": st.column_config.SelectboxColumn(
                "Tipo de Renta", options=["Variable", "Fija", "Mixta"], required=True
            ),
        },
    )

    if st.button(
        "💾 Guardar Portafolio", use_container_width=True, key="guardar_portafolio_btn"
    ):
        portafolio_validado = edited_df.copy()
        portafolio_validado["Monto_Invertido"] = portafolio_validado[
            "Monto_Invertido"
        ].apply(convertir_a_numero)
        montos_validos = all(portafolio_validado["Monto_Invertido"] > 0)

        if montos_validos and not portafolio_validado.empty:
            st.session_state.portafolio = portafolio_validado
            conn = sqlite3.connect("trade_analytics.db")
            conn.execute("DELETE FROM portafolio")
            st.session_state.portafolio.to_sql(
                "portafolio", conn, if_exists="append", index=False
            )
            conn.commit()
            conn.close()
            st.success("✅ Portafolio guardado correctamente!")
            st.rerun()
        else:
            st.error("❌ Verifica que todos los montos sean mayores a 0")

    if not st.session_state.portafolio.empty:
        st.divider()
        portafolio_copy = st.session_state.portafolio.copy()
        portafolio_copy["Monto_Invertido"] = portafolio_copy["Monto_Invertido"].apply(
            convertir_a_numero
        )
        portafolio_copy["Monto_ARS"] = portafolio_copy.apply(
            lambda x: (
                x["Monto_Invertido"] * st.session_state.cotizacion_usd
                if x["Moneda"] in ["USD", "USDT"]
                else x["Monto_Invertido"]
            ),
            axis=1,
        )
        total_invertido_ars = portafolio_copy["Monto_ARS"].sum()

        col_graph, col_table = st.columns(2)

        with col_graph:
            st.subheader("📈 Distribución por Tipo de Activo")
            if not portafolio_copy.empty:
                distribucion_activos = portafolio_copy.groupby("Tipo_Activo")[
                    "Monto_ARS"
                ].sum()
                if not distribucion_activos.empty:
                    fig, ax = plt.subplots(figsize=(8, 8))
                    colors = [
                        "#1a2a6c",
                        "#0047ab",
                        "#0066cc",
                        "#0088cc",
                        "#00aacc",
                        "#00ccdd",
                    ]
                    wedges, texts, autotexts = ax.pie(
                        distribucion_activos.values,
                        labels=distribucion_activos.index,
                        autopct="%1.1f%%",
                        startangle=90,
                        colors=colors,
                        shadow=True,
                        explode=[0.03] * len(distribucion_activos),
                    )
                    for autotext in autotexts:
                        autotext.set_color("white")
                        autotext.set_fontweight("bold")
                        autotext.set_fontsize(9)
                    for text in texts:
                        text.set_fontsize(10)
                    ax.set_title(
                        "Distribución por Tipo de Activo",
                        fontsize=14,
                        fontweight="bold",
                    )
                    ax.axis("equal")
                    ax.grid(True, alpha=0.2, linestyle="--")
                    st.pyplot(fig)

        with col_table:
            st.subheader("🏢 Distribución por Broker")
            if not portafolio_copy.empty:
                distribucion_broker = portafolio_copy.groupby("Broker")[
                    "Monto_ARS"
                ].sum()
                if not distribucion_broker.empty:
                    broker_data = []
                    for broker, monto in distribucion_broker.items():
                        porcentaje = (monto / total_invertido_ars) * 100
                        broker_data.append(
                            {
                                "Broker": broker,
                                "Monto": format_currency(monto),
                                "Porcentaje": f"{porcentaje:.1f}%",
                            }
                        )
                    broker_df = pd.DataFrame(broker_data)
                    st.dataframe(
                        broker_df,
                        column_config={
                            "Broker": "Broker",
                            "Monto": st.column_config.TextColumn("Monto en ARS"),
                            "Porcentaje": st.column_config.TextColumn("Porcentaje"),
                        },
                        hide_index=True,
                        use_container_width=True,
                    )

# Pestaña 2: Libro de Trading - SUPER CLARO
with tab2:
    st.header("📈 Libro de Trading")
    st.info("Registro de operaciones COMPLETAS (compra + venta)")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("🆕 Nueva Operación")

        with st.form("operacion_completa"):
            # Fechas
            col_fecha1, col_fecha2 = st.columns(2)
            with col_fecha1:
                fecha_compra = st.date_input("FECHA ENTRADA", datetime.now())
            with col_fecha2:
                fecha_venta = st.date_input("FECHA SALIDA", datetime.now())

            # Validación de fechas
            if fecha_venta < fecha_compra:
                st.error("❌ La fecha de venta no puede ser anterior a la compra")

            # Activo y Operación
            col_activo, col_operacion = st.columns(2)
            with col_activo:
                activo = st.text_input(
                    "ACTIVO", "BTC", help="Símbolo del activo (BTC, AAPL, etc)"
                )
            with col_operacion:
                operacion = st.selectbox("OPERACIÓN", ["COMPRA", "VENTA"])

            # Precios y Cantidad
            st.text("PRECIO COMPRA:")
            precio_compra = st.number_input(
                "",
                min_value=0.0,
                value=900.0,
                step=1.0,
                format="%.0f",
                key="precio_compra",
                help="Precio por unidad al momento de la compra",
            )

            st.text("CANTIDAD:")
            cantidad = st.number_input(
                "",
                min_value=0.0,
                value=1.594,
                step=0.001,
                format="%.3f",
                key="cantidad",
                help="Número de unidades compradas",
            )

            st.text("PRECIO VENTA:")
            precio_venta = st.number_input(
                "",
                min_value=0.0,
                value=1000.0,
                step=1.0,
                format="%.0f",
                key="precio_venta",
                help="Precio por unidad al momento de la venta",
            )

            # Cálculos automáticos
            inversion_total = precio_compra * cantidad
            resultado = (precio_venta - precio_compra) * cantidad
            roi = (resultado / inversion_total * 100) if inversion_total > 0 else 0
            duracion = (fecha_venta - fecha_compra).days

            # Mostrar resultados
            st.markdown("---")
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.metric("Total operación", format_currency(inversion_total))
            with col_res2:
                color = "green" if resultado >= 0 else "red"
                st.metric("Resultado", format_currency(resultado))

            st.metric("ROI", f"{roi:.1f}%")

            # Estrategia
            estrategia = st.selectbox(
                "ESTRATEGIA", ["ANÁLISIS TÉCNICO", "ANÁLISIS FUNDAMENTAL", "MIXTA"]
            )
            notas = st.text_area("NOTAS")

            submitted = st.form_submit_button("💾 GUARDAR OPERACIÓN")

            if submitted and fecha_venta >= fecha_compra:
                if activo and cantidad > 0 and precio_compra > 0 and precio_venta > 0:
                    nueva_operacion = pd.DataFrame(
                        [
                            {
                                "Fecha_Entrada": fecha_compra,
                                "Fecha_Salida": fecha_venta,
                                "Activo": activo.upper(),
                                "Operacion": operacion,
                                "Cantidad": cantidad,
                                "Precio_Entrada": precio_compra,
                                "Precio_Salida": precio_venta,
                                "Inversion_Total": inversion_total,
                                "Resultado": resultado,
                                "ROI": roi,
                                "Duracion": duracion,
                                "Estrategia": estrategia,
                                "Notas": notas,
                            }
                        ]
                    )

                    st.session_state.libro_trading = pd.concat(
                        [st.session_state.libro_trading, nueva_operacion],
                        ignore_index=True,
                    )
                    conn = sqlite3.connect("trade_analytics.db")
                    nueva_operacion.to_sql(
                        "operaciones", conn, if_exists="append", index=False
                    )
                    conn.commit()
                    conn.close()
                    st.success("✅ Operación registrada correctamente!")
                    st.rerun()
                else:
                    st.error("❌ Complete todos los campos")

    with col2:
        st.subheader("📋 Historial de Operaciones")
        if not st.session_state.libro_trading.empty:
            # Gráfico MEJORADO
            st.subheader("📊 Evolución del Capital")
            df_evolucion = st.session_state.libro_trading.copy()
            df_evolucion["Fecha"] = pd.to_datetime(df_evolucion["Fecha_Entrada"])
            df_evolucion = df_evolucion.sort_values("Fecha")
            df_evolucion["Acumulado_Total"] = df_evolucion["Resultado"].cumsum()

            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(
                df_evolucion["Fecha"],
                df_evolucion["Acumulado_Total"],
                linewidth=3,
                color="#1a2a6c",
                label="Total Acumulado",
                marker="o",
                markersize=6,
            )
            ax.set_xlabel("Fecha")
            ax.set_ylabel("Resultado Acumulado ($)")
            ax.set_title("Evolución del Capital", fontsize=14, fontweight="bold")
            ax.legend()
            ax.grid(True, alpha=0.2, linestyle="--")
            ax.set_facecolor("#f8f9fa")
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)

            # Operaciones individuales
            for i, op in st.session_state.libro_trading.iterrows():
                with st.expander(
                    f"{op['Activo']} - {op['Operacion']} - {op['Fecha_Entrada']}"
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(
                            f"**Inversión:** {format_currency(op['Inversion_Total'])}"
                        )
                        st.write(f"**Cantidad:** {op['Cantidad']}")
                        st.write(
                            f"**Precio Compra:** {format_currency(op['Precio_Entrada'])}"
                        )
                        st.write(
                            f"**Precio Venta:** {format_currency(op['Precio_Salida'])}"
                        )
                    with col2:
                        color = "green" if op["Resultado"] >= 0 else "red"
                        st.write(
                            f"**Resultado:** :{color}[{format_currency(op['Resultado'])}]"
                        )
                        st.write(f"**ROI:** :{color}[{op['ROI']:.1f}%]")
                        st.write(f"**Duración:** {op['Duracion']} días")
                        st.write(f"**Estrategia:** {op['Estrategia']}")

                    if op["Notas"]:
                        st.write(f"**Notas:** {op['Notas']}")

                    if st.button("🗑️ Eliminar", key=f"del_{i}"):
                        st.session_state.libro_trading = (
                            st.session_state.libro_trading.drop(i).reset_index(
                                drop=True
                            )
                        )
                        conn = sqlite3.connect("trade_analytics.db")
                        conn.execute("DELETE FROM operaciones WHERE id = ?", (i + 1,))
                        conn.commit()
                        conn.close()
                        st.success("✅ Operación eliminada")
                        st.rerun()

            # Estadísticas
            st.divider()
            st.subheader("📈 Estadísticas")
            total_ops = len(st.session_state.libro_trading)
            ganadoras = len(
                st.session_state.libro_trading[
                    st.session_state.libro_trading["Resultado"] > 0
                ]
            )
            tasa_acierto = (ganadoras / total_ops * 100) if total_ops > 0 else 0
            ganancia_total = st.session_state.libro_trading["Resultado"].sum()

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Operaciones", total_ops)
                st.metric("Operaciones Ganadoras", ganadoras)
            with col2:
                st.metric("Tasa de Acierto", f"{tasa_acierto:.1f}%")
                st.metric("Ganancia Total", format_currency(ganancia_total))
        else:
            st.info("📝 No hay operaciones registradas")

# Pestaña 3: TP/SL Calculator - INTELIGENTE (VERSIÓN CORREGIDA)
with tab3:
    st.header("🎯 TP/SL Calculator")
    st.info("Calcula Stop Loss y Take Profit automáticamente")

    col1, col2 = st.columns(2)

    with col1:
        st.text("PRECIO DE COMPRA:")
        precio_compra = st.number_input(
            "",
            min_value=0.0,
            value=866.0,
            step=1.0,
            format="%.0f",
            key="tp_precio_compra",
            help="Precio al que compraste o planeas comprar",
        )

        st.text("CAPITAL A INVERTIR:")
        capital_total = st.number_input(
            "",
            min_value=0.0,
            value=10000.0,
            step=100.0,
            format="%.0f",
            key="tp_capital",
            help="Monto total a invertir en la operación",
        )

    with col2:
        st.text("ACTIVO:")
        activo = st.text_input(
            "", "BTC", key="tp_activo", help="Símbolo del activo para análisis técnico"
        )

        # ✅ CORRECCIÓN: Asegurar que se ejecute la función
        if precio_compra > 0 and activo:
            stop_loss, take_profit = sugerir_sl_tp_inteligente(precio_compra, activo)

            st.text("STOP LOSS (sugerido):")
            st.info(f"${stop_loss:.2f}")

            st.text("TAKE PROFIT (sugerido):")
            st.success(f"${take_profit:.2f}")
        else:
            st.text("STOP LOSS (sugerido):")
            st.info("$0.00")

            st.text("TAKE PROFIT (sugerido):")
            st.success("$0.00")
            stop_loss, take_profit = 0, 0

    # ✅ CORRECCIÓN: Solo calcular si tenemos valores válidos
    if precio_compra > 0 and stop_loss > 0 and take_profit > 0:
        riesgo_por_unidad = precio_compra - stop_loss
        recompensa_por_unidad = take_profit - precio_compra
        ratio_rr = (
            recompensa_por_unidad / riesgo_por_unidad if riesgo_por_unidad > 0 else 0
        )
        tamaño_posicion = capital_total / precio_compra if precio_compra > 0 else 0
        inversion_total = tamaño_posicion * precio_compra
        perdida_potencial = (precio_compra - stop_loss) * tamaño_posicion
        ganancia_potencial = (take_profit - precio_compra) * tamaño_posicion

        st.markdown("---")
        st.subheader("📊 RESULTADOS")

        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.metric("Cantidad a comprar", f"{tamaño_posicion:.2f} unidades")
            st.metric("Inversión total", format_currency(inversion_total))
        with col_res2:
            st.metric("Pérdida potencial", format_currency(perdida_potencial))
            st.metric("Ganancia potencial", format_currency(ganancia_potencial))

        st.metric("Ratio Riesgo/Beneficio", f"1 : {ratio_rr:.2f}")

        # Gráfico
        fig, ax = plt.subplots(figsize=(10, 2))
        ax.barh(
            [0],
            [ganancia_potencial],
            left=[inversion_total],
            height=0.5,
            color="green",
            label="Ganancia",
        )
        ax.barh(
            [0],
            [perdida_potencial],
            left=[inversion_total - perdida_potencial],
            height=0.5,
            color="red",
            label="Pérdida",
        )
        ax.axvline(x=inversion_total, color="black", linestyle="--", label="Inversión")
        ax.set_yticks([])
        ax.set_xlabel("Capital ($)")
        ax.legend(loc="lower center")
        ax.grid(True, alpha=0.2, linestyle="--")
        ax.set_facecolor("#f8f9fa")
        st.pyplot(fig)
    else:
        st.warning("⏳ Ingresa un precio de compra válido para ver los resultados")

# Footer
st.divider()
st.caption("TradeAnalytics Pro © 2024 - Sistema premium de gestión de inversiones")
