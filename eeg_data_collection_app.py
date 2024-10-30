import streamlit as st
import time
import numpy as np
import pandas as pd
import threading
import ssl
import websocket
import json
from datetime import datetime
import plotly.graph_objs as go

# Set page configuration
st.set_page_config(
    page_title="EEG Data Collection Interface",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for styling
st.markdown("""
    <style>
    /* Main content area */
    .main {
        background-color: #ffffff; /* Set background to white for better contrast */
    }
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #2b3e50; /* Darker background for sidebar */
    }
    /* Sidebar text colors */
    .sidebar .markdown-text-container, .sidebar .css-1n76uvr p {
        color: #ffffff; /* Light text on dark background for sidebar */
    }
    /* Text colors for main content */
    body, .markdown-text-container, .stText, .stMarkdown {
        color: #333333; /* Darker text for better contrast */
    }
    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: #2c3e50; /* Dark blue headings */
    }
    /* Button styling */
    .stButton>button {
        color: #ffffff;
        background-color: #3498db; /* Blue button */
        border-radius: 5px;
        border: none;
        padding: 0.5em 1em;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #2980b9;
    }
    /* Progress bar */
    .stProgress > div > div > div > div {
        background-color: #27ae60; /* Green progress bar */
    }
    /* Selectbox styling */
    .stSelectbox select {
        background-color: #ecf0f1; /* Light background for select box */
        color: #2c3e50;
    }
    /* Input fields */
    input {
        background-color: #ffffff;
        color: #333333;
    }
    /* Text area */
    textarea {
        background-color: #ffffff;
        color: #333333;
    }
    /* Slider styling */
    .stSlider > div > div > div {
        color: #2c3e50;
    }
    /* Footer text */
    footer {
        color: #808080;
    }
    /* Links */
    a {
        color: #3498db;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    </style>
    """, unsafe_allow_html=True)

# Placeholder for logo (replace 'logo.png' with your logo file)
st.sidebar.image('neurotech_logo.png', use_column_width=True)

# Initialize session state variables
if 'is_collecting' not in st.session_state:
    st.session_state.is_collecting = False

if 'eeg_data' not in st.session_state:
    st.session_state.eeg_data = []

if 'start_time' not in st.session_state:
    st.session_state.start_time = None

if 'task_duration' not in st.session_state:
    st.session_state.task_duration = 300  # Default to 5 minutes

# Emotiv Client Class
class EmotivClient:
    def __init__(self, client_id, client_secret):
        self.ws = None
        self.auth_token = None
        self.session_id = None
        self.client_id = client_id
        self.client_secret = client_secret
        self.headset_id = None

    def connect(self):
        self.ws = websocket.create_connection(
            "wss://localhost:6868",
            sslopt={"cert_reqs": ssl.CERT_NONE}
        )
        self.authorize()
        self.create_session()

    def authorize(self):
        auth_request = {
            "jsonrpc": "2.0",
            "method": "authorize",
            "params": {
                "clientId": self.client_id,
                "clientSecret": self.client_secret
            },
            "id": 1
        }
        self.ws.send(json.dumps(auth_request))
        result = self.ws.recv()
        response = json.loads(result)
        self.auth_token = response['result']['cortexToken']
        print("Authorized")

    def create_session(self):
        # Query headset ID
        query_headset = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "queryHeadsets",
            "params": {}
        }
        self.ws.send(json.dumps(query_headset))
        result = self.ws.recv()
        response = json.loads(result)
        if len(response['result']) == 0:
            raise Exception("No headset connected")
        else:
            self.headset_id = response['result'][0]['id']

        create_session_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "createSession",
            "params": {
                "cortexToken": self.auth_token,
                "headset": self.headset_id,
                "status": "active"
            }
        }
        self.ws.send(json.dumps(create_session_request))
        result = self.ws.recv()
        response = json.loads(result)
        self.session_id = response['result']['id']
        print("Session created: ", self.session_id)

    def subscribe(self, streams):
        subscribe_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "subscribe",
            "params": {
                "cortexToken": self.auth_token,
                "session": self.session_id,
                "streams": streams
            }
        }
        self.ws.send(json.dumps(subscribe_request))
        result = self.ws.recv()
        response = json.loads(result)
        if 'error' in response:
            print("Subscription error: ", response['error'])
        else:
            print("Subscribed to streams: ", streams)

    def get_data(self):
        try:
            data = self.ws.recv()
            data_json = json.loads(data)
            return data_json
        except Exception as e:
            print("Error receiving data: ", e)
            return None

    def close(self):
        self.ws.close()

