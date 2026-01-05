import streamlit as st
import cv2
import numpy as np
import mediapipe as mp
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import math
import time

# --- 1. НАСТРОЙКИ (Стиль: Неоновый Чертеж) ---
st.set_page_config(page_title="SPACEF", layout="wide", page_icon="🚀")

st.markdown("""
<style>
    .stApp { background-color: #00020a; color: #00ffff; }
    h1, h2, h3 { color: #00ffff; font-family: 'Courier New', monospace; text-transform: uppercase; text-shadow: 0 0 10px #00ffff; }
    img { border: 2px solid #00ffff; opacity: 0.9; box-shadow: 0 0 20px #0044ff; border-radius: 5px; }
    div[data-testid="stMetricValue"] { color: #ccffff; font-family: 'Consolas', monospace; text-shadow: 0 0 12px #00ffff; }
    .stCheckbox { color: #00ffff; }
</style>
""", unsafe_allow_html=True)

# --- 2. БАЗА ДАННЫХ ---
ENGINES_DB = {
    "SpaceX Raptor 2": {
        "c_r": 200, "t_r": 90, "e_r": 650, "len": 2400, "p": 300,
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/Raptor_2_engine_on_stand_%28cropped%29.jpg/800px-Raptor_2_engine_on_stand_%28cropped%29.jpg"
    },
    "Rocketdyne F-1": {
        "c_r": 500, "t_r": 250, "e_r": 1850, "len": 3600, "p": 70,
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/F-1_rocket_engine.jpg/800px-F-1_rocket_engine.jpg"
    },
    "SpaceX Merlin 1D": {
        "c_r": 140, "t_r": 60, "e_r": 450, "len": 1900, "p": 97,
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Merlin_1D_Engine.jpg/640px-Merlin_1D_Engine.jpg"
    }
}

if 'hand_scale' not in st.session_state: st.session_state.hand_scale = 1.0
if 'rotation_angle' not in st.session_state: st.session_state.rotation_angle = 0.0

# --- 3. ФИЗИЧЕСКОЕ ЯДРО (APOGEE SIMULATION) ---
def calculate_performance(chamber_p, t_r, e_r):
    # Упрощенная физика тяги
    # Переводим радиусы (мм) в площади (м2)
    t_area = math.pi * (t_r / 1000) ** 2
    e_area = math.pi * (e_r / 1000) ** 2
    expansion = e_area / (t_area + 1e-9)
    
    # Тяга (F = P * A * Eff)
    pressure_pa = chamber_p * 100000
    thrust = pressure_pa * t_area * 1.6 
    
    # ISP (Удельный импульс)
    isp = 250 + (expansion * 0.15)
    if isp > 350: isp = 350
    
    return thrust, isp

def simulate_flight(thrust, isp, fuel_mass, dry_mass=2000):
    # Симуляция полета для графика
    g = 9.81
    dt = 0.5
    current_mass = dry_mass + fuel_mass
    mass_flow = thrust / (isp * g)
    
    alt = 0
    vel = 0
    time_elapsed = 0
    data = []
    
    while True:
        # 1. Тяга
        if current_mass > dry_mass:
            f_thrust = thrust
            current_mass -= mass_flow * dt
        else:
            f_thrust = 0 # Топливо кончилось
            
        # 2. Силы
        weight = current_mass * g
        # Сопротивление воздуха (упрощенно)
        drag = 0.5 * 1.2 * (vel**2) * 2.0 * 0.5 
        if vel < 0: drag = -drag # Сопротивление при падении
        
        net_force = f_thrust - weight - drag
        
        # 3. Движение
        acc = net_force / current_mass
        vel += acc * dt
        alt += vel * dt
        time_elapsed += dt
        
        data.append({"Time": time_elapsed, "Altitude": alt})
        
        # Условия выхода
        if vel < 0 and f_thrust == 0: break # Начали падать (Апогей)
        if alt < -10: break
        
    return alt, pd.DataFrame(data)

