import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Skylark Drone Ops Agent", layout="wide")
st.title("🚁 Skylark Drone Operations Coordinator")

# ================= GOOGLE SHEETS =================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=SCOPES
)
client = gspread.authorize(creds)

PILOT_SHEET_ID = "18yDQbQHiOEZ4Duc36t23wztIPSKU9yPHEJu6KAqHe0c"
DRONE_SHEET_ID = "1n5ERcFnwDJzUquSpaxNnRdETq3UWzfJ_lbhwhcnQniA"
MISSION_SHEET_ID = "1PBS1TLaXYbvuR004TJKrbuVdgWHPlDYtOINdKx5Fqf0"

# ================= LOAD DATA =================
@st.cache_data
def load_sheet(sheet_id):
    sheet = client.open_by_key(sheet_id).sheet1
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip().str.lower()
    return df

try:
    pilots_df = load_sheet(PILOT_SHEET_ID)
    drones_df = load_sheet(DRONE_SHEET_ID)
    missions_df = load_sheet(MISSION_SHEET_ID)
except Exception as e:
    st.error("❌ Google Sheets connection failed")
    st.exception(e)
    st.stop()

# ================= SIDEBAR =================
st.sidebar.title("Navigation")
section = st.sidebar.radio(
    "Go to",
    ["Pilot Roster", "Drone Fleet", "Missions", "Update Pilot Status"]
)

# ================= UI =================
if section == "Pilot Roster":
    st.subheader("👨‍✈️ Pilot Roster")
    st.dataframe(pilots_df)

elif section == "Drone Fleet":
    st.subheader("🚁 Drone Fleet")
    st.dataframe(drones_df)

elif section == "Missions":
    st.subheader("📍 Missions")
    st.dataframe(missions_df)

elif section == "Update Pilot Status":
    st.subheader("🔄 Update Pilot Status")

    pilot = st.selectbox("Select Pilot", pilots_df["name"].tolist())
    status = st.selectbox("New Status", ["available", "on leave", "unavailable"])

    if st.button("Update"):
        sheet = client.open_by_key(PILOT_SHEET_ID).sheet1
        row = sheet.find(pilot).row
        col = pilots_df.columns.get_loc("status") + 1
        sheet.update_cell(row, col, status)
        st.success("Status updated")
        st.cache_data.clear()

# ================= HELPERS =================
def is_free(val):
    return pd.isna(val) or val == ""

def maintenance_ok(date_val):
    if is_free(date_val):
        return True
    try:
        return pd.to_datetime(date_val).date() > datetime.today().date()
    except:
        return False

def parse_list(val):
    if is_free(val):
        return set()
    return set(v.strip().lower() for v in str(val).split(","))

def pilot_qualified(pilot, mission):
    skills = parse_list(pilot["skills"])
    certs = parse_list(pilot["certifications"])

    req_skills = parse_list(mission.get("required_skills", ""))
    req_certs = parse_list(mission.get("required_certifications", ""))

    if not req_skills.issubset(skills):
        return False
    if not req_certs.issubset(certs):
        return False
    return True

# ================= CORE ENGINE =================
def assign_or_reassign(pilots_df, drones_df, missions_df):
    pilots_df["status"] = pilots_df["status"].str.lower()
    drones_df["status"] = drones_df["status"].str.lower()
    missions_df["priority"] = missions_df["priority"].str.lower()

    mission = missions_df.iloc[0]

    urgent = mission.get("priority", "normal") == "urgent"

    # Check if current assignment is broken
    if urgent:
        for _, p in pilots_df.iterrows():
            if p["current_assignment"] == mission["project_id"] and p["status"] != "available":
                st.warning("⚠️ Assigned pilot unavailable — triggering reassignment")

        for _, d in drones_df.iterrows():
            if d["current_assignment"] == mission["project_id"] and not maintenance_ok(d["maintenance_due"]):
                st.warning("⚠️ Drone under maintenance — triggering reassignment")

    eligible_pilots = [
        p for _, p in pilots_df.iterrows()
        if p["status"] == "available"
        and is_free(p["current_assignment"])
        and pilot_qualified(p, mission)
    ]

    eligible_drones = drones_df[
        (drones_df["status"] == "available") &
        (drones_df["current_assignment"].apply(is_free)) &
        (drones_df["maintenance_due"].apply(maintenance_ok))
    ]

    if not eligible_pilots:
        return "❌ Urgent reassignment failed: no qualified pilots"

    if eligible_drones.empty:
        return "❌ Urgent reassignment failed: no available drones"

    return (
        f"🚨 URGENT REASSIGNMENT\n\n"
        f"Pilot: **{eligible_pilots[0]['name']}**\n"
        f"Drone: **{eligible_drones.iloc[0]['drone_id']}**\n"
        f"Mission: **{mission['project_id']}**"
    )

# ================= DECISION =================
st.divider()
st.subheader("🤖 Mission Assignment Engine")

result = assign_or_reassign(pilots_df, drones_df, missions_df)

if "❌" in result:
    st.error(result)
elif "URGENT" in result:
    st.warning(result)
else:
    st.success(result)