# Function to acquire EEG data
def acquire_eeg_data(duration, client_id, client_secret):
    emotiv_client = EmotivClient(client_id, client_secret)
    emotiv_client.connect()
    emotiv_client.subscribe(["eeg"])  # Subscribe to EEG data stream

    start_time = time.time()
    channels = ['AF3', 'F7', 'F3', 'FC5', 'T7', 'P7', 'O1', 'O2',
                'P8', 'T8', 'FC6', 'F4', 'F8', 'AF4']
    while st.session_state.is_collecting and (time.time() - start_time) < duration:
        data_json = emotiv_client.get_data()
        if data_json and 'eeg' in data_json:
            eeg_data = data_json['eeg']
            timestamp = eeg_data[0]
            # The EEG data starts from index 2 in the 'eeg' list
            samples = eeg_data[2:16]  # Adjust indices based on the data structure
            st.session_state.eeg_data.append([timestamp] + samples)
        time.sleep(0.01)  # Control data acquisition rate

    emotiv_client.close()
    st.session_state.is_collecting = False

# Sidebar for participant information
st.sidebar.title("Participant Information")
participant_id = st.sidebar.text_input("Participant ID", value="")
age = st.sidebar.number_input("Age", min_value=1, max_value=100, value=25)
gender = st.sidebar.selectbox("Gender", options=["Select", "Male", "Female", "Other"])
session_notes = st.sidebar.text_area("Session Notes")

# Main interface
st.title("🧠 EEG Data Collection Interface")

st.markdown("""
Welcome to the **EEG Data Collection Interface**. This application is designed to facilitate efficient and high-quality EEG data gathering for our research study.
""")

# Instructions Section
with st.expander("📝 Instructions"):
    st.markdown("""
    **Preparation:**

    - Ensure the **EEG headset** is properly fitted and all sensors have good contact.
    - Sit in a **comfortable position** in a quiet environment.
    - Minimize movements and avoid talking during data collection
        **Tasks:**

    You will be asked to perform specific mental tasks, such as **imagining a fist opening and closing**, or resting.

    **Artifact Minimization:**

    - Try to **minimize blinking** and facial movements during the tasks.
    - Keep your body **relaxed and still**.

    **Engagement:**

    - Stay **focused** on the tasks as instructed.
    - If you feel uncomfortable at any time, please **pause** the session.
    """)

# Session Control Buttons
st.sidebar.subheader("Session Control")
task_duration = st.sidebar.slider("Session Duration (minutes)", min_value=1, max_value=10, value=5)
st.session_state.task_duration = task_duration * 60  # Convert minutes to seconds

col_start, col_pause, col_stop = st.sidebar.columns(3)
with col_start:
    if st.button("Start", key="start_button") and not st.session_state.is_collecting:
        if participant_id == "" or gender == "Select":
            st.error("Please complete all participant information before starting.")
        else:
            st.session_state.is_collecting = True
            st.session_state.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            st.success("Session Started")
            # Replace 'YOUR_CLIENT_ID' and 'YOUR_CLIENT_SECRET' with your actual credentials
            client_id = 'YOUR_CLIENT_ID'
            client_secret = 'YOUR_CLIENT_SECRET'
            # Start data acquisition in a separate thread
            threading.Thread(target=acquire_eeg_data, args=(st.session_state.task_duration, client_id, client_secret)).start()
