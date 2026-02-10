import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Skylark Drone Ops Agent", layout="wide")
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

# Sheet IDs
PILOT_SHEET_ID = "18yDQbQHiOEZ4Duc36t23wztIPSKU9yPHEJu6KAqHe0c"
DRONE_SHEET_ID = "1n5ERcFnwDJzUquSpaxNnRdETq3UWzfJ_lbhwhcnQniA"
MISSION_SHEET_ID = "1PBS1TLaXYbvuR004TJKrbuVdgWHPlDYtOINdKx5Fqf0"

# ================= DATA LOADING =================
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

# ================= UI SECTIONS =================
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

# ================= HELPER FUNCTIONS =================
def is_free(value):
    return pd.isna(value) or value == ""

def maintenance_ok(date_value):
    if pd.isna(date_value) or date_value == "":
        return True
    try:
        return pd.to_datetime(date_value).date() > datetime.today().date()
    except:
        return False

def parse_list(value):
    if pd.isna(value) or value == "":
        return set()
    return set(v.strip().lower() for v in str(value).split(","))

def pilot_qualified(pilot_row, mission_row):
    pilot_skills = parse_list(pilot_row["skills"])
    pilot_certs = parse_list(pilot_row["certifications"])

    required_skills = parse_list(mission_row.get("required_skills", ""))
    required_certs = parse_list(mission_row.get("required_certifications", ""))

    if not required_skills.issubset(pilot_skills):
        return False, "Skill mismatch"

    if not required_certs.issubset(pilot_certs):
        return False, "Certification mismatch"

    return True, ""

# ================= CORE LOGIC =================
def assign_mission(pilots_df, drones_df, missions_df):
    pilots_df["status"] = pilots_df["status"].str.lower()
    drones_df["status"] = drones_df["status"].str.lower()

    mission = missions_df.iloc[0]  # highest priority mission

    # Filter pilots
    eligible_pilots = []
    for _, pilot in pilots_df.iterrows():
        if pilot["status"] != "available":
            continue
        if not is_free(pilot["current_assignment"]):
            continue

        qualified, reason = pilot_qualified(pilot, mission)
        if qualified:
            eligible_pilots.append(pilot)

    # Filter drones
    eligible_drones = drones_df[
        (drones_df["status"] == "available") &
        (drones_df["current_assignment"].apply(is_free)) &
        (drones_df["maintenance_due"].apply(maintenance_ok))
    ]

    if not eligible_pilots:
        return "❌ No qualified pilots (skill/cert mismatch)"

    if eligible_drones.empty:
        return "❌ No available drones (busy or maintenance due)"

    pilot = eligible_pilots[0]["name"]
    drone = eligible_drones.iloc[0]["drone_id"]
    mission_id = mission.get("project_id", "Mission")

    return f"✅ Assign pilot **{pilot}** to drone **{drone}** for **{mission_id}**"

# ================= DECISION OUTPUT =================
st.divider()
st.subheader("🤖 Mission Coordinator Decision")
decision = assign_mission(pilots_df, drones_df, missions_df)
st.success(decision)