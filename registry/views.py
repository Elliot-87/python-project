# registry/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from collections import Counter
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle
from .models import RegistryEntry
from .forms import RegistryForm
import json
from django.http import JsonResponse
from .utils import signature_data_to_image
import base64
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw
import os
from django.conf import settings
import tempfile
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.utils import timezone
from django.core.files.base import ContentFile
from django.utils.text import slugify
from django.db.models import Count, Case, When, Value, IntegerField
from django.http import JsonResponse











def dashboard_data(request):
    """
    Efficiently aggregate registry statistics and return JSON
    used by the dashboard frontend.
    """
    qs = RegistryEntry.objects.all()

    # Helper: convert queryset of dicts [{'gender': 'M', 'count': 10}, ...] -> { 'M': 10, ... }
    def counts_from_qs(qs_vals, key_name):
        return {item[key_name]: item['count'] for item in qs_vals if item.get(key_name) not in (None, '')}

    # 1) Generic text fields (gender, social_grant, tish_area, race, ward_no)
    gender_counts_qs = qs.values('gender').annotate(count=Count('id'))
    grant_counts_qs  = qs.values('social_grant').annotate(count=Count('id'))
    tish_counts_qs   = qs.values('tish_area').annotate(count=Count('id'))
    race_counts_qs   = qs.values('race').annotate(count=Count('id'))
    ward_counts_qs   = qs.values('ward_no').annotate(count=Count('id'))

    gender_counts = counts_from_qs(gender_counts_qs, 'gender')
    grant_counts  = counts_from_qs(grant_counts_qs, 'social_grant')
    tish_counts   = counts_from_qs(tish_counts_qs, 'tish_area')
    race_counts   = counts_from_qs(race_counts_qs, 'race')
    ward_counts   = counts_from_qs(ward_counts_qs, 'ward_no')

    # 2) Boolean fields - count Yes / No
    disability_counts = {
        "Yes": qs.filter(disability=True).count(),
        "No": qs.filter(disability=False).count()
    }
    recovering_counts = {
        "Yes": qs.filter(recovering_service_user=True).count(),
        "No": qs.filter(recovering_service_user=False).count()
    }
    cooperative_counts = {
        "Yes": qs.filter(cooperative_member=True).count(),
        "No": qs.filter(cooperative_member=False).count()
    }

    # 3) Contact counts — entries that have contact_number vs those that don't
    contact_counts = {
        "Has Contact": qs.exclude(contact_number__isnull=True).exclude(contact_number__exact='').count(),
        "No Contact": qs.filter(contact_number__isnull=True).count() + qs.filter(contact_number__exact='').count()
    }

    # 4) Signature counts — handle if signature_image field exists
    try:
        signature_counts = {
            "Signed": qs.exclude(signature_image__isnull=True).exclude(signature_image__exact='').count(),
            "Not Signed": qs.filter(signature_image__isnull=True).count() + qs.filter(signature_image__exact='').count()
        }
    except Exception:
        signature_counts = {}

    # 5) Address counts - using physical_address field
    address_counts = {
        "Has Address": qs.exclude(physical_address__isnull=True).exclude(physical_address__exact='').count(),
        "No Address": qs.filter(physical_address__isnull=True).count() + qs.filter(physical_address__exact='').count()
    }

    # 6) Calculate total participants
    total_participants = qs.count()

    # 7) Assemble final data dictionary
    data = {
        "gender_counts": gender_counts,
        "grant_counts": grant_counts,
        "tish_counts": tish_counts,
        "disability_counts": disability_counts,
        "race_counts": race_counts,
        "recovering_counts": recovering_counts,
        "cooperative_counts": cooperative_counts,
        "ward_counts": ward_counts,
        "contact_counts": contact_counts,
        "signature_counts": signature_counts,
        "address_counts": address_counts,
        "total_participants": total_participants,
    }

    # 8) Return JSON response
    return JsonResponse(data)
def dashboard(request):
    """
    Render the dashboard template.
    Make sure this file exists at:
    registry/templates/registry/registry_dashboard.html
    """
    return render(request, "registry/registry_dashboard.html")


