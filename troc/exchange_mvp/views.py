from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Avg, Q
from django.utils import timezone
import datetime

from .models import Item, Category, Trade, Message, Rating, Notification


def create_notification(user, notif_type, message_text, trade=None):
    Notification.objects.create(
        user=user,
        notif_type=notif_type,
        message=message_text,
        trade=trade,
    )


# --- AUTH ---

def login_view(request):
    error_message = None
    username_value = ""

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username_value = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username_value, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            error_message = "Nom d'utilisateur ou mot de passe incorrect."

    return render(request, "login.html", {
        "error_message": error_message,
        "username_value": username_value,
    })


def logout_view(request):
    logout(request)
    return redirect("home")


# --- ACCUEIL ---

def home(request):
    items = Item.objects.filter(available=True).select_related("owner", "category")

    query = request.GET.get("q", "").strip()
    if query:
        items = items.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    category_id = request.GET.get("category", "")
    if category_id:
        items = items.filter(category_id=category_id)

    if request.user.is_authenticated:
        items = items.exclude(owner=request.user)

    categories = Category.objects.all()

    return render(request, "home.html", {
        "items": items,
        "categories": categories,
        "query": query,
        "selected_category": category_id,
    })


# --- DÉTAIL ARTICLE ---

def item_detail(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    ratings = Rating.objects.filter(rated_user=item.owner).select_related("rater")
    avg_rating = ratings.aggregate(avg=Avg("score"))["avg"]
    can_trade = (
        request.user.is_authenticated
        and request.user != item.owner
        and item.available
    )
    return render(request, "item_detail.html", {
        "item": item,
        "avg_rating": avg_rating,
        "ratings_count": ratings.count(),
        "can_trade": can_trade,
    })


# --- MES ARTICLES ---

@login_required
def my_items(request):
    original_items = Item.objects.filter(owner=request.user, received_by_trade=False)
    traded_items = Item.objects.filter(owner=request.user, received_by_trade=True)
    return render(request, "my_items.html", {
        "original_items": original_items,
        "traded_items": traded_items,
    })


@login_required
def toggle_item_availability(request, item_id):
    item = get_object_or_404(Item, id=item_id, owner=request.user)
    item.available = not item.available
    item.save()
    if item.available:
        messages.success(request, f"« {item.title} » est maintenant visible dans le catalogue.")
    else:
        messages.info(request, f"« {item.title} » n'est plus visible dans le catalogue.")
    return redirect("my_items")


# --- CRÉER UN ÉCHANGE ---

@login_required
def create_trade(request, item_id):
    target_item = get_object_or_404(Item, id=item_id)

    if target_item.owner == request.user:
        messages.error(request, "Vous ne pouvez pas proposer un échange sur votre propre article.")
        return redirect("home")

    if not target_item.available:
        messages.error(request, "Cet article n'est plus disponible à l'échange.")
        return redirect("home")

    user_items = Item.objects.filter(owner=request.user, available=True)

    if request.method == "POST":
        offered_ids = request.POST.getlist("offered_items")
        message_content = request.POST.get("message", "").strip()

        if not offered_ids:
            messages.error(request, "Vous devez sélectionner au moins un article à proposer.")
            return render(request, "create_trade.html", {
                "target_item": target_item,
                "user_items": user_items,
            })

        trade = Trade.objects.create(
            proposer=request.user,
            receiver=target_item.owner,
            status="pending"
        )
        trade.offered_items.set(Item.objects.filter(id__in=offered_ids, owner=request.user))
        trade.requested_items.set([target_item])
        trade.save()

        if message_content:
            Message.objects.create(trade=trade, sender=request.user, content=message_content)

        create_notification(
            user=target_item.owner,
            notif_type="trade_received",
            message_text=f"{request.user.username} vous propose un échange pour « {target_item.title} ».",
            trade=trade,
        )

        messages.success(request, "Votre proposition d'échange a été envoyée !")
        return redirect("my_trades")

    return render(request, "create_trade.html", {
        "target_item": target_item,
        "user_items": user_items,
    })


# --- MES ÉCHANGES ---

@login_required
def my_trades(request):
    trades_received = Trade.objects.filter(receiver=request.user).prefetch_related(
        "offered_items", "requested_items", "messages"
    ).select_related("proposer")

    trades_sent = Trade.objects.filter(proposer=request.user).prefetch_related(
        "offered_items", "requested_items", "messages"
    ).select_related("receiver")

    rated_trade_ids = Rating.objects.filter(rater=request.user).values_list("trade_id", flat=True)

    # Calculer le délai d'annulation pour chaque échange accepté
    cancel_deadlines = {}
    for trade in trades_sent:
        if trade.status == "accepted":
            deadline = trade.updated_at + datetime.timedelta(hours=24)
            cancel_deadlines[trade.id] = deadline > timezone.now()

    return render(request, "my_trades.html", {
        "trades_received": trades_received,
        "trades_sent": trades_sent,
        "rated_trade_ids": rated_trade_ids,
        "cancel_deadlines": cancel_deadlines,
    })


# --- ACTIONS SUR UN ÉCHANGE ---

@login_required
def trade_action(request, trade_id):
    trade = get_object_or_404(Trade, id=trade_id)

    if request.user not in [trade.proposer, trade.receiver]:
        messages.error(request, "Accès non autorisé.")
        return redirect("my_trades")

    if request.method == "POST":
        action = request.POST.get("action")
        content = request.POST.get("message", "").strip()

        # --- ENVOYER UN MESSAGE ---
        if content:
            Message.objects.create(trade=trade, sender=request.user, content=content)
            other_user = trade.receiver if request.user == trade.proposer else trade.proposer
            create_notification(
                user=other_user,
                notif_type="message_received",
                message_text=f"{request.user.username} vous a envoyé un message sur l'échange #{trade.id}.",
                trade=trade,
            )

        # --- ACCEPTER (destinataire) ---
        if action == "accept" and trade.receiver == request.user and trade.status == "pending":
            trade.status = "accepted"
            trade.save()

            for item in list(trade.offered_items.all()) + list(trade.requested_items.all()):
                item.available = False
                item.save()

            _cancel_conflicting_trades(trade)

            create_notification(
                user=trade.proposer,
                notif_type="trade_accepted",
                message_text=f"{trade.receiver.username} a accepté votre échange #{trade.id} ! Choisissez maintenant le mode de livraison.",
                trade=trade,
            )
            messages.success(request, "Échange accepté ! Choisissez maintenant le mode de livraison.")

        # --- REFUSER (destinataire) ---
        elif action == "refuse" and trade.receiver == request.user and trade.status == "pending":
            trade.status = "refused"
            trade.save()
            create_notification(
                user=trade.proposer,
                notif_type="trade_refused",
                message_text=f"{trade.receiver.username} a refusé votre échange #{trade.id}.",
                trade=trade,
            )
            messages.info(request, "Échange refusé.")

        # --- ANNULER (proposeur, pendant pending) ---
        elif action == "cancel" and trade.proposer == request.user and trade.status == "pending":
            trade.status = "cancelled"
            trade.save()
            create_notification(
                user=trade.receiver,
                notif_type="trade_cancelled",
                message_text=f"{trade.proposer.username} a annulé sa proposition d'échange #{trade.id}.",
                trade=trade,
            )
            messages.info(request, "Échange annulé.")

        # --- ANNULER APRÈS ACCEPTATION (dans les 24h, proposeur) ---
        elif action == "cancel_accepted" and trade.proposer == request.user and trade.status == "accepted":
            deadline = trade.updated_at + datetime.timedelta(hours=24)
            if timezone.now() <= deadline:
                trade.status = "cancelled"
                trade.save()

                # Remettre les articles disponibles
                for item in list(trade.offered_items.all()) + list(trade.requested_items.all()):
                    item.available = True
                    item.received_by_trade = False
                    item.save()

                create_notification(
                    user=trade.receiver,
                    notif_type="trade_cancelled",
                    message_text=f"{trade.proposer.username} a annulé l'échange #{trade.id} après acceptation. Les articles sont de nouveau disponibles.",
                    trade=trade,
                )
                messages.warning(request, "Échange annulé. Les articles sont de nouveau disponibles.")
            else:
                messages.error(request, "Le délai de 24h pour annuler est dépassé.")

        # --- CHOISIR MODE DE LIVRAISON (proposeur) ---
        elif action == "set_delivery" and trade.proposer == request.user and trade.status == "accepted":
            delivery_mode = request.POST.get("delivery_mode", "").strip()
            delivery_info = request.POST.get("delivery_info", "").strip()

            if not delivery_mode:
                messages.error(request, "Veuillez choisir un mode de livraison.")
                return redirect("my_trades")

            if not delivery_info:
                messages.error(request, "Veuillez renseigner les informations de livraison.")
                return redirect("my_trades")

            trade.delivery_mode = delivery_mode
            trade.delivery_info = delivery_info
            trade.save()

            create_notification(
                user=trade.receiver,
                notif_type="delivery_set",
                message_text=f"{trade.proposer.username} a proposé le mode « {trade.get_delivery_mode_display()} » pour l'échange #{trade.id}. Confirmez !",
                trade=trade,
            )
            messages.success(request, "Mode de livraison envoyé ! En attente de confirmation.")

        # --- CONFIRMER LIVRAISON (destinataire) ---
        elif action == "confirm_delivery" and trade.receiver == request.user and trade.delivery_mode and trade.status == "accepted":
            trade.status = "completed"
            trade.save()

            for item in trade.offered_items.all():
                item.owner = trade.receiver
                item.available = False
                item.received_by_trade = True
                item.save()

            for item in trade.requested_items.all():
                item.owner = trade.proposer
                item.available = False
                item.received_by_trade = True
                item.save()

            create_notification(
                user=trade.proposer,
                notif_type="delivery_confirmed",
                message_text=f"{trade.receiver.username} a confirmé la livraison. L'échange #{trade.id} est terminé !",
                trade=trade,
            )
            messages.success(request, "Livraison confirmée ! Les articles ont été transférés. Retrouvez-les dans 'Mes articles'.")

    return redirect("my_trades")


def _cancel_conflicting_trades(accepted_trade):
    all_items = list(accepted_trade.offered_items.all()) + list(accepted_trade.requested_items.all())
    conflicting = Trade.objects.filter(status="pending").filter(
        Q(offered_items__in=all_items) | Q(requested_items__in=all_items)
    ).exclude(id=accepted_trade.id).distinct()

    for trade in conflicting:
        trade.status = "cancelled"
        trade.save()
        create_notification(
            user=trade.proposer,
            notif_type="trade_cancelled",
            message_text=f"L'échange #{trade.id} a été annulé car un article concerné a été échangé.",
            trade=trade,
        )


# --- NOTATION ---

@login_required
def rate_trade(request, trade_id):
    trade = get_object_or_404(Trade, id=trade_id, status="completed")

    if request.user not in [trade.proposer, trade.receiver]:
        messages.error(request, "Accès non autorisé.")
        return redirect("my_trades")

    if Rating.objects.filter(trade=trade, rater=request.user).exists():
        messages.warning(request, "Vous avez déjà noté cet échange.")
        return redirect("my_trades")

    rated_user = trade.receiver if request.user == trade.proposer else trade.proposer

    if request.method == "POST":
        score = request.POST.get("score")
        comment = request.POST.get("comment", "").strip()

        if not score or not score.isdigit() or not (1 <= int(score) <= 5):
            messages.error(request, "Note invalide. Choisissez entre 1 et 5.")
            return render(request, "rate_trade.html", {"trade": trade, "rated_user": rated_user})

        Rating.objects.create(
            trade=trade,
            rater=request.user,
            rated_user=rated_user,
            score=int(score),
            comment=comment,
        )
        create_notification(
            user=rated_user,
            notif_type="rating_received",
            message_text=f"{request.user.username} vous a laissé une note de {score}/5.",
            trade=trade,
        )
        messages.success(request, "Merci pour votre note !")
        return redirect("my_trades")

    return render(request, "rate_trade.html", {"trade": trade, "rated_user": rated_user})


# --- PROFIL ---

def user_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    items = Item.objects.filter(owner=profile_user, available=True)
    ratings = Rating.objects.filter(rated_user=profile_user).select_related("rater")
    avg_rating = ratings.aggregate(avg=Avg("score"))["avg"]
    completed_trades = Trade.objects.filter(
        Q(proposer=profile_user) | Q(receiver=profile_user),
        status="completed"
    ).count()

    return render(request, "user_profile.html", {
        "profile_user": profile_user,
        "items": items,
        "ratings": ratings,
        "avg_rating": avg_rating,
        "completed_trades": completed_trades,
    })


# --- NOTIFICATIONS ---

@login_required
def notifications_view(request):
    notifs = Notification.objects.filter(user=request.user)
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, "notifications.html", {"notifications": notifs})


@login_required
def mark_notification_read(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, user=request.user)
    notif.is_read = True
    notif.save()
    return redirect("notifications")