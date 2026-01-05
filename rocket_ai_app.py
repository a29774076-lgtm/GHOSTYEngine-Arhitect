import streamlit as st
import cv2
import numpy as np
import mediapipe as mp
import plotly.graph_objects as go
import math

# === 1. НАСТРОЙКИ (Стиль: Неоновый Чертеж) ===
st.set_page_config(page_title="SPACEF", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
        .stApp { background-color: #000000; color: #00ff00; }
        h1, h2, h3 { color: #00ff00; font-family: 'Courier New', monospace; text-shadow: 0 0 10px #00ff00; }
        .stSlider { color: #00ff00; }
    </style>
""", unsafe_allow_html=True)

# === 2. ФУНКЦИИ 3D (Старая сетка Wireframe) ===
def generate_wireframe_cylinder(r, h, z_offset):
    # Создаем точки для "скелета" ракеты
    theta = np.linspace(0, 2*np.pi, 20)
    z = np.linspace(z_offset, z_offset + h, 8)
    T, Z = np.meshgrid(theta, z)
    X = r * np.cos(T)
    Y = r * np.sin(T)
    return X, Y, Z

def get_rocket_parts(scale, rotation):
    # Размеры частей
    parts = []
    # Камера сгорания
    parts.append(generate_wireframe_cylinder(0.5*scale, 1.5*scale, 0))
    # Горловина
    parts.append(generate_wireframe_cylinder(0.3*scale, 0.5*scale, 1.5*scale))
    # Сопло
    parts.append(generate_wireframe_cylinder(0.8*scale, 1.0*scale, 2.0*scale))
    
    # Вращение
    rad = np.radians(rotation)
    c, s = np.cos(rad), np.sin(rad)
    
    rotated_parts = []
    for X, Y, Z in parts:
        Rx = X * c - Y * s
        Ry = X * s + Y * c
        rotated_parts.append((Rx, Ry, Z))
        
    return rotated_parts

# === 3. ИНТЕРФЕЙС ===
st.title("🖐️ VECTOR-15 // NEON GESTURE CORE")

col_control, col_view = st.columns([1, 3])

# Переменные состояния (чтобы хранить зум и поворот)
if 'zoom' not in st.session_state: st.session_state.zoom = 1.0
if 'angle' not in st.session_state: st.session_state.angle = 0.0

# === БЛОК УПРАВЛЕНИЯ (КАМЕРА ИЛИ СЛАЙДЕРЫ) ===
with col_control:
    st.header("SENSOR DATA")
    use_camera = st.checkbox("ACTIVATE OPTICAL SENSOR", value=True)
    status_log = st.empty()
    cam_preview = st.empty()
    
    manual_mode = False

    if use_camera:
        try:
            # Инициализация ИИ
            mp_hands = mp.solutions.hands
            hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
            
            # Попытка открыть камеру
            cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                # ЕСЛИ КАМЕРЫ НЕТ (СЕРВЕР)
                status_log.warning("⚠️ SERVER MODE: OPTICS OFFLINE")
                st.info("Remote server detected. Switching to Manual Override.")
                manual_mode = True # Включаем ручной режим
            else:
                # ЕСЛИ КАМЕРА ЕСТЬ (ЛОКАЛЬНО)
                status_log.success("🟢 OPTICS ONLINE: TRACKING HANDS")
                
                # Читаем кадр (в цикле Streamlit это работает как один кадр за обновление)
                ret, frame = cap.read()
                if ret:
                    frame = cv2.flip(frame, 1)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    res = hands.process(rgb)
                    
                    if res.multi_hand_landmarks:
                        for lm in res.multi_hand_landmarks:
                            # Рисуем скелет руки
                            mp.solutions.drawing_utils.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS)
                            
                            # Логика жестов
                            # 1. Зум (расстояние между большим и указательным)
                            x1, y1 = lm.landmark[4].x, lm.landmark[4].y
                            x2, y2 = lm.landmark[8].x, lm.landmark[8].y
                            dist = math.hypot(x2-x1, y2-y1)
                            st.session_state.zoom = np.interp(dist, [0.05, 0.3], [0.5, 3.0])
                            
                            # 2. Вращение (координата X ладони)
                            cx = lm.landmark[9].x
                            st.session_state.angle = np.interp(cx, [0.2, 0.8], [-180, 180])

                    cam_preview.image(frame, channels="BGR")
                
                cap.release() # Освобождаем камеру

        except Exception as e:
            status_log.error(f"SENSOR ERROR: {e}")
            manual_mode = True
    else:
        manual_mode = True

    # РУЧНОЕ УПРАВЛЕНИЕ (Если камера выключена или недоступна)
    if manual_mode:
        st.write("---")
        st.write("**MANUAL OVERRIDE**")
        st.session_state.zoom = st.slider("ZOOM LEVEL", 0.5, 3.0, st.session_state.zoom)
        st.session_state.angle = st.slider("ROTATION", -180, 180, int(st.session_state.angle))

# === 4. ОТРИСОВКА 3D (ГОЛОГРАММА) ===
with col_view:
    fig = go.Figure()
    
    parts = get_rocket_parts(st.session_state.zoom, st.session_state.angle)
    colors = ['#00ff00', '#00ffff', '#ff00ff'] # Неоновые цвета
    
    for i, (X, Y, Z) in enumerate(parts):
        # Рисуем линии (сетку)
        for j in range(X.shape[0]):
            fig.add_trace(go.Scatter3d(x=X[j,:], y=Y[j,:], z=Z[j,:], mode='lines', line=dict(color=colors[i], width=4)))
        for j in range(X.shape[1]):
            fig.add_trace(go.Scatter3d(x=X[:,j], y=Y[:,j], z=Z[:,j], mode='lines', line=dict(color=colors[i], width=4)))
        
        # Точки на стыках
        fig.add_trace(go.Scatter3d(x=X.flatten(), y=Y.flatten(), z=Z.flatten(), mode='markers', marker=dict(size=3, color='white')))

    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False, range=[-4, 4]),
            yaxis=dict(visible=False, range=[-4, 4]),
            zaxis=dict(visible=False, range=[0, 8]),
            bgcolor='#000000'
        ),
        paper_bgcolor='#000000',
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)