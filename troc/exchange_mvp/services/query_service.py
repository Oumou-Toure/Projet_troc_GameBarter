from django.db.models import Avg, Q
from django.contrib.auth.models import User

from exchange_mvp.models import Item, Trade, Message, Rating, Notification


class TradeQueryService:
    """
    Service responsable de toutes les consultations (queries) sur les échanges.
    Aucune modification de données dans ce service.
    """

    @staticmethod
    def get_trades_for_user(user):
        """
        Retourne tous les échanges d'un utilisateur
        (envoyés et reçus).
        """
        return Trade.objects.filter(
            Q(proposer=user) | Q(receiver=user)
        ).order_by("-created_at")

    @staticmethod
    def get_sent_trades(user):
        """Retourne les échanges envoyés par un utilisateur."""
        return Trade.objects.filter(
            proposer=user
        ).prefetch_related(
            "offered_items", "requested_items", "messages"
        ).select_related("receiver").order_by("-created_at")

    @staticmethod
    def get_received_trades(user):
        """Retourne les échanges reçus par un utilisateur."""
        return Trade.objects.filter(
            receiver=user
        ).prefetch_related(
            "offered_items", "requested_items", "messages"
        ).select_related("proposer").order_by("-created_at")

    @staticmethod
    def get_pending_trades(user):
        """Retourne les échanges en attente d'un utilisateur."""
        return Trade.objects.filter(
            Q(proposer=user) | Q(receiver=user),
            status="pending",
        ).order_by("-created_at")

    @staticmethod
    def get_completed_trades(user):
        """Retourne les échanges terminés d'un utilisateur."""
        return Trade.objects.filter(
            Q(proposer=user) | Q(receiver=user),
            status="completed",
        ).order_by("-created_at")

    @staticmethod
    def get_trade_history(user):
        """
        Retourne l'historique complet des échanges d'un utilisateur
        (tous statuts confondus).
        """
        return Trade.objects.filter(
            Q(proposer=user) | Q(receiver=user)
        ).prefetch_related(
            "offered_items", "requested_items", "messages"
        ).order_by("-created_at")

    @staticmethod
    def get_trades_for_item(item):
        """Retourne tous les échanges impliquant un article donné."""
        return Trade.objects.filter(
            Q(offered_items=item) | Q(requested_items=item)
        ).distinct().order_by("-created_at")

    @staticmethod
    def get_active_trades_for_item(item):
        """Retourne les échanges actifs (pending/accepted) pour un article."""
        return Trade.objects.filter(
            Q(offered_items=item) | Q(requested_items=item),
            status__in=["pending", "accepted"],
        ).distinct()

    @staticmethod
    def get_messages_for_trade(trade):
        """Retourne tous les messages d'un échange, dans l'ordre chronologique."""
        return Message.objects.filter(trade=trade).select_related("sender").order_by("created_at")

    @staticmethod
    def get_user_ratings(user):
        """Retourne toutes les notations reçues par un utilisateur."""
        return Rating.objects.filter(
            rated_user=user
        ).select_related("rater").order_by("-created_at")

    @staticmethod
    def get_average_rating(user):
        """Retourne la note moyenne d'un utilisateur."""
        result = Rating.objects.filter(rated_user=user).aggregate(avg=Avg("score"))
        return result["avg"]

    @staticmethod
    def get_unread_notifications(user):
        """Retourne les notifications non lues d'un utilisateur."""
        return Notification.objects.filter(
            user=user,
            is_read=False,
        ).order_by("-created_at")

    @staticmethod
    def get_all_notifications(user):
        """Retourne toutes les notifications d'un utilisateur."""
        return Notification.objects.filter(
            user=user
        ).order_by("-created_at")

    @staticmethod
    def get_available_items(exclude_user=None):
        """
        Retourne tous les articles disponibles.
        - exclude_user : exclure les articles de cet utilisateur (optionnel)
        """
        items = Item.objects.filter(
            available=True
        ).select_related("owner", "category")

        if exclude_user:
            items = items.exclude(owner=exclude_user)

        return items

    @staticmethod
    def get_items_for_user(user):
        """Retourne tous les articles d'un utilisateur."""
        return Item.objects.filter(owner=user).select_related("category")

    @staticmethod
    def get_completed_trades_count(user):
        """Retourne le nombre d'échanges complétés d'un utilisateur."""
        return Trade.objects.filter(
            Q(proposer=user) | Q(receiver=user),
            status="completed",
        ).count()

    @staticmethod
    def get_rated_trade_ids(user):
        """Retourne les ids des échanges déjà notés par un utilisateur."""
        from exchange_mvp.models import Rating
        return Rating.objects.filter(
            rater=user
        ).values_list("trade_id", flat=True)