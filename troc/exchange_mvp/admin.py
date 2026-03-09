from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Item, Category, Trade, Message

admin.site.register(Item)
admin.site.register(Category)
admin.site.register(Trade)
admin.site.register(Message)