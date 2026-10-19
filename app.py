import streamlit as st
import pandas as pd

# 1. Page Configuration
st.set_page_config(
    page_title="Industrial Parts Inventory Engine",
    page_icon="⚙️",
    layout="wide"
)

# 2. Custom CSS & Dark Theme Styling
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
    }
    div[data-testid="stMetric"] {
        background: #151c2c;
        border: 1px solid #243048;
        border-radius: 8px;
        padding: 14px 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.8rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.75rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .plant-sub {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-top: -8px;
        margin-bottom: 18px;
    }
    div[data-testid="stRadio"] > div {
        background-color: #151c2c;
        padding: 10px 14px;
        border-radius: 8px;
        border: 1px solid #243048;
        gap: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize view mode state
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "dashboard"

# 3. File and Sheet Settings
EXCEL_FILE = "inventory_master.xlsx"
SHEET_NAME = "Sheet1"

# 4. Load Excel Data Safely with Header Detection
@st.cache_data
def get_raw_data():
    try:
        raw_df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME)

        # Auto-detect header row if preceded by blank rows
        if "S.NO." not in raw_df.columns:
            for idx, row in raw_df.iterrows():
                if "S.NO." in row.values:
                    raw_df.columns = raw_df.iloc[idx]
                    raw_df = raw_df.iloc[idx + 1 :].reset_index(drop=True)
                    break

        if "S.NO." in raw_df.columns:
            raw_df = raw_df.dropna(subset=["S.NO."])
        raw_df = raw_df.dropna(how="all")

        # Location columns
        location_cols = ['CS06', 'CS11', 'CCR', 'TRNG', 'CS02', 'CS03', 'CS04', 'CS05', 'CS07', 'CS09', 'CS10']
        for col in location_cols:
            if col in raw_df.columns:
                raw_df[col] = pd.to_numeric(raw_df[col], errors="coerce").fillna(0).astype(int)

        available_locs = [c for c in location_cols if c in raw_df.columns]
        if available_locs:
            raw_df["TOTAL"] = raw_df[available_locs].sum(axis=1)

        return raw_df, available_locs
    except FileNotFoundError:
        st.error(f"Error: Could not find '{EXCEL_FILE}' in this directory.")
        st.stop()

df, available_locs = get_raw_data()

# Identify description column dynamically
desc_col = None
for col_candidate in ["Item Description", "Description", "ITEM DESCRIPTION", "DESCRIPTION", "Item", "ITEM"]:
    if col_candidate in df.columns:
        desc_col = col_candidate
        break
if not desc_col and len(df.columns) > 1:
    desc_col = df.columns[1]

meta_cols = [c for c in df.columns if c not in available_locs and c != 'TOTAL']

# ========================================================
# VIEW 1: DEDICATED FULL-SCREEN ANALYTICS & CHARTS
# ========================================================
if st.session_state.view_mode == "analytics":
    # Navigation Back to Dashboard
    nav_col1, _ = st.columns([1, 4])
    with nav_col1:
        if st.button("← Back to Master Matrix", type="secondary", use_container_width=True):
            st.session_state.view_mode = "dashboard"
            st.rerun()

    st.title("📊 DCS Spares & Hardware Analytics")
    st.markdown('<p class="plant-sub">Comprehensive hardware distribution analytics across plant control stations.</p>', unsafe_allow_html=True)

    # 1. Summary Metrics
    tot_spares = int(df['TOTAL'].sum()) if 'TOTAL' in df.columns else 0
    hwl_count = int(df[df['Make'].astype(str).str.upper().str.contains('HWL', na=False)]['TOTAL'].sum()) if 'Make' in df.columns and 'TOTAL' in df.columns else 0
    hwl_share = round((hwl_count / tot_spares * 100), 1) if tot_spares > 0 else 0
    active_stns = [loc for loc in available_locs if df[loc].sum() > 0]

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Total Line Items", len(df))
    a2.metric("Total Plant Spares", f"{tot_spares:,}")
    a3.metric("OEM (HWL) Modules", f"{hwl_count:,}", delta=f"{hwl_share}% share")
    a4.metric("Active Stations", f"{len(active_stns)} / {len(available_locs)}")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Side-by-Side Charts
    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("🏭 Spare Density by Control Station")
        station_distribution = pd.DataFrame({
            "Station": available_locs,
            "Module Count": [int(df[loc].sum()) for loc in available_locs]
        }).sort_values(by="Module Count", ascending=False)
        st.bar_chart(data=station_distribution.set_index("Station"), color="#38bdf8", use_container_width=True)

    with c_right:
        st.subheader("🏷️ Distribution by Make")
        if "Make" in df.columns and "TOTAL" in df.columns:
            make_group = df.groupby("Make")["TOTAL"].sum().reset_index().sort_values(by="TOTAL", ascending=False)
            st.bar_chart(data=make_group.set_index("Make"), color="#0ea5e9", use_container_width=True)
        else:
            st.info("Make column not found.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Functional Categorization
    st.subheader("🧩 Spares Allocation by Hardware Category")
    def categorize_item(desc):
        d = str(desc).upper()
        if "PROCESSOR" in d or "CPU" in d:
            return "Controllers / Processors"
        elif "MODULE" in d or "FTBE" in d or "TC-" in d:
            return "I/O & Comm Modules"
        elif "CABLE" in d:
            return "Buses & System Cables"
        elif "SLOT" in d or "CHASSIS" in d or "RACK" in d:
            return "Chassis & Racks"
        elif "POWER" in d or "SUPPLY" in d:
            return "Power Supplies"
        else:
            return "Other Hardware"

    df_cat = df.copy()
    df_cat["Category"] = df_cat[desc_col].apply(categorize_item)
    category_summary = df_cat.groupby("Category")["TOTAL"].sum().reset_index().sort_values(by="TOTAL", ascending=False)
    st.bar_chart(data=category_summary.set_index("Category"), color="#06b6d4", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Station Deep Dive
    st.subheader("🔍 Station-Specific Inventory Breakdown")
    col_sel, _ = st.columns([2, 2])
    with col_sel:
        inspected_station = st.selectbox("Select Station to Audit:", options=available_locs, index=0)

    stn_parts = df[[desc_col, inspected_station]].copy()
    stn_parts = stn_parts[stn_parts[inspected_station] > 0].sort_values(by=inspected_station, ascending=False)
    if not stn_parts.empty:
        st.bar_chart(data=stn_parts.head(10).set_index(desc_col)[[inspected_station]], color="#6366f1", use_container_width=True)
    else:
        st.warning(f"No modules currently allocated to {inspected_station}.")

    st.stop()

# ========================================================
# VIEW 2: PRIMARY DASHBOARD & EDITABLE MATRIX
# ========================================================

# Header with Navigation Link to Analytics
h_left, h_right = st.columns([3, 1])
with h_left:
    st.title("Industrial Parts Stock & Inventory Manager")
    st.markdown('<p class="plant-sub">Dynamic tracking, modifications, and site-wise allocation matrix.</p>', unsafe_allow_html=True)
with h_right:
    st.write("")
    if st.button("📊 Open Stock Analytics & Charts →", type="primary", use_container_width=True):
        st.session_state.view_mode = "analytics"
        st.rerun()

# Top Station Scope Selector
st.markdown("##### 📍 Select Control Room / Scope")
station_options = ["All Stations"] + available_locs
selected_room = st.radio("Control Room Scope", options=station_options, horizontal=True, label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

# Dynamic Context-Aware Metrics
m1, m2, m3, m4 = st.columns(4)
if selected_room == "All Stations":
    m1.metric("Registered Items", f"{len(df):,}")
    m2.metric("Total Plant Stock", f"{int(df['TOTAL'].sum()):,}")
    m3.metric("Stations Tracked", len(available_locs))
    zero_stock = int((df['TOTAL'] == 0).sum())
    m4.metric("Zero Stock Spares", zero_stock, delta="-Alert" if zero_stock > 0 else "Normal", delta_color="inverse")
else:
    room_qty = int(df[selected_room].sum())
    equipped_items = int((df[selected_room] > 0).sum())
    depleted_items = int((df[selected_room] == 0).sum())
    m1.metric(f"{selected_room} Total Units", f"{room_qty:,}")
    m2.metric("Active Spares Present", equipped_items)
    m3.metric("Zero Count in Station", depleted_items, delta="-Deficit" if depleted_items > 0 else "Normal", delta_color="inverse")
    m4.metric("Plant Total Units", f"{int(df['TOTAL'].sum()):,}")

st.markdown("<br>", unsafe_allow_html=True)

# Search & Zero Stock Toggle
col_search, col_filter = st.columns([3, 1])
with col_search:
    search_term = st.text_input("Search Line Items", placeholder="Filter by description, make, or part number...", label_visibility="collapsed")
with col_filter:
    if selected_room == "All Stations":
        filter_toggle = st.checkbox("Show Zero Total Stock Only", value=False)
    else:
        filter_toggle = st.checkbox(f"Show Only Items Stocked in {selected_room}", value=False)

# Build View Dataframe
if selected_room == "All Stations":
    active_columns = list(df.columns)
    view_df = df.copy()
    if filter_toggle and 'TOTAL' in view_df.columns:
        view_df = view_df[view_df['TOTAL'] == 0]
else:
    active_columns = meta_cols + [selected_room, 'TOTAL']
    view_df = df[active_columns].copy()
    if filter_toggle:
        view_df = view_df[view_df[selected_room] > 0]

if search_term:
    mask = view_df.astype(str).apply(lambda row: row.str.contains(search_term, case=False).any(), axis=1)
    view_df = view_df[mask]

# Configure Columns
col_config = {}
if desc_col:
    col_config[desc_col] = st.column_config.TextColumn(desc_col, width="large", required=True)

for loc in available_locs:
    if loc in active_columns:
        col_config[loc] = st.column_config.NumberColumn(loc, min_value=0, step=1, format="%d", width="small")

if 'TOTAL' in active_columns:
    col_config['TOTAL'] = st.column_config.NumberColumn("TOTAL", format="%d", width="small", disabled=True)

# Data Table
st.subheader(f"Data Matrix — {selected_room}")
edited_df = st.data_editor(
    view_df,
    num_rows="dynamic" if selected_room == "All Stations" else "fixed",
    use_container_width=True,
    hide_index=True,
    column_config=col_config
)

st.markdown("<br>", unsafe_allow_html=True)

# Save & Export Controls
save_col, export_col = st.columns([2, 1])
with save_col:
    if st.button("Save All Modifications Directly to Excel", type="primary", use_container_width=True):
        df.update(edited_df)
        if available_locs:
            df['TOTAL'] = df[available_locs].sum(axis=1)

        df.to_excel(EXCEL_FILE, index=False, sheet_name=SHEET_NAME)
        st.cache_data.clear()
        st.success("Modifications saved successfully to Excel!")
        st.rerun()

with export_col:
    st.download_button(
        label=f"Export {selected_room} View (CSV)",
        data=edited_df.to_csv(index=False),
        file_name=f"{selected_room.lower()}_inventory.csv",
        mime="text/csv",
        use_container_width=True
    )
