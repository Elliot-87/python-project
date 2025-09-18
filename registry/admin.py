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

# ==================== EXPORT FUNCTIONS (DEFINE FIRST) ====================

def export_as_pdf_template(modeladmin, request, queryset):
    """Export selected entries as PDF using template"""
    context = {
        'entries': queryset,
        'export_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    html_string = render_to_string('registry/registry_export_pdf.html', context)
    
    response = HttpResponse(content_type='application/pdf')
    filename = f"registry_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Create PDF
    pdf = pisa.pisaDocument(BytesIO(html_string.encode("UTF-8")), response)
    
    if pdf.err:
        return HttpResponse('Error generating PDF', status=500)
    
    return response

export_as_pdf_template.short_description = "Export as PDF (Formatted)"

def export_csv(modeladmin, request, queryset):
    """Export selected entries as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="registry_entries.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Names', 'Surname', 'ID/DOB', 'Gender', 'Disability', 
        'Physical Address', 'Area Type', 'Ward No', 'Contact Number',
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
    list_display = [
        'names', 'surname', 'gender', 'race', 'ward_no', 
        'disability_status', 'social_grant', 'created_display'
    ]
    list_filter = [
        'gender', 'race', 'ward_no', 'disability', 
        'social_grant', 'recovering_service_user', 
        'cooperative_member', ('created_at', DateFieldListFilter)
    ]
    search_fields = ['names', 'surname', 'id_no_or_dob', 'contact_number']
    readonly_fields = ['created_at']
    
    # ADD ALL ACTIONS HERE - functions are now defined above
    actions = [
        export_as_pdf_template, export_csv, generate_daily_report,
        generate_weekly_report, generate_monthly_report, generate_yearly_report
    ]
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:  # Editing an existing object
            fieldsets += (('System Information', {
                'fields': ('created_at',),
                'classes': ('collapse',)
            }),)
        return fieldsets
    
    def created_display(self, obj):
        if obj.created_at:
            return obj.created_at.strftime('%Y-%m-%d %H:%M')
        return "No date"
    created_display.short_description = 'Created'
    
    def disability_status(self, obj):
        return "Yes" if obj.disability else "No"
    disability_status.short_description = 'Disability'
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        return actions