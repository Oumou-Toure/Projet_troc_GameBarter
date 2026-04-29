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
        return Trade.objects.filter(
            Q(proposer=user) | Q(receiver=user)
        ).order_by("-created_at")

    @staticmethod
    def get_sent_trades(user):
        return Trade.objects.filter(
            proposer=user
        ).prefetch_related(
            "offered_items", "requested_items", "messages"
        ).select_related("receiver").order_by("-created_at")

    @staticmethod
    def get_received_trades(user):
        return Trade.objects.filter(
            receiver=user
        ).prefetch_related(
            "offered_items", "requested_items", "messages"
        ).select_related("proposer").order_by("-created_at")

    @staticmethod
    def get_pending_trades(user):
        return Trade.objects.filter(
            Q(proposer=user) | Q(receiver=user),
            status="pending",
        ).order_by("-created_at")

    @staticmethod
    def get_completed_trades(user):
        return Trade.objects.filter(
            Q(proposer=user) | Q(receiver=user),
            status="completed",
        ).order_by("-created_at")

    @staticmethod
    def get_trade_history(user):
        return Trade.objects.filter(
            Q(proposer=user) | Q(receiver=user)
        ).prefetch_related(
            "offered_items", "requested_items", "messages"
        ).order_by("-created_at")

    @staticmethod
    def get_trades_for_item(item):
        return Trade.objects.filter(
            Q(offered_items=item) | Q(requested_items=item)
        ).distinct().order_by("-created_at")

    @staticmethod
    def get_active_trades_for_item(item):
        return Trade.objects.filter(
            Q(offered_items=item) | Q(requested_items=item),
            status__in=["pending", "accepted"],
        ).distinct()

    @staticmethod
    def get_messages_for_trade(trade):
        return Message.objects.filter(
            trade=trade
        ).select_related("sender").order_by("created_at")

    @staticmethod
    def get_user_ratings(user):
        return Rating.objects.filter(
            rated_user=user
        ).select_related("rater").order_by("-created_at")

    @staticmethod
    def get_average_rating(user):
        result = Rating.objects.filter(rated_user=user).aggregate(avg=Avg("score"))
        return result["avg"]

    @staticmethod
    def get_unread_notifications(user):
        return Notification.objects.filter(
            user=user,
            is_read=False,
        ).order_by("-created_at")

    @staticmethod
    def get_all_notifications(user):
        return Notification.objects.filter(
            user=user
        ).order_by("-created_at")

    @staticmethod
    def get_available_items(exclude_user=None):
        items = Item.objects.filter(
            available=True
        ).select_related("owner", "category")

        if exclude_user:
            items = items.exclude(owner=exclude_user)

        return items

    @staticmethod
    def get_items_for_user(user):
        return Item.objects.filter(owner=user).select_related("category")

    @staticmethod
    def get_completed_trades_count(user):
        return Trade.objects.filter(
            Q(proposer=user) | Q(receiver=user),
            status="completed",
        ).count()

    @staticmethod
    def get_rated_trade_ids(user):
        return Rating.objects.filter(
            rater=user
        ).values_list("trade_id", flat=True)

    @staticmethod
    def get_items_by_platform(platform, exclude_user=None):
        """Retourne les articles disponibles filtrés par plateforme."""
        items = Item.objects.filter(
            available=True,
            platform=platform,
        ).select_related("owner", "category")

        if exclude_user:
            items = items.exclude(owner=exclude_user)

        return items

    @staticmethod
    def get_items_by_condition(condition, exclude_user=None):
        """Retourne les articles disponibles filtrés par état."""
        items = Item.objects.filter(
            available=True,
            condition=condition,
        ).select_related("owner", "category")

        if exclude_user:
            items = items.exclude(owner=exclude_user)

        return items

    @staticmethod
    def get_items_with_value_range(min_value, max_value, exclude_user=None):
        """Retourne les articles dans une fourchette de valeur estimée."""
        items = Item.objects.filter(
            available=True,
            estimated_value__gte=min_value,
            estimated_value__lte=max_value,
        ).select_related("owner", "category")

        if exclude_user:
            items = items.exclude(owner=exclude_user)

        return items

    @staticmethod
    def check_value_imbalance(offered_items, target_item, threshold=2.0):
        """
        Vérifie si les valeurs sont déséquilibrées.
        Retourne True si le ratio dépasse le seuil.
        """
        if not target_item.estimated_value:
            return False

        total_offered = sum(
            float(item.estimated_value)
            for item in offered_items
            if item.estimated_value
        )

        if total_offered == 0:
            return False

        ratio = max(total_offered, float(target_item.estimated_value)) / \
                min(total_offered, float(target_item.estimated_value))

        return ratio >= threshold