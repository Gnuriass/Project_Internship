import os
import json
import pandas as pd
from datetime import datetime
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc

# ==== CONFIG ====
REPORT_ROOT = "reports"
app = Dash(__name__, external_stylesheets=[dbc.themes.SANDSTONE])
app.title = "Network Maintenance Dashboard"


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


# ==== Layout ====
app.layout = dbc.Container([
    dbc.Row([
        html.H2("Network Preventive Maintenance Dashboard", className="text-center mt-3 mb-4")
    ]),
    dbc.Row([
        dbc.Col([
            html.Label("📁 Select Report File:"),
            dcc.Dropdown(
                id="report-dropdown",
                options=[{"label": f["filename"], "value": f["path"]} for f in list_reports()],
                placeholder="เลือกไฟล์รายงาน...",
                value=None,
                clearable=False
            ),
            html.Div(id="report-info", className="mt-3")
        ], width=4),
        dbc.Col([
            html.H4("📊 Device Summary", className="mt-2"),
            dash_table.DataTable(
                id="device-summary-table",
                columns=[{"name": "Field", "id": "Field"}, {"name": "Value", "id": "Value"}],
                data=[],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left"},
                style_header={"backgroundColor": "#007BFF", "color": "white"}
            ),
            html.Br(),
            html.H4("🔌 Port Summary"),
            dcc.Graph(id="port-summary-graph")
        ], width=8)
    ]),
], fluid=True)


# ==== Callbacks ====
@app.callback(
    [Output("report-info", "children"),
     Output("device-summary-table", "data"),
     Output("port-summary-graph", "figure")],
    [Input("report-dropdown", "value")]
)
def update_dashboard(report_path):
    if not report_path:
        return "No file selected.", [], {}

    info = f"📄 Loaded file: {os.path.basename(report_path)}"
    data = parse_report(report_path)

    # Device summary table
    summary_data = [{"Field": k, "Value": v} for k, v in data.items() if k not in ("brand", "ip", "Fiber", "UTP")]

    # Port summary chart
    import plotly.graph_objects as go
    fiber = data.get("Fiber", {"up": 0, "down": 0, "total": 0})
    utp = data.get("UTP", {"up": 0, "down": 0, "total": 0})

    fig = go.Figure(data=[
        go.Bar(name="UP", x=["Fiber", "UTP"], y=[fiber["up"], utp["up"]]),
        go.Bar(name="DOWN", x=["Fiber", "UTP"], y=[fiber["down"], utp["down"]])
    ])
    fig.update_layout(barmode="stack", title="Port Status Summary")

    return info, summary_data, fig


if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