def registry_update(request, pk):
    entry = get_object_or_404(RegistryEntry, pk=pk)
    if request.method == "POST":
        form = RegistryForm(request.POST, request.FILES, instance=entry)
        if form.is_valid():
            entry = form.save(commit=False)
            
            # Process signature data (same as above)
            signature_data = request.POST.get('signature_data', '')
            if signature_data:
                try:
                    format, imgstr = signature_data.split(';base64,') 
                    ext = format.split('/')[-1] 
                    signature_file = ContentFile(
                        base64.b64decode(imgstr), 
                        name=f"signature_{slugify(entry.names)}_{slugify(entry.surname)}.{ext}"
                    )
                    entry.signature_image = signature_file
                except Exception as e:
                    print(f"Signature processing error: {e}")
            
            entry.save()
            return redirect('registry_list')
    else:
        form = RegistryForm(instance=entry)
    return render(request, 'registry/registry_form.html', {'form': form})

# Your pdf_preview view rewritten


def pdf_preview(request):
    # ✅ Query the data for the table
    entries = RegistryEntry.objects.all().order_by("surname")

    # ✅ Load the HTML template
    template_path = "registry/pdf_preview.html"
    context = {
        "request": request,
        "entries": entries,   # This is the missing piece!
    }

    # ✅ Render the HTML with context
    template = get_template(template_path)
    html = template.render(context)

    # ✅ Generate PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="beneficiary_register.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response, link_callback=link_callback)

    if pisa_status.err:
        return HttpResponse("PDF generation error.<pre>" + html + "</pre>")
    
    return response


    # Create a PDF in memory
    result = io.BytesIO()

    pisa_status = pisa.CreatePDF(
        src=html,
        dest=result,
        encoding="UTF-8",
        default_css="""
            @page {
                size: A4 landscape;
                margin: 15mm;
            }
            body {
                font-family: DejaVu Sans, sans-serif;
                font-size: 10pt;
            }
            table {
                border-collapse: collapse;
                width: 100%;
            }
            th, td {
                border: 1px solid #444;
                padding: 4px;
                text-align: left;
            }
        """
    )

    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)

    # Write PDF to response
    response.write(result.getvalue())
    return response

    # Serve the PDF
    response = HttpResponse(result.getvalue(), content_type="application/pdf")
    if request.GET.get("download"):
        response["Content-Disposition"] = 'attachment; filename="registry_report.pdf"'
    else:
        response["Content-Disposition"] = 'inline; filename="registry_report.pdf"'
    return response


def export_pdf(request):
    # Create a buffer
    buffer = BytesIO()
    
    # Landscape A4
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # Add company logo at top-left (adjust path as needed)
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.png")
    if os.path.exists(logo_path):
        pdf.drawImage(logo_path, x=30, y=height-80, width=100, height=50, preserveAspectRatio=True, mask='auto')
    
    # Title
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(150, height-50, "Registry Entries Report")
    
    # Table headers
    headers = ["Names", "Surname", "ID/DOB", "Gender", "Contact", "Area", "Signature"]
    data = [headers]
    
    # Fetch entries
    entries = RegistryEntry.objects.all()
    
    for entry in entries:
        # If signature exists, create an Image object for table
        if entry.signature_image and entry.signature_image.path and os.path.exists(entry.signature_image.path):
            sig_img = Image(entry.signature_image.path, width=80, height=30)  # resize for table
        else:
            sig_img = "No Signature"
        
        row = [
            entry.names,
            entry.surname,
            entry.id_no_or_dob,
            entry.gender,
            entry.contact_number,
            entry.tish_area,
            sig_img
        ]
        data.append(row)
    
    # Create table
    table = Table(data, repeatRows=1, colWidths=[80, 80, 90, 60, 90, 80, 120])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1f2937")),  # dark gray header
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        
        ('GRID', (0,0), (-1,-1), 0.25, colors.black),
        ('ALIGN', (0,0), (-2,-1), 'CENTER'),   # center text except signature column
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    # Calculate table position
    table_width, table_height = table.wrap(0, 0)
    x = (width - table_width) / 2
    y = height - 150 - table_height
    
    table.wrapOn(pdf, width, height)
    table.drawOn(pdf, x, y)
    
    # Footer with page number
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(width-40, 30, f"Page 1 of 1")  # (basic single-page example)
    
    # Finalize PDF
    pdf.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    # Return response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="registry_report.pdf"'
    response.write(pdf_bytes)
    return response


