import pytest
import uuid


@pytest.mark.django_db
def test_create_user(create_user):
    """Test that create_user fixture works."""
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    user = create_user(username)
    assert user.username == username
    assert user.email == f"{username}@example.com"


@pytest.mark.django_db
def test_server_accessible(django_live_server, browser):
    """Test that the server is accessible."""
    page = browser.new_page()
    page.goto(f"{django_live_server.url}/")
    assert (
        page.locator("text=GameBarter").is_visible()
        or page.locator("text=Troc").is_visible()
        or len(page.title()) > 0
    )
    page.close()


@pytest.mark.django_db
def test_login_page_accessible(django_live_server, browser):
    """Test that the login page is accessible."""
    page = browser.new_page()
    page.goto(f"{django_live_server.url}/login/")
    username_field = page.locator('input[name="username"]')
    password_field = page.locator('input[name="password"]')
    assert username_field.is_visible()
    assert password_field.is_visible()
    page.close()


class TestAuthentication:
    """Test user authentication workflows."""

    @pytest.mark.django_db
    def test_login_valid_credentials(self, django_live_server, browser, create_user):
        page = browser.new_page()
        username = f"login_user_{uuid.uuid4().hex[:8]}"
        password = "admin123"
        create_user(username, password=password)

        page.goto(f"{django_live_server.url}/login/")
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_url(f"{django_live_server.url}/")

        assert page.locator('a[href="/logout/"]').is_visible()
        assert page.locator(f"text={username}").is_visible()

        page.close()

    @pytest.mark.django_db
    def test_login_invalid_password(self, django_live_server, browser, create_user):
        page = browser.new_page()
        username = f"wrong_pass_{uuid.uuid4().hex[:8]}"
        create_user(username, password="admin123")

        page.goto(f"{django_live_server.url}/login/")
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', "wrongpass")
        page.click('button[type="submit"]')

        assert "/login/" in page.url
        assert page.locator("text=Nom d'utilisateur ou mot de passe incorrect.").is_visible()
        assert page.locator('input[name="username"]').input_value() == username

        page.close()

    @pytest.mark.django_db
    def test_login_nonexistent_user(self, django_live_server, browser):
        page = browser.new_page()

        page.goto(f"{django_live_server.url}/login/")
        page.fill('input[name="username"]', f"nonexistent_{uuid.uuid4().hex[:8]}")
        page.fill('input[name="password"]', "anypassword")
        page.click('button[type="submit"]')

        assert page.locator("text=Nom d'utilisateur ou mot de passe incorrect.").is_visible()

        page.close()

    @pytest.mark.django_db
    def test_logout(self, django_live_server, browser, create_user):
        page = browser.new_page()
        username = f"logout_user_{uuid.uuid4().hex[:8]}"
        password = "admin123"
        create_user(username, password=password)

        page.goto(f"{django_live_server.url}/login/")
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_url(f"{django_live_server.url}/")

        page.click('a[href="/logout/"]')
        page.wait_for_url(f"{django_live_server.url}/")

        assert page.locator("text=Se connecter").is_visible()

        page.close()

    @pytest.mark.django_db
    def test_unauthorized_access_redirects_to_login(self, django_live_server, browser):
        page = browser.new_page()
        page.goto(f"{django_live_server.url}/my-items/")
        page.wait_for_url("**/login/**")
        page.close()

    @pytest.mark.django_db
    def test_authenticated_user_can_access_protected_pages(
        self,
        django_live_server,
        browser,
        create_user,
    ):
        page = browser.new_page()
        username = f"protected_user_{uuid.uuid4().hex[:8]}"
        password = "admin123"
        create_user(username, password=password)

        page.goto(f"{django_live_server.url}/login/")
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_url(f"{django_live_server.url}/")

        page.goto(f"{django_live_server.url}/my-items/")

        assert "/my-items/" in page.url
        assert page.locator("h2:has-text('Mes articles')").is_visible()

        page.close()
