import streamlit as st
import cv2
import numpy as np
import plotly.graph_objects as go
import math

# === 1. НАСТРОЙКИ ===
st.set_page_config(page_title="VECTOR-15 FINAL", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
        .stApp { background-color: #000000; color: #00ff00; }
        h1, h2, h3 { color: #00ff00; font-family: 'Courier New', monospace; text-shadow: 0 0 10px #00ff00; }
        .stSlider { color: #00ff00; }
    </style>
""", unsafe_allow_html=True)

# === 2. 3D ФУНКЦИИ (Сетка) ===
def get_rocket_parts(scale, rotation):
    def cyl(r, h, z0):
        t = np.linspace(0, 2*np.pi, 20)
        z = np.linspace(z0, z0+h, 5)
        T, Z = np.meshgrid(t, z)
        X = r * np.cos(T)
        Y = r * np.sin(T)
        return X, Y, Z

    parts = [cyl(0.5*scale, 1.5*scale, 0), cyl(0.3*scale, 0.5*scale, 1.5*scale), cyl(0.8*scale, 1.0*scale, 2.0*scale)]
    
    rad = np.radians(rotation)
    c, s = np.cos(rad), np.sin(rad)
    return [(X*c - Y*s, X*s + Y*c, Z) for X, Y, Z in parts]

# === 3. ИНТЕРФЕЙС ===
st.title("🚀 VECTOR-15 // SYSTEM ONLINE")

c1, c2 = st.columns([1, 3])

if 'zoom' not in st.session_state: st.session_state.zoom = 1.0
if 'rot' not in st.session_state: st.session_state.rot = 0.0

# === ЛОГИКА КАМЕРЫ ===
with c1:
    st.header("SENSOR ARRAY")
    use_cam = st.checkbox("ACTIVATE OPTICS", value=True)
    status = st.empty()
    frame_box = st.empty()
    
    manual = True
    
    if use_cam:
        try:
            # ИМПОРТ ВНУТРИ (Защита от сбоев загрузки)
            import mediapipe as mp
            
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                status.warning("⚠️ SERVER MODE: OPTICS OFFLINE")
                st.caption("Running in Cloud Mode. Manual overrides active.")
            else:
                status.success("🟢 OPTICS ONLINE")
                manual = False
                
                hands = mp.solutions.hands.Hands(max_num_hands=1)
                ret, frame = cap.read()
                if ret:
                    frame = cv2.flip(frame, 1)
                    res = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    
                    if res.multi_hand_landmarks:
                        for lm in res.multi_hand_landmarks:
                            mp.solutions.drawing_utils.draw_landmarks(frame, lm, mp.solutions.hands.HAND_CONNECTIONS)
                            # Простая логика жестов
                            d = math.hypot(lm.landmark[4].x - lm.landmark[8].x, lm.landmark[4].y - lm.landmark[8].y)
                            st.session_state.zoom = np.interp(d, [0.05, 0.2], [0.5, 2.5])
                            st.session_state.rot = np.interp(lm.landmark[9].x, [0.2, 0.8], [-180, 180])
                    
                    frame_box.image(frame, channels="BGR")
                cap.release()
                
        except Exception as e:
            status.error(f"MODULE ERROR: {e}")
            manual = True

    if manual:
        st.write("---")
        st.session_state.zoom = st.slider("MANUAL ZOOM", 0.5, 3.0, st.session_state.zoom)
        st.session_state.rot = st.slider("MANUAL ROTATION", -180, 180, int(st.session_state.rot))

# === ОТРИСОВКА ===
with c2:
    fig = go.Figure()
    for X, Y, Z in get_rocket_parts(st.session_state.zoom, st.session_state.rot):
        for i in range(X.shape[0]): fig.add_trace(go.Scatter3d(x=X[i], y=Y[i], z=Z[i], mode='lines', line=dict(color='#00ff00')))
        for i in range(X.shape[1]): fig.add_trace(go.Scatter3d(x=X[:,i], y=Y[:,i], z=Z[:,i], mode='lines', line=dict(color='#00ff00')))
    
    fig.update_layout(scene=dict(bgcolor='black', xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False)), height=600, margin=dict(t=0,b=0,l=0,r=0))
    st.plotly_chart(fig, use_container_width=True)