# --- 4. 3D ГЕНЕРАТОРЫ (PRIME DETAILS) ---
def generate_neon_pipes(c_r, length):
    px, py, pz = [], [], []
    len_head = length * 0.25
    z_spiral = np.linspace(len_head, length*0.6, 60)
    theta_spiral = np.linspace(0, 8*np.pi, 60) 
    r_spiral = c_r * 1.15 
    px.extend(r_spiral * np.cos(theta_spiral)); px.append(None)
    py.extend(r_spiral * np.sin(theta_spiral)); py.append(None)
    pz.extend(z_spiral); pz.append(None)
    
    # Downcomer
    z_down = np.linspace(len_head*0.5, length*0.7, 10)
    r_down = c_r * 1.5 
    px.extend(np.full_like(z_down, r_down)); px.append(None)
    py.extend(np.zeros_like(z_down)); py.append(None)
    pz.extend(z_down); pz.append(None)
    
    px.extend([r_down, c_r]); px.append(None)
    py.extend([0, 0]); py.append(None)
    pz.extend([len_head*0.5, len_head*0.5]); pz.append(None)
    return px, py, pz

def generate_details(c_r, length, pipe_x, pipe_y, pipe_z):
    vx, vy, vz = [], [], []
    for i in range(0, len(pipe_x), 8):
        if pipe_x[i] is not None:
            vx.append(pipe_x[i]); vy.append(pipe_y[i]); vz.append(pipe_z[i])
            
    ax, ay, az = [], [], []
    box_r = c_r * 1.6
    corners_x = [box_r, -box_r, -box_r, box_r, box_r]
    corners_y = [box_r, box_r, -box_r, -box_r, box_r]
    h1, h2 = length*0.1, length*0.2
    
    ax.extend(corners_x); ax.append(None); ay.extend(corners_y); ay.append(None); az.extend([h1]*5); az.append(None)
    ax.extend(corners_x); ax.append(None); ay.extend(corners_y); ay.append(None); az.extend([h2]*5); az.append(None)
    for i in range(4):
        ax.extend([corners_x[i], corners_x[i]]); ax.append(None)
        ay.extend([corners_y[i], corners_y[i]]); ay.append(None)
        az.extend([h1, h2]); az.append(None)
    return vx, vy, vz, ax, ay, az

def generate_final_mesh(c_r, t_r, e_r, length, scale, angle_rad):
    c_r, t_r, e_r, length = c_r*scale, t_r*scale, e_r*scale, length*scale
    
    # Hull
    hx, hy, hz = [], [], []
    len_head, len_chamber = length * 0.2, length * 0.15
    for i in range(12):
        theta = (2*np.pi/12)*i
        z_pts = np.linspace(0, length, 15)
        r_pts = []
        for h in z_pts:
            if h < len_head: r=c_r*1.1
            elif h < len_head+len_chamber: r=c_r
            elif h < len_head+len_chamber+length*0.05: r=np.interp(h, [len_head+len_chamber, len_head+len_chamber+length*0.05], [c_r, t_r])
            else: 
                t=(h-(len_head+len_chamber+length*0.05))/(length-(len_head+len_chamber+length*0.05))
                r=t_r+(e_r-t_r)*np.sqrt(t)
            r_pts.append(r)
        hx.extend(np.array(r_pts)*np.cos(theta)); hx.append(None)
        hy.extend(np.array(r_pts)*np.sin(theta)); hy.append(None)
        hz.extend(z_pts); hz.append(None)
        
    for h in np.linspace(0, length, 15):
        if h < len_head: r=c_r*1.1
        elif h < len_head+len_chamber: r=c_r
        elif h > length*0.4: r=t_r+(e_r-t_r)*((h-length*0.4)/(length*0.6))
        else: r=t_r
        th = np.linspace(0, 2*np.pi, 20)
        hx.extend(r*np.cos(th)); hx.append(None)
        hy.extend(r*np.sin(th)); hy.append(None)
        hz.extend(np.full_like(th, h)); hz.append(None)

    px, py, pz = generate_neon_pipes(c_r, length)
    vx, vy, vz, ax, ay, az = generate_details(c_r, length, px, py, pz)

    # Rotation
    cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
    def rot(x, y):
        xr, yr = [], []
        for i in range(len(x)):
            if x[i] is None: xr.append(None); yr.append(None)
            else: xr.append(x[i]*cos_a - y[i]*sin_a); yr.append(x[i]*sin_a + y[i]*cos_a)
        return xr, yr
    
    hx, hy = rot(hx, hy)
    px, py = rot(px, py)
    vx, vy = rot(vx, vy)
    ax, ay = rot(ax, ay)
    
    return hx, hy, hz, px, py, pz, vx, vy, vz, ax, ay, az

