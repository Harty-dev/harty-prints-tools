import datetime
import os
import csv
import subprocess
import argparse
import sys
import glob
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MACHINE_RATE_PER_HOUR = 3.00
SETUP_FEE = 10.00
TAX_RATE = 0.07  # 7% sales tax
CHARGE_TAX = True
COUNTER_FILE = os.path.join(BASE_DIR, "invoice_counter.txt")
NAS_TARGET = "harty@100.108.30.62:~/HartyPrints_Backups/"

MATERIALS = {
    "1": {"name": "PLA Standard", "price_per_g": 0.10},
    "2": {"name": "PLA Silk / Matte", "price_per_g": 0.12},
    "3": {"name": "PETG", "price_per_g": 0.12},
    "4": {"name": "PETG-CF (Carbon Fiber)", "price_per_g": 0.20},
    "5": {"name": "ABS / ASA", "price_per_g": 0.12},
    "6": {"name": "TPU (Flexible)", "price_per_g": 0.15},
    "7": {"name": "Nylon / Carbon Fiber Nylon", "price_per_g": 0.25},
    "8": {"name": "Polycarbonate (PC)", "price_per_g": 0.22},
    "9": {"name": "Customer Supplied", "price_per_g": 0.00},
    "10": {"name": "Customer Supplied (Abrasive)", "price_per_g": 0.05}
}

CAD_TIERS = {
    "1": {"name": "Print-Ready (No CAD)", "price": 0.00},
    "2": {"name": "Minor Tweak", "price": 15.00},
    "3": {"name": "Basic Custom Part", "price": 45.00},
    "4": {"name": "Complex Engineering", "price": 85.00}
}

SCAN_TIERS = {
    "1": {"name": "None", "price": 0.00},
    "2": {"name": "Standard Object Scan", "price": 35.00},
    "3": {"name": "Complex Part / Detailed Scan", "price": 75.00},
    "4": {"name": "Large / Full Assembly Scan", "price": 150.00}
}

LASER_TIERS = {
    "1": {"name": "None", "price": 0.00},
    "2": {"name": "Quick Text / Logo Engraving", "price": 20.00},
    "3": {"name": "Detailed Surface / Panel Engraving", "price": 45.00},
    "4": {"name": "Rotary / Drinkware Engraving", "price": 30.00}
}

PAYMENT_TERMS = {
    "1": "Paid in Full",
    "2": "Installments",
    "3": "Unpaid"
}

def format_phone_number(raw):
    if not raw or raw == "N/A":
        return "N/A"
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) == 10:
        return f"({digits[:3]}){digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        digits = digits[1:]
        return f"({digits[:3]}){digits[3:6]}-{digits[6:]}"
    return raw

def get_positive_float(prompt):
    while True:
        try:
            val = float(input(prompt))
            if val < 0:
                print("Error: Value cannot be negative. Please try again.")
                continue
            return val
        except ValueError:
            print("Error: Please enter a valid numeric value.")

def get_positive_int(prompt):
    while True:
        try:
            val = int(input(prompt))
            if val <= 0:
                print("Error: Must be at least 1. Please try again.")
                continue
            return val
        except ValueError:
            print("Error: Please enter a valid whole number.")

def get_validated_choice(prompt, options_dict):
    while True:
        choice = input(prompt).strip()
        if choice in options_dict:
            return options_dict[choice]
        print(f"Error: Invalid choice. Please select from {list(options_dict.keys())}.")