with col_pause:
    if st.button("Pause", key="pause_button") and st.session_state.is_collecting:
        st.session_state.is_collecting = False
        st.warning("Session Paused")
with col_stop:
    if st.button("Stop", key="stop_button") and st.session_state.is_collecting:
        st.session_state.is_collecting = False
        st.error("Session Stopped")

# Progress Bar and Timer
if st.session_state.is_collecting:
    progress_bar = st.progress(0)
    status_text = st.empty()
    start_time = time.time()
    duration = st.session_state.task_duration
    while st.session_state.is_collecting and (time.time() - start_time) < duration:
        elapsed_time = time.time() - start_time
        remaining_time = duration - elapsed_time
        progress = min(int((elapsed_time / duration) * 100), 100)
        progress_bar.progress(progress)
        mins, secs = divmod(int(remaining_time), 60)
        status_text.markdown(f"**Time Remaining:** {mins:02d}:{secs:02d}")
        time.sleep(1)
    progress_bar.empty()
    status_text.empty()

# Real-Time EEG Data Visualization
st.subheader("📊 Real-Time EEG Data")
channels = ['AF3', 'F7', 'F3', 'FC5', 'T7', 'P7',
            'O1', 'O2', 'P8', 'T8', 'FC6', 'F4', 'F8', 'AF4']

if st.session_state.is_collecting or st.session_state.eeg_data:
    selected_channel = st.selectbox("Select EEG Channel", options=channels)
    plot_placeholder = st.empty()
    while st.session_state.is_collecting:
        if len(st.session_state.eeg_data) > 0:
            df = pd.DataFrame(st.session_state.eeg_data, columns=['Timestamp'] + channels)
            df[selected_channel] = df[selected_channel].astype(float)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
            # Plotting with Plotly
            fig = go.Figure(
                data=[go.Scatter(
                    x=df['Timestamp'][-256:],  # Last 256 samples (~2 seconds at 128 Hz)
                    y=df[selected_channel][-256:],
                    mode='lines',
                    line=dict(color='#3498db')
                )],
                layout=go.Layout(
                    title=f"Channel {selected_channel} Real-Time Plot",
                    xaxis_title="Time",
                    yaxis_title="Amplitude (µV)",
                    template="plotly_white",
                    height=400
                )
            )
            plot_placeholder.plotly_chart(fig, use_container_width=True)
        time.sleep(0.1)
else:
    st.info("No data to display. Start a session to see real-time EEG data.")

# Task Instructions
st.subheader("🧠 Current Task")
if st.session_state.is_collecting:
    task = "Imagine opening and closing your fist."
    st.markdown(f"### {task}")
    st.write("Focus on this task for the duration of the session.")
else:
    st.write("No task is currently active.")

# Save Data Button
if not st.session_state.is_collecting and st.session_state.eeg_data:
    if st.button("💾 Save Data"):
        df = pd.DataFrame(st.session_state.eeg_data, columns=['Timestamp'] + channels)
        # Convert data types
        df[channels] = df[channels].astype(float)
        # Add participant info to metadata
        df['ParticipantID'] = participant_id
        df['Age'] = age
        df['Gender'] = gender
        df['SessionNotes'] = session_notes
        df['StartTime'] = st.session_state.start_time

        # Save to CSV format
        filename = f"eeg_data_{participant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        st.success(f"Data saved to {filename}")
        # Clear the data
        st.session_state.eeg_data = []
    else:
        st.write("Click 'Save Data' to store the collected EEG data.")
elif not st.session_state.eeg_data:
    st.write("No data to save yet.")

# Footer
st.write("---")
st.markdown("""
*For assistance, please contact the research coordinator at [email@example.com](mailto:email@example.com).*
""")