# --- 5. ИНТЕРФЕЙС ---
st.title( "🚀 SPACEF")

selected_engine = st.selectbox("SELECT BLUEPRINT:", list(ENGINES_DB.keys()))
db = ENGINES_DB[selected_engine]

# === ЛЕВЫЙ СТОЛБЕЦ: ПАРАМЕТРЫ И ФИЗИКА ===
col_left, col_right = st.columns([1, 2])

with col_left:
    st.markdown("### ⚙️ ENGINEERING")
    
    # Слайдеры (влияют и на 3D, и на Физику)
    pressure = st.slider("Pressure (Bar)", 50, 400, db["p"])
    scale_factor = st.slider("Scale Modifier", 0.5, 2.0, 1.0)
    
    # Данные для расчетов (из базы * масштаб)
    c_r_calc = db["c_r"] * scale_factor
    t_r_calc = db["t_r"] * scale_factor
    e_r_calc = db["e_r"] * scale_factor
    
    # 1. РАСЧЕТ ТЯГИ
    thrust, isp = calculate_performance(pressure, t_r_calc, e_r_calc)
    
    c1, c2 = st.columns(2)
    c1.metric("THRUST", f"{thrust/1000:,.0f} kN")
    c2.metric("ISP", f"{int(isp)} s")
    
    st.markdown("---")
    st.markdown("### ⛽ MISSION CONTROL")
    fuel = st.slider("Fuel Mass (kg)", 1000, 200000, 50000)
    
    # 2. РАСЧЕТ ПОЛЕТА
    apogee, df_traj = simulate_flight(thrust, isp, fuel)
    
    st.metric("PREDICTED APOGEE", f"{apogee/1000:.1f} km", delta="Space" if apogee>100000 else "Sub-orbital")
    
    # График
    fig_traj = px.line(df_traj, x="Time", y="Altitude", title="Mission Trajectory")
    fig_traj.update_traces(line_color='#39ff14')
    fig_traj.update_layout(
        plot_bgcolor="#00020a", paper_bgcolor="#00020a", font=dict(color="white"),
        margin=dict(t=30,b=0,l=0,r=0), height=200, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#333")
    )
    st.plotly_chart(fig_traj, use_container_width=True)

