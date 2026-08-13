from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('signup/',  views.signup,       name= 'login_chat'),
    path('login/',   views.login_view,   name='login_chat'),
    path('logout/',  views.logout_view,  name='logout_chat'),

    # Dashboard
    path('chat/dashboard/', views.chat_dashboard, name='chat_dashboard'),

    # AJAX — پیام‌ها
    path('chat/messages/<int:user_id>/', views.get_messages,     name='chat_messages'),
    path('chat/send/<int:user_id>/',     views.send_message,     name='chat_send'),
    path('chat/unread/',                 views.get_unread_counts, name='chat_unread'),
    path('chat/online/',                 views.get_online_status, name='chat_online'),
    path('chat/picture/',                views.upload_picture,    name='chat_picture'),
]
