from django.shortcuts import render,redirect
from .models import Item
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

from django.shortcuts import render
from django.contrib.auth.models import User
from .models import Item

def home(request):

    items = Item.objects.all()

    user_id = request.session.get("user_id")
    current_user = None

    if user_id:
        current_user = User.objects.get(id=user_id)

    return render(request, "home.html", {
        "items": items,
        "current_user": current_user
    })



def login_view(request):
    error_message = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)  # connecte l'utilisateur
            return redirect("home")
        else:
            error_message = "Nom d'utilisateur ou mot de passe incorrect"

    return render(request, "login.html", {"error_message": error_message})


from django.shortcuts import redirect

def logout_view(request):
    logout(request)
    return redirect("home")

def create_trade(request, item_id):
    # juste pour tester pour l'instant
    return render(request, "create_trade.html", {"item_id": item_id})