# === ПРАВЫЙ СТОЛБЕЦ: 3D ГОЛОГРАММА ===
with col_right:
    st.markdown(f"### 🧊 HOLOGRAM: {selected_engine.upper()}")
    
    s = st.session_state.hand_scale
    a = st.session_state.rotation_angle
    
    # Используем модификаторы слайдеров для базы данных при генерации
    # Но жест руки (s) накладывается сверху для визуального зума
    
    hx, hy, hz, px, py, pz, vx, vy, vz, ax, ay, az = generate_final_mesh(
        db["c_r"]*scale_factor, db["t_r"]*scale_factor, db["e_r"]*scale_factor, db["len"]*scale_factor, 
        s, a
    )
    
    fig = go.Figure()
    # Hull
    fig.add_trace(go.Scatter3d(x=hx, y=hy, z=hz, mode='lines', line=dict(color='#00ffff', width=2), opacity=0.4, name='Hull'))
    # Pipes
    fig.add_trace(go.Scatter3d(x=px, y=py, z=pz, mode='lines', line=dict(color='#39ff14', width=5), opacity=1.0, name='Fuel Lines'))
    # Details
    fig.add_trace(go.Scatter3d(x=vx, y=vy, z=vz, mode='markers', marker=dict(color='white', size=3), opacity=0.8, name='Sensors'))
    fig.add_trace(go.Scatter3d(x=ax, y=ay, z=az, mode='lines', line=dict(color='#00ccff', width=3), opacity=0.7, name='Avionics'))
    
    fig.update_layout(
        scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False), aspectmode='data', bgcolor='#00020a', camera=dict(eye=dict(x=0, y=2.8, z=0.6))),
        margin=dict(t=0, b=0, l=0, r=0), height=700, paper_bgcolor='#00020a', showlegend=False
    )
    
    view_ph = st.empty()
    view_ph.plotly_chart(fig, use_container_width=True)

# === УПРАВЛЕНИЕ ===
st.markdown("---")
run = st.checkbox("ACTIVATE GESTURE CONTROL", value=True)

if run:
    c_cam, c_stat = st.columns([1, 4])
    with c_cam: cam_ph = st.empty()
    with c_stat: status_ph = st.empty()

    try:
        hands = mp.solutions.hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
        
        # Попытка подключиться к камере (только для локального запуска)
        cap = cv2.VideoCapture(0) 
        if not cap.isOpened():
            status_ph.warning("⚠️ CAMERA NOT FOUND (Server Mode). Use sliders to control the engine.")
            # Если камеры нет, просто останавливаем этот блок, но сайт продолжает работать
            run = False 
        else:
            status_ph.info("Gestures Active: Pinch to Zoom, Rotate hands to Spin.")

        last_t = 0
        rot_speed = 0
        
        while run and cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = hands.process(rgb)
            h, w, _ = frame.shape
            
            if res.multi_hand_landmarks and len(res.multi_hand_landmarks) == 2:
                p1 = res.multi_hand_landmarks[0].landmark[8]
                p2 = res.multi_hand_landmarks[1].landmark[8]
                cx1, cy1 = int(p1.x*w), int(p1.y*h)
                cx2, cy2 = int(p2.x*w), int(p2.y*h)
                
                dist = math.hypot(cx2-cx1, cy2-cy1)
                st.session_state.hand_scale = np.interp(dist, [50, 500], [0.5, 2.5])
                
                dy = cy2 - cy1
                if abs(dy) > 30: rot_speed = dy * 0.002
                else: rot_speed = 0
                st.session_state.rotation_angle += rot_speed
                cv2.line(frame, (cx1, cy1), (cx2, cy2), (0, 255, 0), 2)
                
            cam_ph.image(frame, channels="BGR")
            
            # Обновление 3D (раз в 0.1 сек)
            if time.time() - last_t > 0.1:
                s = st.session_state.hand_scale
                a = st.session_state.rotation_angle
                hx, hy, hz, px, py, pz, vx, vy, vz, ax, ay, az = generate_final_mesh(
                    db["c_r"]*scale_factor, db["t_r"]*scale_factor, db["e_r"]*scale_factor, db["len"]*scale_factor, 
                    s, a
                )
                with fig.batch_update():
                    fig.data[0].x, fig.data[0].y, fig.data[0].z = hx, hy, hz
                    fig.data[1].x, fig.data[1].y, fig.data[1].z = px, py, pz
                    fig.data[2].x, fig.data[2].y, fig.data[2].z = vx, vy, vz
                    fig.data[3].x, fig.data[3].y, fig.data[3].z = ax, ay, az
                view_ph.plotly_chart(fig, use_container_width=True, key=f"v_{time.time()}")
                last_t = time.time()
                
        if cap: cap.release()
        
    except Exception as e:
        # Если библиотека крашнулась - не ломаем весь сайт
        status_ph.error(f"Gesture Control Error: {e}")