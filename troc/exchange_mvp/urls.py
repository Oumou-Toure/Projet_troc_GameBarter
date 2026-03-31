from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("my-items/", views.my_items, name="my_items"),
    path("my-items/<int:item_id>/toggle/", views.toggle_item_availability, name="toggle_item_availability"),
    path("item/<int:item_id>/", views.item_detail, name="item_detail"),
    path("trade/create/<int:item_id>/", views.create_trade, name="create_trade"),
    path("my-trades/", views.my_trades, name="my_trades"),
    path("trade/<int:trade_id>/action/", views.trade_action, name="trade_action"),
    path("trade/<int:trade_id>/rate/", views.rate_trade, name="rate_trade"),
    path("profil/<str:username>/", views.user_profile, name="user_profile"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("notifications/<int:notif_id>/read/", views.mark_notification_read, name="mark_notification_read"),
]