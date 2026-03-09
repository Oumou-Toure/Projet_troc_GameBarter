from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Item(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="items/")
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class Trade(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("refused", "Refused"),
    ]

    proposer = models.ForeignKey(User, related_name="sent_trades", on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name="received_trades", on_delete=models.CASCADE)

    offered_items = models.ManyToManyField(Item, related_name="offered")
    requested_items = models.ManyToManyField(Item, related_name="requested")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)