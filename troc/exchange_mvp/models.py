from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ["name"]


class Item(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="items/")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="items")
    available = models.BooleanField(default=True)
    received_by_trade = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        ordering = ["-created_at"]


class Trade(models.Model):
    STATUS_CHOICES = [
        ("pending", "En attente"),
        ("accepted", "Accepté - En attente de confirmation livraison"),
        ("confirmed", "Livraison confirmée"),
        ("completed", "Terminé"),
        ("refused", "Refusé"),
        ("cancelled", "Annulé"),
    ]

    DELIVERY_CHOICES = [
        ("hand", "🤝 Remise en main propre"),
        ("post", "📦 Via la poste"),
        ("other", "📋 Autre"),
    ]

    proposer = models.ForeignKey(User, related_name="sent_trades", on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name="received_trades", on_delete=models.CASCADE)
    offered_items = models.ManyToManyField(Item, related_name="offered_in_trades")
    requested_items = models.ManyToManyField(Item, related_name="requested_in_trades")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Livraison
    delivery_mode = models.CharField(max_length=20, choices=DELIVERY_CHOICES, null=True, blank=True)
    delivery_info = models.TextField(null=True, blank=True)  # infos selon le mode

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Échange #{self.id} : {self.proposer.username} → {self.receiver.username} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Échange"
        verbose_name_plural = "Échanges"
        ordering = ["-created_at"]


class Message(models.Model):
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message de {self.sender.username} sur échange #{self.trade.id}"

    class Meta:
        ordering = ["created_at"]


class Rating(models.Model):
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name="ratings")
    rater = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_ratings")
    rated_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_ratings")
    score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("trade", "rater")
        verbose_name = "Notation"
        verbose_name_plural = "Notations"

    def __str__(self):
        return f"{self.rater.username} → {self.rated_user.username} : {self.score}/5"


class Notification(models.Model):
    NOTIF_TYPES = [
        ("trade_received", "Nouvel échange reçu"),
        ("trade_accepted", "Échange accepté"),
        ("trade_refused", "Échange refusé"),
        ("trade_cancelled", "Échange annulé"),
        ("delivery_set", "Mode de livraison défini"),
        ("delivery_confirmed", "Livraison confirmée"),
        ("message_received", "Nouveau message"),
        ("rating_received", "Nouvelle notation"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    notif_type = models.CharField(max_length=30, choices=NOTIF_TYPES)
    message = models.CharField(max_length=300)
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notif pour {self.user.username} : {self.get_notif_type_display()}"

    class Meta:
        ordering = ["-created_at"]