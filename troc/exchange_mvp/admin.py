from django.contrib import admin
from .models import Item, Category, Trade, Message, Rating, Notification


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "category", "available", "created_at")
    list_filter = ("category", "available")
    search_fields = ("title", "owner__username")
    list_editable = ("available",)


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ("id", "proposer", "receiver", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("proposer__username", "receiver__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("trade", "sender", "created_at")
    search_fields = ("sender__username",)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("rater", "rated_user", "score", "trade", "created_at")
    list_filter = ("score",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notif_type", "is_read", "created_at")
    list_filter = ("notif_type", "is_read")
    list_editable = ("is_read",)