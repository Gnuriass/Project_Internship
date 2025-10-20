import os
import json
import streamlit as st
from datetime import datetime

REPORT_ROOT = "reports"

def list_reports():
    """ดึงรายชื่อไฟล์ report ทั้งหมด"""
    files = []
    for root, dirs, filenames in os.walk(REPORT_ROOT):
        for f in filenames:
            if f.endswith(".txt"):
                path = os.path.join(root, f)
                files.append({
                    "filename": f,
                    "path": path,
                    "modified": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
                })
    return sorted(files, key=lambda x: x["modified"], reverse=True)


def parse_report(file_path):
    """อ่านไฟล์รายงานและสรุปข้อมูลหลักออกมา"""
    device_data = {}
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    brand = ""
    ip = ""
    for line in text.splitlines():
        if line.startswith("Brand:"):
            brand = line.split(":", 1)[1].strip()
        if line.startswith("Management IP:"):
            ip = line.split(":", 1)[1].strip()

    # ดึงส่วน Summary
    match = text.split("Device Summary:")
    if len(match) > 1:
        try:
            summary_str = match[1].split("Port Summary:")[0]
            summary = json.loads(summary_str)
            device_data = summary
        except Exception:
            pass

    return {
        "brand": brand,
        "ip": ip,
        **device_data
    }


# ==============================
# Streamlit App
# ==============================
st.set_page_config(page_title="Network Maintenance Dashboard", layout="wide")

st.title("🌐 Network Preventive Maintenance Dashboard")

# เลือกไฟล์รายงาน
reports = list_reports()
if not reports:
    st.warning("❌ No report files found in the 'reports/' folder.")
    st.stop()

report_file = st.selectbox(
    "📄 Select a report file:",
    options=[f["path"] for f in reports],
    format_func=lambda x: os.path.basename(x)
)

if report_file:
    st.info(f"📂 Loaded file: {os.path.basename(report_file)}")
    data = parse_report(report_file)

    # ==============================
    # Device Summary
    # ==============================
    st.subheader("📊 Device Summary")
    summary_data = {k: v for k, v in data.items() if k not in ("brand", "ip", "Fiber", "UTP")}
    st.table(summary_data)

    # ==============================
    # Port Summary
    # ==============================
    st.subheader("🔌 Port Summary")
    import plotly.graph_objects as go

    fiber = data.get("Fiber", {"up": 0, "down": 0, "total": 0})
    utp = data.get("UTP", {"up": 0, "down": 0, "total": 0})

    fig = go.Figure(data=[
        go.Bar(name="UP", x=["Fiber", "UTP"], y=[fiber["up"], utp["up"]]),
        go.Bar(name="DOWN", x=["Fiber", "UTP"], y=[fiber["down"], utp["down"]])
    ])
    fig.update_layout(
        barmode="stack",
        title="Port Status Summary",
        xaxis_title="Port Type",
        yaxis_title="Number of Ports"
    )
    st.plotly_chart(fig, use_container_width=True)

    # ==============================
    # Raw JSON Output (Optional)
    # ==============================
    with st.expander("Show Raw JSON Data"):
        st.json(data)
