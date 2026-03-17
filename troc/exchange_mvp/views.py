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

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Item, Trade, Message
from django.utils import timezone

@login_required
def create_trade(request, item_id):
    # L'objet cible
    target_item = get_object_or_404(Item, id=item_id)

    # On ne peut pas échanger son propre objet
    if target_item.owner == request.user:
        return redirect("home")

    # Liste des objets de l'utilisateur connecté
    user_items = Item.objects.filter(owner=request.user)

    if request.method == "POST":
        # Ids des objets proposés par l'utilisateur
        offered_ids = request.POST.getlist("offered_items")
        # Ids des objets demandés (toujours le target)
        requested_ids = request.POST.getlist("requested_items")
        message_content = request.POST.get("message", "").strip()

        # Créer le Trade
        trade = Trade.objects.create(
            proposer=request.user,
            receiver=target_item.owner,
            status="pending"
        )

        # Ajouter les objets proposés
        trade.offered_items.set(Item.objects.filter(id__in=offered_ids))
        # Ajouter les objets demandés
        trade.requested_items.set(Item.objects.filter(id__in=requested_ids))
        trade.save()

        # Ajouter le message initial si présent
        if message_content:
            Message.objects.create(
                trade=trade,
                sender=request.user,
                content=message_content,
                created_at=timezone.now()
            )

        return redirect("my_trades")

    # GET : afficher le formulaire
    return render(request, "create_trade.html", {
        "target_item": target_item,
        "user_items": user_items
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Item

@login_required
def my_items(request):
    items = Item.objects.filter(owner=request.user)
    return render(request, "my_items.html", {"items": items})


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Trade, Message
from django.utils import timezone

@login_required
def my_trades(request):

    # Tous les échanges liés à l'utilisateur
    trades_received = Trade.objects.filter(receiver=request.user).order_by('-created_at')
    trades_sent = Trade.objects.filter(proposer=request.user).order_by('-created_at')

    return render(request, "my_trades.html", {
        "trades_received": trades_received,
        "trades_sent": trades_sent
    })


@login_required
def trade_action(request, trade_id):
    """
    Gérer les actions : accepter, refuser, envoyer message
    """
    trade = get_object_or_404(Trade, id=trade_id)

    if request.method == "POST":

        action = request.POST.get("action")
        content = request.POST.get("message", "").strip()

        # Ajouter message si présent
        if content:
            Message.objects.create(
                trade=trade,
                sender=request.user,
                content=content,
                created_at=timezone.now()
            )

        # Accepter / Refuser (seulement pour le destinataire)
        if trade.receiver == request.user:
            if action == "accept":
                trade.status = "accepted"
                trade.save()
            elif action == "refuse":
                trade.status = "refused"
                trade.save()

        return redirect("my_trades")

    return redirect("my_trades")