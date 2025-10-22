import pandas as pd
from netmiko import ConnectHandler
from ntc_templates.parse import parse_output
import datetime
import os
import json
import textfsm
import re

# ... (ส่วนของ TEMPLATE_PATH และ dataset ไม่มีการเปลี่ยนแปลง) ...
TEMPLATE_PATH_POOL = os.path.join(os.getcwd(), "templates", "cisco_ios_show_processes_pool.textfsm")
TEMPLATE_PATH_PROCESSES = os.path.join(os.getcwd(), "templates", "cisco_ios_show_processes_process.textfsm")
TEMPLATE_PATH_RUNNING = os.path.join(os.getcwd(), "templates", "cisco_ios_show_running-config.textfsm")

dataset = pd.read_excel("dataset.xlsx")

brand_commands = {
    "Cisco": [
        "show running-config",
        "show ip interface brief",
        "show version",
        "show lldp neighbors detail",
        "show processes cpu",
        "show processes memory",
        "show env all",
        "show interfaces transceiver",
        "show interfaces transceiver detail",
        "show etherchannel summary",
        "show etherchannel port-channel",
    ],
    "HPE": [
        "display current-configuration",
        "display ip interface brief",
        "display version",
        "display device manuinfo",
        "display lldp neighbor-information",
        "display environment",
        "display fan",
        "display power",
        "display transceiver interface",
        "display transceiver manuinfo interface",
        "display link-aggregation summary",
        "display link-aggregation member-port",
    ],
    "H3C": [
        "display current-configuration",
        "display version",
        "display ip interface brief",
        "display device manuinfo",
        "display environment",
        "display cpu-usage",
        "display ntp-service status",
        "display fan",
    ],
}


POOL_KEYS_ORDER = ["POOL_NAME", "POOL_TOTAL", "POOL_USED", "POOL_FREE"]
PROCESS_KEYS_ORDER = [
    "PROCESS_PID",
    "PROCESS_TTY",
    "PROCESS_ALLOCATED",
    "PROCESS_FREED",
    "PROCESS_HOLDING",
    "PROCESS_GETBUFS",
    "PROCESS_RETBUFS",
    "PROCESS_NAME",
]
RUNNING_KEYS_ORDER = [
    "HOSTNAME",
    "DOMAIN",
    "USERNAME",
    "PRIVILEGE",
    "PASSWORD",
    "INTERFACE",
    "IP_ADDRESS",
    "SUBNET_MASK",
    "GATEWAY",
    "SNMP_COMMUNITY",
    "NTP_SERVER",
]


def reorder_dict(d, key_order):
    return {k: d.get(k, "") for k in key_order}


def parse_custom_template(command, output):
    try:
        output_str = "\n".join(output) if isinstance(output, list) else str(output)
        results = {}

        if "show processes memory" in command:
            lines = output_str.splitlines()
            pool_lines, process_lines = [], []
            process_section = False

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("PID") and "Process" in line:
                    process_section = True
                    continue
                if process_section:
                    process_lines.append(line)
                else:
                    pool_lines.append(line)

            with open(TEMPLATE_PATH_POOL) as f:
                fsm = textfsm.TextFSM(f)
                parsed = fsm.ParseText("\n".join(pool_lines))
                results["pool"] = [
                    reorder_dict(dict(zip(fsm.header, row)), POOL_KEYS_ORDER)
                    for row in parsed
                ]

            with open(TEMPLATE_PATH_PROCESSES) as f:
                fsm = textfsm.TextFSM(f)
                parsed = fsm.ParseText("\n".join(process_lines))
                results["process"] = [
                    reorder_dict(dict(zip(fsm.header, row)), PROCESS_KEYS_ORDER)
                    for row in parsed[:15]
                ]

        elif "show running-config" in command or "display current-configuration" in command:
            with open(TEMPLATE_PATH_RUNNING) as f:
                fsm = textfsm.TextFSM(f)
                parsed = fsm.ParseText(output_str)

                parsed_list = [dict(zip(fsm.header, row)) for row in parsed]

                for item in parsed_list:
                    for k, v in item.items():
                        if not v:
                            continue
                        if k == "NTP_SERVER":
                            if "NTP_SERVER" in results:
                                if isinstance(results["NTP_SERVER"], list):
                                    results["NTP_SERVER"].append(v)
                                else:
                                    results["NTP_SERVER"] = [results["NTP_SERVER"], v]
                            else:
                                results["NTP_SERVER"] = v
                        else:
                            results[k] = v

        if "NTP_SERVER" not in results:
            ntp_fallback = re.findall(r"ntp\s+server\s+(\d{1,3}(?:\.\d{1,3}){3})", output_str, re.I)
            if ntp_fallback:
                results["NTP_SERVER"] = ntp_fallback if len(ntp_fallback) > 1 else ntp_fallback[0]

        return results if results else output_str.splitlines()[:50]

    except Exception as e:
        print(f"❌ TextFSM parse error for {command}: {e}")
        return output_str.splitlines()[:50]



