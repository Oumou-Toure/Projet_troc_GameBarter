from django.contrib.auth.models import User
from django.utils import timezone
import datetime

from exchange_mvp.models import Item, Trade, Message, Rating, Notification


def create_notification(user, notif_type, message_text, trade=None):
    Notification.objects.create(
        user=user,
        notif_type=notif_type,
        message=message_text,
        trade=trade,
    )


class TradeCommandService:
    """
    Service responsable de toutes les actions (commandes) sur les échanges.
    Toute modification de données passe par ce service.
    """

    @staticmethod
    def propose_trade(proposer, target_item, offered_item_ids, message_content=""):
        """
        Propose un échange.
        - proposer : utilisateur qui propose
        - target_item : article demandé
        - offered_item_ids : liste d'ids des articles proposés
        - message_content : message initial optionnel
        """
        if target_item.owner == proposer:
            raise ValueError("Vous ne pouvez pas échanger votre propre article.")

        if not target_item.available:
            raise ValueError("Cet article n'est plus disponible.")

        if not offered_item_ids:
            raise ValueError("Vous devez sélectionner au moins un article à proposer.")

        offered_items = Item.objects.filter(
            id__in=offered_item_ids,
            owner=proposer,
            available=True,
        )

        if not offered_items.exists():
            raise ValueError("Aucun article valide sélectionné.")

        trade = Trade.objects.create(
            proposer=proposer,
            receiver=target_item.owner,
            status="pending",
        )
        trade.offered_items.set(offered_items)
        trade.requested_items.set([target_item])
        trade.save()

        if message_content:
            Message.objects.create(
                trade=trade,
                sender=proposer,
                content=message_content,
            )

        create_notification(
            user=target_item.owner,
            notif_type="trade_received",
            message_text=f"{proposer.username} vous propose un échange pour « {target_item.title} ».",
            trade=trade,
        )

        return trade

    @staticmethod
    def accept_trade(trade, receiver):
        """
        Accepte un échange.
        - trade : l'échange à accepter
        - receiver : utilisateur qui accepte (doit être le destinataire)
        """
        if trade.receiver != receiver:
            raise PermissionError("Seul le destinataire peut accepter cet échange.")

        if trade.status != "pending":
            raise ValueError(f"Impossible d'accepter un échange avec le statut '{trade.status}'.")

        trade.status = "accepted"
        trade.save()

        # Marquer les articles indisponibles
        for item in list(trade.offered_items.all()) + list(trade.requested_items.all()):
            item.available = False
            item.save()

        # Annuler les échanges conflictuels
        TradeCommandService._cancel_conflicting_trades(trade)

        create_notification(
            user=trade.proposer,
            notif_type="trade_accepted",
            message_text=f"{receiver.username} a accepté votre échange #{trade.id} ! Choisissez le mode de livraison.",
            trade=trade,
        )

        return trade

    @staticmethod
    def refuse_trade(trade, receiver):
        """
        Refuse un échange.
        - trade : l'échange à refuser
        - receiver : utilisateur qui refuse (doit être le destinataire)
        """
        if trade.receiver != receiver:
            raise PermissionError("Seul le destinataire peut refuser cet échange.")

        if trade.status != "pending":
            raise ValueError(f"Impossible de refuser un échange avec le statut '{trade.status}'.")

        trade.status = "refused"
        trade.save()

        create_notification(
            user=trade.proposer,
            notif_type="trade_refused",
            message_text=f"{receiver.username} a refusé votre échange #{trade.id}.",
            trade=trade,
        )

        return trade

    @staticmethod
    def cancel_trade(trade, proposer):
        """
        Annule un échange pending.
        - trade : l'échange à annuler
        - proposer : utilisateur qui annule (doit être le proposeur)
        """
        if trade.proposer != proposer:
            raise PermissionError("Seul le proposeur peut annuler cet échange.")

        if trade.status != "pending":
            raise ValueError(f"Impossible d'annuler un échange avec le statut '{trade.status}'.")

        trade.status = "cancelled"
        trade.save()

        create_notification(
            user=trade.receiver,
            notif_type="trade_cancelled",
            message_text=f"{proposer.username} a annulé sa proposition d'échange #{trade.id}.",
            trade=trade,
        )

        return trade

    @staticmethod
    def cancel_accepted_trade(trade, proposer):
        """
        Annule un échange accepté dans les 24h.
        - trade : l'échange à annuler
        - proposer : utilisateur qui annule (doit être le proposeur)
        """
        if trade.proposer != proposer:
            raise PermissionError("Seul le proposeur peut annuler cet échange.")

        if trade.status != "accepted":
            raise ValueError("Seul un échange accepté peut être annulé via cette action.")

        deadline = trade.updated_at + datetime.timedelta(hours=24)
        if timezone.now() > deadline:
            raise ValueError("Le délai de 24h pour annuler est dépassé.")

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
            message_text=f"{proposer.username} a annulé l'échange #{trade.id} après acceptation.",
            trade=trade,
        )

        return trade

    @staticmethod
    def send_message(trade, sender, content):
        """
        Envoie un message dans un échange.
        - trade : l'échange concerné
        - sender : utilisateur qui envoie
        - content : contenu du message
        """
        if sender not in [trade.proposer, trade.receiver]:
            raise PermissionError("Vous ne participez pas à cet échange.")

        if not content.strip():
            raise ValueError("Le message ne peut pas être vide.")

        message = Message.objects.create(
            trade=trade,
            sender=sender,
            content=content,
        )

        other_user = trade.receiver if sender == trade.proposer else trade.proposer
        create_notification(
            user=other_user,
            notif_type="message_received",
            message_text=f"{sender.username} vous a envoyé un message sur l'échange #{trade.id}.",
            trade=trade,
        )

        return message

    @staticmethod
    def set_delivery(trade, proposer, delivery_mode, delivery_info):
        """
        Définit le mode de livraison.
        - trade : l'échange concerné
        - proposer : utilisateur qui définit (doit être le proposeur)
        - delivery_mode : mode choisi (hand, post, other)
        - delivery_info : informations complémentaires
        """
        if trade.proposer != proposer:
            raise PermissionError("Seul le proposeur peut définir le mode de livraison.")

        if trade.status != "accepted":
            raise ValueError("Le mode de livraison ne peut être défini que sur un échange accepté.")

        if not delivery_mode:
            raise ValueError("Veuillez choisir un mode de livraison.")

        if not delivery_info.strip():
            raise ValueError("Veuillez renseigner les informations de livraison.")

        trade.delivery_mode = delivery_mode
        trade.delivery_info = delivery_info
        trade.save()

        create_notification(
            user=trade.receiver,
            notif_type="delivery_set",
            message_text=f"{proposer.username} a proposé le mode « {trade.get_delivery_mode_display()} » pour l'échange #{trade.id}.",
            trade=trade,
        )

        return trade

    @staticmethod
    def confirm_delivery(trade, receiver):
        """
        Confirme la livraison et finalise l'échange.
        - trade : l'échange à finaliser
        - receiver : utilisateur qui confirme (doit être le destinataire)
        """
        if trade.receiver != receiver:
            raise PermissionError("Seul le destinataire peut confirmer la livraison.")

        if trade.status != "accepted":
            raise ValueError("Seul un échange accepté peut être confirmé.")

        if not trade.delivery_mode:
            raise ValueError("Le mode de livraison n'a pas encore été défini.")

        trade.status = "completed"
        trade.save()

        # Transférer la propriété des articles
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
            message_text=f"{receiver.username} a confirmé la livraison. L'échange #{trade.id} est terminé !",
            trade=trade,
        )

        return trade

    @staticmethod
    def rate_trade(trade, rater, score, comment=""):
        """
        Note un échange terminé.
        - trade : l'échange à noter
        - rater : utilisateur qui note
        - score : note de 1 à 5
        - comment : commentaire optionnel
        """
        if rater not in [trade.proposer, trade.receiver]:
            raise PermissionError("Vous ne participez pas à cet échange.")

        if trade.status != "completed":
            raise ValueError("Seul un échange terminé peut être noté.")

        if Rating.objects.filter(trade=trade, rater=rater).exists():
            raise ValueError("Vous avez déjà noté cet échange.")

        if not isinstance(score, int) or not (1 <= score <= 5):
            raise ValueError("La note doit être un entier entre 1 et 5.")

        rated_user = trade.receiver if rater == trade.proposer else trade.proposer

        rating = Rating.objects.create(
            trade=trade,
            rater=rater,
            rated_user=rated_user,
            score=score,
            comment=comment,
        )

        create_notification(
            user=rated_user,
            notif_type="rating_received",
            message_text=f"{rater.username} vous a laissé une note de {score}/5.",
            trade=trade,
        )

        return rating

    @staticmethod
    def toggle_item_availability(item, owner):
        """
        Bascule la disponibilité d'un article reçu par échange.
        - item : l'article à modifier
        - owner : utilisateur propriétaire
        """
        if item.owner != owner:
            raise PermissionError("Vous n'êtes pas le propriétaire de cet article.")

        if not item.received_by_trade:
            raise ValueError("Seuls les articles reçus par échange peuvent être basculés.")

        item.available = not item.available
        item.save()

        return item

    @staticmethod
    def _cancel_conflicting_trades(accepted_trade):
        """Annule tous les échanges pending conflictuels."""
        from django.db.models import Q
        all_items = (
            list(accepted_trade.offered_items.all()) +
            list(accepted_trade.requested_items.all())
        )
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