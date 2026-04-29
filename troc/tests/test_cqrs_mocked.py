import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from decimal import Decimal

from exchange_mvp.services.command_service import TradeCommandService
from exchange_mvp.services.query_service import TradeQueryService


# =======================
# TESTS AVEC MOCKS
# =======================

class TestProposeTradeCommandMocked:

    def test_propose_trade_raises_if_own_item(self):
        """Test sans DB — vérifie la règle métier uniquement."""
        proposer = MagicMock()
        proposer.username = "proposer"

        target_item = MagicMock()
        target_item.owner = proposer  # même utilisateur
        target_item.available = True

        with pytest.raises(ValueError, match="propre article"):
            TradeCommandService.propose_trade(
                proposer=proposer,
                target_item=target_item,
                offered_item_ids=[1],
            )

    def test_propose_trade_raises_if_unavailable(self):
        """Test sans DB — article indisponible."""
        proposer = MagicMock()
        receiver = MagicMock()

        target_item = MagicMock()
        target_item.owner = receiver
        target_item.available = False

        with pytest.raises(ValueError, match="disponible"):
            TradeCommandService.propose_trade(
                proposer=proposer,
                target_item=target_item,
                offered_item_ids=[1],
            )

    def test_propose_trade_raises_if_no_offered_items(self):
        """Test sans DB — aucun article proposé."""
        proposer = MagicMock()
        receiver = MagicMock()

        target_item = MagicMock()
        target_item.owner = receiver
        target_item.available = True

        with pytest.raises(ValueError, match="au moins un article"):
            TradeCommandService.propose_trade(
                proposer=proposer,
                target_item=target_item,
                offered_item_ids=[],
            )

    @patch("exchange_mvp.services.command_service.Item.objects.filter")
    @patch("exchange_mvp.services.command_service.Trade.objects.create")
    @patch("exchange_mvp.services.command_service.Notification.objects.create")
    def test_propose_trade_creates_notification(
        self, mock_notif_create, mock_trade_create, mock_item_filter
    ):
        """Test avec mocks — vérifie que la notification est créée."""
        proposer = MagicMock()
        proposer.username = "proposer"

        receiver = MagicMock()
        receiver.username = "receiver"

        target_item = MagicMock()
        target_item.owner = receiver
        target_item.available = True
        target_item.estimated_value = None
        target_item.title = "Jeu Test"

        # Mock des articles proposés
        mock_offered = MagicMock()
        mock_offered.estimated_value = None
        mock_queryset = MagicMock()
        mock_queryset.exists.return_value = True
        mock_queryset.__iter__ = MagicMock(return_value=iter([mock_offered]))
        mock_item_filter.return_value = mock_queryset

        # Mock du trade créé
        mock_trade = MagicMock()
        mock_trade_create.return_value = mock_trade

        TradeCommandService.propose_trade(
            proposer=proposer,
            target_item=target_item,
            offered_item_ids=[1],
        )

        # Vérifier que la notification a été créée
        mock_notif_create.assert_called_once()
        call_kwargs = mock_notif_create.call_args.kwargs
        assert call_kwargs["notif_type"] == "trade_received"
        assert call_kwargs["user"] == receiver

    @patch("exchange_mvp.services.command_service.Item.objects.filter")
    @patch("exchange_mvp.services.command_service.Trade.objects.create")
    @patch("exchange_mvp.services.command_service.Notification.objects.create")
    @patch("exchange_mvp.services.command_service.Message.objects.create")
    def test_propose_trade_creates_message_when_content_provided(
        self, mock_msg_create, mock_notif_create, mock_trade_create, mock_item_filter
    ):
        """Test avec mocks — vérifie que le message est créé si contenu."""
        proposer = MagicMock()
        proposer.username = "proposer"
        receiver = MagicMock()

        target_item = MagicMock()
        target_item.owner = receiver
        target_item.available = True
        target_item.estimated_value = None
        target_item.title = "Jeu"

        mock_offered = MagicMock()
        mock_offered.estimated_value = None
        mock_queryset = MagicMock()
        mock_queryset.exists.return_value = True
        mock_queryset.__iter__ = MagicMock(return_value=iter([mock_offered]))
        mock_item_filter.return_value = mock_queryset

        mock_trade = MagicMock()
        mock_trade_create.return_value = mock_trade

        TradeCommandService.propose_trade(
            proposer=proposer,
            target_item=target_item,
            offered_item_ids=[1],
            message_content="Bonjour !",
        )

        mock_msg_create.assert_called_once()

    @patch("exchange_mvp.services.command_service.Item.objects.filter")
    @patch("exchange_mvp.services.command_service.Trade.objects.create")
    @patch("exchange_mvp.services.command_service.Notification.objects.create")
    def test_propose_trade_no_message_when_no_content(
        self, mock_notif_create, mock_trade_create, mock_item_filter
    ):
        """Test avec mocks — pas de message si contenu vide."""
        proposer = MagicMock()
        proposer.username = "proposer"
        receiver = MagicMock()

        target_item = MagicMock()
        target_item.owner = receiver
        target_item.available = True
        target_item.estimated_value = None
        target_item.title = "Jeu"

        mock_offered = MagicMock()
        mock_offered.estimated_value = None
        mock_queryset = MagicMock()
        mock_queryset.exists.return_value = True
        mock_queryset.__iter__ = MagicMock(return_value=iter([mock_offered]))
        mock_item_filter.return_value = mock_queryset

        mock_trade = MagicMock()
        mock_trade_create.return_value = mock_trade

        with patch("exchange_mvp.services.command_service.Message.objects.create") as mock_msg:
            TradeCommandService.propose_trade(
                proposer=proposer,
                target_item=target_item,
                offered_item_ids=[1],
                message_content="",
            )
            mock_msg.assert_not_called()


