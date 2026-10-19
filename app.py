import streamlit as st
import pandas as pd

# 1. Dashboard Layout Settings
st.set_page_config(page_title="Industrial Parts Inventory Engine", page_icon="??", layout="wide")
st.title("?? Industrial Parts Stock & Inventory Manager")
st.markdown("Dynamic tracking, modifications, and site-wise allocation matrix.")

# 2. File and Sheet Settings
EXCEL_FILE = "inventory_master.xlsx"
SHEET_NAME = "Sheet1"  # If your Excel tab name is different, change it here

# 3. Load Excel Data Safely with Header Detection
try:
    df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME)
    
    # Check if header needs adjusting due to blank top rows
    if "S.NO." not in df.columns:
        for idx, row in df.iterrows():
            if "S.NO." in row.values:
                df.columns = df.iloc[idx]
                df = df.iloc[idx + 1 :].reset_index(drop=True)
                break
                
    # Drop rows without a serial number or that are completely empty
    if "S.NO." in df.columns:
        df = df.dropna(subset=["S.NO."])
    df = df.dropna(how='all')
    
    # Ensure warehouse column counts are treated as round numbers
    location_cols = ['CS06', 'CS11', 'CCR', 'TRNG', 'CS02', 'CS03', 'CS04', 'CS05', 'CS07', 'CS09', 'CS10']
    for col in location_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
    # Calculate fresh row-by-row TOTAL column values
    available_locs = [c for c in location_cols if c in df.columns]
    if available_locs:
        df['TOTAL'] = df[available_locs].sum(axis=1)

except FileNotFoundError:
    st.error(f"? Error: Could not find '{EXCEL_FILE}' in this folder. Please verify the filename.")
    st.stop()

# 4. Show Visual Inventory Metrics Counters
total_unique_items = len(df)
overall_stock_volume = int(df['TOTAL'].sum()) if 'TOTAL' in df.columns else 0

m1, m2 = st.columns(2)
with m1:
    st.metric(label="Registered Unique Part Line Items", value=total_unique_items)
with m2:
    st.metric(label="Total Units in Stock Across All Locations", value=overall_stock_volume)

st.divider()

# 5. Interactive Editing Table Grid
st.subheader("?? Dynamic Live Stock Matrix (Editable)")
st.caption("Double-click any cell to modify quantities or text. Scroll to the bottom to add new rows.")

edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)

# 6. Save Button to Write Directly Back to the Spreadsheet file
if st.button("?? Save All Modifications Directly to Excel", type="primary"):
    # Automatically recalculate the TOTAL column row-by-row before saving
    if available_locs:
        edited_df['TOTAL'] = edited_df[available_locs].sum(axis=1)
        
    # Write back over your original Excel file securely
    edited_df.to_excel(EXCEL_FILE, index=False, sheet_name=SHEET_NAME)
    st.success("?? Excel workbook successfully updated!")
    st.rerun()
