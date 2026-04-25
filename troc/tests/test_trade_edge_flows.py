from datetime import timedelta

import pytest
from django.utils import timezone

from exchange_mvp.models import Message, Notification, Rating, Trade


def _set_hidden_control(page, selector):
    page.locator(selector).evaluate(
        """(element) => {
            element.checked = true;
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )


def _accept_trade(page, base_url, trade_id):
    page.goto(f"{base_url}/my-trades/")
    page.click(f'form[action="/trade/{trade_id}/action/"] button[value="accept"]')
    page.wait_for_url(f"{base_url}/my-trades/")


@pytest.mark.django_db
def test_trade_can_be_refused_and_notifies_proposer(
    django_live_server,
    create_user,
    create_category,
    create_item,
    create_trade,
    login_user,
):
    proposer = create_user("refuse_proposer")
    receiver = create_user("refuse_receiver")
    category = create_category("PS4")
    offered_item = create_item("Bloodborne", "Goty", proposer, category)
    requested_item = create_item("Uncharted 4", "Aventure", receiver, category)
    trade = create_trade(
        proposer=proposer,
        receiver=receiver,
        offered_items=[offered_item],
        requested_items=[requested_item],
    )

    session = login_user(receiver)
    page = session["page"]
    page.goto(f"{django_live_server.url}/my-trades/")
    page.click(f'form[action="/trade/{trade.id}/action/"] button[value="refuse"]')
    page.wait_for_url(f"{django_live_server.url}/my-trades/")

    trade.refresh_from_db()
    assert trade.status == "refused"
    assert Notification.objects.filter(
        user=proposer,
        trade=trade,
        notif_type="trade_refused",
    ).exists()
    assert page.get_by_text("Refusé", exact=True).is_visible()

    session["context"].close()


@pytest.mark.django_db
def test_proposer_can_cancel_pending_trade_and_receiver_is_notified(
    django_live_server,
    create_user,
    create_category,
    create_item,
    create_trade,
    login_user,
):
    proposer = create_user("cancel_pending_proposer")
    receiver = create_user("cancel_pending_receiver")
    category = create_category("Xbox")
    offered_item = create_item("Halo Infinite", "Boite incluse", proposer, category)
    requested_item = create_item("Forza Horizon 5", "Excellent etat", receiver, category)
    trade = create_trade(
        proposer=proposer,
        receiver=receiver,
        offered_items=[offered_item],
        requested_items=[requested_item],
    )

    session = login_user(proposer)
    page = session["page"]
    page.goto(f"{django_live_server.url}/my-trades/")
    page.once("dialog", lambda dialog: dialog.accept())
    page.click(f'form[action="/trade/{trade.id}/action/"] button[value="cancel"]')
    page.wait_for_url(f"{django_live_server.url}/my-trades/")

    trade.refresh_from_db()
    assert trade.status == "cancelled"
    assert Notification.objects.filter(
        user=receiver,
        trade=trade,
        notif_type="trade_cancelled",
    ).exists()
    assert page.get_by_text("Échange annulé.", exact=True).is_visible()

    session["context"].close()


@pytest.mark.django_db
def test_proposer_can_cancel_accepted_trade_within_24_hours(
    django_live_server,
    create_user,
    create_category,
    create_item,
    create_trade,
    login_user,
):
    proposer = create_user("cancel_accepted_proposer")
    receiver = create_user("cancel_accepted_receiver")
    category = create_category("PC")
    offered_item = create_item("Hades", "Version Steam", proposer, category)
    requested_item = create_item("Baldur Gate 3", "Code fourni", receiver, category)
    trade = create_trade(
        proposer=proposer,
        receiver=receiver,
        offered_items=[offered_item],
        requested_items=[requested_item],
    )

    receiver_session = login_user(receiver)
    _accept_trade(receiver_session["page"], django_live_server.url, trade.id)

    proposer_session = login_user(proposer)
    proposer_page = proposer_session["page"]
    proposer_page.goto(f"{django_live_server.url}/my-trades/")
    proposer_page.once("dialog", lambda dialog: dialog.accept())
    proposer_page.click(f'form[action="/trade/{trade.id}/action/"] button[value="cancel_accepted"]')
    proposer_page.wait_for_url(f"{django_live_server.url}/my-trades/")

    trade.refresh_from_db()
    offered_item.refresh_from_db()
    requested_item.refresh_from_db()
    assert trade.status == "cancelled"
    assert offered_item.available is True
    assert requested_item.available is True
    assert Notification.objects.filter(
        user=receiver,
        trade=trade,
        notif_type="trade_cancelled",
    ).exists()

    proposer_session["context"].close()
    receiver_session["context"].close()


@pytest.mark.django_db
def test_cannot_cancel_accepted_trade_after_24_hours(
    django_live_server,
    create_user,
    create_category,
    create_item,
    create_trade,
    login_user,
):
    proposer = create_user("late_cancel_proposer")
    receiver = create_user("late_cancel_receiver")
    category = create_category("VR")
    offered_item = create_item("Beat Saber", "Casque propre", proposer, category)
    requested_item = create_item("Half Life Alyx", "Version physique", receiver, category)
    trade = create_trade(
        proposer=proposer,
        receiver=receiver,
        offered_items=[offered_item],
        requested_items=[requested_item],
    )

    receiver_session = login_user(receiver)
    _accept_trade(receiver_session["page"], django_live_server.url, trade.id)
    Trade.objects.filter(id=trade.id).update(updated_at=timezone.now() - timedelta(hours=25))

    proposer_session = login_user(proposer)
    proposer_page = proposer_session["page"]
    proposer_page.goto(f"{django_live_server.url}/my-trades/")
    proposer_page.once("dialog", lambda dialog: dialog.accept())
    proposer_page.click(f'form[action="/trade/{trade.id}/action/"] button[value="cancel_accepted"]')
    proposer_page.wait_for_url(f"{django_live_server.url}/my-trades/")

    trade.refresh_from_db()
    assert trade.status == "accepted"
    assert proposer_page.get_by_text("Le délai de 24h pour annuler est dépassé.", exact=True).is_visible()

    proposer_session["context"].close()
    receiver_session["context"].close()


@pytest.mark.django_db
def test_accepting_trade_cancels_conflicting_pending_trade(
    django_live_server,
    create_user,
    create_category,
    create_item,
    create_trade,
    login_user,
):
    receiver = create_user("conflict_receiver")
    proposer_one = create_user("conflict_sender_one")
    proposer_two = create_user("conflict_sender_two")
    category = create_category("Retro")
    requested_item = create_item("Chrono Trigger", "SNES", receiver, category)
    offered_one = create_item("Secret of Mana", "SNES", proposer_one, category)
    offered_two = create_item("Illusion of Time", "SNES", proposer_two, category)

    accepted_trade = create_trade(
        proposer=proposer_one,
        receiver=receiver,
        offered_items=[offered_one],
        requested_items=[requested_item],
    )
    cancelled_trade = create_trade(
        proposer=proposer_two,
        receiver=receiver,
        offered_items=[offered_two],
        requested_items=[requested_item],
    )

    receiver_session = login_user(receiver)
    _accept_trade(receiver_session["page"], django_live_server.url, accepted_trade.id)

    accepted_trade.refresh_from_db()
    cancelled_trade.refresh_from_db()
    assert accepted_trade.status == "accepted"
    assert cancelled_trade.status == "cancelled"
    assert Notification.objects.filter(
        user=proposer_two,
        trade=cancelled_trade,
        notif_type="trade_cancelled",
    ).exists()

    second_session = login_user(proposer_two)
    second_page = second_session["page"]
    second_page.goto(f"{django_live_server.url}/my-trades/")
    assert second_page.locator("text=Annul").is_visible()

    second_session["context"].close()
    receiver_session["context"].close()


@pytest.mark.django_db
def test_users_can_send_messages_during_trade_negotiation(
    django_live_server,
    create_user,
    create_category,
    create_item,
    create_trade,
    login_user,
):
    proposer = create_user("message_proposer")
    receiver = create_user("message_receiver")
    category = create_category("Wii")
    offered_item = create_item("Mario Galaxy", "Complet", proposer, category)
    requested_item = create_item("Zelda Skyward Sword", "Boitier bleu", receiver, category)
    trade = create_trade(
        proposer=proposer,
        receiver=receiver,
        offered_items=[offered_item],
        requested_items=[requested_item],
    )

    session = login_user(receiver)
    page = session["page"]
    page.goto(f"{django_live_server.url}/my-trades/")
    page.fill(f'form[action="/trade/{trade.id}/action/"] input[name="message"]', "Ca m'interesse, disponible demain ?")
    page.click(f'form[action="/trade/{trade.id}/action/"] button[value="message"]')
    page.wait_for_url(f"{django_live_server.url}/my-trades/")

    assert Message.objects.filter(trade=trade, sender=receiver, content__icontains="demain").exists()
    assert Notification.objects.filter(
        user=proposer,
        trade=trade,
        notif_type="message_received",
    ).exists()
    assert page.locator("text=disponible demain").is_visible()

    session["context"].close()


@pytest.mark.django_db
def test_create_trade_requires_selecting_at_least_one_offered_item(
    django_live_server,
    create_user,
    create_category,
    create_item,
    login_user,
):
    proposer = create_user("empty_offer_proposer")
    receiver = create_user("empty_offer_receiver")
    category = create_category("PS3")
    target_item = create_item("The Last of Us", "Edition steelbook", receiver, category)
    create_item("Heavy Rain", "Bon etat", proposer, category)

    session = login_user(proposer)
    page = session["page"]
    page.goto(f"{django_live_server.url}/trade/create/{target_item.id}/")
    page.click('button[type="submit"]')

    assert page.locator("text=/[Ss][ée]lectionner au moins un article/").is_visible()
    assert Trade.objects.count() == 0

    session["context"].close()


@pytest.mark.django_db
def test_delivery_form_requires_mode_and_information(
    django_live_server,
    create_user,
    create_category,
    create_item,
    create_trade,
    login_user,
):
    proposer = create_user("delivery_proposer")
    receiver = create_user("delivery_receiver")
    category = create_category("GameCube")
    offered_item = create_item("F-Zero GX", "Notice incluse", proposer, category)
    requested_item = create_item("Mario Sunshine", "Jaquette propre", receiver, category)
    trade = create_trade(
        proposer=proposer,
        receiver=receiver,
        offered_items=[offered_item],
        requested_items=[requested_item],
        status="accepted",
    )

    session = login_user(proposer)
    page = session["page"]
    page.goto(f"{django_live_server.url}/my-trades/")
    page.click(f'form[action="/trade/{trade.id}/action/"] button[value="set_delivery"]')
    page.wait_for_url(f"{django_live_server.url}/my-trades/")
    assert page.locator("text=Veuillez choisir un mode de livraison.").is_visible()

    _set_hidden_control(page, 'input[name="delivery_mode"][value="post"]')
    page.click(f'form[action="/trade/{trade.id}/action/"] button[value="set_delivery"]')
    page.wait_for_url(f"{django_live_server.url}/my-trades/")
    assert page.locator("text=Veuillez renseigner les informations de livraison.").is_visible()

    trade.refresh_from_db()
    assert trade.delivery_mode in [None, ""]
    assert not trade.delivery_info

    session["context"].close()


@pytest.mark.django_db
def test_item_owner_and_unavailable_item_cannot_start_trade(
    django_live_server,
    create_user,
    create_category,
    create_item,
    login_user,
):
    owner = create_user("guard_owner")
    visitor = create_user("guard_visitor")
    category = create_category("DS")
    own_item = create_item("Pokemon Noir", "Version FR", owner, category)
    unavailable_item = create_item("Pokemon Blanc", "Reserve", owner, category, available=False)

    owner_session = login_user(owner)
    owner_page = owner_session["page"]
    owner_page.goto(f"{django_live_server.url}/item/{own_item.id}/")
    assert owner_page.locator("text=votre article").is_visible()
    owner_page.goto(f"{django_live_server.url}/trade/create/{own_item.id}/")
    owner_page.wait_for_url(f"{django_live_server.url}/")
    assert owner_page.locator("text=propre article").is_visible()

    visitor_session = login_user(visitor)
    visitor_page = visitor_session["page"]
    visitor_page.goto(f"{django_live_server.url}/item/{unavailable_item.id}/")
    assert visitor_page.locator("text=n'est plus disponible").is_visible()
    visitor_page.goto(f"{django_live_server.url}/trade/create/{unavailable_item.id}/")
    visitor_page.wait_for_url(f"{django_live_server.url}/")
    assert visitor_page.locator("text=n'est plus disponible").is_visible()

    owner_session["context"].close()
    visitor_session["context"].close()


@pytest.mark.django_db
def test_received_item_visibility_can_be_toggled_from_my_items(
    django_live_server,
    create_user,
    create_category,
    create_item,
    login_user,
):
    owner = create_user("toggle_owner")
    visitor = create_user("toggle_visitor")
    category = create_category("PSP")
    traded_item = create_item(
        "Monster Hunter Freedom",
        "Article recu par echange",
        owner,
        category,
        available=True,
        received_by_trade=True,
    )

    owner_session = login_user(owner)
    owner_page = owner_session["page"]
    owner_page.goto(f"{django_live_server.url}/my-items/")
    owner_page.click(f'form[action="/my-items/{traded_item.id}/toggle/"] button[type="submit"]')
    owner_page.wait_for_url(f"{django_live_server.url}/my-items/")

    traded_item.refresh_from_db()
    assert traded_item.available is False

    visitor_session = login_user(visitor)
    visitor_page = visitor_session["page"]
    visitor_page.goto(f"{django_live_server.url}/")
    assert visitor_page.locator("text=Monster Hunter Freedom").count() == 0

    owner_page.goto(f"{django_live_server.url}/my-items/")
    owner_page.click(f'form[action="/my-items/{traded_item.id}/toggle/"] button[type="submit"]')
    owner_page.wait_for_url(f"{django_live_server.url}/my-items/")

    traded_item.refresh_from_db()
    assert traded_item.available is True

    visitor_page.goto(f"{django_live_server.url}/")
    assert visitor_page.locator("text=Monster Hunter Freedom").is_visible()

    owner_session["context"].close()
    visitor_session["context"].close()


@pytest.mark.django_db
def test_notification_badge_disappears_after_opening_notifications(
    django_live_server,
    create_user,
    create_category,
    create_item,
    create_trade,
    login_user,
):
    proposer = create_user("badge_proposer")
    receiver = create_user("badge_receiver")
    category = create_category("Mobile")
    offered_item = create_item("Genshin Card", "Objet collector", proposer, category)
    requested_item = create_item("Zenless Card", "Objet collector", receiver, category)
    trade = create_trade(
        proposer=proposer,
        receiver=receiver,
        offered_items=[offered_item],
        requested_items=[requested_item],
    )
    Notification.objects.create(
        user=receiver,
        notif_type="trade_received",
        message="Nouvelle proposition a lire.",
        trade=trade,
    )

    session = login_user(receiver)
    page = session["page"]
    page.goto(f"{django_live_server.url}/")
    assert page.locator("#notif-dot").is_visible()

    page.click('a[href="/notifications/"]')
    page.wait_for_url(f"{django_live_server.url}/notifications/")
    assert page.locator("#notif-dot").count() == 0

    session["context"].close()


@pytest.mark.django_db
def test_invalid_rating_shows_error_and_does_not_create_review(
    django_live_server,
    create_user,
    create_category,
    create_item,
    create_trade,
    login_user,
):
    proposer = create_user("invalid_rating_proposer")
    receiver = create_user("invalid_rating_receiver")
    category = create_category("Arcade")
    offered_item = create_item("Pac-Man", "Mini borne", proposer, category)
    requested_item = create_item("Metal Slug", "Cartouche", receiver, category)
    trade = create_trade(
        proposer=proposer,
        receiver=receiver,
        offered_items=[offered_item],
        requested_items=[requested_item],
        status="completed",
        delivery_mode="other",
        delivery_info="Retrait sur place",
    )

    session = login_user(proposer)
    page = session["page"]
    page.goto(f"{django_live_server.url}/trade/{trade.id}/rate/")
    page.fill('textarea[name="comment"]', "Je laisse un avis sans note.")
    page.click('button[type="submit"]')

    assert page.locator("text=Note invalide").is_visible()
    assert Rating.objects.count() == 0

    session["context"].close()
