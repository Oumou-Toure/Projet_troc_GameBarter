import datetime
import pytest
from decimal import Decimal
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from exchange_mvp.models import Item, Trade, Message, Rating, Notification
from exchange_mvp.services.command_service import TradeCommandService
from exchange_mvp.services.query_service import TradeQueryService


# =======================
# FIXTURES
# =======================

IMAGE_BYTES = (
    b"GIF87a\x01\x00\x01\x00\x80\x00\x00"
    b"\x00\x00\x00\xff\xff\xff!\xf9\x04\x01"
    b"\x00\x00\x00\x00,\x00\x00\x00\x00\x01"
    b"\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


@pytest.fixture
def make_item(db):
    def _make(title, owner, category, available=True, received_by_trade=False,
              condition="good", platform="other", estimated_value=None, release_year=None):
        return Item.objects.create(
            title=title,
            description=f"Description de {title}",
            owner=owner,
            category=category,
            available=available,
            received_by_trade=received_by_trade,
            condition=condition,
            platform=platform,
            estimated_value=estimated_value,
            release_year=release_year,
            image=SimpleUploadedFile(
                f"{title}.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )
    return _make


# =======================
# TESTS COMMAND SERVICE
# =======================

class TestProposeTradeCommand:

    @pytest.mark.django_db
    def test_propose_trade_creates_trade(
        self, create_user, create_category, make_item
    ):
        proposer = create_user("cmd_proposer")
        receiver = create_user("cmd_receiver")
        category = create_category("Action")
        target = make_item("Zelda", receiver, category)
        offered = make_item("Mario", proposer, category)

        trade, _ = TradeCommandService.propose_trade(
            proposer=proposer,
            target_item=target,
            offered_item_ids=[offered.id],
            message_content="Échange rapide ?",
        )

        assert trade.status == "pending"
        assert trade.proposer == proposer
        assert trade.receiver == receiver
        assert target in trade.requested_items.all()
        assert offered in trade.offered_items.all()

    @pytest.mark.django_db
    def test_propose_trade_creates_message_if_content(
        self, create_user, create_category, make_item
    ):
        proposer = create_user("msg_proposer")
        receiver = create_user("msg_receiver")
        category = create_category("RPG")
        target = make_item("Dark Souls", receiver, category)
        offered = make_item("Elden Ring", proposer, category)

        trade, _ = TradeCommandService.propose_trade(
            proposer=proposer,
            target_item=target,
            offered_item_ids=[offered.id],
            message_content="Je suis intéressé !",
        )

        assert Message.objects.filter(
            trade=trade, content__icontains="intéressé"
        ).exists()

    @pytest.mark.django_db
    def test_propose_trade_creates_notification(
        self, create_user, create_category, make_item
    ):
        proposer = create_user("notif_prop")
        receiver = create_user("notif_recv")
        category = create_category("Sport")
        target = make_item("FIFA", receiver, category)
        offered = make_item("NBA 2K", proposer, category)

        trade, _ = TradeCommandService.propose_trade(
            proposer=proposer,
            target_item=target,
            offered_item_ids=[offered.id],
        )

        assert Notification.objects.filter(
            user=receiver,
            trade=trade,
            notif_type="trade_received",
        ).exists()

    @pytest.mark.django_db
    def test_propose_trade_raises_if_own_item(
        self, create_user, create_category, make_item
    ):
        user = create_user("own_item_user")
        category = create_category("Aventure")
        own_item = make_item("Mon jeu", user, category)
        other_item = make_item("Autre jeu", user, category)

        with pytest.raises(ValueError, match="propre article"):
            TradeCommandService.propose_trade(
                proposer=user,
                target_item=own_item,
                offered_item_ids=[other_item.id],
            )

    @pytest.mark.django_db
    def test_propose_trade_raises_if_item_unavailable(
        self, create_user, create_category, make_item
    ):
        proposer = create_user("unavail_prop")
        receiver = create_user("unavail_recv")
        category = create_category("FPS")
        target = make_item("COD", receiver, category, available=False)
        offered = make_item("Battlefield", proposer, category)

        with pytest.raises(ValueError, match="disponible"):
            TradeCommandService.propose_trade(
                proposer=proposer,
                target_item=target,
                offered_item_ids=[offered.id],
            )

    @pytest.mark.django_db
    def test_propose_trade_raises_if_no_offered_items(
        self, create_user, create_category, make_item
    ):
        proposer = create_user("no_offer_prop")
        receiver = create_user("no_offer_recv")
        category = create_category("Puzzle")
        target = make_item("Tetris", receiver, category)

        with pytest.raises(ValueError, match="au moins un article"):
            TradeCommandService.propose_trade(
                proposer=proposer,
                target_item=target,
                offered_item_ids=[],
            )


class TestAcceptTradeCommand:

    @pytest.mark.django_db
    def test_accept_trade_changes_status(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("accept_prop")
        receiver = create_user("accept_recv")
        category = create_category("Nintendo")
        offered = make_item("Kirby", proposer, category)
        requested = make_item("Pikmin", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        TradeCommandService.accept_trade(trade, receiver)

        trade.refresh_from_db()
        assert trade.status == "accepted"

    @pytest.mark.django_db
    def test_accept_trade_marks_items_unavailable(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("accept_items_prop")
        receiver = create_user("accept_items_recv")
        category = create_category("Sega")
        offered = make_item("Sonic", proposer, category)
        requested = make_item("Knuckles", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        TradeCommandService.accept_trade(trade, receiver)

        offered.refresh_from_db()
        requested.refresh_from_db()
        assert offered.available is False
        assert requested.available is False

    @pytest.mark.django_db
    def test_accept_trade_notifies_proposer(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("accept_notif_prop")
        receiver = create_user("accept_notif_recv")
        category = create_category("Atari")
        offered = make_item("Pong", proposer, category)
        requested = make_item("Asteroids", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        TradeCommandService.accept_trade(trade, receiver)

        assert Notification.objects.filter(
            user=proposer,
            trade=trade,
            notif_type="trade_accepted",
        ).exists()

    @pytest.mark.django_db
    def test_accept_trade_raises_if_not_receiver(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("wrong_accept_prop")
        receiver = create_user("wrong_accept_recv")
        category = create_category("Mobile")
        offered = make_item("Clash", proposer, category)
        requested = make_item("Brawl", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        with pytest.raises(PermissionError):
            TradeCommandService.accept_trade(trade, proposer)

    @pytest.mark.django_db
    def test_accept_trade_raises_if_not_pending(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("status_prop")
        receiver = create_user("status_recv")
        category = create_category("VR")
        offered = make_item("Beat Saber", proposer, category)
        requested = make_item("Alyx", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested], status="refused"
        )

        with pytest.raises(ValueError):
            TradeCommandService.accept_trade(trade, receiver)


class TestRefuseTradeCommand:

    @pytest.mark.django_db
    def test_refuse_trade_changes_status(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("refuse_prop")
        receiver = create_user("refuse_recv")
        category = create_category("PC")
        offered = make_item("Hades", proposer, category)
        requested = make_item("Hollow Knight", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        TradeCommandService.refuse_trade(trade, receiver)

        trade.refresh_from_db()
        assert trade.status == "refused"

    @pytest.mark.django_db
    def test_refuse_trade_notifies_proposer(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("refuse_notif_prop")
        receiver = create_user("refuse_notif_recv")
        category = create_category("Indie")
        offered = make_item("Celeste", proposer, category)
        requested = make_item("Ori", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        TradeCommandService.refuse_trade(trade, receiver)

        assert Notification.objects.filter(
            user=proposer,
            trade=trade,
            notif_type="trade_refused",
        ).exists()

    @pytest.mark.django_db
    def test_refuse_trade_raises_if_not_receiver(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("refuse_wrong_prop")
        receiver = create_user("refuse_wrong_recv")
        category = create_category("Retro")
        offered = make_item("Contra", proposer, category)
        requested = make_item("Castlevania", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        with pytest.raises(PermissionError):
            TradeCommandService.refuse_trade(trade, proposer)


class TestCancelTradeCommand:

    @pytest.mark.django_db
    def test_cancel_pending_trade(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("cancel_prop")
        receiver = create_user("cancel_recv")
        category = create_category("Fighting")
        offered = make_item("Street Fighter", proposer, category)
        requested = make_item("Mortal Kombat", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        TradeCommandService.cancel_trade(trade, proposer)

        trade.refresh_from_db()
        assert trade.status == "cancelled"

    @pytest.mark.django_db
    def test_cancel_accepted_trade_within_24h(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("cancel24_prop")
        receiver = create_user("cancel24_recv")
        category = create_category("Simulation")
        offered = make_item("The Sims", proposer, category)
        requested = make_item("Cities Skylines", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested], status="accepted"
        )

        TradeCommandService.cancel_accepted_trade(trade, proposer)

        trade.refresh_from_db()
        offered.refresh_from_db()
        requested.refresh_from_db()
        assert trade.status == "cancelled"
        assert offered.available is True
        assert requested.available is True

    @pytest.mark.django_db
    def test_cancel_accepted_trade_after_24h_raises(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("late_cancel_prop")
        receiver = create_user("late_cancel_recv")
        category = create_category("Strategy")
        offered = make_item("Civilization", proposer, category)
        requested = make_item("Age of Empires", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested], status="accepted"
        )
        Trade.objects.filter(id=trade.id).update(
            updated_at=timezone.now() - datetime.timedelta(hours=25)
        )
        trade.refresh_from_db()

        with pytest.raises(ValueError, match="24h"):
            TradeCommandService.cancel_accepted_trade(trade, proposer)


class TestSendMessageCommand:

    @pytest.mark.django_db
    def test_send_message_creates_message(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("msg_send_prop")
        receiver = create_user("msg_send_recv")
        category = create_category("Horror")
        offered = make_item("Resident Evil", proposer, category)
        requested = make_item("Silent Hill", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        message = TradeCommandService.send_message(
            trade, proposer, "Disponible ce weekend ?"
        )

        assert message.content == "Disponible ce weekend ?"
        assert message.sender == proposer

    @pytest.mark.django_db
    def test_send_message_notifies_other_party(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("msg_notif_prop")
        receiver = create_user("msg_notif_recv")
        category = create_category("Shoot")
        offered = make_item("Doom", proposer, category)
        requested = make_item("Quake", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        TradeCommandService.send_message(trade, proposer, "Hello !")

        assert Notification.objects.filter(
            user=receiver,
            trade=trade,
            notif_type="message_received",
        ).exists()

    @pytest.mark.django_db
    def test_send_empty_message_raises(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("empty_msg_prop")
        receiver = create_user("empty_msg_recv")
        category = create_category("Platformer")
        offered = make_item("Crash", proposer, category)
        requested = make_item("Spyro", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        with pytest.raises(ValueError, match="vide"):
            TradeCommandService.send_message(trade, proposer, "   ")


class TestSetDeliveryCommand:

    @pytest.mark.django_db
    def test_set_delivery_updates_trade(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("delivery_prop")
        receiver = create_user("delivery_recv")
        category = create_category("Racing")
        offered = make_item("Mario Kart", proposer, category)
        requested = make_item("F-Zero", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested], status="accepted"
        )

        TradeCommandService.set_delivery(
            trade, proposer, "hand", "Paris 15e, samedi à 14h"
        )

        trade.refresh_from_db()
        assert trade.delivery_mode == "hand"
        assert trade.delivery_info == "Paris 15e, samedi à 14h"

    @pytest.mark.django_db
    def test_set_delivery_raises_if_no_mode(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("no_mode_prop")
        receiver = create_user("no_mode_recv")
        category = create_category("MMO")
        offered = make_item("WoW", proposer, category)
        requested = make_item("FFXIV", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested], status="accepted"
        )

        with pytest.raises(ValueError, match="mode de livraison"):
            TradeCommandService.set_delivery(trade, proposer, "", "Paris")

    @pytest.mark.django_db
    def test_set_delivery_raises_if_no_info(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("no_info_prop")
        receiver = create_user("no_info_recv")
        category = create_category("Sandbox")
        offered = make_item("Minecraft", proposer, category)
        requested = make_item("Terraria", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested], status="accepted"
        )

        with pytest.raises(ValueError, match="informations"):
            TradeCommandService.set_delivery(trade, proposer, "post", "   ")


class TestConfirmDeliveryCommand:

    @pytest.mark.django_db
    def test_confirm_delivery_completes_trade(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("confirm_prop")
        receiver = create_user("confirm_recv")
        category = create_category("Adventure")
        offered = make_item("Uncharted", proposer, category)
        requested = make_item("Tomb Raider", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested],
            status="accepted",
            delivery_mode="post",
            delivery_info="10 rue de la Paix",
        )

        TradeCommandService.confirm_delivery(trade, receiver)

        trade.refresh_from_db()
        assert trade.status == "completed"

    @pytest.mark.django_db
    def test_confirm_delivery_transfers_ownership(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("transfer_prop")
        receiver = create_user("transfer_recv")
        category = create_category("JRPG")
        offered = make_item("Persona", proposer, category)
        requested = make_item("Dragon Quest", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested],
            status="accepted",
            delivery_mode="hand",
            delivery_info="Gare du Nord",
        )

        TradeCommandService.confirm_delivery(trade, receiver)

        offered.refresh_from_db()
        requested.refresh_from_db()
        assert offered.owner == receiver
        assert requested.owner == proposer
        assert offered.received_by_trade is True
        assert requested.received_by_trade is True

    @pytest.mark.django_db
    def test_confirm_delivery_raises_if_no_delivery_mode(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("no_delivery_prop")
        receiver = create_user("no_delivery_recv")
        category = create_category("Tactical")
        offered = make_item("XCOM", proposer, category)
        requested = make_item("Fire Emblem", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested], status="accepted"
        )

        with pytest.raises(ValueError, match="livraison"):
            TradeCommandService.confirm_delivery(trade, receiver)


class TestRateTradeCommand:

    @pytest.mark.django_db
    def test_rate_trade_creates_rating(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("rate_prop")
        receiver = create_user("rate_recv")
        category = create_category("Stealth")
        offered = make_item("Metal Gear", proposer, category)
        requested = make_item("Hitman", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested],
            status="completed",
            delivery_mode="post",
            delivery_info="Adresse test",
        )

        rating = TradeCommandService.rate_trade(trade, proposer, 5, "Super échange !")

        assert rating.score == 5
        assert rating.rater == proposer
        assert rating.rated_user == receiver

    @pytest.mark.django_db
    def test_rate_trade_raises_on_double_rating(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("double_rate_prop")
        receiver = create_user("double_rate_recv")
        category = create_category("Survival")
        offered = make_item("The Forest", proposer, category)
        requested = make_item("Green Hell", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested],
            status="completed",
            delivery_mode="other",
            delivery_info="Sur place",
        )

        TradeCommandService.rate_trade(trade, proposer, 4)

        with pytest.raises(ValueError, match="déjà noté"):
            TradeCommandService.rate_trade(trade, proposer, 3)

    @pytest.mark.django_db
    def test_rate_trade_raises_on_invalid_score(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("invalid_score_prop")
        receiver = create_user("invalid_score_recv")
        category = create_category("Music")
        offered = make_item("Guitar Hero", proposer, category)
        requested = make_item("Rock Band", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested],
            status="completed",
            delivery_mode="hand",
            delivery_info="Paris",
        )

        with pytest.raises(ValueError, match="entier entre 1 et 5"):
            TradeCommandService.rate_trade(trade, proposer, 6)


# =======================
# TESTS QUERY SERVICE
# =======================

class TestTradeQueryService:

    @pytest.mark.django_db
    def test_get_trades_for_user(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("query_prop")
        receiver = create_user("query_recv")
        other = create_user("query_other")
        category = create_category("Query")
        offered = make_item("Item A", proposer, category)
        requested = make_item("Item B", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        trades = TradeQueryService.get_trades_for_user(proposer)
        assert trade in trades

        trades_other = TradeQueryService.get_trades_for_user(other)
        assert trade not in trades_other

    @pytest.mark.django_db
    def test_get_pending_trades(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("pending_prop")
        receiver = create_user("pending_recv")
        category = create_category("Pending")
        offered = make_item("Item C", proposer, category)
        requested = make_item("Item D", receiver, category)
        pending_trade = create_trade(proposer, receiver, [offered], [requested])

        offered2 = make_item("Item E", proposer, category)
        requested2 = make_item("Item F", receiver, category)
        create_trade(
            proposer, receiver, [offered2], [requested2], status="completed"
        )

        pending = TradeQueryService.get_pending_trades(proposer)
        assert pending_trade in pending
        assert all(t.status == "pending" for t in pending)

    @pytest.mark.django_db
    def test_get_completed_trades(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("comp_prop")
        receiver = create_user("comp_recv")
        category = create_category("Completed")
        offered = make_item("Item G", proposer, category)
        requested = make_item("Item H", receiver, category)
        completed_trade = create_trade(
            proposer, receiver, [offered], [requested], status="completed"
        )

        completed = TradeQueryService.get_completed_trades(proposer)
        assert completed_trade in completed
        assert all(t.status == "completed" for t in completed)

    @pytest.mark.django_db
    def test_get_trades_for_item(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("item_query_prop")
        receiver = create_user("item_query_recv")
        category = create_category("ItemQuery")
        offered = make_item("Item I", proposer, category)
        requested = make_item("Item J", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        trades = TradeQueryService.get_trades_for_item(requested)
        assert trade in trades

    @pytest.mark.django_db
    def test_get_average_rating(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("avg_prop")
        receiver = create_user("avg_recv")
        category = create_category("Rating")
        offered = make_item("Item K", proposer, category)
        requested = make_item("Item L", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested],
            status="completed",
            delivery_mode="post",
            delivery_info="Adresse",
        )
        Rating.objects.create(
            trade=trade,
            rater=proposer,
            rated_user=receiver,
            score=4,
        )

        avg = TradeQueryService.get_average_rating(receiver)
        assert avg == 4.0

    @pytest.mark.django_db
    def test_get_average_rating_no_ratings(self, create_user):
        user = create_user("no_rating_user")
        avg = TradeQueryService.get_average_rating(user)
        assert avg is None

    @pytest.mark.django_db
    def test_get_unread_notifications(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("unread_prop")
        receiver = create_user("unread_recv")
        category = create_category("Notif")
        offered = make_item("Item M", proposer, category)
        requested = make_item("Item N", receiver, category)
        trade = create_trade(proposer, receiver, [offered], [requested])

        Notification.objects.create(
            user=receiver,
            notif_type="trade_received",
            message="Nouvelle proposition",
            trade=trade,
            is_read=False,
        )
        Notification.objects.create(
            user=receiver,
            notif_type="message_received",
            message="Nouveau message",
            trade=trade,
            is_read=True,
        )

        unread = TradeQueryService.get_unread_notifications(receiver)
        assert unread.count() == 1
        assert all(not n.is_read for n in unread)

    @pytest.mark.django_db
    def test_get_available_items_excludes_user(
        self, create_user, create_category, make_item
    ):
        user = create_user("avail_user")
        other = create_user("avail_other")
        category = create_category("Available")
        own_item = make_item("Mon article", user, category)
        other_item = make_item("Autre article", other, category)

        items = TradeQueryService.get_available_items(exclude_user=user)
        assert other_item in items
        assert own_item not in items

    @pytest.mark.django_db
    def test_get_completed_trades_count(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("count_prop")
        receiver = create_user("count_recv")
        category = create_category("Count")

        for i in range(3):
            offered = make_item(f"Offered {i}", proposer, category)
            requested = make_item(f"Requested {i}", receiver, category)
            create_trade(
                proposer, receiver, [offered], [requested], status="completed"
            )

        offered_p = make_item("Pending offered", proposer, category)
        requested_p = make_item("Pending requested", receiver, category)
        create_trade(proposer, receiver, [offered_p], [requested_p])

        count = TradeQueryService.get_completed_trades_count(proposer)
        assert count == 3

    @pytest.mark.django_db
    def test_get_rated_trade_ids(
        self, create_user, create_category, make_item, create_trade
    ):
        proposer = create_user("rated_ids_prop")
        receiver = create_user("rated_ids_recv")
        category = create_category("Rated")
        offered = make_item("Item O", proposer, category)
        requested = make_item("Item P", receiver, category)
        trade = create_trade(
            proposer, receiver, [offered], [requested],
            status="completed",
            delivery_mode="hand",
            delivery_info="Lyon",
        )
        Rating.objects.create(
            trade=trade,
            rater=proposer,
            rated_user=receiver,
            score=5,
        )

        rated_ids = TradeQueryService.get_rated_trade_ids(proposer)
        assert trade.id in rated_ids


# =======================
# TESTS CRITÈRES DE VALEUR
# =======================

class TestValueCriteriaCommand:

    @pytest.mark.django_db
    def test_propose_trade_detects_value_imbalance(
        self, create_user, create_category
    ):
        proposer = create_user("imbalance_prop")
        receiver = create_user("imbalance_recv")
        category = create_category("Imbalance")

        target = Item.objects.create(
            title="Jeu cher",
            description="Valeur élevée",
            owner=receiver,
            category=category,
            available=True,
            estimated_value=Decimal("60.00"),
            platform="ps5",
            condition="new",
            image=SimpleUploadedFile(
                "cher.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )
        offered = Item.objects.create(
            title="Jeu pas cher",
            description="Valeur faible",
            owner=proposer,
            category=category,
            available=True,
            estimated_value=Decimal("10.00"),
            platform="ps5",
            condition="good",
            image=SimpleUploadedFile(
                "cheap.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )

        trade, imbalance_warning = TradeCommandService.propose_trade(
            proposer=proposer,
            target_item=target,
            offered_item_ids=[offered.id],
        )

        assert imbalance_warning is True
        assert trade.status == "pending"

    @pytest.mark.django_db
    def test_propose_trade_no_imbalance_when_balanced(
        self, create_user, create_category
    ):
        proposer = create_user("balanced_prop")
        receiver = create_user("balanced_recv")
        category = create_category("Balanced")

        target = Item.objects.create(
            title="Jeu A",
            description="Valeur normale",
            owner=receiver,
            category=category,
            available=True,
            estimated_value=Decimal("30.00"),
            platform="switch",
            condition="good",
            image=SimpleUploadedFile(
                "a.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )
        offered = Item.objects.create(
            title="Jeu B",
            description="Valeur similaire",
            owner=proposer,
            category=category,
            available=True,
            estimated_value=Decimal("25.00"),
            platform="switch",
            condition="good",
            image=SimpleUploadedFile(
                "b.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )

        trade, imbalance_warning = TradeCommandService.propose_trade(
            proposer=proposer,
            target_item=target,
            offered_item_ids=[offered.id],
        )

        assert imbalance_warning is False

    @pytest.mark.django_db
    def test_check_value_imbalance_query(self, create_user, create_category):
        user = create_user("check_imbalance_user")
        category = create_category("CheckImbalance")

        target = Item.objects.create(
            title="Target",
            description="Cible",
            owner=user,
            category=category,
            available=True,
            estimated_value=Decimal("60.00"),
            platform="ps5",
            condition="new",
            image=SimpleUploadedFile(
                "target.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )
        offered = Item.objects.create(
            title="Offered",
            description="Offert",
            owner=user,
            category=category,
            available=True,
            estimated_value=Decimal("10.00"),
            platform="ps5",
            condition="good",
            image=SimpleUploadedFile(
                "offered.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )

        assert TradeQueryService.check_value_imbalance([offered], target) is True

    @pytest.mark.django_db
    def test_get_items_by_platform(self, create_user, create_category):
        owner = create_user("platform_owner")
        category = create_category("PlatformTest")

        ps5_item = Item.objects.create(
            title="PS5 Game",
            description="Pour PS5",
            owner=owner,
            category=category,
            available=True,
            platform="ps5",
            condition="new",
            image=SimpleUploadedFile(
                "ps5.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )
        Item.objects.create(
            title="Switch Game",
            description="Pour Switch",
            owner=owner,
            category=category,
            available=True,
            platform="switch",
            condition="good",
            image=SimpleUploadedFile(
                "switch.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )

        ps5_items = TradeQueryService.get_items_by_platform("ps5")
        assert ps5_item in ps5_items
        assert all(i.platform == "ps5" for i in ps5_items)

    @pytest.mark.django_db
    def test_get_items_by_condition(self, create_user, create_category):
        owner = create_user("condition_owner")
        category = create_category("ConditionTest")

        new_item = Item.objects.create(
            title="Jeu Neuf",
            description="Tout neuf",
            owner=owner,
            category=category,
            available=True,
            platform="ps5",
            condition="new",
            image=SimpleUploadedFile(
                "new.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )
        Item.objects.create(
            title="Jeu Abimé",
            description="Abîmé",
            owner=owner,
            category=category,
            available=True,
            platform="ps5",
            condition="damaged",
            image=SimpleUploadedFile(
                "damaged.gif", IMAGE_BYTES, content_type="image/gif"
            ),
        )

        new_items = TradeQueryService.get_items_by_condition("new")
        assert new_item in new_items
        assert all(i.condition == "new" for i in new_items)