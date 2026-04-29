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


@pytest.mark.django_db
def test_home_filters_and_hides_authenticated_user_items(
    django_live_server,
    browser,
    create_user,
    create_category,
    create_item,
    login_user,
):
    owner = create_user("owner_catalog")
    viewer = create_user("viewer_catalog")
    action = create_category("Action")
    rpg = create_category("RPG")

    visible_item = create_item(
        "Zelda Breath",
        "Aventure en monde ouvert",
        owner,
        action,
    )
    create_item(
        "Persona 5",
        "JRPG tres long",
        owner,
        rpg,
    )
    create_item(
        "Mon jeu cache",
        "Cet article appartient au visiteur connecte",
        viewer,
        action,
    )

    page = browser.new_page()
    page.goto(f"{django_live_server.url}/?q=Zelda&category={action.id}")

    assert page.locator(f"text={visible_item.title}").is_visible()
    assert page.locator("text=Persona 5").count() == 0

    page.close()

    session = login_user(viewer)
    auth_page = session["page"]
    auth_page.goto(f"{django_live_server.url}/")

    assert auth_page.locator(f"text={visible_item.title}").is_visible()
    assert auth_page.locator("text=Mon jeu cache").count() == 0

    session["context"].close()


@pytest.mark.django_db
def test_item_detail_page_displays_item_information(
    django_live_server,
    browser,
    create_user,
    create_category,
    create_item,
):
    owner = create_user("detail_owner")
    category = create_category("Adventure")
    item = create_item(
        "Okami HD",
        "Aventure dessinee avec pinceau celeste.",
        owner,
        category,
    )

    page = browser.new_page()
    page.goto(f"{django_live_server.url}/item/{item.id}/")

    assert page.locator("h2", has_text=item.title).is_visible()
    assert page.locator(f"text={item.description}").is_visible()
    assert page.locator(f"text={category.name}").is_visible()
    assert page.locator(f'a[href="/profil/{owner.username}/"]').is_visible()
    assert page.locator(f'img[alt="{item.title}"]').is_visible()
    assert page.locator('a[href="/"]').filter(has_text="Retour").is_visible()

    page.close()


@pytest.mark.django_db
def test_empty_catalog_displays_empty_state(django_live_server, browser):
    page = browser.new_page()
    page.goto(f"{django_live_server.url}/")

    assert page.locator("text=0 article").is_visible()
    assert page.locator("text=/Aucun article/").is_visible()
    assert page.locator(".card-item").count() == 0

    page.close()


@pytest.mark.django_db
def test_search_without_results_displays_no_result_message(
    django_live_server,
    browser,
    create_user,
    create_category,
    create_item,
):
    owner = create_user("search_owner")
    category = create_category("Puzzle")
    create_item("Portal 2", "Jeu de reflexion.", owner, category)

    page = browser.new_page()
    page.goto(f"{django_live_server.url}/?q=Introuvable")

    assert page.locator("text=Portal 2").count() == 0
    assert page.locator("text=/Aucun article/").is_visible()
    assert page.locator('a[href="/"]').filter(has_text="Voir tous les articles").is_visible()

    page.close()


@pytest.mark.django_db
def test_anonymous_user_sees_catalog_without_trade_button(
    django_live_server,
    browser,
    create_user,
    create_category,
    create_item,
):
    owner = create_user("anonymous_catalog_owner")
    category = create_category("Racing")
    item = create_item("F-Zero", "Course futuriste.", owner, category)

    page = browser.new_page()
    page.goto(f"{django_live_server.url}/")

    assert page.locator(f"text={item.title}").is_visible()
    assert page.locator(f'a[href="/item/{item.id}/"]').first.is_visible()
    assert page.locator(f'a[href="/trade/create/{item.id}/"]').count() == 0
    assert page.locator('a[href="/login/"]').filter(has_text="Connectez-vous").is_visible()

    page.close()


@pytest.mark.django_db
def test_create_trade_from_item_detail_creates_trade_message_and_notification(
    django_live_server,
    create_user,
    create_category,
    create_item,
    login_user,
):
    proposer = create_user("alice_trade")
    receiver = create_user("bob_trade")
    category = create_category("Switch")

    target_item = create_item(
        "Mario Kart 8",
        "Edition physique",
        receiver,
        category,
    )
    offered_item = create_item(
        "Splatoon 3",
        "Jeu en parfait etat",
        proposer,
        category,
    )

    session = login_user(proposer)
    page = session["page"]

    page.goto(f"{django_live_server.url}/item/{target_item.id}/")
    page.click("a[href*='/trade/create/']")
    _set_hidden_control(page, f'input[name="offered_items"][value="{offered_item.id}"]')
    page.fill('textarea[name="message"]', "Je peux echanger rapidement cette semaine.")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{django_live_server.url}/my-trades/")

    trade = Trade.objects.get(proposer=proposer, receiver=receiver)
    assert trade.status == "pending"
    assert list(trade.offered_items.values_list("id", flat=True)) == [offered_item.id]
    assert list(trade.requested_items.values_list("id", flat=True)) == [target_item.id]
    assert Message.objects.filter(trade=trade, content__icontains="rapidement").exists()
    assert Notification.objects.filter(
        user=receiver,
        trade=trade,
        notif_type="trade_received",
    ).exists()
    assert page.locator("text=Splatoon 3").is_visible()
    assert page.locator("text=Mario Kart 8").is_visible()

    session["context"].close()


