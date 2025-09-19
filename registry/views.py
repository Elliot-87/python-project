# registry/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from collections import Counter
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
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
# registry/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from collections import Counter
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle
from .models import RegistryEntry
from .forms import RegistryForm
import json
from django.http import JsonResponse
from .utils import signature_data_to_image






def dashboard_data(request):
    entries = RegistryEntry.objects.all()
    
    gender_counts = dict(Counter([entry.gender for entry in entries]))
    grant_counts = dict(Counter([entry.social_grant for entry in entries]))
    tish_counts = dict(Counter([entry.tish_area for entry in entries]))

    data = {
        "gender_counts": gender_counts,
        "grant_counts": grant_counts,
        "tish_counts": tish_counts,
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

