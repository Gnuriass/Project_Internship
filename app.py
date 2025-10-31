import streamlit as st
import pandas as pd
import json
import datetime
import os
from io import StringIO

from main import (
    get_all_raw_outputs,
    get_switch_info,
    summarize_device_status,
    summarize_ports,
)

# ================= Page Config =================
st.set_page_config(page_title="Network Maintenance Tool", layout="wide")
st.title("🌐 Network Preventive Maintenance Dashboard")
st.write("Perform backup, summarize configuration, and manage device lists easily.")

APP_DIR = os.path.dirname(__file__)
DATASET_PATH = os.path.join(APP_DIR, "dataset.xlsx")

# ================= Load dataset =================
if os.path.exists(DATASET_PATH):
    dataset = pd.read_excel(DATASET_PATH)
else:
    dataset = pd.DataFrame(columns=["Brand", "IP", "Username", "Password"])

# ================= Initialize session_state =================
for key, default in [("brand_new", "Cisco"), ("ip_new", ""), ("username_new", ""), ("password_new", "")]:
    if key not in st.session_state:
        st.session_state[key] = default

# ================= Sidebar: Add New Device =================
st.sidebar.header("➕ Add New Device")
save_msg_placeholder = st.sidebar.empty()


def save_device():
    ip = st.session_state.ip_new.strip()
    username = st.session_state.username_new.strip()
    password = st.session_state.password_new.strip()
    brand = st.session_state.brand_new

    save_msg_placeholder.empty()

    if not ip or not username or not password:
        save_msg_placeholder.error("⚠️ All fields are required.")
        return

    global dataset
    new_row = pd.DataFrame([[brand, ip, username, password]], columns=[
                           "Brand", "IP", "Username", "Password"])
    dataset = pd.concat([dataset, new_row], ignore_index=True)
    dataset.to_excel(DATASET_PATH, index=False)
    st.cache_data.clear()

    save_msg_placeholder.success("✅ Device added successfully!")

    st.session_state.brand_new = "Cisco"
    st.session_state.ip_new = ""
    st.session_state.username_new = ""
    st.session_state.password_new = ""


# Sidebar Inputs
brand_new = st.sidebar.selectbox("Select Brand", ["Cisco", "HPE", "H3C"],
                                 index=["Cisco", "HPE", "H3C"].index(
                                     st.session_state.brand_new),
                                 key="brand_new")
ip_new = st.sidebar.text_input(
    "IP Address", value=st.session_state.ip_new, key="ip_new")
username_new = st.sidebar.text_input(
    "Username", value=st.session_state.username_new, key="username_new")
password_new = st.sidebar.text_input(
    "Password", type="password", value=st.session_state.password_new, key="password_new")

st.sidebar.button("💾 Save Device", on_click=save_device)

st.subheader("📋 Device List")
with st.expander("🔽 Show/Hide Device List", expanded=True):
    if not dataset.empty:
        display_df = dataset.copy()

        header_cols = st.columns([1.5, 1.5, 1.5, 0.7])
        header_names = ["Brand", "IP", "Username", "Action"]
        for col, name in zip(header_cols, header_names):
            col.markdown(f"**{name}**<hr>", unsafe_allow_html=True)

        confirm_idx = st.session_state.get("confirm_delete", None)

        for i, row in display_df.iterrows():
            cols = st.columns([1.5, 1.5, 1.5, 0.7])
            cols[0].write(row["Brand"])
            cols[1].write(row["IP"])
            cols[2].write(row["Username"])

            # Delete button
            if cols[3].button("🗑️ Delete", key=f"del_{i}"):
                st.session_state["confirm_delete"] = i
                confirm_idx = i

            if confirm_idx == i:
                st.warning(f"⚠️ Confirm Delete: {row['Brand']} {row['IP']}")
                col_c, col_d = st.columns([0.5, 0.5])
                if col_c.button("❌ Cancel", key=f"cancel_{i}"):
                    del st.session_state["confirm_delete"]
                    st.rerun()
                if col_d.button("✅ Confirm", key=f"confirm_{i}"):
                    dataset = dataset.drop(i).reset_index(drop=True)
                    dataset.to_excel(DATASET_PATH, index=False)
                    st.cache_data.clear()
                    st.success(f"✅ Deleted {row['IP']} successfully.")
                    del st.session_state["confirm_delete"]
                    st.rerun()
    else:
        st.info("No devices found. Please add")

# ================= Program Run Backup / Summary =================
st.markdown("---")
st.subheader("🕹️ Program Run Backup / Summary")

