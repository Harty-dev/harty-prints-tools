import datetime
import os
import csv
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

MACHINE_RATE_PER_HOUR = 3.00
SETUP_FEE = 10.00
TAX_RATE = 0.07
CHARGE_TAX = True

MATERIALS = {
    "1": {"name": "PLA", "price_per_g": 0.10},
    "2": {"name": "PETG", "price_per_g": 0.12},
    "3": {"name": "ABS / ASA", "price_per_g": 0.12},
    "4": {"name": "TPU (Flexible)", "price_per_g": 0.15},
    "5": {"name": "Carbon Fiber / Nylon", "price_per_g": 0.25}
}

CAD_TIERS = {
    "1": {"name": "Print-Ready (No CAD)", "price": 0.00},
    "2": {"name": "Minor Tweak", "price": 15.00},
    "3": {"name": "Basic Custom Part", "price": 45.00},
    "4": {"name": "Complex Engineering", "price": 85.00}
}

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

def get_validated_choice(prompt, options_dict):
    while True:
        choice = input(prompt).strip()
        if choice in options_dict:
            return options_dict[choice]
        print(f"Error: Invalid choice. Please select from {list(options_dict.keys())}.")

def get_quarter(month):
    return f"Q{(int(month) - 1) // 3 + 1}"

def generate_pdf_invoice(invoice_data, pdf_path):
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('InvoiceTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#1a365d'), spaceAfter=4)
    subtitle_style = ParagraphStyle('InvoiceSubtitle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#4a5568'), spaceAfter=20)
    body_style = ParagraphStyle('InvoiceBody', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#2d3748'), leading=14)
    
    story.append(Paragraph("HARTY PRINTS", title_style))
    story.append(Paragraph("Custom 3D Printing & CAD Design | Bloomingdale, GA", subtitle_style))
    story.append(Spacer(1, 10))
    
    meta_text = f"""
    <b>Invoice ID:</b> {invoice_data['receipt_id']}<br/>
    <b>Date:</b> {invoice_data['timestamp']}<br/>
    <b>Customer:</b> {invoice_data['customer_name']}
    """
    story.append(Paragraph(meta_text, body_style))
    story.append(Spacer(1, 15))
    
    table_data = [
        ["Description", "Details", "Amount"],
        ["Setup Fee", "Standard print job setup", f"${invoice_data['setup_fee']:.2f}"],
        [f"Material: {invoice_data['material_name']}", f"{invoice_data['grams']}g @ ${invoice_data['mat_price']}/g", f"${invoice_data['mat_cost']:.2f}"],
        ["Machine Time", f"{invoice_data['hours']} hrs @ ${invoice_data['machine_rate']}/hr", f"${invoice_data['machine_cost']:.2f}"],
        ["Design Service", invoice_data['cad_name'], f"${invoice_data['cad_price']:.2f}"],
        ["", "Subtotal", f"${invoice_data['subtotal']:.2f}"],
        ["", f"Sales Tax ({invoice_data['tax_rate_pct']}%)", f"${invoice_data['tax_amount']:.2f}"],
        ["", "TOTAL DUE", f"${invoice_data['total']:.2f}"]
    ]
    
    t = Table(table_data, colWidths=[180, 240, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2b6cb0')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,4), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,-3), (-1,-1), colors.HexColor('#f7fafc')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,-1), (-1,-1), colors.HexColor('#1a202c')),
        ('TOPPADDING', (0,-3), (-1,-1), 6),
        ('BOTTOMPADDING', (0,-3), (-1,-1), 6),
    ]))
    
    story.append(t)
    story.append(Spacer(1, 30))
    story.append(Paragraph("Thank you for choosing Harty Prints! Payment is due upon receipt.", body_style))
    doc.build(story)

def main():
    print("\n=== Harty Prints Automated Invoice & Record System ===")
    
    customer_name = input("Customer Name: ").strip()
    if not customer_name:
        customer_name = "Valued Customer"
    
    print("\nSelect Material:")
    for key, val in MATERIALS.items():
        print(f"[{key}] {val['name']} (${val['price_per_g']}/g)")
    material = get_validated_choice("Material Choice (1-5): ", MATERIALS)
    
    grams = get_positive_float("Estimated weight in grams (including supports): ")
    hours = get_positive_float("Estimated print time in hours: ")
    
    print("\nSelect CAD/Design Tier:")
    for key, val in CAD_TIERS.items():
        print(f"[{key}] {val['name']} (${val['price']:.2f})")
    cad_tier = get_validated_choice("CAD Choice (1-4): ", CAD_TIERS)
    
    material_cost = round(grams * material["price_per_g"], 2)
    machine_cost = round(hours * MACHINE_RATE_PER_HOUR, 2)
    subtotal = round(SETUP_FEE + material_cost + machine_cost + cad_tier["price"], 2)
    tax_amount = round(subtotal * TAX_RATE, 2) if CHARGE_TAX else 0.00
    total = round(subtotal + tax_amount, 2)
    
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    receipt_id = now.strftime("%Y%m%d-%H%M")
    
    year_str = str(now.year)
    quarter_str = get_quarter(now.month)
    month_str = now.strftime("%B")
    
    base_dir = "Invoices_Records"
    quarter_dir = os.path.join(base_dir, year_str, quarter_str)
    month_dir = os.path.join(quarter_dir, month_str)
    
    try:
        os.makedirs(month_dir, exist_ok=True)
    except OSError as e:
        print(f"[Error] Could not create directory structure: {e}")
        return
    
    safe_customer = "".join(c for c in customer_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    if not safe_customer:
        safe_customer = "Client"
        
    pdf_filename = f"INV_{receipt_id}_{safe_customer}.pdf"
    pdf_path = os.path.join(month_dir, pdf_filename)
    
    invoice_data = {
        'receipt_id': f"INV-{receipt_id}",
        'timestamp': timestamp,
        'customer_name': customer_name,
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
        'subtotal': subtotal,
        'tax_rate_pct': int(TAX_RATE * 100),
        'tax_amount': tax_amount,
        'total': total
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
                writer.writerow(["Timestamp", "Receipt_ID", "Quarter", "Month", "Customer", "Material", "Grams", "Print_Hours", "Setup_Fee", "CAD_Tier", "CAD_Fee", "Subtotal", "Tax", "Total", "PDF_Path"])
            
            writer.writerow([
                timestamp, f"INV-{receipt_id}", quarter_str, month_str, customer_name, 
                material['name'], grams, hours, SETUP_FEE, cad_tier['name'], 
                cad_tier['price'], f"{subtotal:.2f}", f"{tax_amount:.2f}", f"{total:.2f}", pdf_path
            ])
    except PermissionError:
        print(f"[Warning] Could not write to tax ledger. Please ensure '{csv_filename}' is closed in Excel and run again.")
        
    print(f"\n[Success!] PDF Invoice created: {pdf_path}")
    print(f"[Success!] Transaction logged to quarterly tax ledger: {csv_filename}")

if __name__ == "__main__":
    main()
