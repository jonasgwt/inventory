from .models import *

def kitcartitemlength(request):
    numitemsincart = len(kitloancart.objects.filter(archived=False))           
    return {'numitemsinkitcart': numitemsincart}


def cartitemlength(request):
    numitemsincart = len(cart.objects.filter(archived=False))           
    return {'numitemsincart': numitemsincart}


def alertslength(request):
    num_alerts = len(alerts.objects.all())           
    return {'num_alerts': num_alerts}