# Add this function to convert signature data to an image
def signature_data_to_image(signature_data, output_size=(300, 100)):
    """Convert signature data to an image"""
    if not signature_data:
        return None
        
    # Create a transparent image
    img = Image.new('RGBA', output_size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Scale factor to fit the signature to output size
    # First, find the bounds of the signature
    all_x = [point['x'] for stroke in signature_data for point in stroke['points']]
    all_y = [point['y'] for stroke in signature_data for point in stroke['points']]
    
    if not all_x or not all_y:
        return None
        
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    
    width = max_x - min_x
    height = max_y - min_y
    
    if width == 0 or height == 0:
        return None
        
    scale_x = (output_size[0] - 10) / width
    scale_y = (output_size[1] - 10) / height
    scale = min(scale_x, scale_y)
    
    # Draw each stroke
    for stroke in signature_data:
        points = []
        for point in stroke['points']:
            x = (point['x'] - min_x) * scale + 5  # Add 5px margin
            y = (point['y'] - min_y) * scale + 5
            points.append((x, y))
        
        if len(points) > 1:
            draw.line(points, fill='black', width=2)
    
    return img

# Update your registry_create and registry_update views
def registry_create(request):
    if request.method == "POST":
        form = RegistryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            
            # Process signature data if provided
            signature_data_json = request.POST.get('signature_data', '')
            if signature_data_json:
                try:
                    signature_data = json.loads(signature_data_json)
                    entry.signature_data = signature_data
                    
                    # Convert to image
                    signature_img = signature_data_to_image(signature_data)
                    if signature_img:
                        # Save image to BytesIO buffer
                        buffer = BytesIO()
                        signature_img.save(buffer, format='PNG')
                        
                        # Save to ImageField
                        entry.signature_image.save(
                            f'signature_{entry.names}_{entry.surname}.png',
                            ContentFile(buffer.getvalue()),
                            save=False
                        )
                except json.JSONDecodeError:
                    pass  # Invalid JSON, skip signature processing
            
            entry.save()
            return redirect('registry_list')
    else:
        form = RegistryForm()
    return render(request, 'registry/registry_form.html', {'form': form})

def registry_update(request, pk):
    entry = get_object_or_404(RegistryEntry, pk=pk)
    if request.method == "POST":
        form = RegistryForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save(commit=False)
            
            # Process signature data if provided
            signature_data_json = request.POST.get('signature_data', '')
            if signature_data_json:
                try:
                    signature_data = json.loads(signature_data_json)
                    entry.signature_data = signature_data
                    
                    # Convert to image
                    signature_img = signature_data_to_image(signature_data)
                    if signature_img:
                        # Save image to BytesIO buffer
                        buffer = BytesIO()
                        signature_img.save(buffer, format='PNG')
                        
                        # Save to ImageField
                        entry.signature_image.save(
                            f'signature_{entry.names}_{entry.surname}.png',
                            ContentFile(buffer.getvalue()),
                            save=False
                        )
                except json.JSONDecodeError:
                    pass  # Invalid JSON, skip signature processing
            
            entry.save()
            return redirect('registry_list')
    else:
        form = RegistryForm(instance=entry)
    return render(request, 'registry/registry_form.html', {'form': form})

def registry_view(request):
    """Handle the registry form submission"""
    if request.method == "POST":
        form = RegistryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            
            # MANUALLY process signature data
            signature_data_json = request.POST.get('signature_data', '')
            if signature_data_json:
                try:
                    signature_data = json.loads(signature_data_json)
                    entry.signature_data = signature_data
                    
                    # Convert to image and save
                    signature_img = signature_data_to_image(signature_data)
                    if signature_img:
                        # Save image logic here
                        # Example: save signature image to a file or image field
                        pass
                        
                except json.JSONDecodeError:
                    # Handle JSON decode error
                    pass
            
            entry.save()
            
            # Return success response or redirect
            return redirect('success-page')  # or JsonResponse({'success': True})
    
    else:
        form = RegistryForm()
    
    # For GET requests, render the form
    return render(request, 'registry_form.html', {'form': form})

# 1️⃣ Registry List with Search + Filter + Summaries
from django.shortcuts import render
from django.http import HttpResponse
import csv
from xhtml2pdf import pisa
from django.template.loader import get_template
from .models import RegistryEntry
from datetime import datetime, timedelta



def registry_export(request):
    # Filter entries based on query params
    entries = RegistryEntry.objects.all()
    search = request.GET.get("search", "")
    gender = request.GET.get("gender", "")
    grant = request.GET.get("grant", "")
    tish_area = request.GET.get("tish_area", "")
    export_format = request.GET.get("export_format", "pdf")

    if search:
        entries = entries.filter(
            Q(names__icontains=search) |
            Q(surname__icontains=search) |
            Q(id_no_or_dob__icontains=search)
        )
    gender_filter = request.GET.get("gender")
    if gender_filter:
        entries = entries.filter(gender=gender_filter)

    if grant:
        entries = entries.filter(social_grant=grant)
    if tish_area:
        entries = entries.filter(tish_area=tish_area)

    # Time-based filters
    now = datetime.now()
    if export_format == "day":
        entries = entries.filter(created_at__date=now.date())
    elif export_format == "week":
        start_week = now - timedelta(days=now.weekday())
        entries = entries.filter(created_at__date__gte=start_week.date())
    elif export_format == "month":
        entries = entries.filter(created_at__month=now.month, created_at__year=now.year)
    elif export_format == "year":
        entries = entries.filter(created_at__year=now.year)

    if export_format in ["pdf", "day", "week", "month", "year"]:
        template = get_template("registry/pdf_preview.html")
        html = template.render({"entries": entries})
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="registry_report.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse("Error generating PDF", status=500)
        return response

    elif export_format == "csv":
        response = HttpResponse(content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="registry_entries.csv"'
        writer = csv.writer(response)
        writer.writerow(['Names', 'Surname', 'ID/DOB', 'Gender', 'Social Grant', 'Tish Area'])
        for entry in entries:
            writer.writerow([entry.names, entry.surname, entry.id_no_or_dob or '',
                             entry.gender, entry.social_grant, entry.tish_area])
        return response

    else:
        return HttpResponse("Invalid export format", status=400)



def _generate_date_report(queryset, period_type):
    now = timezone.now()
    
    if period_type == 'daily':
        start_date = now - timedelta(days=1)
        filename = f"daily_report_{now.strftime('%Y%m%d')}.csv"
    elif period_type == 'weekly':
        start_date = now - timedelta(weeks=1)
        filename = f"weekly_report_{now.strftime('%Y%m%d')}.csv"
    elif period_type == 'monthly':
        start_date = now - timedelta(days=30)
        filename = f"monthly_report_{now.strftime('%Y%m')}.csv"
    else:  # yearly
        start_date = now - timedelta(days=365)
        filename = f"yearly_report_{now.strftime('%Y')}.csv"
    
    date_filtered = queryset.filter(created_at__gte=start_date) if hasattr(queryset.model, 'created_at') else queryset

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([f'{period_type.capitalize()} Registry Report'])
    writer.writerow(['Period', f'{start_date.strftime("%Y-%m-%d")} to {now.strftime("%Y-%m-%d")}'])
    writer.writerow(['Total Entries', date_filtered.count()])
    writer.writerow([])
    
    # Summary statistics
    writer.writerow(['Summary Statistics'])
    gender_counts = Counter([e.gender for e in date_filtered])
    grant_counts = Counter([e.social_grant for e in date_filtered])
    tish_counts = Counter([e.tish_area for e in date_filtered])
    
    writer.writerow(['Gender Distribution'])
    for gender, count in gender_counts.items():
        writer.writerow([f'  {gender}', count])
    
    writer.writerow(['Social Grant Distribution'])
    for grant, count in grant_counts.items():
        writer.writerow([f'  {grant}', count])
    
    writer.writerow(['Tish Area Distribution'])
    for area, count in tish_counts.items():
        writer.writerow([f'  {area}', count])
    
    writer.writerow([])
    writer.writerow(['Detailed Entries'])
    writer.writerow(['Names', 'Surname', 'ID/DOB', 'Gender', 'Social Grant', 'Tish Area'])
    
    for entry in date_filtered:
        writer.writerow([
            entry.names, entry.surname, entry.id_no_or_dob or '',
            entry.gender, entry.social_grant, entry.tish_area
        ])
    
    return response


def generate_daily_report(modeladmin, request, queryset):
    return _generate_date_report(queryset, 'daily')

def generate_weekly_report(modeladmin, request, queryset):
    return _generate_date_report(queryset, 'weekly')

def generate_monthly_report(modeladmin, request, queryset):
    return _generate_date_report(queryset, 'monthly')

def generate_yearly_report(modeladmin, request, queryset):
    return _generate_date_report(queryset, 'yearly')

generate_daily_report.short_description = "Generate Daily Report (selected)"
generate_weekly_report.short_description = "Generate Weekly Report (selected)"
generate_monthly_report.short_description = "Generate Monthly Report (selected)"
generate_yearly_report.short_description = "Generate Yearly Report (selected)"


# ==================== ADMIN CLASS ====================




# 2️⃣ Create Entry
def registry_create(request):
    if request.method == "POST":
        form = RegistryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('registry_list')
    else:
        form = RegistryForm()
    return render(request, 'registry/registry_form.html', {'form': form})


# 3️⃣ Update Entry
def registry_update(request, pk):
    entry = get_object_or_404(RegistryEntry, pk=pk)
    if request.method == "POST":
        form = RegistryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            return redirect('registry_list')
    else:
        form = RegistryForm(instance=entry)
    return render(request, 'registry/registry_form.html', {'form': form})


# 4️⃣ Delete Entry
def registry_delete(request, pk):
    entry = get_object_or_404(RegistryEntry, pk=pk)
    if request.method == "POST":
        entry.delete()
        return redirect('registry_list')
    return render(request, 'registry/registry_confirm_delete.html', {'entry': entry})


# 5️⃣ Export PDF (matches your Blueprint fields)
# registry/views.py





from django.http import JsonResponse
from django.db.models import Count

def dashboard_data(request):
    """
    Aggregate live registry data for the dashboard.
    All field names here match the RegistryEntry model.
    """
    qs = RegistryEntry.objects.all()

    # Helper to convert annotated querysets to dict
    def counts_from_qs(qs_vals, key_name):
        return {item[key_name]: item["count"] for item in qs_vals if item.get(key_name) not in (None, "")}

    # Text/choice fields
    gender_counts = counts_from_qs(qs.values("gender").annotate(count=Count("id")), "gender")
    grant_counts = counts_from_qs(qs.values("social_grant").annotate(count=Count("id")), "social_grant")
    tish_counts = counts_from_qs(qs.values("tish_area").annotate(count=Count("id")), "tish_area")
    race_counts = counts_from_qs(qs.values("race").annotate(count=Count("id")), "race")
    ward_counts = counts_from_qs(qs.values("ward_no").annotate(count=Count("id")), "ward_no")

    # Boolean fields
    disability_counts = {
        "Yes": qs.filter(disability=True).count(),
        "No": qs.filter(disability=False).count()
    }
    recovering_counts = {
        "Yes": qs.filter(recovering_service_user=True).count(),
        "No": qs.filter(recovering_service_user=False).count()
    }
    cooperative_counts = {
        "Yes": qs.filter(cooperative_member=True).count(),
        "No": qs.filter(cooperative_member=False).count()
    }

    # Contact info
    contact_counts = {
        "Has Contact": qs.exclude(contact_number__isnull=True).exclude(contact_number__exact="").count(),
        "No Contact": qs.filter(contact_number__isnull=True).count() + qs.filter(contact_number__exact="").count(),
    }

    # Signature info (safe fallback if field doesn't exist)
    try:
        signature_counts = {
            "Signed": qs.exclude(signature_image__isnull=True).exclude(signature_image__exact="").count(),
            "Not Signed": qs.filter(signature_image__isnull=True).count() + qs.filter(signature_image__exact="").count(),
        }
    except Exception:
        signature_counts = {}

    # Address info
    address_counts = {
        "Has Address": qs.exclude(physical_address__isnull=True).exclude(physical_address__exact="").count(),
        "No Address": qs.filter(physical_address__isnull=True).count() + qs.filter(physical_address__exact="").count(),
    }

    total_participants = qs.count()

    # ✅ Build response
    data = {
        "gender_counts": gender_counts,
        "grant_counts": grant_counts,
        "tish_counts": tish_counts,
        "disability_counts": disability_counts,
        "race_counts": race_counts,
        "recovering_counts": recovering_counts,
        "cooperative_counts": cooperative_counts,
        "ward_counts": ward_counts,
        "contact_counts": contact_counts,
        "signature_counts": signature_counts,
        "address_counts": address_counts,
        "total_participants": total_participants,
    }

    return JsonResponse(data)


def dashboard(request):
    entries = RegistryEntry.objects.all()
    return render(request, 'registry/registry_dashboard.html', {'entries': entries})


def registry_view(request):
    """Handle the registry form submission"""
    if request.method == "POST":
        form = RegistryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            
            # MANUALLY process signature data
            signature_data_json = request.POST.get('signature_data', '')
            if signature_data_json:
                try:
                    signature_data = json.loads(signature_data_json)
                    entry.signature_data = signature_data
                    
                    # Convert to image and save
                    signature_img = signature_data_to_image(signature_data)
                    if signature_img:
                        # Save image logic here
                        # Example: save signature image to a file or image field
                        pass
                        
                except json.JSONDecodeError:
                    # Handle JSON decode error
                    pass
            
            entry.save()
            
            # Return success response or redirect
            return redirect('success-page')  # or JsonResponse({'success': True})
    
    else:
        form = RegistryForm()
    
    # For GET requests, render the form
    return render(request, 'registry_form.html', {'form': form})

# 1️⃣ Registry List with Search + Filter + Summaries
def registry_list(request):
    entries = RegistryEntry.objects.all()

    

    # Get search/filter params
    search = request.GET.get('search', '')
    gender_filter = request.GET.get('gender', '')
    grant_filter = request.GET.get('grant', '')
    tish_filter = request.GET.get('tish_area', '')

    # Apply search
    if search:
        entries = entries.filter(
            Q(names__icontains=search) |
            Q(surname__icontains=search) |
            Q(id_no_or_dob__icontains=search)
        )

    # Apply filters
    if gender_filter:
        entries = entries.filter(gender=gender_filter)
    if grant_filter:
        entries = entries.filter(social_grant=grant_filter)
    if tish_filter:
        entries = entries.filter(tish_area=tish_filter)

    # Generate summaries (guaranteed Counter dicts)
    gender_counts = Counter([entry.gender for entry in entries])
    grant_counts = Counter([entry.social_grant for entry in entries])
    tish_counts = Counter([entry.tish_area for entry in entries])

    context = {
        'entries': entries,
        'gender_counts': dict(gender_counts),  # convert to dict for template safety
        'grant_counts': dict(grant_counts),
        'tish_counts': dict(tish_counts),
    }

    
    return render(request, 'registry/registry_list.html', context)


# 2️⃣ Create Entry
def registry_create(request):
    if request.method == "POST":
        form = RegistryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('registry_list')
    else:
        form = RegistryForm()
    return render(request, 'registry/registry_form.html', {'form': form})


# 3️⃣ Update Entry
def registry_update(request, pk):
    entry = get_object_or_404(RegistryEntry, pk=pk)
    if request.method == "POST":
        form = RegistryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            return redirect('registry_list')
    else:
        form = RegistryForm(instance=entry)
    return render(request, 'registry/registry_form.html', {'form': form})


# 4️⃣ Delete Entry
def registry_delete(request, pk):
    entry = get_object_or_404(RegistryEntry, pk=pk)
    if request.method == "POST":
        entry.delete()
        return redirect('registry_list')
    return render(request, 'registry/registry_confirm_delete.html', {'entry': entry})


# 5️⃣ Export PDF (matches your Blueprint fields)
def export_pdf(request):
    entries = RegistryEntry.objects.all()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="registry.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 40, "Registry Report")

    # Prepare table data
    table_data = []
    headers = [
        "No.", "Names", "Surname", "ID No./DoB", "Gender",
        "Disability", "Address", "TISH Area", "Ward",
        "Contact", "Race", "Recovering", "Grant",
        "Cooperative", "Sign"
    ]
    table_data.append(headers)
    for i, entry in enumerate(entries, start=1):
        # Check if entry has a signature image
        signature_text = "Signed" if entry.signature_image else "Not signed"
        
        row = [
            str(i),
            entry.names,
            entry.surname,
            entry.id_no_or_dob,
            entry.gender,
            "Yes" if entry.disability else "No",
            entry.physical_address,
            entry.tish_area,
            entry.ward_no,
            entry.contact_number,
            entry.race,
            "Yes" if entry.recovering_service_user else "No",
            entry.social_grant,
            "Yes" if entry.cooperative_member else "No",
            signature_text,  # Use this instead of entry.sign
        ]
        table_data.append(row)

    # Column widths (mm)
    col_widths = [
        10*mm, 25*mm, 25*mm, 25*mm, 15*mm,
        15*mm, 45*mm, 25*mm, 15*mm,
        25*mm, 15*mm, 15*mm, 15*mm,
        15*mm, 25*mm
    ]

    table = Table(table_data, colWidths=col_widths)

    style = TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('ALIGN', (0,1), (0,-1), 'CENTER'),
        ('ALIGN', (5,1), (5,-1), 'CENTER'),
        ('ALIGN', (11,1), (11,-1), 'CENTER'),
        ('ALIGN', (13,1), (13,-1), 'CENTER'),
    ])
    table.setStyle(style)

    # Place table dynamically
    table.wrapOn(c, width, height)
    table_height = len(table_data) * 12  # estimate row height
    table.drawOn(c, 15*mm, height - 60*mm - table_height)

    c.showPage()
    c.save()
    return response

