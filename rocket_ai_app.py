import streamlit as st
import numpy as np
import plotly.graph_objects as go
import cv2
import mediapipe as mp

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="Stark Lab: Gesture Control", page_icon="🖐️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #000000; }
    h1, h2, h3 { color: #00FFFF !important; font-family: 'Courier New'; }
    .stMetric { background-color: #111; border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

st.title("🖐️ GESTURE CONTROL INTERFACE")

# --- 1. ИНИЦИАЛИЗАЦИЯ MEDIAPIPE (ЗРЕНИЕ ИИ) ---
if 'mp_hands' not in st.session_state:
    st.session_state.mp_hands = mp.solutions.hands
    st.session_state.hands = st.session_state.mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    st.session_state.mp_draw = mp.solutions.drawing_utils

# --- 2. ФУНКЦИЯ ГЕНЕРАЦИИ РАКЕТЫ (УПРОЩЕННАЯ ДЛЯ СКОРОСТИ) ---
def get_rocket_fig(length, diameter):
    radius = diameter / 2.0
    resolution = 20 # Снизил детализацию для скорости (FPS)
    theta = np.linspace(0, 2*np.pi, resolution)
    
    fig = go.Figure()
    
    # КОРПУС
    z_body = np.linspace(0, length, resolution)
    theta_grid, z_grid = np.meshgrid(theta, z_body)
    x_grid = radius * np.cos(theta_grid)
    y_grid = radius * np.sin(theta_grid)
    
    fig.add_trace(go.Surface(x=x_grid, y=y_grid, z=z_grid, colorscale='Electric', showscale=False, opacity=0.8))

    # НОС
    nose_h = radius * 3
    z_nose = np.linspace(length, length + nose_h, resolution)
    r_nose = np.linspace(radius, 0, resolution)
    theta_grid, z_grid_n = np.meshgrid(theta, z_nose)
    r_grid, _ = np.meshgrid(r_nose, z_nose)
    x_nose = r_grid * np.cos(theta_grid)
    y_nose = r_grid * np.sin(theta_grid)
    
    fig.add_trace(go.Surface(x=x_nose, y=y_nose, z=z_grid_n, colorscale='Reds', showscale=False, opacity=0.9))

    # НАСТРОЙКИ
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False, backgroundcolor="black"),
            yaxis=dict(visible=False, backgroundcolor="black"),
            zaxis=dict(visible=False, backgroundcolor="black"),
            aspectmode='data',
            camera=dict(eye=dict(x=2.5, y=0, z=0)) # Вид сбоку
        ),
        paper_bgcolor="black",
        margin=dict(l=0, r=0, b=0, t=0),
        height=500
    )
    return fig

# --- 3. ИНТЕРФЕЙС УПРАВЛЕНИЯ ---
col_cam, col_3d = st.columns([1, 1])

with col_cam:
    st.subheader("CAMERA FEED")
    run_camera = st.checkbox("ACTIVATE WEBCAM LINK", value=False)
    cam_placeholder = st.empty()
    debug_text = st.empty()

with col_3d:
    st.subheader("HOLOGRAPHIC PROJECTION")
    chart_placeholder = st.empty()
    metrics_placeholder = st.empty()

# --- 4. ГЛАВНЫЙ ЦИКЛ (THE LOOP) ---
if run_camera:
    cap = cv2.VideoCapture(0) # 0 - это обычно встроенная веб-камера
    
    # Начальные параметры
    current_length = 50.0
    current_diameter = 5.0
    
    while cap.isOpened() and run_camera:
        ret, frame = cap.read()
        if not ret:
            st.error("Camera not found")
            break
            
        # Зеркалим кадр (как в зеркале)
        frame = cv2.flip(frame, 1)
        # Переводим в RGB для ИИ
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # --- МАГИЯ ИИ: ИЩЕМ РУКИ ---
        results = st.session_state.hands.process(img_rgb)
        
        status = "SEARCHING FOR HAND..."
        
        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                # Рисуем скелет руки на видео
                st.session_state.mp_draw.draw_landmarks(frame, hand_lms, st.session_state.mp_hands.HAND_CONNECTIONS)
                
                # ПОЛУЧАЕМ КООРДИНАТЫ ПАЛЬЦЕВ
                h, w, c = frame.shape
                # Указательный палец (Index Tip = точка 8)
                idx_x, idx_y = int(hand_lms.landmark[8].x * w), int(hand_lms.landmark[8].y * h)
                # Большой палец (Thumb Tip = точка 4)
                th_x, th_y = int(hand_lms.landmark[4].x * w), int(hand_lms.landmark[4].y * h)
                
                # Рисуем кружки на пальцах
                cv2.circle(frame, (idx_x, idx_y), 10, (0, 255, 255), cv2.FILLED)
                cv2.circle(frame, (th_x, th_y), 10, (0, 255, 255), cv2.FILLED)
                cv2.line(frame, (idx_x, idx_y), (th_x, th_y), (0, 255, 0), 3)
                
                # --- УПРАВЛЕНИЕ ЖЕСТАМИ ---
                
                # 1. ДИАМЕТР = Расстояние между пальцами (Щипок)
                # Вычисляем длину линии между пальцами
                distance = np.hypot(idx_x - th_x, idx_y - th_y)
                # Масштабируем: 20 пикселей = 1м, 200 пикселей = 10м
                target_diam = np.interp(distance, [20, 300], [1.0, 15.0])
                current_diameter = target_diam
                
                # 2. ДЛИНА = Высота руки на экране
                # Чем выше рука (меньше Y), тем длиннее ракета
                # landmark[0] - это запястье
                wrist_y = hand_lms.landmark[0].y
                target_len = np.interp(wrist_y, [0.2, 0.8], [100.0, 20.0])
                current_length = target_len
                
                status = f"TRACKING: Diam={current_diameter:.1f}m | Len={current_length:.1f}m"

        # Добавляем текст на видео
        cv2.putText(frame, status, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # --- ОБНОВЛЕНИЕ ЭКРАНА ---
        # 1. Показываем видео
        cam_placeholder.image(frame, channels="BGR")
        
        # 2. Обновляем 3D модель (каждый кадр!)
        # Внимание: на слабых ПК это может лагать. Surface 3 должен справиться.
        fig = get_rocket_fig(current_length, current_diameter)
        chart_placeholder.plotly_chart(fig, use_container_width=True, key=f"rocket_{np.random.random()}")
        
        metrics_placeholder.markdown(f"""
        ### 📊 LIVE TELEMETRY
        * **Diameter:** {current_diameter:.2f} m
        * **Length:** {current_length:.2f} m
        """)
        
    cap.release()
else:
    st.info("Поставь галочку 'ACTIVATE WEBCAM LINK', чтобы начать.")