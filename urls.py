from django.urls import path, re_path
from django.conf.urls.static import static
from django.conf import settings
from . import views

urlpatterns = [
    path("", views.inventory_index, name="inventory_index"),
    path("items", views.item_list, name="item_list"),
    path("<str:item>/entryselection", views.itementryselection, name="itementryselection"),
    path("<str:item>/withdraw", views.itemwithdraw, name="itemwithdraw"),
    path("<str:item>/deposit", views.itemdeposit, name="itemdeposit"),
    path("activecart", views.activecart, name="activecart"),
    path("receipt/<str:type>/<str:ordernumber>", views.receipt, name="receipt"),
    path("orderlogs", views.orderlogs, name="orderlogs"),
    path("kits", views.kits_list, name="kits_list"),
    path("kit/<str:item>/withdraw", views.kits_withdraw, name="kits_withdraw"),
    path("kits/cart", views.kits_activecart, name="kits_activecart"),
    path("kit/<str:item>/restock", views.kits_restock, name="kits_restock"),
    path("kit/<str:item>/return", views.kits_return, name="kits_return"),
    path("kitlogs", views.kitlogs, name="kitlogs"),
    path("kit/<int:kit>", views.selectedkit, name="selectedkit"),
    path("kit/add", views.addnewkit, name="addnewkit"),
    path("items/add", views.addnewitem, name="addnewitem"),
    path("notifications", views.notifications, name="notifications"),
    path("itemlist", views.item_data, name="item_data"),
    path("csv_creator/<str:mode>", views.csv_creator, name="csv_creator"),
    path("error/<str:error>", views.error, name="error"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)