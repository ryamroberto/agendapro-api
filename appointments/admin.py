from django.contrib import admin
from .models import Service, Appointment


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_minutes', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('date', 'time', 'client', 'service', 'status', 'created_at')
    list_filter = ('status', 'date', 'service')
    search_fields = ('client__username', 'client__email', 'service__name', 'notes')
    ordering = ('-date', '-time')
    date_hierarchy = 'date'