def get_next_invoice_number():
    num = 1
    if os.path.isfile(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    num = int(content)
        except (ValueError, OSError):
            num = 1
            
    with open(COUNTER_FILE, "w") as f:
        f.write(str(num + 1))
        
    return f"INV-{num:03d}"

def get_quarter(month):
    return f"Q{(int(month) - 1) // 3 + 1}"

def search_customer_records(query):
    records_base = os.path.join(BASE_DIR, "Invoices_Records")
    csv_files = glob.glob(os.path.join(records_base, "**", "Tax_Ledger_*.csv"), recursive=True)
    
    if not csv_files:
        print(f"\n[Search] No tax ledger records found in {records_base}.")
        return

    found = False
    print(f"\n=== Customer Search Results for: '{query}' ===")
    print(f"{'Date':<19} | {'Invoice':<8} | {'Customer':<20} | {'Status':<14} | {'Total':<8} | {'Balance':<8}")
    print("-" * 85)

    for file_path in csv_files:
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cust_name = row.get("Customer", "")
                    if query.lower() in cust_name.lower():
                        found = True
                        date_str = row.get("Timestamp", "N/A")
                        inv_id = row.get("Invoice_ID", "N/A")
                        status = row.get("Payment_Status", "N/A")
                        total = row.get("Total", "0.00")
                        balance = row.get("Remaining_Balance", "0.00")
                        print(f"{date_str:<19} | {inv_id:<8} | {cust_name:<20} | {status:<14} | ${total:<7} | ${balance:<7}")
        except Exception as e:
            continue

    if not found:
        print(f"No records found matching '{query}'.")
    print("-" * 85)

def generate_pdf_invoice(invoice_data, pdf_path):
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('InvoiceTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#1a365d'), spaceAfter=4)
    subtitle_style = ParagraphStyle('InvoiceSubtitle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#4a5568'), spaceAfter=20)
    body_style = ParagraphStyle('InvoiceBody', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#2d3748'), leading=14)
    cell_style = ParagraphStyle('CellBody', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#2d3748'), leading=11)
    
    status_color = '#22c55e' if invoice_data['payment_status'] == 'Paid in Full' else ('#f59e0b' if invoice_data['payment_status'] == 'Installments' else '#ef4444')
    
    story.append(Paragraph("HARTY PRINTS", title_style))
    story.append(Paragraph("Custom 3D Printing, Scanning, Laser Engraving & CAD | Bloomingdale, GA", subtitle_style))
    story.append(Spacer(1, 10))
    
    payment_display = invoice_data['payment_status']
    if invoice_data['payment_status'] == 'Installments':
        payment_display += f" (Paid Today: ${invoice_data['paid_today']:.2f} | Remaining: ${invoice_data['remaining_balance']:.2f} | Plan: {invoice_data['total_installments']} Total Installments)"

    due_date_line = f"<br/><b>Due Date:</b> {invoice_data['due_date']}" if invoice_data['payment_status'] != 'Paid in Full' else ""

    meta_text = f"""
    <b>Invoice ID:</b> {invoice_data['receipt_id']}<br/>
    <b>Date:</b> {invoice_data['timestamp']}<br/>
    <b>Customer:</b> {invoice_data['customer_name']}<br/>
    <b>Email:</b> {invoice_data['customer_email']}<br/>
    <b>Phone:</b> {invoice_data['customer_phone']}<br/>
    <b>Payment Terms:</b> <font color="{status_color}"><b>{payment_display}</b></font>{due_date_line}
    """
    story.append(Paragraph(meta_text, body_style))
    story.append(Spacer(1, 15))
    
    table_data = [
        [Paragraph("<b>Description</b>", cell_style), Paragraph("<b>Details</b>", cell_style), Paragraph("<b>Amount</b>", cell_style)],
        [Paragraph("Setup Fee", cell_style), Paragraph("Standard job setup & prep", cell_style), Paragraph(f"${invoice_data['setup_fee']:.2f}", cell_style)],
    ]
    
    if invoice_data['grams'] > 0 or invoice_data['material_name'] != "None":
        table_data.append([
            Paragraph(f"Material: {invoice_data['material_name']}", cell_style),
            Paragraph(f"{invoice_data['grams']}g @ ${invoice_data['mat_price']}/g", cell_style),
            Paragraph(f"${invoice_data['mat_cost']:.2f}", cell_style)
        ])
        
    if invoice_data['hours'] > 0:
        table_data.append([
            Paragraph("Machine Print Time", cell_style),
            Paragraph(f"{invoice_data['hours']} hrs @ ${invoice_data['machine_rate']}/hr", cell_style),
            Paragraph(f"${invoice_data['machine_cost']:.2f}", cell_style)
        ])
        
    if invoice_data['cad_price'] > 0:
        table_data.append([
            Paragraph("CAD Design Service", cell_style),
            Paragraph(invoice_data['cad_name'], cell_style),
            Paragraph(f"${invoice_data['cad_price']:.2f}", cell_style)
        ])
        
    if invoice_data['scan_price'] > 0:
        table_data.append([
            Paragraph("3D Scanning Service", cell_style),
            Paragraph(invoice_data['scan_name'], cell_style),
            Paragraph(f"${invoice_data['scan_price']:.2f}", cell_style)
        ])
        
    if invoice_data['laser_price'] > 0:
        table_data.append([
            Paragraph("Laser Engraving Service", cell_style),
            Paragraph(invoice_data['laser_name'], cell_style),
            Paragraph(f"${invoice_data['laser_price']:.2f}", cell_style)
        ])
        
    table_data.append([Paragraph("", cell_style), Paragraph("Subtotal", cell_style), Paragraph(f"${invoice_data['raw_subtotal']:.2f}", cell_style)])
    
    if invoice_data['discount'] > 0:
        table_data.append([Paragraph("", cell_style), Paragraph("Discount / Promo", cell_style), Paragraph(f"-${invoice_data['discount']:.2f}", cell_style)])
        table_data.append([Paragraph("", cell_style), Paragraph("Adjusted Subtotal", cell_style), Paragraph(f"${invoice_data['subtotal']:.2f}", cell_style)])

    table_data.extend([
        [Paragraph("", cell_style), Paragraph(f"Sales Tax ({invoice_data['tax_rate_pct']}%)", cell_style), Paragraph(f"${invoice_data['tax_amount']:.2f}", cell_style)],
        [Paragraph("", cell_style), Paragraph("<b>TOTAL DUE</b>", cell_style), Paragraph(f"<b>${invoice_data['total']:.2f}</b>", cell_style)]
    ])
    
    if invoice_data['payment_status'] == 'Installments':
        table_data.extend([
            [Paragraph("", cell_style), Paragraph("Paid Today", cell_style), Paragraph(f"${invoice_data['paid_today']:.2f}", cell_style)],
            [Paragraph("", cell_style), Paragraph("<b>REMAINING BALANCE</b>", cell_style), Paragraph(f"<b>${invoice_data['remaining_balance']:.2f}</b>", cell_style)]
        ])

    t = Table(table_data, colWidths=[180, 240, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2b6cb0')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('GRID', (0,0), (-1, len(table_data) - (5 if invoice_data['payment_status'] == 'Installments' else 3)), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,-3 if invoice_data['payment_status'] == 'Installments' else -3), (-1,-1), colors.HexColor('#f7fafc')),
    ]))
    
    story.append(t)
    
    if invoice_data['notes']:
        story.append(Spacer(1, 15))
        story.append(Paragraph(f"<b>Job Notes:</b> {invoice_data['notes']}", body_style))

    story.append(Spacer(1, 20))
    story.append(Paragraph("Thank you for choosing Harty Prints! Payment terms as agreed.", body_style))
    doc.build(story)

def sync_to_nas():
    print("\n[Sync] Backing up records and customer shortcuts to NAS (100.108.30.62)...")
    records_dir = os.path.join(BASE_DIR, "Invoices_Records")
    os.makedirs(records_dir, exist_ok=True)
    try:
        result = subprocess.run(
            ["rsync", "-avz", "-e", "ssh -o BatchMode=yes -o ConnectTimeout=5", "--timeout=5", records_dir + "/", NAS_TARGET],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            print("[Success!] NAS backup completed successfully.")
        else:
            print(f"[Warning] NAS backup skipped or unavailable: {result.stderr.strip()}")
    except Exception as e:
        print(f"[Warning] Could not reach NAS or execute rsync: {e}")

def main():
    parser = argparse.ArgumentParser(description="Harty Prints Terminal Quoting & Invoice System")
    parser.add_argument("--search", type=str, help="Search past customer invoices across quarterly records")
    parser.add_argument("-n", "--name", type=str, help="Customer Name")
    parser.add_argument("-e", "--email", type=str, default="N/A", help="Customer Email")
    parser.add_argument("-p", "--phone", type=str, default="N/A", help="Customer Phone Number")
    parser.add_argument("-s", "--status", type=str, choices=list(PAYMENT_TERMS.keys()), default="1", help="Payment Terms Choice (1-3)")
    parser.add_argument("--paid-today", type=float, default=0.0, help="Amount paid today if installments")
    parser.add_argument("--installments-total", type=int, default=1, help="Total number of installments")
    parser.add_argument("--due-date", type=str, default="", help="Due date for balance (YYYY-MM-DD)")
    parser.add_argument("-m", "--material", type=str, choices=list(MATERIALS.keys()), default="1", help="Material choice (1-10)")
    parser.add_argument("-g", "--grams", type=float, default=0.0, help="Estimated weight in grams")
    parser.add_argument("-t", "--hours", type=float, default=0.0, help="Estimated print hours")
    parser.add_argument("-c", "--cad", type=str, choices=list(CAD_TIERS.keys()), default="1", help="CAD tier choice (1-4)")
    parser.add_argument("--scan", type=str, choices=list(SCAN_TIERS.keys()), default="1", help="3D Scan tier choice (1-4)")
    parser.add_argument("--laser", type=str, choices=list(LASER_TIERS.keys()), default="1", help="Laser Engraving tier choice (1-4)")
    parser.add_argument("--discount", type=float, default=0.0, help="Discount or promo amount in dollars")
    parser.add_argument("--notes", type=str, default="", help="Custom job notes or instructions")
    
    args = parser.parse_args()
    
    if args.search:
        search_customer_records(args.search)
        sys.exit(0)
    
    if args.grams < 0 or args.hours < 0:
        print("[Error] Weight and hours cannot be negative.")
        sys.exit(1)
    
    if not args.name:
        print("\n=== Harty Prints Automated Invoice & Record System ===")
        customer_name = input("Customer Name: ").strip()
        if not customer_name:
            customer_name = "Valued Customer"
            
        customer_email = input("Customer Email (optional): ").strip() or "N/A"
        raw_phone = input("Customer Phone [e.g. 9125550199]: ").strip()
        customer_phone = format_phone_number(raw_phone)
        
        print("\nSelect Payment Terms:\n[1] Paid in Full\n[2] Installments\n[3] Unpaid / Pending")
        payment_status_choice = get_validated_choice("Payment Terms Choice (1-3): ", PAYMENT_TERMS)
        payment_status_str = payment_status_choice
        
        paid_today = 0.0
        total_installments = 1
        due_date_str = ""
        
        if payment_status_str == "Installments":
            paid_today = get_positive_float("Enter amount paid today: $")
            total_installments = get_positive_int("Enter total number of installments planned: ")
            due_date_str = input("Enter balance due date (YYYY-MM-DD, optional): ").strip()
        elif payment_status_str == "Unpaid":
            due_date_str = input("Enter balance due date (YYYY-MM-DD, optional): ").strip()
            
        if not due_date_str:
            default_due = datetime.date.today() + datetime.timedelta(days=14)
            due_date_str = default_due.strftime("%Y-%m-%d")
        
        print("\nSelect Material:")
        for key, val in MATERIALS.items():
            price_str = f"${val['price_per_g']}/g" if val['price_per_g'] > 0 else "Free / Surcharge"
            print(f"[{key}] {val['name']} ({price_str})")
        material = get_validated_choice("Material Choice (1-10): ", MATERIALS)
        
        grams = get_positive_float("Estimated weight in grams (0 if N/A): ")
        hours = get_positive_float("Estimated print time in hours (0 if N/A): ")
        
        print("\nSelect CAD/Design Tier:")
        for key, val in CAD_TIERS.items():
            print(f"[{key}] {val['name']} (${val['price']:.2f})")
        cad_tier = get_validated_choice("CAD Choice (1-4): ", CAD_TIERS)
        
        print("\nSelect 3D Scanning Service:")
        for key, val in SCAN_TIERS.items():
            print(f"[{key}] {val['name']} (${val['price']:.2f})")
        scan_tier = get_validated_choice("Scanning Choice (1-4): ", SCAN_TIERS)
        
        print("\nSelect Laser Engraving Service:")
        for key, val in LASER_TIERS.items():
            print(f"[{key}] {val['name']} (${val['price']:.2f})")
        laser_tier = get_validated_choice("Laser Choice (1-4): ", LASER_TIERS)
        
        discount = get_positive_float("Enter discount amount ($0.00 if none): $")
        notes = input("Custom job notes / instructions (optional): ").strip()
    else:
        customer_name = args.name
        customer_email = args.email
        customer_phone = format_phone_number(args.phone)
        payment_status_str = PAYMENT_TERMS.get(args.status, "Paid in Full")
        paid_today = args.paid_today if payment_status_str == "Installments" else 0.0
        total_installments = args.installments_total if payment_status_str == "Installments" else 1
        
        if args.due_date:
            due_date_str = args.due_date
        else:
            default_due = datetime.date.today() + datetime.timedelta(days=14)
            due_date_str = default_due.strftime("%Y-%m-%d")
            
        material = MATERIALS[args.material]
        grams = args.grams
        hours = args.hours
        cad_tier = CAD_TIERS[args.cad]
        scan_tier = SCAN_TIERS[args.scan]
        laser_tier = LASER_TIERS[args.laser]
        discount = args.discount
        notes = args.notes
    
    material_cost = round(grams * material["price_per_g"], 2)
    machine_cost = round(hours * MACHINE_RATE_PER_HOUR, 2)
    raw_subtotal = round(SETUP_FEE + material_cost + machine_cost + cad_tier["price"] + scan_tier["price"] + laser_tier["price"], 2)
    
    discount = min(discount, raw_subtotal)
    subtotal = round(raw_subtotal - discount, 2)
    tax_amount = round(subtotal * TAX_RATE, 2) if CHARGE_TAX else 0.00
    total = round(subtotal + tax_amount, 2)
    
    if payment_status_str == "Paid in Full":
        paid_today = total
        remaining_balance = 0.0
    elif payment_status_str == "Unpaid":
        paid_today = 0.0
        remaining_balance = total
    else:
        remaining_balance = round(max(0.0, total - paid_today), 2)
    
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    receipt_id = get_next_invoice_number()
    
    year_str = str(now.year)
    quarter_str = get_quarter(now.month)
    month_str = now.strftime("%B")
    
    records_base = os.path.join(BASE_DIR, "Invoices_Records")
    quarter_dir = os.path.join(records_base, year_str, quarter_str)
    month_dir = os.path.join(quarter_dir, month_str)
    
    try:
        os.makedirs(month_dir, exist_ok=True)
    except OSError as e:
        print(f"[Error] Could not create directory structure: {e}")
        return
    
    safe_customer = "".join(c for c in customer_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    if not safe_customer:
        safe_customer = "Client"
        
    pdf_filename = f"{receipt_id}_{safe_customer}.pdf"
    pdf_path = os.path.join(month_dir, pdf_filename)
    
    # --- CUSTOMER FOLDER & SYMLINK SETUP ---
    customers_dir = os.path.join(records_base, "Customers", safe_customer)
    os.makedirs(customers_dir, exist_ok=True)
    symlink_path = os.path.join(customers_dir, pdf_filename)
    if os.path.lexists(symlink_path):
        os.unlink(symlink_path)
    os.symlink(os.path.relpath(pdf_path, customers_dir), symlink_path)
    
    invoice_data = {
        'receipt_id': receipt_id,
        'timestamp': timestamp,
        'customer_name': customer_name,
        'customer_email': customer_email,
        'customer_phone': customer_phone,
        'payment_status': payment_status_str,
        'paid_today': paid_today,
        'remaining_balance': remaining_balance,
        'total_installments': total_installments,
        'due_date': due_date_str,
        'setup_fee': SETUP_FEE,
        'material_name': material['name'],
        'grams': grams,
        'mat_price': material['price_per_g'],
        'mat_cost': material_cost,
        'hours': hours,
        'machine_rate': MACHINE_RATE_PER_HOUR,
        'machine_cost': machine_cost,
        'cad_name': cad_tier['name'],
        'cad_price': cad_tier['price'],
        'scan_name': scan_tier['name'],
        'scan_price': scan_tier['price'],
        'laser_name': laser_tier['name'],
        'laser_price': laser_tier['price'],
        'raw_subtotal': raw_subtotal,
        'discount': discount,
        'subtotal': subtotal,
        'tax_rate_pct': int(TAX_RATE * 100),
        'tax_amount': tax_amount,
        'total': total,
        'notes': notes
    }
    
    try:
        generate_pdf_invoice(invoice_data, pdf_path)
    except Exception as e:
        print(f"[Error] Failed to generate PDF invoice: {e}")
        return
    
    csv_filename = os.path.join(quarter_dir, f"Tax_Ledger_{year_str}_{quarter_str}.csv")
    file_exists = os.path.isfile(csv_filename)
    
    try:
        with open(csv_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow([
                    "Timestamp", "Invoice_ID", "Quarter", "Month", "Customer", "Email", "Phone", 
                    "Payment_Status", "Paid_Today", "Remaining_Balance", "Total_Installments", "Due_Date",
                    "Material", "Grams", "Print_Hours", "Setup_Fee", "CAD_Tier", "CAD_Fee", 
                    "Scan_Service", "Scan_Fee", "Laser_Service", "Laser_Fee", "Raw_Subtotal", "Discount", 
                    "Subtotal", "Tax", "Total", "Notes", "PDF_Path"
                ])
            
            writer.writerow([
                timestamp, receipt_id, quarter_str, month_str, customer_name, customer_email, customer_phone,
                payment_status_str, f"{paid_today:.2f}", f"{remaining_balance:.2f}", total_installments, due_date_str,
                material['name'], grams, hours, SETUP_FEE, cad_tier['name'], cad_tier['price'], 
                scan_tier['name'], scan_tier['price'], laser_tier['name'], laser_tier['price'], 
                f"{raw_subtotal:.2f}", f"{discount:.2f}", f"{subtotal:.2f}", f"{tax_amount:.2f}", f"{total:.2f}", 
                notes, pdf_path
            ])
    except PermissionError:
        print(f"[Warning] Could not write to tax ledger. Please ensure '{csv_filename}' is closed and run again.")
        
    print(f"\n[Success!] PDF Invoice created: {pdf_path}")
    print(f"[Success!] Customer shortcut generated: {symlink_path}")
    print(f"[Success!] Transaction logged to quarterly tax ledger: {csv_filename}")
    
    sync_to_nas()

if __name__ == "__main__":
    main()
