from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('otp-verify/', views.otp_verify_view, name='otp_verify'),
    path('otp-resend/', views.otp_resend_view, name='otp_resend'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('users/', views.user_list_view, name='user_list'),
    path('users/add/', views.user_create_view, name='user_create'),
    path('users/import/', views.user_import_view, name='user_import'),
    path('users/<int:pk>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<int:pk>/reset-password/', views.admin_reset_password_view, name='admin_reset_password'),
    path('users/<int:pk>/toggle/', views.user_toggle_active_view, name='user_toggle'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('forgot-password/otp/', views.forgot_password_otp_view, name='forgot_password_otp'),
    path('forgot-password/otp-resend/', views.forgot_password_resend_view, name='forgot_password_resend'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('password_change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
]
