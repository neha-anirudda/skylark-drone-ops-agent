import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="Skylark Drone Ops Agent",
    layout="wide"
)

st.title("🚁 Skylark Drone Operations Coordinator")

# ================= GOOGLE SHEETS SETUP =================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=SCOPES
)

client = gspread.authorize(creds)

# 🔴 YOUR GOOGLE SHEET IDS
PILOT_SHEET_ID = "18yDQbQHiOEZ4Duc36t23wztIPSKU9yPHEJu6KAqHe0c"
DRONE_SHEET_ID = "1n5ERcFnwDJzUquSpaxNnRdETq3UWzfJ_lbhwhcnQniA"
MISSION_SHEET_ID = "1PBS1TLaXYbvuR004TJKrbuVdgWHPlDYtOINdKx5Fqf0"

# ================= LOAD SHEETS =================
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

# ================= SIDEBAR =================
st.sidebar.title("Navigation")
section = st.sidebar.radio(
    "Go to",
    ["Pilot Roster", "Drone Fleet", "Missions", "Update Pilot Status"]
)

# ================= HELPERS =================
def is_free(value):
    if pd.isna(value):
        return True
    value = str(value).strip().lower()
    return value == "" or value == "-" or value == "none"
# ================= SECTIONS =================
if section == "Pilot Roster":
    st.subheader("👨‍✈️ Pilot Roster")
    st.dataframe(pilots_df, use_container_width=True)

elif section == "Drone Fleet":
    st.subheader("🚁 Drone Fleet")
    st.dataframe(drones_df, use_container_width=True)

elif section == "Missions":
    st.subheader("📍 Missions")
    st.dataframe(missions_df, use_container_width=True)

elif section == "Update Pilot Status":
    st.subheader("🔄 Update Pilot Status")

    pilot_names = pilots_df["name"].tolist()
    selected_pilot = st.selectbox("Select Pilot", pilot_names)

    new_status = st.selectbox(
        "New Status",
        ["available", "on leave", "unavailable"]
    )

    if st.button("Update Status"):
        sheet = client.open_by_key(PILOT_SHEET_ID).sheet1
        cell = sheet.find(selected_pilot)
        status_col = pilots_df.columns.get_loc("status") + 1
        sheet.update_cell(cell.row, status_col, new_status)

        st.success(f"✅ {selected_pilot}'s status updated to {new_status}")
        st.cache_data.clear()

# ================= ASSIGNMENT LOGIC =================
def assign_mission(pilots_df, drones_df):
    pilots_df["status"] = pilots_df["status"].str.lower()
    drones_df["status"] = drones_df["status"].str.lower()

    available_pilots = pilots_df[
        (pilots_df["status"] == "available") &
        (pilots_df["current_assignment"].apply(is_free))
    ]

    available_drones = drones_df[
        (drones_df["status"] == "available") &
        (drones_df["current_assignment"].apply(is_free))
    ]

    if available_pilots.empty:
        return "❌ Urgent reassignment failed: no qualified pilots"

    if available_drones.empty:
        return "❌ No available drones"

    pilot = available_pilots.iloc[0]["name"]
    drone = available_drones.iloc[0]["drone_id"]

    return f"✅ Assign pilot **{pilot}** to drone **{drone}**"

# ================= DECISION =================
st.subheader("🤖 Mission Coordinator Decision")

decision = assign_mission(pilots_df, drones_df)
st.success(decision)

# ================= DEBUG =================
with st.expander("🧪 Why no pilots?"):
    st.write(
        pilots_df[["name", "status", "current_assignment"]]
    )
with st.expander("🧪 Why no drones?"):
    st.write(
        drones_df[["drone_id", "status", "current_assignment"]]
    )