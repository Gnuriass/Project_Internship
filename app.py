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

st.set_page_config(page_title="Network Maintenance Tool", layout="wide")

st.title("🌐 Network Preventive Maintenance Dashboard")
st.write("Perform backup your device and summarize the configuration.")

APP_DIR = os.path.dirname(__file__)
DATASET_PATH = os.path.join(APP_DIR, "dataset.xlsx")
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")

missing_files = []
if not os.path.exists(DATASET_PATH):
    missing_files.append("dataset.xlsx")

template_files = [
    "cisco_ios_show_processes_pool.textfsm",
    "cisco_ios_show_processes_process.textfsm",
    "cisco_ios_show_running-config.textfsm",
]
for t_file in template_files:
    if not os.path.exists(os.path.join(TEMPLATES_DIR, t_file)):
        missing_files.append(f"templates/{t_file}")

dataset = None
if missing_files:
    st.error(
        "❌ **Streamlit Failed:** Please check your file structure. The following essential files/folders are missing:"
    )
    st.markdown(f"**Missing Items:**\n- `{'`\n- `'.join(missing_files)}`")
    st.info(
        "The file structure should be: `run_app.py`, `app.py`, `main.py`, `dataset.xlsx`, and a subfolder `templates/` with the required TextFSM files inside."
    )
    st.stop()

try:
    dataset = pd.read_excel(DATASET_PATH)
except Exception as e:
    st.error(f"❌ Error loading dataset.xlsx: {e}")
    st.stop()

# ---------------- MAIN UI ----------------
if dataset is not None:
    brands = sorted(dataset["Brand"].dropna().astype(str).unique())
    brand = st.selectbox("Select Device Brand", brands)

    if brand:
        ips = dataset[dataset["Brand"] ==
                      brand]["IP"].dropna().astype(str).tolist()
        ip = st.selectbox(f"Select IP for {brand}", ips)

        if ip:
            row = dataset[(dataset["Brand"] == brand) &
                          (dataset["IP"] == ip)].iloc[0]
            username, password = row["Username"], row["Password"]

            st.markdown("---")
            st.subheader("🕹️Select Action")

            action = st.radio(
                "Choose a program to run:",
                [
                    "Backup Configuration (Raw)",
                    "Backup Configuration (Parsed)",
                    "Summary All",
                    "Save All",  
                ],
                horizontal=True,
            )

            all_results = []


            if st.button("🚀 Run Program"):


                try:

                    if action in ["Backup Configuration (Raw)", "Save All"]:
                        st.info(
                            f"Connecting to {brand} ({ip}) for raw command backup..."
                        )
                        with st.spinner("Running commands..."):
                            raw_results = get_all_raw_outputs(
                                ip, brand, username, password
                            )


                            for cmd, output in raw_results.items():
                                if (
                                    "show processes cpu" in cmd
                                    or "show processes memory" in cmd
                                ):
                                    raw_results[cmd] = "\n".join(
                                        output.splitlines()[:15]
                                    )

                            st.success(
                                "✅ Backup (Raw) completed successfully!")
                            if action != "Save All":
                                st.subheader("📋 Backup Configuration (Raw)")
                                st.json(raw_results)

                            all_results.append(
                                {
                                    "ip": ip,
                                    "brand": brand,
                                    "program": "Backup Configuration (Raw)",
                                    "summary": raw_results,
                                }
                            )


                    if action in ["Backup Configuration (Parsed)", "Save All"]:
                        st.info(
                            f"Connecting to {brand} ({ip}) for parsed backup...")
                        with st.spinner("Running commands..."):
                            parsed_results = get_switch_info(
                                ip, brand, username, password
                            )

                            st.success(
                                "✅ Backup (Parsed) completed successfully!")
                            if action != "Save All":
                                st.subheader("📋 Backup Configuration (Parsed)")
                                st.json(parsed_results)

                            all_results.append(
                                {
                                    "ip": ip,
                                    "brand": brand,
                                    "program": "Backup Configuration (Parsed)",
                                    "summary": parsed_results,
                                }
                            )


                    if action in ["Summary All", "Save All"]:
                        st.info(f"Connecting to {brand} ({ip}) for summary...")
                        with st.spinner("Collecting data..."):
                            results = get_switch_info(
                                ip, brand, username, password)
                            device_summary = summarize_device_status(
                                results, brand)
                            iface_cmd = (
                                "show ip interface brief"
                                if brand == "Cisco"
                                else "display ip interface brief"
                            )
                            port_summary = summarize_ports(
                                brand, results.get(iface_cmd, "")
                            )

                            st.success("✅ Summary generated successfully!")
                            if action != "Save All":
                                st.subheader("📋 Device Summary")
                                st.json(device_summary)
                                st.subheader("🔌 Port Summary")
                                st.json(port_summary)

                            all_results.append(
                                {
                                    "ip": ip,
                                    "brand": brand,
                                    "program": "Summary All",
                                    "summary": {
                                        "device_summary": device_summary,
                                        "port_summary": port_summary,
                                    },
                                }
                            )

                    if all_results:
                        buffer = StringIO()
                        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        buffer.write("NETWORK PREVENTIVE MAINTENANCE REPORT\n")
                        buffer.write(
                            f"Brand: {brand}\nIP: {ip}\nTimestamp: {now}\n")
                        buffer.write("=" * 80 + "\n\n")

                        for item in all_results:
                            buffer.write(f"--- {item['program']} ---\n\n")
                            summary_data = item["summary"]

                            if action == "Save All":
                                st.markdown(f"### 🧩 {item['program']}")
                                if item["program"] == "Summary All":
                                    st.subheader("📋 Device Summary")
                                    st.json(summary_data["device_summary"])
                                    st.subheader("🔌 Port Summary")
                                    st.json(summary_data["port_summary"])
                                else:
                                    st.json(summary_data)

                            if isinstance(summary_data, dict):
                                if all(isinstance(v, str) for v in summary_data.values()):
                                    for cmd, output in summary_data.items():
                                        buffer.write("-" * 60 + "\n")
                                        buffer.write(f"> {cmd}\n\n")
                                        buffer.write(output.strip() + "\n\n")
                                else:
                                    buffer.write(
                                        json.dumps(
                                            summary_data, indent=4, ensure_ascii=False)
                                    )
                            else:
                                buffer.write(str(summary_data))

                            buffer.write("\n" + "=" * 80 + "\n\n")

                        report_text = buffer.getvalue()

                        file_suffix = (
                            "all"
                            if action == "Save All"
                            else action.replace(" ", "_")
                            .replace("(", "")
                            .replace(")", "")
                            .lower()
                        )

                        st.download_button(
                            label="📥 Download Report (.txt)",
                            data=report_text.encode("utf-8"),
                            file_name=f"report_{brand}_{ip}_{file_suffix}.txt",
                            mime="text/plain",
                        )

                        if st.button("🔄 Do Another Task"):
                            st.experimental_rerun()

                except Exception as e:
                    st.error(
                        f"❌ An error occurred during connection or operation: {e}"
                    )

else:
    st.stop()

st.markdown("---")
st.caption(
    "Developed by Sarochinee Bunyarit • Streamlit version of main.py CLI tool 🚀")
