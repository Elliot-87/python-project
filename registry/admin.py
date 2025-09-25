from django.contrib import admin
from django.http import HttpResponse
import csv
from datetime import datetime, timedelta
from django.utils import timezone
from .models import RegistryEntry
from django.contrib.admin import DateFieldListFilter
from django.db.models import Count, Q
from django.utils.html import format_html
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Spacer, Paragraph
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.conf import settings
from django.template.loader import get_template
import os
from xhtml2pdf import pisa



# ==================== EXPORT FUNCTIONS (DEFINE FIRST) ====================
# registry/admin.py






def export_as_pdf(modeladmin, request, queryset):
    """
    Admin action: Export selected RegistryEntry objects to PDF.
    Uses pdf_preview.html as the template.
    """
    template = get_template("registry/pdf_preview.html")
    context = {
        "entries": queryset,
        "total_count": queryset.count(),
    }

    # Render HTML
    html = template.render(context)

    # Decide whether to download or just view inline
    download = request.GET.get("download", "false").lower() == "true"
    response = HttpResponse(content_type="application/pdf")
    if download:
        response["Content-Disposition"] = 'attachment; filename="registry_report.pdf"'
    else:
        response["Content-Disposition"] = 'inline; filename="registry_report.pdf"'

    # Create PDF
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)
    return response


export_as_pdf.short_description = "Export selected entries as PDF"



def export_csv(modeladmin, request, queryset):
    """Export selected entries as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="registry_entries.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Names', 'Surname', 'ID/DOB', 'Gender', 'Disability', 
        'Physical Address', 'TISH Area', 'Ward No', 'Contact Number',
        'Race', 'Service User', 'Social Grant', 'Cooperative Member',
        'Created Date'
    ])
    
    for entry in queryset:
        writer.writerow([
            entry.names, entry.surname, entry.id_no_or_dob or '',
            entry.gender, 'Yes' if entry.disability else 'No',
            entry.physical_address, entry.tish_area, entry.ward_no,
            entry.contact_number, entry.race,
            'Yes' if entry.recovering_service_user else 'No',
            entry.social_grant,
            'Yes' if entry.cooperative_member else 'No',
            entry.created_at.strftime('%Y-%m-%d %H:%M') if entry.created_at else ''
        ])
    
    return response

export_csv.short_description = "Export selected entries to CSV"

def generate_daily_report(modeladmin, request, queryset):
    return _generate_date_report(queryset, 'daily')

def generate_weekly_report(modeladmin, request, queryset):
    return _generate_date_report(queryset, 'weekly')

def generate_monthly_report(modeladmin, request, queryset):
    return _generate_date_report(queryset, 'monthly')

def generate_yearly_report(modeladmin, request, queryset):
    return _generate_date_report(queryset, 'yearly')

# Set action descriptions
generate_daily_report.short_description = "Generate Daily Report (selected)"
generate_weekly_report.short_description = "Generate Weekly Report (selected)"
generate_monthly_report.short_description = "Generate Monthly Report (selected)"
generate_yearly_report.short_description = "Generate Yearly Report (selected)"

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
    
    # Filter by date range
    date_filtered = queryset.filter(created_at__gte=start_date)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow([f'{period_type.capitalize()} Registry Report'])
    writer.writerow(['Period', f'{start_date.strftime("%Y-%m-%d")} to {now.strftime("%Y-%m-%d")}'])
    writer.writerow(['Total Entries', date_filtered.count()])
    writer.writerow([])
    
    # Summary statistics
    writer.writerow(['Summary Statistics'])
    writer.writerow(['Gender Distribution'])
    for gender, count in date_filtered.values_list('gender').annotate(count=Count('id')):
        writer.writerow([f'  {gender}', count])
    
    writer.writerow(['Race Distribution'])
    for race, count in date_filtered.values_list('race').annotate(count=Count('id')):
        writer.writerow([f'  {race}', count])
    
    writer.writerow(['Disability', date_filtered.filter(disability=True).count()])
    writer.writerow(['Service Users', date_filtered.filter(recovering_service_user=True).count()])
    writer.writerow(['Cooperative Members', date_filtered.filter(cooperative_member=True).count()])
    
    writer.writerow([])
    writer.writerow(['Detailed Entries'])
    writer.writerow([
        'Names', 'Surname', 'Gender', 'Race', 'Ward', 'Disability', 
        'Social Grant', 'Contact', 'Created'
    ])
    
    for entry in date_filtered:
        writer.writerow([
            entry.names, entry.surname, entry.gender, entry.race,
            entry.ward_no, 'Yes' if entry.disability else 'No',
            entry.social_grant, entry.contact_number,
            entry.created_at.strftime('%Y-%m-%d') if entry.created_at else ''
        ])
    
    return response

# ==================== ADMIN CLASS (DEFINE LAST) ====================

@admin.register(RegistryEntry)
class RegistryEntryAdmin(admin.ModelAdmin):
    list_display = (
        'names',
        'surname',
        'id_no_or_dob',
        'gender',
        'social_grant',
        'ward_no',
        'tish_area',
        'contact_number',
        'disability',
        'recovering_service_user',
        'cooperative_member',
    )

    list_filter = (
        'gender',
        'social_grant',
        'tish_area',
        'ward_no',
        'disability',
        'recovering_service_user',
        'cooperative_member',
    )

    search_fields = (
        'names',
        'surname',
        'id_no_or_dob',
    )

    actions = ['export_as_csv']

    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta}.csv'
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected Entries as CSV"