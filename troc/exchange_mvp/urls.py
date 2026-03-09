from django.urls import path
from .views import home,login_view,logout_view,create_trade

urlpatterns = [
    path("", home, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("trade/create/<int:item_id>/", create_trade, name="create_trade"),  # <== important
]