@pytest.mark.django_db
def test_trade_can_be_accepted_delivered_and_completed(
    django_live_server,
    create_user,
    create_category,
    create_item,
    create_trade,
    login_user,
):
    proposer = create_user("proposer_flow")
    receiver = create_user("receiver_flow")
    category = create_category("Nintendo")

    offered_item = create_item(
        "Metroid Prime",
        "Version remastered",
        proposer,
        category,
    )
    requested_item = create_item(
        "Luigi Mansion 3",
        "Avec boite",
        receiver,
        category,
    )
    trade = create_trade(
        proposer=proposer,
        receiver=receiver,
        offered_items=[offered_item],
        requested_items=[requested_item],
    )

    receiver_session = login_user(receiver)
    receiver_page = receiver_session["page"]
    receiver_page.goto(f"{django_live_server.url}/my-trades/")
    receiver_page.click(f'form[action="/trade/{trade.id}/action/"] button[value="accept"]')
    receiver_page.wait_for_url(f"{django_live_server.url}/my-trades/")

    trade.refresh_from_db()
    offered_item.refresh_from_db()
    requested_item.refresh_from_db()
    assert trade.status == "accepted"
    assert offered_item.available is False
    assert requested_item.available is False

    proposer_session = login_user(proposer)
    proposer_page = proposer_session["page"]
    proposer_page.goto(f"{django_live_server.url}/my-trades/")
    _set_hidden_control(proposer_page, 'input[name="delivery_mode"][value="hand"]')
    proposer_page.fill('textarea[name="delivery_info"]', "Rendez-vous samedi a la gare.")
    proposer_page.click(f'form[action="/trade/{trade.id}/action/"] button[value="set_delivery"]')
    proposer_page.wait_for_url(f"{django_live_server.url}/my-trades/")

    trade.refresh_from_db()
    assert trade.delivery_mode == "hand"
    assert trade.delivery_info == "Rendez-vous samedi a la gare."

    receiver_page.goto(f"{django_live_server.url}/my-trades/")
    receiver_page.click(f'form[action="/trade/{trade.id}/action/"] button[value="confirm_delivery"]')
    receiver_page.wait_for_url(f"{django_live_server.url}/my-trades/")

    trade.refresh_from_db()
    offered_item.refresh_from_db()
    requested_item.refresh_from_db()

    assert trade.status == "completed"
    assert offered_item.owner_id == receiver.id
    assert requested_item.owner_id == proposer.id
    assert offered_item.received_by_trade is True
    assert requested_item.received_by_trade is True
    assert Notification.objects.filter(
        user=proposer,
        trade=trade,
        notif_type="delivery_confirmed",
    ).exists()

    proposer_session["context"].close()
    receiver_session["context"].close()


@pytest.mark.django_db
def test_notifications_are_marked_read_when_opened(
    django_live_server,
    create_user,
    create_category,
    create_item,
    create_trade,
    login_user,
):
    proposer = create_user("notif_proposer")
    receiver = create_user("notif_receiver")
    category = create_category("Retro")

    offered_item = create_item("GoldenEye", "N64", proposer, category)
    requested_item = create_item("Perfect Dark", "N64", receiver, category)
    trade = create_trade(
        proposer=proposer,
        receiver=receiver,
        offered_items=[offered_item],
        requested_items=[requested_item],
    )
    Notification.objects.create(
        user=receiver,
        notif_type="trade_received",
        message="Une nouvelle proposition vous attend.",
        trade=trade,
    )

    session = login_user(receiver)
    page = session["page"]
    page.goto(f"{django_live_server.url}/notifications/")

    assert page.locator("text=Une nouvelle proposition vous attend.").is_visible()
    assert page.locator("text=Nouveau").count() == 0

    notification = Notification.objects.get(user=receiver, trade=trade)
    assert notification.is_read is True

    session["context"].close()


@pytest.mark.django_db
def test_completed_trade_can_be_rated_and_rating_is_visible_on_profile(
    django_live_server,
    create_user,
    create_category,
    create_item,
    create_trade,
    login_user,
):
    proposer = create_user("rating_proposer")
    receiver = create_user("rating_receiver")
    category = create_category("PS5")

    offered_item = create_item("Spider-Man 2", "Edition standard", proposer, category)
    requested_item = create_item("Ratchet", "Jeu termine", receiver, category)
    trade = create_trade(
        proposer=proposer,
        receiver=receiver,
        offered_items=[offered_item],
        requested_items=[requested_item],
        status="completed",
        delivery_mode="post",
        delivery_info="10 rue des tests",
    )
    trade.updated_at = timezone.now()
    trade.save(update_fields=["updated_at"])

    session = login_user(proposer)
    page = session["page"]
    page.goto(f"{django_live_server.url}/trade/{trade.id}/rate/")
    _set_hidden_control(page, 'input[name="score"][value="5"]')
    page.fill('textarea[name="comment"]', "Echange impeccable et communication fluide.")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{django_live_server.url}/my-trades/")

    rating = Rating.objects.get(trade=trade, rater=proposer)
    assert rating.score == 5
    assert "communication fluide" in rating.comment

    page.goto(f"{django_live_server.url}/profil/{receiver.username}/")
    assert page.locator("text=communication fluide").is_visible()
    assert page.locator("text=/5[\\.,]0/").is_visible()
    assert Notification.objects.filter(
        user=receiver,
        trade=trade,
        notif_type="rating_received",
    ).exists()

    session["context"].close()
