from django.urls import path
from .views import home,login_view,logout_view,create_trade, my_items,my_trades,trade_action

urlpatterns = [
    path("", home, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("trade/create/<int:item_id>/", create_trade, name="create_trade"),
    path("my-items/", my_items, name="my_items"),
    path("my-trades/", my_trades, name="my_trades"),
    path("trade/<int:trade_id>/action/", trade_action, name="trade_action"),
]