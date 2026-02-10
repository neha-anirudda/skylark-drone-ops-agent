import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ================== PAGE CONFIG ==================
st.set_page_config(page_title="Skylark Drone Ops Agent", layout="wide")
st.title("🚁 Skylark Drone Operations Coordinator")

# ================== GOOGLE SHEETS SETUP ==================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=SCOPES
)
client = gspread.authorize(creds)

# Sheet IDs
PILOT_SHEET_ID = "18yDQbQHiOEZ4Duc36t23wztIPSKU9yPHEJu6KAqHe0c"
DRONE_SHEET_ID = "1n5ERcFnwDJzUquSpaxNnRdETq3UWzfJ_lbhwhcnQniA"
MISSION_SHEET_ID = "1PBS1TLaXYbvuR004TJKrbuVdgWHPlDYtOINdKx5Fqf0"

# ================== DATA LOADING ==================
@st.cache_data
def load_sheet(sheet_id):
    sheet = client.open_by_key(sheet_id).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip().str.lower()
    return df

try:
    pilots_df = load_sheet(PILOT_SHEET_ID)
    drones_df = load_sheet(DRONE_SHEET_ID)
    missions_df = load_sheet(MISSION_SHEET_ID)
except Exception as e:
    st.error("❌ Error connecting to Google Sheets")
    st.exception(e)
    st.stop()

# ================== SIDEBAR NAV ==================
st.sidebar.title("Navigation")
section = st.sidebar.radio(
    "Go to",
    ["Pilot Roster", "Drone Fleet", "Missions", "Update Pilot Status"]
)

# ================== UI SECTIONS ==================
if section == "Pilot Roster":
    st.subheader("👨‍✈️ Pilot Roster (Live)")
    st.dataframe(pilots_df)

elif section == "Drone Fleet":
    st.subheader("🚁 Drone Fleet")
    st.dataframe(drones_df)

elif section == "Missions":
    st.subheader("📍 Missions")
    st.dataframe(missions_df)

elif section == "Update Pilot Status":
    st.subheader("🔄 Update Pilot Status")

    pilot_name = st.selectbox("Select Pilot", pilots_df["name"].tolist())
    new_status = st.selectbox(
        "New Status",
        ["available", "on leave", "unavailable"]
    )

    if st.button("Update Status"):
        sheet = client.open_by_key(PILOT_SHEET_ID).sheet1
        cell = sheet.find(pilot_name)
        status_col = pilots_df.columns.get_loc("status") + 1
        sheet.update_cell(cell.row, status_col, new_status)

        st.success(f"✅ Updated {pilot_name} to {new_status}")
        st.cache_data.clear()

# ================== CORE LOGIC ==================
def assign_mission(pilots_df, drones_df):
    pilots_df["status"] = pilots_df["status"].str.lower()
    drones_df["status"] = drones_df["status"].str.lower()

    available_pilots = pilots_df[
        (pilots_df["status"] == "available") &
        (pilots_df["current_assignment"].isna() | (pilots_df["current_assignment"] == ""))
    ]

    available_drones = drones_df[
        (drones_df["status"] == "available") &
        (drones_df["current_assignment"].isna() | (drones_df["current_assignment"] == ""))
    ]

    if available_pilots.empty:
        return "❌ No available pilots"

    if available_drones.empty:
        return "❌ No available drones"

    pilot = available_pilots.iloc[0]["name"]
    drone = available_drones.iloc[0]["drone_id"]

    return f"✅ Assign pilot **{pilot}** to drone **{drone}**"

# ================== DECISION OUTPUT ==================
st.divider()
st.subheader("🤖 Mission Coordinator Decision")
decision = assign_mission(pilots_df, drones_df)
st.success(decision)