class TestAcceptTradeCommandMocked:

    def test_accept_raises_if_not_receiver(self):
        """Test sans DB — vérifie la règle de permission."""
        proposer = MagicMock()
        receiver = MagicMock()
        wrong_user = MagicMock()

        trade = MagicMock()
        trade.receiver = receiver
        trade.status = "pending"

        with pytest.raises(PermissionError):
            TradeCommandService.accept_trade(trade, wrong_user)

    def test_accept_raises_if_not_pending(self):
        """Test sans DB — vérifie que seul un échange pending peut être accepté."""
        receiver = MagicMock()

        trade = MagicMock()
        trade.receiver = receiver
        trade.status = "refused"

        with pytest.raises(ValueError):
            TradeCommandService.accept_trade(trade, receiver)

    @patch("exchange_mvp.services.command_service.Notification.objects.create")
    def test_accept_trade_saves_and_notifies(self, mock_notif_create):
        """Test avec mock — vérifie save et notification."""
        proposer = MagicMock()
        proposer.username = "proposer"
        receiver = MagicMock()
        receiver.username = "receiver"

        trade = MagicMock()
        trade.receiver = receiver
        trade.proposer = proposer
        trade.status = "pending"
        trade.offered_items.all.return_value = []
        trade.requested_items.all.return_value = []

        with patch.object(TradeCommandService, "_cancel_conflicting_trades"):
            TradeCommandService.accept_trade(trade, receiver)

        trade.save.assert_called_once()
        assert trade.status == "accepted"
        mock_notif_create.assert_called_once()


class TestRefuseTradeCommandMocked:

    def test_refuse_raises_if_not_receiver(self):
        """Test sans DB."""
        proposer = MagicMock()
        receiver = MagicMock()

        trade = MagicMock()
        trade.receiver = receiver
        trade.status = "pending"

        with pytest.raises(PermissionError):
            TradeCommandService.refuse_trade(trade, proposer)

    def test_refuse_raises_if_not_pending(self):
        """Test sans DB."""
        receiver = MagicMock()

        trade = MagicMock()
        trade.receiver = receiver
        trade.status = "accepted"

        with pytest.raises(ValueError):
            TradeCommandService.refuse_trade(trade, receiver)

    @patch("exchange_mvp.services.command_service.Notification.objects.create")
    def test_refuse_trade_saves_and_notifies(self, mock_notif_create):
        """Test avec mock."""
        proposer = MagicMock()
        receiver = MagicMock()
        receiver.username = "receiver"

        trade = MagicMock()
        trade.receiver = receiver
        trade.proposer = proposer
        trade.status = "pending"

        TradeCommandService.refuse_trade(trade, receiver)

        trade.save.assert_called_once()
        assert trade.status == "refused"
        mock_notif_create.assert_called_once()
        call_kwargs = mock_notif_create.call_args.kwargs
        assert call_kwargs["notif_type"] == "trade_refused"
        assert call_kwargs["user"] == proposer


