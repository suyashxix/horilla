from invoicing.models import Client, Placement, Invoice
from recruitment.models import Candidate, Recruitment, JobPosition
from employee.models import Employee
from base.models import Company, Department
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

# Get existing data
User = get_user_model()
user = User.objects.first()
company = Company.objects.first()

print(f"User: {user}")
print(f"Company: {company}")

# Use existing department
try:
    department = Department.objects.first()
    if not department:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("INSERT INTO base_department (department) VALUES (%s)", ["IT Department"])
        department = Department.objects.get(department="IT Department")
        department.company_id.add(company)
    print(f"Using department: {department}")
except Exception as e:
    print(f"Department error: {e}")
    department = Department.objects.first()

# Use existing job position or create one
try:
    job_position = JobPosition.objects.first()
    if not job_position:
        job_position = JobPosition(job_position="Software Engineer", department_id=department)
        job_position.save()
        job_position.company_id.add(company)
    print(f"Using job position: {job_position}")
except Exception as e:
    print(f"Job position error: {e}")
    job_position = JobPosition.objects.first()

# Use existing recruitment or create one
try:
    recruitment = Recruitment.objects.first()
    if not recruitment:
        recruitment = Recruitment(
            title="Software Engineer Recruitment 2025",
            description="Looking for experienced software engineers",
            is_event_based=False,
            job_position_id=job_position,
            vacancy=5,
            company_id=company,
            start_date=date.today() - timedelta(days=60)
        )
        recruitment.save()
        
        employee = Employee.objects.first()
        if employee:
            recruitment.recruitment_managers.add(employee)
    print(f"Using recruitment: {recruitment}")
except Exception as e:
    print(f"Recruitment error: {e}")
    recruitment = Recruitment.objects.first()

# Create or get client - THIS WAS MISSING!
try:
    client = Client.objects.filter(name="Tech Solutions Inc").first()
    if not client:
        client = Client.objects.create(
            name="Tech Solutions Inc",
            email="contact@techsolutions.com",
            phone="+1-555-0123",
            contact_person="Sarah Johnson",
            address="123 Business Park, Tech City, TC 12345",
            company=company
        )
    print(f"Using client: {client}")
except Exception as e:
    print(f"Client error: {e}")
    client = Client.objects.first()  # Fallback to any existing client

# Create candidates
candidate_data = [
    {"name": "John Doe", "email": "john.doe@email.com", "mobile": "1234567890"},
    {"name": "Jane Smith", "email": "jane.smith@email.com", "mobile": "1234567891"},
    {"name": "Mike Johnson", "email": "mike.johnson@email.com", "mobile": "1234567892"},
    {"name": "Sarah Wilson", "email": "sarah.wilson@email.com", "mobile": "1234567893"},
    {"name": "David Brown", "email": "david.brown@email.com", "mobile": "1234567894"}
]

candidates = []
if recruitment and job_position:
    for data in candidate_data:
        try:
            # Check if candidate already exists
            existing_candidate = Candidate.objects.filter(email=data["email"]).first()
            if existing_candidate:
                candidates.append(existing_candidate)
                print(f"Using existing candidate: {existing_candidate}")
            else:
                candidate = Candidate.objects.create(
                    name=data["name"],
                    email=data["email"],
                    mobile=data["mobile"],
                    recruitment_id=recruitment,
                    job_position_id=job_position,
                    address="123 Main St, City, State",
                    country="India",
                    gender="male"
                )
                candidates.append(candidate)
                print(f"Created candidate: {candidate}")
        except Exception as e:
            print(f"Candidate creation error: {e}")

# Create placements
placements = []
positions = ["Software Engineer", "Senior Developer", "Full Stack Developer", "Backend Developer", "Frontend Developer"]

if client:  # Make sure client exists before creating placements
    for i, candidate in enumerate(candidates):
        try:
            # Check if placement already exists
            existing_placement = Placement.objects.filter(candidate=candidate, client=client).first()
            if existing_placement:
                placements.append(existing_placement)
                print(f"Using existing placement: {existing_placement}")
            else:
                placement = Placement.objects.create(
                    candidate=candidate,
                    client=client,
                    position=positions[i % len(positions)],
                    joining_date=date.today() - timedelta(days=100 + i*10),
                    notice_period_days=90,
                    placement_fee=Decimal(f'{50000 + (i * 15000)}.00'),
                    created_by=user
                )
                placements.append(placement)
                print(f"Created placement: {placement}")
        except Exception as e:
            print(f"Placement creation error: {e}")
else:
    print("No client available - cannot create placements")

# Create invoices
for i, placement in enumerate(placements, 1):
    try:
        # Check if invoice already exists
        existing_invoice = Invoice.objects.filter(placement=placement).first()
        if existing_invoice:
            print(f"Invoice already exists: {existing_invoice.invoice_number}")
        else:
            invoice = Invoice.objects.create(
                placement=placement,
                amount=placement.placement_fee,
                tax_rate=Decimal('18.00'),
                status='draft',
                email_subject=f"Invoice for {placement.candidate.name} - {placement.position}",
                email_body=f"Dear {placement.client.contact_person},\n\nPlease find attached the invoice for the placement of {placement.candidate.name} as {placement.position}.\n\nBest regards",
                sent_by=user
            )
            print(f"Created invoice: {invoice.invoice_number} - ₹{invoice.total_amount}")
    except Exception as e:
        print(f"Invoice creation error: {e}")

print(f"\n=== FINAL SUMMARY ===")
print(f"Departments: {Department.objects.count()}")
print(f"Job Positions: {JobPosition.objects.count()}")
print(f"Recruitments: {Recruitment.objects.count()}")
print(f"Candidates: {Candidate.objects.count()}")
print(f"Clients: {Client.objects.count()}")
print(f"Placements: {Placement.objects.count()}")
print(f"Invoices: {Invoice.objects.count()}")