if not dataset.empty:
    brands = sorted(dataset["Brand"].dropna().astype(str).unique())
    brand = st.selectbox("Select Device Brand", brands, key="run_brand")
    ips = dataset[dataset["Brand"] == brand]["IP"].astype(str).tolist()
    ip = st.selectbox(f"Select IP for {brand}", ips, key="run_ip")

    row = dataset[(dataset["Brand"] == brand) & (dataset["IP"] == ip)].iloc[0]
    username = row["Username"]
    password = row["Password"]

    action = st.radio(
        "Choose a program to run:",
        [
            "Backup Configuration (Raw)",
            "Backup Configuration (textfsm and ntc-template)",
            "Summary All",
            "Save All",
        ],
        horizontal=True,
        key="run_action"
    )

    if st.button("🚀 Run Program", key="run_program"):
        all_results = []
        try:
            # RAW Backup
            if action in ["Backup Configuration (Raw)", "Save All"]:
                st.info(f"Connecting to {brand} ({ip}) for raw backup...")
                with st.spinner("Running commands..."):
                    raw_results = get_all_raw_outputs(
                        ip, brand, username, password)
                    for cmd, output in raw_results.items():
                        if "show processes" in cmd.lower():
                            raw_results[cmd] = "\n".join(
                                output.splitlines()[:15])
                st.success("✅ Successfully connected to Configuration (Raw)!")
                if action != "Save All":
                    st.subheader("📋 Backup Configuration (Raw) Output")
                    st.json(raw_results)
                all_results.append(
                    {"program": "Backup Configuration (Raw)", "summary": raw_results})

            # Parsed Backup
            if action in ["Backup Configuration (textfsm and ntc-template)", "Save All"]:
                st.info(f"Connecting to {brand} ({ip}) for backup...")
                with st.spinner("Running commands..."):
                    parsed_results = get_switch_info(
                        ip, brand, username, password)
                st.success(
                    "✅ Successfully connected to Configuration (textfsm and ntc-template)!")
                if action != "Save All":
                    st.subheader(
                        "📋 Backup Configuration (textfsm and ntc-template) Output")
                    st.json(parsed_results)
                all_results.append(
                    {"program": "Backup Configuration (textfsm and ntc-template)", "summary": parsed_results})

            # Summary
            if action in ["Summary All", "Save All"]:
                st.info(f"Connecting to {brand} ({ip}) for summary...")
                with st.spinner("Collecting summary..."):
                    results = get_switch_info(ip, brand, username, password)
                    device_summary = summarize_device_status(results, brand)
                    iface_cmd = "show ip interface brief" if brand == "Cisco" else "display ip interface brief"
                    port_summary = summarize_ports(
                        brand, results.get(iface_cmd, ""))
                st.success("✅ Successfully connected to Summary!")
                if action != "Save All":
                    st.subheader("📋 Device Summary")
                    st.json(device_summary)
                    st.subheader("🔌 Port Summary")
                    st.json(port_summary)
                all_results.append({"program": "Summary All", "summary": {
                                   "device_summary": device_summary, "port_summary": port_summary}})
                # ================= SHOW OUTPUT FOR SAVE ALL =================
                if action == "Save All":
                    for item in all_results:
                        st.write(f"### 🧩 {item['program']}")
                        if item['program'] == "Summary All":
                            st.subheader(" Device Summary")
                            st.json(item["summary"]["device_summary"])
                            st.subheader(" Port Summary")
                            st.json(item["summary"]["port_summary"])
                        else:
                            st.json(item["summary"])


            # ================= EXPORT REPORT & DOWNLOAD =================
            buffer = StringIO()
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            buffer.write("NETWORK PREVENTIVE MAINTENANCE REPORT\n")
            buffer.write(f"Brand: {brand}\nIP: {ip}\nTimestamp: {now}\n")
            buffer.write("=" * 80 + "\n\n")

            for item in all_results:
                buffer.write(f"--- {item['program']} ---\n\n")
                buffer.write(json.dumps(item["summary"], indent=4, ensure_ascii=False))
                buffer.write("\n" + "=" * 80 + "\n\n")

            # ✅ ตั้งชื่อไฟล์ดาวน์โหลดตามประเภทโปรแกรม
            base_filename = f"{brand}_{ip}"

            if action == "Backup Configuration (Raw)":
                filename = f"{base_filename}_backup(raw).txt"
            elif action == "Backup Configuration (textfsm and ntc-template)":
                filename = f"{base_filename}_backup(parse).txt"
            elif action == "Summary All":
                filename = f"{base_filename}_summaryall.txt"
            elif action == "Save All":
                filename = f"{base_filename}_saveall.txt"
            else:
                filename = f"{base_filename}.txt"

            st.download_button(
                label="📥 Download Report (.txt)",
                data=buffer.getvalue().encode("utf-8"),
                file_name=filename,
                mime="text/plain"
            )

            # ✅ ปุ่ม Run Again
            if st.button("🔄 Run Again"):
                for key in ["run_action", "run_brand", "run_ip", "run_program"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()



        except Exception as e:
            st.error(f"❌ Error occurred: {e}")

st.markdown("---")
st.caption("Developed by Sarochinee Bunyarit 🚀")
