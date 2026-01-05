import streamlit as st
import plotly.graph_objects as go
import numpy as np

# === НАСТРОЙКИ СТРАНИЦЫ (Киберпанк) ===
st.set_page_config(page_title="HOLO-DOCK V-15", layout="wide", page_icon="🏗️")

# Убираем лишние отступы и красим фон
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        .main { background-color: #02020a; color: #00ffff; }
        h1, h2, h3, span { color: #00ffff !important; text-shadow: 0 0 8px #00ffff; font-family: 'Courier New', monospace; }
        .stSelectbox label, .stSlider label { color: #ff00ff !important; }
        div[data-testid="stMetricValue"] { color: #ff00ff; text-shadow: 0 0 10px #ff00ff; }
    </style>
""", unsafe_allow_html=True)

# === РАСШИРЕННАЯ БАЗА ДАННЫХ ===

# Двигатели (параметры сопла и камеры)
ENGINES = {
    "MERLIN-1D (Kerolox)": {"thrust": 845, "len": 1.5, "c_r": 0.4, "t_r": 0.2, "e_r": 0.9, "color": "#ff9900"},
    "RAPTOR V2 (Methalox)": {"thrust": 2300, "len": 2.1, "c_r": 0.6, "t_r": 0.3, "e_r": 1.3, "color": "#ff00ff"},
    "BE-4 (Methalox)": {"thrust": 2400, "len": 2.8, "c_r": 0.7, "t_r": 0.4, "e_r": 1.5, "color": "#00ffff"},
    "F-1 V (Saturn Legacy)": {"thrust": 6770, "len": 3.5, "c_r": 1.2, "t_r": 0.8, "e_r": 2.5, "color": "#ff3300"},
    "ION-THRUSTER X9": {"thrust": 50, "len": 0.8, "c_r": 0.3, "t_r": 0.1, "e_r": 0.4, "color": "#00ffcc"},
    "GRAV-DRIVE (Experimental)": {"thrust": 5000, "len": 2.0, "c_r": 1.5, "t_r": 1.0, "e_r": 1.8, "color": "#ffffff"}
}

# Конфигурации ракет (Ступени, размеры, какие двигатели и сколько их)
ROCKETS = {
    "VECTOR-Scout (Light)": {
        "stages": [
            {"type": "body", "h": 14.0, "d": 2.0, "eng": "MERLIN-1D (Kerolox)", "count": 1}, # Ступень 1
            {"type": "body", "h": 6.0, "d": 1.8, "eng": "MERLIN-1D (Kerolox)", "count": 1},  # Ступень 2
            {"type": "fairing", "h": 4.0, "d": 1.8} # Обтекатель
        ]
    },
    "AERO-Vanguard (Medium)": {
        "stages": [
            {"type": "body", "h": 25.0, "d": 3.7, "eng": "BE-4 (Methalox)", "count": 2},
            {"type": "body", "h": 10.0, "d": 3.7, "eng": "RAPTOR V2 (Methalox)", "count": 1},
            {"type": "fairing", "h": 6.0, "d": 3.7}
        ]
    },
    "TITAN-Heavy (Orbital)": {
        "stages": [
            {"type": "body", "h": 35.0, "d": 5.5, "eng": "RAPTOR V2 (Methalox)", "count": 7}, # Кластер из 7 двигателей
            {"type": "body", "h": 15.0, "d": 5.5, "eng": "RAPTOR V2 (Methalox)", "count": 1},
            {"type": "fairing", "h": 8.0, "d": 5.5}
        ]
    },
    "STAR-CRUISER (Interplanetary)": {
        "stages": [
            {"type": "body", "h": 50.0, "d": 9.0, "eng": "F-1 V (Saturn Legacy)", "count": 9}, # Монстр
            {"type": "body", "h": 30.0, "d": 9.0, "eng": "GRAV-DRIVE (Experimental)", "count": 3},
            {"type": "fairing", "h": 15.0, "d": 9.0}
        ]
    }
}

# === ГЕНЕРАТОРЫ УЛЬТРА-ДЕТАЛИЗИРОВАННОЙ СЕТКИ ===
# nr=40, nt=80 - очень высокая плотность точек для "вау-эффекта"

def gen_cylinder(r_base, r_top, h, z_pos, nr=40, nt=80):
    t = np.linspace(0, 2*np.pi, nt)
    r = np.linspace(r_base, r_top, nr)
    T, R = np.meshgrid(t, r)
    X = R * np.cos(T)
    Y = R * np.sin(T)
    Z = np.linspace(z_pos, z_pos + h, nr)
    _, Z_mesh = np.meshgrid(t, Z)
    return X.flatten(), Y.flatten(), Z_mesh.flatten()

# Функция для создания одного двигателя в нужной точке
def build_engine(eng_data, ox, oy, oz, scale):
    l, cr, tr, er = eng_data['len']*scale, eng_data['c_r']*scale, eng_data['t_r']*scale, eng_data['e_r']*scale
    # Камера
    cx, cy, cz = gen_cylinder(cr, cr, l*0.5, oz, nr=20, nt=40)
    # Горловина
    tx, ty, tz = gen_cylinder(cr, tr, l*0.2, oz + l*0.5, nr=10, nt=40)
    # Сопло
    nx, ny, nz = gen_cylinder(tr, er, l*0.3, oz + l*0.7, nr=30, nt=60)
    return cx+ox, cy+oy, cz, tx+ox, ty+oy, tz, nx+ox, ny+oy, nz

# === ИНТЕРФЕЙС ===
st.title("🏗️ HOLO-DOCK // VECTOR-15 ARSENAL")

with st.sidebar:
    st.header("💠 ASSEMBLY CONFIG")
    rocket_name = st.selectbox("SELECT HULL CLASS", list(ROCKETS.keys()))
    st.markdown("---")
    st.header("📐 VIEW CONTROLS")
    scale = st.slider("Holo-Scale", 0.5, 2.0, 1.0, 0.1)
    rot_z = st.slider("Rotate Dock (Z-Axis)", 0, 360, 90, 5)

# === СБОРКА РАКЕТЫ (ГЛАВНЫЙ АЛГОРИТМ) ===
rocket_data = ROCKETS[rocket_name]
traces = []
current_z = 0.0
total_thrust = 0

# Математика вращения для слайдера
angle_rad = np.radians(rot_z)
cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)

def rotate_xy(x, y): return x*cos_a - y*sin_a, x*sin_a + y*cos_a

# Проходим по всем ступеням и собираем их
for stage in rocket_data["stages"]:
    h, d = stage["h"] * scale, stage["d"] * scale
    
    if stage["type"] == "body":
        # 1. Строим корпус ступени (Синий неон)
        bx, by, bz = gen_cylinder(d/2, d/2, h, current_z)
        rbx, rby = rotate_xy(bx, by)
        traces.append(go.Scatter3d(x=rbx, y=rby, z=bz, mode='lines', line=dict(color='#0088ff', width=3), opacity=0.4, name="Hull"))
        traces.append(go.Scatter3d(x=rbx, y=rby, z=bz, mode='markers', marker=dict(size=1.5, color='#00ffff'), opacity=0.6, name="Hull Grid"))
        
        # 2. Расставляем двигатели снизу ступени
        eng_info = ENGINES[stage["eng"]]
        count = stage["count"]
        total_thrust += eng_info["thrust"] * count
        
        # Вычисляем позиции для кластера двигателей
        if count == 1: offsets = [(0,0)]
        else:
            radius = (d/2) * 0.6 # Двигатели стоят по кругу внутри диаметра
            angles = np.linspace(0, 2*np.pi, count, endpoint=False)
            offsets = [(radius*np.cos(a), radius*np.sin(a)) for a in angles]
            
        for ox, oy in offsets:
            # Строим двигатель со смещением (Маджента неон)
            ecx, ecy, ecz, etx, ety, etz, enx, eny, enz = build_engine(eng_info, ox, oy, current_z - (eng_info['len']*scale), scale)
            # Вращаем и добавляем
            rcx, rcy = rotate_xy(ecx, ecy); rtx, rty = rotate_xy(etx, ety); rnx, rny = rotate_xy(enx, eny)
            
            eng_style = dict(mode='lines+markers', line=dict(color=eng_info['color'], width=2), marker=dict(size=2, color='#ffffff', opacity=0.8))
            traces.append(go.Scatter3d(x=rcx, y=rcy, z=ecz, **eng_style, name="Chamber"))
            traces.append(go.Scatter3d(x=rnx, y=rny, z=enz, **eng_style, name="Nozzle"))

    elif stage["type"] == "fairing":
        # 3. Строим обтекатель сверху (Циан неон)
        fx, fy, fz = gen_cylinder(d/2, 0, h, current_z, nr=50) # Верхний радиус 0 = конус
        rfx, rfy = rotate_xy(fx, fy)
        traces.append(go.Scatter3d(x=rfx, y=rfy, z=fz, mode='lines', line=dict(color='#00ffff', width=3), opacity=0.5, name="Fairing"))
        traces.append(go.Scatter3d(x=rfx, y=rfy, z=fz, mode='markers', marker=dict(size=2, color='#ffffff'), opacity=0.8, name="Fairing Grid"))

    current_z += h # Поднимаемся выше для следующей ступени

# === ВИЗУАЛИЗАЦИЯ ===
c1, c2 = st.columns([3, 1])

with c1:
    # Настройка 3D сцены
    fig = go.Figure(data=traces)
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False, range=[-15, 15]),
            yaxis=dict(visible=False, range=[-15, 15]),
            zaxis=dict(visible=False, range=[0, 100]), # Высокая ось Z для больших ракет
            bgcolor='#02020a',
            aspectmode='data' # Сохранять реальные пропорции
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='#02020a',
        showlegend=False,
        height=700 # Высокое окно
    )
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.header("📊 SPEC SHEET")
    st.metric("TOTAL STACK HEIGHT", f"{current_z:.1f} M")
    st.metric("LIFTOFF THRUST", f"{total_thrust/1000:.1f} MN")
    st.markdown("---")
    st.write("STAGES DETECTED:")
    for i, stage in enumerate(rocket_data["stages"]):
        if stage["type"] == "body":
            st.code(f"STAGE {i+1}: {stage['count']}x {stage['eng']}")
    st.markdown("---")
    st.caption("HOLO-RENDER CORE V3 // GPU ACCELERATED")