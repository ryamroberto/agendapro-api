from django.urls import path
from .views import CurrentUserView

app_name = 'core'

urlpatterns = [
    path('api/me/', CurrentUserView.as_view(), name='current_user'),
]