class TestSendMessageCommandMocked:

    def test_send_message_raises_if_not_participant(self):
        """Test sans DB."""
        proposer = MagicMock()
        receiver = MagicMock()
        outsider = MagicMock()

        trade = MagicMock()
        trade.proposer = proposer
        trade.receiver = receiver

        with pytest.raises(PermissionError):
            TradeCommandService.send_message(trade, outsider, "Bonjour")

    def test_send_message_raises_if_empty(self):
        """Test sans DB."""
        proposer = MagicMock()
        receiver = MagicMock()

        trade = MagicMock()
        trade.proposer = proposer
        trade.receiver = receiver

        with pytest.raises(ValueError, match="vide"):
            TradeCommandService.send_message(trade, proposer, "   ")

    @patch("exchange_mvp.services.command_service.Notification.objects.create")
    @patch("exchange_mvp.services.command_service.Message.objects.create")
    def test_send_message_creates_message_and_notifies(
        self, mock_msg_create, mock_notif_create
    ):
        """Test avec mocks."""
        proposer = MagicMock()
        proposer.username = "proposer"
        receiver = MagicMock()

        trade = MagicMock()
        trade.proposer = proposer
        trade.receiver = receiver
        trade.id = 1

        mock_message = MagicMock()
        mock_msg_create.return_value = mock_message

        result = TradeCommandService.send_message(trade, proposer, "Hello !")

        mock_msg_create.assert_called_once()
        mock_notif_create.assert_called_once()
        assert result == mock_message


class TestSetDeliveryCommandMocked:

    def test_set_delivery_raises_if_not_proposer(self):
        """Test sans DB."""
        proposer = MagicMock()
        receiver = MagicMock()

        trade = MagicMock()
        trade.proposer = proposer
        trade.status = "accepted"

        with pytest.raises(PermissionError):
            TradeCommandService.set_delivery(trade, receiver, "hand", "Paris")

    def test_set_delivery_raises_if_not_accepted(self):
        """Test sans DB."""
        proposer = MagicMock()

        trade = MagicMock()
        trade.proposer = proposer
        trade.status = "pending"

        with pytest.raises(ValueError):
            TradeCommandService.set_delivery(trade, proposer, "hand", "Paris")

    def test_set_delivery_raises_if_no_mode(self):
        """Test sans DB."""
        proposer = MagicMock()

        trade = MagicMock()
        trade.proposer = proposer
        trade.status = "accepted"

        with pytest.raises(ValueError, match="mode de livraison"):
            TradeCommandService.set_delivery(trade, proposer, "", "Paris")

    def test_set_delivery_raises_if_no_info(self):
        """Test sans DB."""
        proposer = MagicMock()

        trade = MagicMock()
        trade.proposer = proposer
        trade.status = "accepted"

        with pytest.raises(ValueError, match="informations"):
            TradeCommandService.set_delivery(trade, proposer, "hand", "   ")

    @patch("exchange_mvp.services.command_service.Notification.objects.create")
    def test_set_delivery_saves_and_notifies(self, mock_notif_create):
        """Test avec mock."""
        proposer = MagicMock()
        proposer.username = "proposer"
        receiver = MagicMock()

        trade = MagicMock()
        trade.proposer = proposer
        trade.receiver = receiver
        trade.status = "accepted"
        trade.id = 1
        trade.get_delivery_mode_display.return_value = "Remise en main propre"

        TradeCommandService.set_delivery(trade, proposer, "hand", "Paris 15e")

        trade.save.assert_called_once()
        assert trade.delivery_mode == "hand"
        assert trade.delivery_info == "Paris 15e"
        mock_notif_create.assert_called_once()


class TestRateTradeCommandMocked:

    def test_rate_raises_if_not_participant(self):
        """Test sans DB."""
        proposer = MagicMock()
        receiver = MagicMock()
        outsider = MagicMock()

        trade = MagicMock()
        trade.proposer = proposer
        trade.receiver = receiver
        trade.status = "completed"

        with pytest.raises(PermissionError):
            TradeCommandService.rate_trade(trade, outsider, 5)

    def test_rate_raises_if_not_completed(self):
        """Test sans DB."""
        proposer = MagicMock()
        receiver = MagicMock()

        trade = MagicMock()
        trade.proposer = proposer
        trade.receiver = receiver
        trade.status = "accepted"

        with pytest.raises(ValueError, match="terminé"):
            TradeCommandService.rate_trade(trade, proposer, 5)

    def test_rate_raises_if_invalid_score(self):
        """Test sans DB."""
        proposer = MagicMock()
        receiver = MagicMock()

        trade = MagicMock()
        trade.proposer = proposer
        trade.receiver = receiver
        trade.status = "completed"

        with patch("exchange_mvp.services.command_service.Rating.objects.filter") as mock_filter:
            mock_filter.return_value.exists.return_value = False
            with pytest.raises(ValueError, match="entier entre 1 et 5"):
                TradeCommandService.rate_trade(trade, proposer, 6)

    def test_rate_raises_if_already_rated(self):
        """Test sans DB."""
        proposer = MagicMock()
        receiver = MagicMock()

        trade = MagicMock()
        trade.proposer = proposer
        trade.receiver = receiver
        trade.status = "completed"

        with patch("exchange_mvp.services.command_service.Rating.objects.filter") as mock_filter:
            mock_filter.return_value.exists.return_value = True
            with pytest.raises(ValueError, match="déjà noté"):
                TradeCommandService.rate_trade(trade, proposer, 4)


