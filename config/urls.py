"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # Standard Django Auth (login, logout, password change/reset)
    path('accounts/', include('django.contrib.auth.urls')),
    # DRF Browsable API login/logout
    path('api-auth/', include('rest_framework.urls')),
    # OpenAPI / Swagger Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # Core app API routes
    path('', include('core.urls')),
    # Appointments app API routes
    path('', include('appointments.urls')),
]
