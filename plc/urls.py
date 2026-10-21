from django.urls import path
from . import views

app_name = "plc"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/status/", views.motor_status, name="status"),
    path("api/speed/", views.motor_speed, name="speed"),
    path(
        "api/command/<str:command>/",
        views.motor_command,
        name="command",
    ),
]