def parse_with_ntc(brand, command, output):
    try:
        if isinstance(output, list):
            output = "\n".join(output)

        if brand == "Cisco":
            if command in ["show processes memory", "show running-config"]:
                return parse_custom_template(command, output)
            else:
                parsed = parse_output(platform="cisco_ios", command=command, data=output)
        else:
            device_types = {"HPE": "hp_procurve", "H3C": "h3c_comware"}
            parsed = parse_output(platform=device_types[brand], command=command, data=output)

        if isinstance(parsed, list):
            if command in ["show processes cpu", "show processes memory"]:
                parsed = parsed[:15]

        return parsed if parsed else output

    except Exception:
        return output if isinstance(output, str) else "\n".join(output)


def get_switch_info(ip, brand, username, password):
    """Connects and runs all commands, returning PARSED output."""
    device_types = {"Cisco": "cisco_ios", "HPE": "hp_procurve", "H3C": "h3c_comware"}
    if brand not in device_types:
        raise ValueError(f"❌ Brand {brand} not supported")

    device = {
        "device_type": device_types[brand],
        "ip": ip,
        "username": username,
        "password": password,
        "secret": password,
        "fast_cli": True,
    }
    
    connection = None
    try:
        connection = ConnectHandler(**device)

        if brand == "Cisco":
            connection.enable()
            connection.send_command("terminal length 0", read_timeout=5)
        elif brand in ["HPE", "H3C"]:
            connection.send_command("screen-length disable", read_timeout=5)
        
        print(f"✅ Successfully connected to {brand} {ip}\n")

        results = {}
        for cmd in brand_commands[brand]:
            try:
                if "processes cpu" in cmd.lower():
                    output = connection.send_command_timing(cmd, delay_factor=2, max_loops=1000)
                else:
                    output = connection.send_command(cmd, read_timeout=60, delay_factor=1.0, expect_string=r"[#>]")

                output_str = "\n".join(output) if isinstance(output, list) else output
                results[cmd] = parse_with_ntc(brand, cmd, output_str)

            except Exception as e:
                results[cmd] = f"❌ Error running command {cmd}: {e}"
        
        return results
    finally:
        if connection:
            connection.disconnect()


def get_all_raw_outputs(ip, brand, username, password):
    """Connects and runs all commands for a brand, returning RAW TEXT output."""
    device_types = {"Cisco": "cisco_ios", "HPE": "hp_procurve", "H3C": "h3c_comware"}
    if brand not in device_types:
        raise ValueError(f"❌ Brand {brand} not supported")

    device = {
        "device_type": device_types[brand],
        "ip": ip,
        "username": username,
        "password": password,
        "secret": password,
        "fast_cli": True,
    }
    
    connection = None
    try:
        connection = ConnectHandler(**device)

        if brand == "Cisco":
            connection.enable()
            connection.send_command("terminal length 0", read_timeout=5)
        elif brand in ["HPE", "H3C"]:
            connection.send_command("screen-length disable", read_timeout=5)
        
        print(f"✅ Successfully connected to {brand} {ip} for raw command output\n")

        results = {}
        for cmd in brand_commands[brand]:
            try:
                if "processes cpu" in cmd.lower():
                    output = connection.send_command_timing(cmd, delay_factor=2, max_loops=1000)
                else:
                    output = connection.send_command(cmd, read_timeout=60, expect_string=r"[#>]")
                
                results[cmd] = output if isinstance(output, str) else str(output)

            except Exception as e:
                results[cmd] = f"❌ Error running command {cmd}: {e}"
        
        return results
    finally:
        if connection:
            connection.disconnect()


