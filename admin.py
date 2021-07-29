from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Item)
admin.site.register(order)
admin.site.register(cart)
admin.site.register(loanorder)
admin.site.register(loancart)
admin.site.register(loanoutstanding)
admin.site.register(kits)
admin.site.register(kititems)
admin.site.register(kitloancart)
admin.site.register(tempcart)
admin.site.register(ItemExpiry)
admin.site.register(kititemexpiry)
admin.site.register(kit_transactions)
admin.site.register(alerts)