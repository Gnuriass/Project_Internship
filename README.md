# Automatic Network Device Backup and Monitoring System (NetworkTool)

ระบบสำรองข้อมูลและตรวจสอบอุปกรณ์เครือข่ายอัตโนมัติ พัฒนาขึ้นในรูปแบบ Web Dashboard เพื่อเปลี่ยนกระบวนการทำ Network Preventive Maintenance จากเดิมที่เป็นแบบ Manual ให้เป็นระบบอัตโนมัติ ช่วยเพิ่มความรวดเร็ว ลดความผิดพลาด และจัดการข้อมูลการตั้งค่าอย่างเป็นระบบ

---

## 🌟 คุณสมบัติเด่นของระบบ (Key Features)
- **Multi-Vendor Auto-Backup:** เชื่อมต่อและสำรองข้อมูลการตั้งค่าอุปกรณ์เครือข่ายได้หลากหลายยี่ห้อ (รองรับ Cisco, HPE, H3C) พร้อมกันแบบอัตโนมัติ
- **Smart Configuration Parsing:** แปลงข้อมูลข้อความดิบ (Raw Data) จากการใช้คำสั่ง `show running-config` ให้ออกมาเป็นโครงสร้างข้อมูลที่อ่านง่าย (เช่น JSON/Key-Value)
- **Device & Port Summary:** หน้าจอสรุปข้อมูลสถานะของอุปกรณ์ (Version, Uptime, Hardware, CPU/Memory Usage) และสถานะพอร์ตเชื่อมต่อ (นับจำนวนพอร์ต Fiber และ UTP ที่ใช้งานอยู่และปิดอยู่) เพื่อความสะดวกในการกรอก Network Equipment Check Sheet
- **Executable Version:** สามารถคอมไพล์ระบบเป็นไฟล์ Executable (.exe) เพื่อเปิดใช้งานได้ทันทีโดยที่เครื่องปลายทางไม่จำเป็นต้องติดตั้ง Python
- **Report Generation:** จัดเก็บรายงานสรุปผลอัตโนมัติออกมาในรูปแบบไฟล์ Text (.txt) โดยตั้งชื่อแยกตามสถาปัตยกรรม `Brand_IP_Program.txt` พร้อมระบบประทับเวลา (Timestamp)

---

## 🏗️ สถาปัตยกรรมและการทำงานของระบบ (System Architecture)
ระบบทำงานผ่าน 4 โปรแกรมหลักที่ผู้ใช้งานสามารถเลือกสั่งการได้ตามความต้องการ:
1. **Program 1 (Backup Config Raw):** สำรองข้อมูลคอนฟิกดิบจากตัวอุปกรณ์โดยตรง
2. **Program 2 (Backup Config Parsed):** สำรองข้อมูลคอนฟิกพร้อมแปลงค่าให้อยู่ในโครงสร้าง Structured Data ด้วย Engine พิเศษ
3. **Program 3 (Summary All):** ดึงข้อมูลสรุปภาพรวมของฮาร์ดแวร์ อุณหภูมิ ประวัติการรีโหลด และปริมาณพอร์ตที่ใช้งาน
4. **Program 4 (Save All):** สั่งรันและบันทึกข้อมูลทุกหมวดหมู่พร้อมกันในครั้งเดียว

---

## 🛠️ เครื่องมือที่ใช้พัฒนาเทคโนโลยี (Tech Stack)

### Core Language & UI Framework
- **Python 3.8+** (ภาษาหลักในการพัฒนา Logic)
- **Streamlit** (Web UI Framework สำหรับสร้าง Dashboard หน้าบ้าน)

### Libraries & Core Utilities
- **Netmiko:** จัดการการเชื่อมต่อระยะไกลและส่งชุดคำสั่งไปยัง Switch/Router ผ่านโปรโตคอล SSH
- **TextFSM & NTC Templates:** มอเตอร์หลักในการแปลง Text Output ที่ไม่มีโครงสร้างให้กลายเป็น Structured Data และมีการปรับแต่ง Custom Template เพิ่มเติมเพื่อรองรับคำสั่งที่ซับซ้อน
- **Pandas:** ใช้สำหรับเขียน-อ่าน และจัดการตารางข้อมูลอุปกรณ์
- **PyInstaller:** ใช้ห่อหุ้มซอร์สโค้ดเพื่อสร้างโปรแกรมพร้อมใช้งานแบบ Executable (.exe)

---

## 📂 โครงสร้างของโปรเจค (Project Structure)
    ```text
    NetworkTool/
    ├── templates/             # โฟลเดอร์เก็บไฟล์ Custom TextFSM Template สำหรับ Parse ข้อมูล
    ├── app.py                 # ตัวจัดการหน้าเว็บหน้าบ้าน (Web Interface & UI Logic)
    ├── main.py                # ระบบประมวลผลหลังบ้าน (Backend Logic & SSH Connection)
    ├── run_app.py             # Script สำหรับการสั่งรันโปรแกรมหลัก
    ├── dataset.xlsx           # ฐานข้อมูลภายในสำหรับเก็บค่า Brand, IP, Username, Password ของอุปกรณ์
    ├── requirements.txt       # รายการ Library และ Dependency ที่ระบบต้องการ
    └── NetworkTool.spec       # ไฟล์ตั้งค่าสำหรับใช้ทำคอมไพล์ด้วย PyInstaller

## 🚀 ขั้นตอนการติดตั้งและรันใช้งาน (Getting Started)
1. โคลนและเตรียมตัวโปรเจค
   - git clone [https://github.com/Gnuriass/NetworkTool.git](https://github.com/Gnuriass/NetworkTool.git)
cd NetworkTool
2. ติดตั้ง Library ที่จำเป็น
   - pip install -r requirements.txt
3. สั่งรันระบบ
   - streamlit run app.py
จากนั้นเข้าใช้งานผ่านเว็บเบราว์เซอร์ที่ URL: http://localhost:8501 (หรือพอร์ตที่ระบุบน Terminal)

## 👥 ผู้จัดทำโครงการ (Project Members)
  - นางสาวสโรชินี บุญฤทธิ์ (Sarochinee Bunyarit)
  - นักศึกษาชั้นปีที่ 4 คณะวิศวกรรมศาสตร์ สาขาคอมพิวเตอร์และปัญญาประดิษฐ์ (CE)
  - สถาบันเทคโนโลยีไทย-ญี่ปุ่น (TNI)

โครงงานนี้เป็นส่วนหนึ่งของวิชา CPE-492 Co-operative Education (สหกิจศึกษา) โดยได้รับการสนับสนุนด้านเทคนิคและการฝึกฝนการทำ Preventive Maintenance ภายใต้การดูแลของทีม Network Engineer บริษัท ชุน บ็อก จำกัด
