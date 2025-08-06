# admin.py
from django.contrib import admin
from .models import Framework, ControlCategory, Control, ControlMapping


@admin.register(Framework)
class FrameworkAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ControlCategory)
class ControlCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'framework', 'parent_category']
    list_filter = ['framework', 'parent_category']
    search_fields = ['name', 'code', 'description']
    ordering = ['framework__name', 'name']


@admin.register(Control)
class ControlAdmin(admin.ModelAdmin):
    list_display = ['control_id', 'title', 'framework', 'category', 'created_at']
    list_filter = ['framework', 'category', 'created_at']
    search_fields = ['control_id', 'title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 50

    fieldsets = (
        ('Basic Information', {
            'fields': ('framework', 'control_id', 'title', 'category')
        }),
        ('Content', {
            'fields': ('description', 'recommendation')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


from django.contrib import admin
from .models import ControlMapping


@admin.register(ControlMapping)
class ControlMappingAdmin(admin.ModelAdmin):
    # Remove or comment out these lines until you fix the model
    # list_display = ['primary_control', 'secondary_control', 'mapping_type', 'created_at']
    # list_filter = ['mapping_type', 'primary_control__framework']
    # autocomplete_fields = ['primary_control']

    # Use only fields that actually exist in your model
    list_display = ['id']  # Replace with actual field names
    pass