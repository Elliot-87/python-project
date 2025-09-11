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
            entry.sign,
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
