from django.urls import path
from . import views, staff_views

app_name = 'circulation'

urlpatterns = [
    path('counter-borrow/', views.counter_borrow_view, name='counter_borrow'),
    path('borrow/<int:pk>/cancel/', views.borrow_cancel_view, name='borrow_cancel'),
    path('borrow/<int:pk>/renew/', views.renew_borrow_view, name='renew_borrow'),
    path('history/', views.borrow_history_view, name='borrow_history'),
    path('manage/', views.manage_borrows_view, name='manage_borrows'),
    path('request/<int:pk>/', views.borrow_request_view, name='borrow_request'),
    path('approve/<int:pk>/', views.approve_borrow_view, name='approve_borrow'),
    path('handover/<int:pk>/', views.handover_book_view, name='handover_book'),
    path('return/<int:pk>/', views.return_book_view, name='return_book'),
    path('report_lost/<int:pk>/', views.report_lost_view, name='report_lost'),
    path('report_violation/<int:pk>/', views.report_violation_view, name='report_violation'),
    path('resolve_violation/<int:pk>/', views.resolve_violation_view, name='resolve_violation'),
    path('reserve/<int:book_id>/', views.reservation_create_view, name='reserve_book'),
    path('reservations/', views.reservation_list_view, name='reservation_list'),
    path('reservations/<int:pk>/cancel/', views.reservation_cancel_view, name='reservation_cancel'),
    path('staff/reservations/', staff_views.manage_reservations_view, name='manage_reservations'),
    path('staff/reservations/<int:pk>/cancel/', staff_views.cancel_reservation_view, name='staff_cancel_reservation'),
]