def is_fiber_port(iface):
    iface = iface.lower()
    fiber_keywords = (
        "gi", "te", "tengig", "xge", "fo", "fiber", "forty",
        "hundred", "twentyfive", "xe", "eth-trunk", "port-channel",
    )
    return any(iface.startswith(k) for k in fiber_keywords)


def summarize_ports(brand, interface_output):
    summary = {
        "Fiber": {"total": 0, "up": 0, "down": 0},
        "UTP": {"total": 0, "up": 0, "down": 0},
    }
    lines = interface_output if isinstance(interface_output, list) else interface_output.splitlines()
    for row in lines:
        iface, status, protocol = "", "down", "down"
        if isinstance(row, dict):
            iface = (row.get("intf") or row.get("interface") or row.get("port") or row.get("name") or "").strip()
            status = (row.get("status") or "").lower()
            protocol = (row.get("protocol") or row.get("proto") or "").lower()
            is_up = (status == "up" and protocol == "up") if brand == "Cisco" else (status == "up")
        else:
            line = str(row).strip()
            if not line or line.lower().startswith(("interface", "port", "---")):
                continue
            parts = line.split()
            iface = parts[0]
            if len(parts) >= 3:
                status, protocol = parts[-2].lower(), parts[-1].lower()
            elif len(parts) >= 2:
                status, protocol = parts[-1].lower(), ""
            else:
                continue
            is_up = (status == "up" and protocol == "up") if brand == "Cisco" else (status == "up")
        if not iface:
            continue
        iface_lower = iface.lower()
        if is_fiber_port(iface_lower):
            port_type = "Fiber"
        else:
            port_type = "UTP"
        summary[port_type]["total"] += 1
        summary[port_type]["up" if is_up else "down"] += 1
    return summary


def summarize_device_status(results, brand):
    summary = {
        "version": "", "bootloader": "", "uptime": "", "NTP_SERVER": "",
        "CPU Usage": "", "Memory Usage": "", "Temperature": "",
    }
    try:
        version_cmd = "display version" if brand in ["HPE", "H3C"] else "show version"
        version_output = results.get(version_cmd, "")
        if isinstance(version_output, list) and len(version_output) > 0:
            ver = version_output[0]
            summary.update(ver)
        elif isinstance(version_output, dict):
            summary.update(version_output)
        elif isinstance(version_output, str):
            ver_match = re.search(r"[Vv]ersion\s+([\w\.\(\)]+)", version_output)
            if ver_match: summary["version"] = ver_match.group(1)
            boot_match = re.search(r"(Boot\s*Loader|BOOTLDR).*?Version.*", version_output)
            if boot_match: summary["bootloader"] = boot_match.group(0).strip()
            uptime_match = re.search(r"[Uu]ptime\s+is\s+(.+)", version_output)
            if uptime_match: summary["uptime"] = uptime_match.group(1).strip()

        config_cmd = "display current-configuration" if brand in ["HPE", "H3C"] else "show running-config"
        config_output = results.get(config_cmd, "")
        ntp_servers = []
        if isinstance(config_output, dict):
            val = config_output.get("NTP_SERVER", "")
            if val: ntp_servers.extend(val) if isinstance(val, list) else ntp_servers.append(val)
        config_output_str = str(config_output)
        if not ntp_servers:
            ntp_servers += re.findall(r"ntp\s+server\s+(\d{1,3}(?:\.\d{1,3}){3})", config_output_str, re.I)
        summary["NTP_SERVER"] = ",".join(ntp_servers) if ntp_servers else ""

        # --- โค้ดที่แก้ไขแล้ว ---
        # show processes cpu
        cpu_cmd = "display cpu-usage" if brand in ["HPE", "H3C"] else "show processes cpu"
        cpu_output = results.get(cpu_cmd, "")

        cpu_val = ""
        if isinstance(cpu_output, list) and len(cpu_output) > 0:
            # ตรวจสอบ key ที่เป็นไปได้หลายชื่อ
            cpu_info = cpu_output[0]
            cpu_val = cpu_info.get("cpu_5_sec") or cpu_info.get("five_sec_cpu") or cpu_info.get("cpu_usage_5_sec")
            
        if cpu_val:
            summary["CPU Usage"] = f"{cpu_val}%"
        # หากยังหาไม่เจอในข้อมูลที่ Parse แล้ว ให้ลองหาจากข้อความดิบ (กรณี Parse ล้มเหลว)
        elif isinstance(cpu_output, str):
            # ปรับปรุง regex ให้รองรับ H3C และ Cisco
            cpu_match = re.search(r"five\s+seconds.*?(\d+)%|CPU Usage.*?(\d+)%", cpu_output, re.I)
            if cpu_match:
                # group(1) สำหรับ Cisco, group(2) สำหรับ H3C
                usage = cpu_match.group(1) or cpu_match.group(2)
                summary["CPU Usage"] = f"{usage}%"

        mem_cmd = "display memory" if brand in ["HPE", "H3C"] else "show processes memory"
        mem_output = results.get(mem_cmd, "")
        if isinstance(mem_output, dict) and "pool" in mem_output:
            for pool in mem_output["pool"]:
                if pool.get("POOL_NAME", "").lower() == "processor":
                    try:
                        used, total = int(pool.get("POOL_USED", 0)), int(pool.get("POOL_TOTAL", 1))
                        summary["Memory Usage"] = f"{round((used / total) * 100, 2)}%"
                    except (ValueError, ZeroDivisionError): pass
        
        env_cmd = "display environment" if brand in ["HPE", "H3C"] else "show env all"
        env_output = results.get(env_cmd, "")
        if isinstance(env_output, str):
            env_lines = [key for key in ["FAN is OK", "TEMPERATURE is OK", "POWER is OK"] if key in env_output]
            summary["Temperature"] = ",".join(env_lines) if env_lines else "No status found"
    except Exception as e:
        print(f"⚠️ summarize_device_status error: {e}")
    return summary


