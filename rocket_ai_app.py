import streamlit as st
import plotly.graph_objects as go
import numpy as np

# === НАСТРОЙКИ СТРАНИЦЫ ===
st.set_page_config(page_title="VECTOR-15 SOLID", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
        .main { background-color: #0e1117; }
        h1, h2, h3 { color: #ffffff; font-family: sans-serif; }
    </style>
""", unsafe_allow_html=True)

# === БАЗА ДАННЫХ ===
ENGINES = {
    "Merlin-1D": {"thrust": 845, "len": 1.5, "r": 0.5, "color": "orange"},
    "Raptor V2": {"thrust": 2300, "len": 2.2, "r": 0.7, "color": "purple"},
    "F-1 Legacy": {"thrust": 6770, "len": 3.8, "r": 1.8, "color": "red"},
    "Ion-X": {"thrust": 50, "len": 0.8, "r": 0.4, "color": "cyan"}
}

ROCKETS = {
    "VECTOR-Scout": {
        "stages": [
            {"h": 12.0, "d": 2.0, "eng": "Merlin-1D", "count": 1, "color": "lightgray"},
            {"h": 5.0, "d": 2.0, "eng": "Merlin-1D", "count": 1, "color": "white"}
        ]
    },
    "TITAN-Heavy": {
        "stages": [
            {"h": 30.0, "d": 4.0, "eng": "Raptor V2", "count": 7, "color": "silver"}, # 7 двигателей!
            {"h": 15.0, "d": 4.0, "eng": "Raptor V2", "count": 1, "color": "white"}
        ]
    },
    "STAR-CRUISER": {
        "stages": [
            {"h": 50.0, "d": 9.0, "eng": "F-1 Legacy", "count": 12, "color": "darkgray"}, # Монстр
            {"h": 25.0, "d": 9.0, "eng": "Ion-X", "count": 6, "color": "gray"}
        ]
    }
}

# === ФУНКЦИИ 3D (ТВЕРДЫЕ ТЕЛА) ===
def cylinder(r, h, z0, color_scale='Gray'):
    # Создает твердый цилиндр
    theta = np.linspace(0, 2*np.pi, 50)
    z = np.linspace(z0, z0+h, 10)
    theta_grid, z_grid = np.meshgrid(theta, z)
    x_grid = r * np.cos(theta_grid)
    y_grid = r * np.sin(theta_grid)
    return x_grid, y_grid, z_grid

def cone(r_base, h, z0):
    # Создает конус (обтекатель)
    theta = np.linspace(0, 2*np.pi, 50)
    z = np.linspace(z0, z0+h, 10)
    theta_grid, z_grid = np.meshgrid(theta, z)
    # Радиус уменьшается с высотой
    r_grid = r_base * (1 - (z_grid - z0)/h)
    x_grid = r_grid * np.cos(theta_grid)
    y_grid = r_grid * np.sin(theta_grid)
    return x_grid, y_grid, z_grid

# === ИНТЕРФЕЙС ===
st.title("🚀 VECTOR-15 DESIGN BUREAU")
st.write("Solid-State Rendering Core Active")

with st.sidebar:
    st.header("Configuration")
    model = st.selectbox("Select Rocket Model", list(ROCKETS.keys()))
    scale = st.slider("Scale Factor", 0.5, 2.0, 1.0)

# === СБОРКА СЦЕНЫ ===
fig = go.Figure()
rocket = ROCKETS[model]
current_z = 0

# 1. Рисуем ступени и двигатели
for stage in rocket["stages"]:
    h, d = stage["h"] * scale, stage["d"] * scale
    
    # КОРПУС (Solid Surface)
    x, y, z = cylinder(d/2, h, current_z)
    fig.add_trace(go.Surface(x=x, y=y, z=z, colorscale='Greys', showscale=False, opacity=1.0, lighting=dict(ambient=0.5, diffuse=0.8)))
    
    # ДВИГАТЕЛИ
    eng_name = stage["eng"]
    eng_data = ENGINES[eng_name]
    count = stage["count"]
    
    # Логика расстановки (Кластер)
    offsets = []
    if count == 1: offsets = [(0,0)]
    else:
        # Расставляем по кругу
        r_circle = (d/2) * 0.6
        angles = np.linspace(0, 2*np.pi, count, endpoint=False)
        offsets = [(r_circle*np.cos(a), r_circle*np.sin(a)) for a in angles]
    
    # Рисуем каждый двигатель как конус/сопло
    for ox, oy in offsets:
        eng_len = eng_data['len'] * scale
        eng_r = eng_data['r'] * scale
        
        # Сопло (Конус вниз)
        theta = np.linspace(0, 2*np.pi, 20)
        z_nozzle = np.linspace(current_z - eng_len, current_z, 10)
        th_g, z_g = np.meshgrid(theta, z_nozzle)
        # Радиус растет к низу (сопло)
        r_g = eng_r * ((current_z - z_g)/eng_len * 0.5 + 0.5) 
        
        x_eng = r_g * np.cos(th_g) + ox
        y_eng = r_g * np.sin(th_g) + oy
        
        # Цвет сопла зависит от типа
        cscale = 'Oranges' if 'Merlin' in eng_name or 'F-1' in eng_name else 'Bluered'
        
        fig.add_trace(go.Surface(x=x_eng, y=y_eng, z=z_g, colorscale=cscale, showscale=False))

    current_z += h

# 2. Обтекатель сверху (Нос)
last_d = rocket["stages"][-1]["d"] * scale
xf, yf, zf = cone(last_d/2, 5.0 * scale, current_z)
fig.add_trace(go.Surface(x=xf, y=yf, z=zf, colorscale='Greys', showscale=False))

# === ОТОБРАЖЕНИЕ ===
fig.update_layout(
    scene=dict(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        zaxis=dict(visible=False),
        aspectmode='data'
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    height=700,
    paper_bgcolor='#0e1117'
)

st.plotly_chart(fig, use_container_width=True)
st.metric("Total Height", f"{(current_z + 5*scale):.1f} meters")