class TestQueryServiceMocked:

    @patch("exchange_mvp.services.query_service.Trade.objects.filter")
    def test_get_trades_for_user_calls_filter(self, mock_filter):
        """Test avec mock — vérifie que le bon filtre est appliqué."""
        user = MagicMock()
        mock_queryset = MagicMock()
        mock_filter.return_value.order_by.return_value = mock_queryset

        result = TradeQueryService.get_trades_for_user(user)

        mock_filter.assert_called_once()
        assert result == mock_queryset

    @patch("exchange_mvp.services.query_service.Trade.objects.filter")
    def test_get_pending_trades_filters_by_status(self, mock_filter):
        """Test avec mock — vérifie le filtre sur status=pending."""
        user = MagicMock()
        mock_queryset = MagicMock()
        mock_filter.return_value.order_by.return_value = mock_queryset

        TradeQueryService.get_pending_trades(user)

        call_kwargs = mock_filter.call_args.kwargs
        assert call_kwargs.get("status") == "pending"

    @patch("exchange_mvp.services.query_service.Rating.objects.filter")
    def test_get_average_rating_returns_none_if_no_ratings(self, mock_filter):
        """Test avec mock — moyenne nulle si pas de notations."""
        user = MagicMock()
        mock_filter.return_value.aggregate.return_value = {"avg": None}

        result = TradeQueryService.get_average_rating(user)

        assert result is None

    @patch("exchange_mvp.services.query_service.Rating.objects.filter")
    def test_get_average_rating_returns_value(self, mock_filter):
        """Test avec mock — retourne la moyenne correcte."""
        user = MagicMock()
        mock_filter.return_value.aggregate.return_value = {"avg": 4.5}

        result = TradeQueryService.get_average_rating(user)

        assert result == 4.5

    @patch("exchange_mvp.services.query_service.Notification.objects.filter")
    def test_get_unread_notifications_filters_unread(self, mock_filter):
        """Test avec mock — vérifie le filtre is_read=False."""
        user = MagicMock()
        mock_queryset = MagicMock()
        mock_filter.return_value.order_by.return_value = mock_queryset

        TradeQueryService.get_unread_notifications(user)

        call_kwargs = mock_filter.call_args.kwargs
        assert call_kwargs.get("is_read") is False

    @patch("exchange_mvp.services.query_service.Item.objects.filter")
    def test_get_available_items_filters_available(self, mock_filter):
        """Test avec mock — vérifie le filtre available=True."""
        mock_queryset = MagicMock()
        mock_filter.return_value.select_related.return_value = mock_queryset

        TradeQueryService.get_available_items()

        call_kwargs = mock_filter.call_args.kwargs
        assert call_kwargs.get("available") is True

    @patch("exchange_mvp.services.query_service.Trade.objects.filter")
    def test_get_completed_trades_count_filters_completed(self, mock_filter):
        """Test avec mock — vérifie le filtre status=completed."""
        user = MagicMock()
        mock_filter.return_value.count.return_value = 5

        result = TradeQueryService.get_completed_trades_count(user)

        call_kwargs = mock_filter.call_args.kwargs
        assert call_kwargs.get("status") == "completed"
        assert result == 5

    @patch("exchange_mvp.services.query_service.Item.objects.filter")
    def test_get_items_by_platform_filters_correctly(self, mock_filter):
        """Test avec mock — vérifie le filtre par plateforme."""
        mock_queryset = MagicMock()
        mock_filter.return_value.select_related.return_value = mock_queryset

        TradeQueryService.get_items_by_platform("ps5")

        call_kwargs = mock_filter.call_args.kwargs
        assert call_kwargs.get("platform") == "ps5"
        assert call_kwargs.get("available") is True

    @patch("exchange_mvp.services.query_service.Item.objects.filter")
    def test_get_items_by_condition_filters_correctly(self, mock_filter):
        """Test avec mock — vérifie le filtre par état."""
        mock_queryset = MagicMock()
        mock_filter.return_value.select_related.return_value = mock_queryset

        TradeQueryService.get_items_by_condition("new")

        call_kwargs = mock_filter.call_args.kwargs
        assert call_kwargs.get("condition") == "new"
        assert call_kwargs.get("available") is True