def save_selected_results_txt(all_results, save_root="reports"):
    if not all_results:
        print("\nNo results to save!")
        return
    now = datetime.datetime.now()
    year, month = now.strftime("%Y"), now.strftime("%m")
    save_dir = os.path.join(save_root, year, month)
    os.makedirs(save_dir, exist_ok=True)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    grouped_results = {}
    for item in all_results:
        key = (item["ip"], item["brand"])
        grouped_results.setdefault(key, []).append(item)
    for (ip, brand), device_results in grouped_results.items():
        filename = os.path.join(save_dir, f"report_{brand}_{ip}_{timestamp}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("Network Preventive Maintenance Report\n")
            f.write(f"Brand: {brand}\n")
            f.write(f"Management IP: {ip}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write("=" * 80 + "\n\n")
            executed_programs = [entry["program"] for entry in device_results]
            for entry in device_results:
                program_name = entry["program"]
                summary_data = entry["summary"]
                f.write(f"===== Program: {program_name} =====\n\n")
                if program_name in ["Backup Configuration", "Backup Configuration (textfsm and ntc-template)"]:
                    for cmd, output in summary_data.items():
                        f.write(f"------ {cmd} ------\n")
                        if isinstance(output, (dict, list)):
                            f.write(json.dumps(output, indent=4, ensure_ascii=False))
                        else:
                            f.write(str(output))
                        f.write("\n\n")
                elif program_name == "Summary All":
                    f.write(json.dumps(summary_data, indent=4, ensure_ascii=False))
                    f.write("\n\n")
            f.write("=" * 80 + "\n")
            f.write("=== Summary of Executed Programs (This Device) ===\n")
            f.write(f"{brand} {ip} → {', '.join(executed_programs)}\n")
            f.write("=" * 80 + "\n")
        print(f"\n✅ Report for {ip} saved to: {filename}")


def interactive_main():
    all_results = []
    first_run = True
    while True:
        if first_run:
            print("\n=== Welcome to Network Maintenance CLI ===")
            print("\n>Please choose an option to make")
            first_run = False
        else:
            print("\n>Please choose an option to continue.")
        print("1. Backup Configuration")
        print("2. Backup Configuration (textfsm and ntc-template)")
        print("3. Summary All")
        print("4. Save and End of Program")
        while True:
            choice = input("\nChoose your choice (1-4): ").strip()
            if choice in ("1", "2", "3", "4"):
                break
            else:
                print("\n❌ Invalid choice or number. Please choose again.")
        if choice == "4":
            save_selected_results_txt(all_results)
            print("End of program execution ✅")
            break

        print("\n=== Available Brands ===")
        brands = sorted(dataset["Brand"].dropna().astype(str).unique())
        for i, b in enumerate(brands, start=1):
            print(f"{i}. {b}")
        while True:
            try:
                brand_choice = int(input("\nChoose a Brand: "))
                if 1 <= brand_choice <= len(brands):
                    brand = brands[brand_choice - 1]
                    break
                else:
                    print("\n❌ Invalid number. Please choose again.")
            except ValueError:
                print("\n❌ Invalid input. Please enter a number.")
        
        print(f"\n=== Available IPs for {brand} ===")
        brand_ips = dataset[dataset["Brand"] == brand]["IP"].dropna().astype(str).tolist()
        for i, ip in enumerate(brand_ips, start=1):
            print(f"{i}. {ip}")
        while True:
            try:
                ip_choice = int(input("\nChoose an IP: "))
                if 1 <= ip_choice <= len(brand_ips):
                    ip = brand_ips[ip_choice - 1]
                    break
                else:
                    print("\n❌ Invalid number. Please choose again.")
            except ValueError:
                print("\n❌ Invalid input. Please enter a number.")
        
        row = dataset[(dataset["Brand"] == brand) & (dataset["IP"] == ip)].iloc[0]
        username, password = row["Username"], row["Password"]
        try:
            # 1. Backup Configuration
            if choice == "1":
                program_name = "Backup Configuration"
                print("=" * 80 + "")
                print(f"Connecting to {brand} ({ip}) for raw command backup...")
                raw_results = get_all_raw_outputs(ip, brand, username, password)
                
                # --- CHANGE HERE: Truncate specific commands for raw output ---
                for cmd, output in raw_results.items():
                    if "show processes cpu" in cmd or "show processes memory" in cmd:
                        truncated_output = "\n".join(output.splitlines()[:15])
                        raw_results[cmd] = truncated_output

                print(f"===== Program: {program_name} =====")
                for cmd, output in raw_results.items():
                    print(f"------ {cmd} ------")
                    print(output)
                    print()
                
                all_results.append({"ip": ip, "brand": brand, "program": program_name, "summary": raw_results})

            # 2. Backup All Commands (Parsed)
            elif choice == "2":
                program_name = "Backup Configuration (textfsm and ntc-template)"
                print("=" * 80 + "")
                print(f"Connecting to {brand} ({ip}) for parsed backup...")
                results = get_switch_info(ip, brand, username, password)
                
                print(f"===== Program: {program_name} =====")
                for cmd, output in results.items():
                    print(f"------ {cmd} ------")
                    if isinstance(output, (dict, list)):
                        print(json.dumps(output, indent=4, ensure_ascii=False))
                    else:
                        print(output)
                    print()
                
                all_results.append({"ip": ip, "brand": brand, "program": program_name, "summary": results})

            # 3. Summary All
            elif choice == "3":
                program_name = "Summary All"
                print("=" * 80 + "")
                print(f"Connecting to {brand} ({ip}) for summary...")
                results = get_switch_info(ip, brand, username, password)
                
                print(f"===== Program: {program_name} =====")
                device_summary = summarize_device_status(results, brand)
                print("Device Summary:")
                print(json.dumps(device_summary, indent=4, ensure_ascii=False))

                iface_cmd = "show ip interface brief" if brand == "Cisco" else "display ip interface brief"
                port_summary = summarize_ports(brand, results.get(iface_cmd, ""))
                print("\nPort Summary:")
                print(json.dumps(port_summary, indent=4, ensure_ascii=False))

                all_results.append({"ip": ip, "brand": brand, "program": program_name, "summary": {"device_summary": device_summary, "port_summary": port_summary}})

        except Exception as e:
            print(f"❌ An error occurred during operation for {ip}: {e}")


if __name__ == "__main__":
    interactive_main()