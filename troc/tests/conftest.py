import os

import django
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

# Allow async unsafe operations for testing
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', '1')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'troc.settings')
django.setup()

from django.contrib.auth.models import User

from exchange_mvp.models import Category, Item, Message, Notification, Rating, Trade


@pytest.fixture(scope="session")
def django_live_server(live_server):
    """Expose pytest-django's live server with the interface used by tests."""
    return live_server


@pytest.fixture
def create_user():
    """Factory fixture to create users."""

    def _create_user(username, password="testpass123", email=None):
        email_val = email or f"{username}@example.com"
        return User.objects.create_user(
            username=username,
            password=password,
            email=email_val,
        )

    return _create_user


@pytest.fixture
def create_category():
    """Factory fixture to create categories."""
    def _create_category(name):
        return Category.objects.create(name=name)

    return _create_category


@pytest.fixture
def create_item():
    """Factory fixture to create items."""
    image_bytes = (
        b"GIF87a\x01\x00\x01\x00\x80\x00\x00"
        b"\x00\x00\x00\xff\xff\xff!\xf9\x04\x01"
        b"\x00\x00\x00\x00,\x00\x00\x00\x00\x01"
        b"\x00\x01\x00\x00\x02\x02D\x01\x00;"
    )

    def _create_item(
        title,
        description,
        owner,
        category,
        available=True,
        received_by_trade=False,
    ):
        image_name = f"{title.lower().replace(' ', '_')}.gif"
        return Item.objects.create(
            title=title,
            description=description,
            owner=owner,
            category=category,
            available=available,
            received_by_trade=received_by_trade,
            image=SimpleUploadedFile(image_name, image_bytes, content_type="image/gif"),
        )

    return _create_item


@pytest.fixture
def browser_context_args(browser_context_args):
    """Configure browser context for tests."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


@pytest.fixture
def login_user(django_live_server, browser):
    """Factory fixture to open a browser context and authenticate a user."""

    def _login_user(user, password="testpass123"):
        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{django_live_server.url}/login/")
        page.fill('input[name="username"]', user.username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_url(f"{django_live_server.url}/")
        return {"user": user, "page": page, "context": context}

    return _login_user


@pytest.fixture
def logged_in_user(create_user, login_user):
    """Fixture that provides a logged-in user context."""
    user = create_user("playwright_user")
    session = login_user(user)
    yield session
    session["context"].close()


@pytest.fixture
def create_trade():
    """Factory fixture to create trades with linked items."""

    def _create_trade(proposer, receiver, offered_items, requested_items, status="pending", **extra_fields):
        trade = Trade.objects.create(
            proposer=proposer,
            receiver=receiver,
            status=status,
            **extra_fields,
        )
        trade.offered_items.set(offered_items)
        trade.requested_items.set(requested_items)
        return trade

    return _create_trade
