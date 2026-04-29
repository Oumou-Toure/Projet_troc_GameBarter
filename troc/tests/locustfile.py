from locust import HttpUser, task, between


class GameBarterUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Récupérer le CSRF token puis se connecter."""
        # Récupérer la page login pour obtenir le CSRF token
        response = self.client.get("/login/")
        csrf_token = response.cookies.get("csrftoken", "")

        self.client.post("/login/", {
            "username": "oumou2023",
            "password": "1234",
            "csrfmiddlewaretoken": csrf_token,
        }, headers={"X-CSRFToken": csrf_token})

    @task(5)
    def browse_catalog(self):
        self.client.get("/")

    @task(3)
    def search_catalog(self):
        self.client.get("/?q=mario")

    @task(2)
    def filter_by_platform(self):
        self.client.get("/?platform=ps5")

    @task(2)
    def view_my_trades(self):
        self.client.get("/my-trades/")

    @task(1)
    def view_notifications(self):
        self.client.get("/notifications/")

    @task(1)
    def view_profile(self):
        self.client.get("/profil/oumou2023/")


class CatalogOnlyUser(HttpUser):
    wait_time = between(1, 5)

    @task(5)
    def browse_catalog(self):
        self.client.get("/")

    @task(3)
    def search_catalog(self):
        self.client.get("/?q=zelda")

    @task(2)
    def filter_catalog(self):
        self.client.get("/?platform=switch")

    @task(1)
    def view_profile(self):
        self.client.get("/profil/oumou2023/")