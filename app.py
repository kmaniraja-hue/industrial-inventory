import streamlit as st
import pandas as pd

# 1. Page Configuration
st.set_page_config(
    page_title="Industrial Parts Inventory Engine",
    page_icon="⚙️",
    layout="wide"
)

# 2. Custom CSS Background & Dark Theme Palette
st.markdown(
    """
    <style>
    /* Main App Background */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }

    /* Container Spacing */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
    }

    /* Metric Cards */
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

    /* Plant Subtitle */
    .plant-sub {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-top: -8px;
        margin-bottom: 18px;
    }

    /* Control Room Selector Radio Styling */
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

st.title("Industrial Parts Stock & Inventory Manager")
st.markdown('<p class="plant-sub">Dynamic tracking, modifications, and site-wise allocation matrix.</p>', unsafe_allow_html=True)

# 3. File and Sheet Settings
EXCEL_FILE = "inventory_master.xlsx"
SHEET_NAME = "Sheet1"

# 4. Load Excel Data Safely with Header Detection
@st.cache_data
def get_raw_data():
    try:
        raw_df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME)

        # Check if header needs adjusting due to blank top rows
        if "S.NO." not in raw_df.columns:
            for idx, row in raw_df.iterrows():
                if "S.NO." in row.values:
                    raw_df.columns = raw_df.iloc[idx]
                    raw_df = raw_df.iloc[idx + 1 :].reset_index(drop=True)
                    break

        # Drop rows without a serial number or that are completely empty
        if "S.NO." in raw_df.columns:
            raw_df = raw_df.dropna(subset=["S.NO."])
        raw_df = raw_df.dropna(how="all")

        # Warehouse location columns
        location_cols = ['CS06', 'CS11', 'CCR', 'TRNG', 'CS02', 'CS03', 'CS04', 'CS05', 'CS07', 'CS09', 'CS10']
        for col in location_cols:
            if col in raw_df.columns:
                raw_df[col] = pd.to_numeric(raw_df[col], errors="coerce").fillna(0).astype(int)

        available_locs = [c for c in location_cols if c in raw_df.columns]
        if available_locs:
            raw_df["TOTAL"] = raw_df[available_locs].sum(axis=1)

        return raw_df, available_locs
    except FileNotFoundError:
        st.error(f"Error: Could not find '{EXCEL_FILE}' in this directory. Please verify the filename.")
        st.stop()

df, available_locs = get_raw_data()

# Identify description column
desc_col = None
for potential_name in ["Item Description", "Description", "ITEM DESCRIPTION", "DESCRIPTION", "Item", "ITEM"]:
    if potential_name in df.columns:
        desc_col = potential_name
        break
if not desc_col and len(df.columns) > 1:
    desc_col = df.columns[1]

# Base identification columns (S.No, Description, Make, UOM, etc.)
meta_cols = [c for c in df.columns if c not in available_locs and c != 'TOTAL']

# 5. Top Control Room Selector
st.markdown("##### 📍 Select Control Room / View Scope")
station_options = ["All Stations"] + available_locs
selected_room = st.radio(
    "Select Control Room Scope",
    options=station_options,
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("<br>", unsafe_allow_html=True)

# 6. Context-Aware Dynamic KPI Metrics
m1, m2, m3, m4 = st.columns(4)

if selected_room == "All Stations":
    total_unique_items = len(df)
    overall_stock_volume = int(df['TOTAL'].sum()) if 'TOTAL' in df.columns else 0
    zero_stock_items = int((df['TOTAL'] == 0).sum()) if 'TOTAL' in df.columns else 0

    m1.metric("Registered Items", f"{total_unique_items:,}")
    m2.metric("Total Plant Stock", f"{overall_stock_volume:,}")
    m3.metric("Stations Tracked", len(available_locs))
    m4.metric("Zero Stock Spares", zero_stock_items, delta="-Alert" if zero_stock_items > 0 else "Normal", delta_color="inverse")
else:
    room_qty = int(df[selected_room].sum())
    equipped_items = int((df[selected_room] > 0).sum())
    depleted_items = int((df[selected_room] == 0).sum())

    m1.metric(f"{selected_room} Total Units", f"{room_qty:,}")
    m2.metric("Active Spares Present", equipped_items)
    m3.metric("Zero Count in Station", depleted_items, delta="-Deficit" if depleted_items > 0 else "Normal", delta_color="inverse")
    m4.metric("Plant Total Units", f"{int(df['TOTAL'].sum()):,}")

st.markdown("<br>", unsafe_allow_html=True)

# 7. Search Bar & Station In-Stock Filter
col_search, col_filter = st.columns([3, 1])
with col_search:
    search_term = st.text_input(
        "Search Line Items",
        placeholder="Filter by spare description, make, or part number...",
        label_visibility="collapsed"
    )

with col_filter:
    if selected_room == "All Stations":
        filter_toggle = st.checkbox("Show Zero Total Stock Only", value=False)
    else:
        filter_toggle = st.checkbox(f"Show Only Items Stocked in {selected_room}", value=False)

# 8. View Construction based on Selection
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

# Search filtering
if search_term:
    mask = view_df.astype(str).apply(lambda row: row.str.contains(search_term, case=False).any(), axis=1)
    view_df = view_df[mask]

# 9. Configure Column Widths & Displays
col_config = {}
if desc_col:
    col_config[desc_col] = st.column_config.TextColumn(desc_col, width="large", required=True)

for loc in available_locs:
    if loc in active_columns:
        col_config[loc] = st.column_config.NumberColumn(loc, min_value=0, step=1, format="%d", width="small")

if 'TOTAL' in active_columns:
    col_config['TOTAL'] = st.column_config.NumberColumn("TOTAL", format="%d", width="small", disabled=True)

# 10. Data Editor
st.subheader(f"Data Matrix — {selected_room}")
st.caption("Double-click any count to edit. Modifications apply to the master record.")

edited_df = st.data_editor(
    view_df,
    num_rows="dynamic" if selected_room == "All Stations" else "fixed",
    use_container_width=True,
    hide_index=True,
    column_config=col_config
)

st.markdown("<br>", unsafe_allow_html=True)

# 11. Save & Export Controls
save_col, export_col = st.columns([2, 1])
with save_col:
    if st.button("Save All Modifications Directly to Excel", type="primary", use_container_width=True):
        # Merge changes back into master dataframe
        df.update(edited_df)

        # Recalculate the master TOTAL row-by-row
        if available_locs:
            df['TOTAL'] = df[available_locs].sum(axis=1)

        # Write directly back to file
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
