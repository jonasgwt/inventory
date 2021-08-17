from django.db.models.expressions import OrderBy
from django.http import response
from django.http.response import Http404
from requests.models import parse_url
from Kcanto.views import login_view
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import *
from json import dumps
import datetime
from django.contrib.admin.views.decorators import staff_member_required
import os
from django.utils.encoding import force_text, smart_str
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
import random
from movies.models import genres
import math
import re
from Kcanto.decorators import *
import json as simplejson
import requests
from discord import Webhook, RequestsWebhookAdapter
import schedule
from django.http import HttpResponseNotFound
from django.db.models import Sum
import traceback
from django.http import JsonResponse
from .functions import handle_uploaded_file  
import json
import collections
import csv
import xlwt
from .secret import *


# Create your views here.

#expiremental ordering
#formula: attractability score = 1/((current time - median active time of item)/10000) * weight + (total times item appear in cart / total items in cart) * (1 - weight)
def orderfaitems():
    all_inventory = list(Item.objects.all())
    all_attractability=[]
    outcome=[]
    now = datetime.datetime.now().time()
    #adjust weight here (higher weight means more emphasis on time sorting) (weight must be < 1)
    weight = 0.1
    for i in all_inventory:
        #median time, popularity
        result=[]
        #calculate time score
        if i.avg_transact_time:
            diff = abs(datetime.datetime.combine(datetime.datetime.today(), now) - datetime.datetime.combine(datetime.datetime.today(), i.avg_transact_time)).seconds
            result.append(1/(diff/10000))
        else:
            result.append(0)
        #calculate popularity score
        popularity = (cart.objects.filter(item__item=i).count() + loancart.objects.filter(item__item=i).count())/(cart.objects.all().count()+ loancart.objects.all().count())
        result.append(popularity)
        #total score
        attractability_score = result[0]*weight + result[1]*(1-weight)
        all_attractability.append(attractability_score)
    zipped = list(zip(all_attractability,all_inventory))
    zipped.sort(key=lambda x:x[0])
    for i in reversed(zipped):
        outcome.append(i[1])
    return outcome

def orderkits():
    all_kits = kits.objects.all()
    attractability_scores=[]
    outcome=[]
    now = datetime.datetime.now().time()
    #adjust weight here (higher weight means more emphasis on time sorting) (weight must be < 1)
    weight = 0.1
    for k in all_kits:
        #median time, popularity
        result=[]
        #calculate time score
        if k.avg_transact_time:
            diff = abs(datetime.datetime.combine(datetime.datetime.today(), now) - datetime.datetime.combine(datetime.datetime.today(), k.avg_transact_time)).seconds
            result.append(1/(diff/10000))
        else:
            result.append(0)
        popularity = kit_transactions.objects.filter(kit=k).count()/kit_transactions.objects.all().count()
        result.append(popularity)
        attractability_score = result[0]*weight + result[1]*(1-weight)
        attractability_scores.append(attractability_score)
    zipped = list(zip(attractability_scores,all_kits))
    zipped.sort(key=lambda x:x[0])
    for i in reversed(zipped):
        outcome.append(i[1])
    return outcome

def update_kit_transact_time(transaction, type):
    target_kit = transaction.kit
    kit_expiry_list=[]
    for t in kit_transactions.objects.filter(kit=target_kit).values_list('time', flat=True).order_by('time__hour', 'time__minute'):
        kit_expiry_list.append(t.time())
    if type == 'delete':
        kit_expiry_list.remove(transaction.time.time())
    if len(kit_expiry_list)>0:
            median = sorted(kit_expiry_list)[round(len(kit_expiry_list)/2)]
            target_kit.avg_transact_time = str(median)
            target_kit.save()

def update_transact_time(order, type):
    loan = False
    try:
        item_expirys = order.cart.all()
    except AttributeError:
        item_expirys = order.loancart.all()
        loan = True
    for i in item_expirys:
        i_expiry_list=[]
        for x in list(loancart.objects.filter(item__item=i.item.item).values_list('time', flat=True).order_by('time__hour', 'time__minute')) + list(cart.objects.filter(item__item=i.item.item).values_list('time', flat=True).order_by('time__hour', 'time__minute')):
            i_expiry_list.append((x.time())) 
        if type == 'delete':
            if loan:
                for a in loancart.objects.filter(item=i.item, order=order):
                    i_expiry_list.remove(a.time.time())
            else:
                for a in cart.objects.filter(item=i.item, order=order):
                    i_expiry_list.remove(a.time.time())
        if len(i_expiry_list)>0:
            median = sorted(i_expiry_list)[round(len(i_expiry_list)/2)]
            i.avg_transact_time = str(median)
            i.save()


#uncomment to enable telegram updates
""" def telegram_bot_sendtext(bot_message):
    bot_chatID = group
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=HTML&text=' + bot_message
    response = requests.get(send_text)
    return response.json() """

#delete to enable telegram updates
def telegram_bot_sendtext(bot_message):
    pass

#uncomment to enable telegram updates
""" def telegram_bot_sendpmphoto(bot_message, person, photo):
    
    if person == "eriol":
        bot_chatID = Eriol
    elif person == "Jonas":
        bot_chatID = Jonas
    else:
        bot_chatID = Jonas
    if photo:
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendPhoto?chat_id=' + bot_chatID + '&parse_mode=HTML&caption=' + bot_message +'&photo=' + photo
        response = requests.get(send_text)
        return response.json()
    else:
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=HTML&text=' + bot_message
        response = requests.get(send_text)
        return response.json() """

#delete to enable telegram updates
def telegram_bot_sendpmphoto(bot_message, person, photo):
    pass

def sendmessageforlowqty(itemexpiry):
    target=itemexpiry.item
    if target.total_quantityopen <= target.min_quantityopen and target.total_quantityunopened <= target.min_quantityunopened:
        message="\U0001F4C9<u><b>Quantity of "+ str(target.name)+ " is Low!</b></u>\U0001F4C9\n\n" + "Type: "+str(target.type)+"\nQuantity Opened: "+str(target.total_quantityopen)+"\nMin Quantity Opened: "+str(target.min_quantityopen)+"\n\nQuantity Unopened: "+str(target.total_quantityunopened)+"\nMin Quantity Unopened: "+str(target.min_quantityunopened)
        if target.image:
                telegram_bot_sendpmphoto(message, "Jonas", "https://playground.nhhs-sjb.org/uploaded/inventoryitemimages/"+target.image)
        else:
            telegram_bot_sendpmphoto(message, "Jonas", False)
    else:
        if target.total_quantityopen <= target.min_quantityopen:
            message="\U0001F4C9<u><b>Opened Quantity of "+ str(target.name)+ " is Low!</b></u>\U0001F4C9\n\n" + "Type: "+str(target.type)+"\nQuantity Opened: "+str(target.total_quantityopen)+"\nMin Quantity Opened: "+str(target.min_quantityopen)
            if target.image:
                telegram_bot_sendpmphoto(message, "Jonas", "https://playground.nhhs-sjb.org/uploaded/inventoryitemimages/"+target.image)
            else:
                telegram_bot_sendpmphoto(message, "Jonas", False)
        if target.total_quantityunopened <= target.min_quantityunopened:
            message="\U0001F4C9<u><b>Unopened Quantity of "+ str(target.name)+ " is Low!</b></u>\U0001F4C9\n\n" + "Type: "+str(target.type)+"\nQuantity Unopened: "+str(target.total_quantityunopened)+"\nMin Quantity Unopened: "+str(target.min_quantityunopened)
            if target.image:
                telegram_bot_sendpmphoto(message, "Jonas", "https://playground.nhhs-sjb.org/uploaded/inventoryitemimages/"+target.image)
            else:
                telegram_bot_sendpmphoto(message, "Jonas", False)

def check():
    datenow = datetime.date.today()
    alerts.objects.all().delete()
    #check all loans and add to database
    for activeloan in loanorder.objects.filter(loan_active = True):
        if activeloan.loan_end_date < datenow:
            newalert = alerts(loan=activeloan, category="Loan Expired")
            newalert.save()
        elif activeloan.loan_end_date <= datenow + datetime.timedelta(days=1):
            newalert = alerts(loan=activeloan, category="Loan Expiring", urgent=False)
            newalert.save()
    #check all items and add to database
    for item in Item.objects.filter():
        #check expiry
        for itemexpiry in item.expirydates.filter(archived=False):
            if itemexpiry.expirydate != None:
                if itemexpiry.expirydate < datenow:
                    newalert = alerts(itemexpiry=itemexpiry, category="Item Expired")
                    newalert.save()
                elif itemexpiry.expirydate <= datenow + datetime.timedelta(days=1):
                    newalert = alerts(itemexpiry=itemexpiry, category="Item Expiring", urgent=False)
                    newalert.save()
        #check qty of items
        if int(item.total_quantityopen)<=int(item.min_quantityopen) and int(item.total_quantityunopened)<=int(item.min_quantityunopened):
            newalert = alerts(item=item, category="Low Item Qty")
            newalert.save()
        elif int(item.total_quantityopen)<=int(item.min_quantityopen):
            newalert = alerts(item=item, category="Low Item Qty (Opened)")
            newalert.save()
        elif int(item.total_quantityunopened)<=int(item.min_quantityunopened):
            newalert = alerts(item=item, category="Low Item Qty (Unopened)")
            newalert.save()
    #check all kits and add to database
    for kit in kits.objects.all():
        if kit.nearest_expiry != None:
            if kit.nearest_expiry < datenow:
                newalert = alerts(kit=kit, category="Kit Expired")
                newalert.save()
            elif kit.nearest_expiry <= datenow + datetime.timedelta(days=1):
                newalert = alerts(kit=kit, category="Kit Expiring", urgent=False)
                newalert.save()
    if len(alerts.objects.all())>0:
        return False
    else:
        return True

def report():
    datenow = datetime.date.today()
    loanexpire=[]
    loanwarn=[]
    itemexpire=[]
    itemwarn=[]
    itemqtyopened=[]
    itemqtyunopened=[]
    itemqty=[]
    kitexpire=[]
    kitwarn=[]
    alerts.objects.all().delete()
    #check all loans and add to database
    for activeloan in loanorder.objects.filter(loan_active = True):
        if activeloan.loan_end_date < datenow:
            newalert = alerts(loan=activeloan, category="Loan Expired")
            newalert.save()
            loanexpire.append(activeloan)
        elif activeloan.loan_end_date <= datenow + datetime.timedelta(days=1):
            newalert = alerts(loan=activeloan, category="Loan Expiring", urgent=False)
            newalert.save()
            loanwarn.append(activeloan)
    #check all items and add to database
    for item in Item.objects.all():
        #check item expiry
        for itemexpiry in item.expirydates.filter(archived=False):
            if itemexpiry.expirydate != None:
                if itemexpiry.expirydate < datenow:
                    newalert = alerts(itemexpiry=itemexpiry, category="Item Expired")
                    newalert.save()
                    itemexpire.append(itemexpiry)
                elif itemexpiry.expirydate <= datenow + datetime.timedelta(days=1):
                    newalert = alerts(itemexpiry=itemexpiry, category="Item Expiring", urgent=False)
                    newalert.save()
                    itemwarn.append(itemexpiry)
        #check qty of items
        if int(item.total_quantityopen)<=int(item.min_quantityopen) and int(item.total_quantityunopened)<=int(item.min_quantityunopened):
            newalert = alerts(item=item, category="Low Item Qty")
            newalert.save()
            itemqty.append(item)
        elif int(item.total_quantityopen)<=int(item.min_quantityopen):
            newalert = alerts(item=item, category="Low Item Qty (Opened)")
            newalert.save()
            itemqtyopened.append(item)
        elif int(item.total_quantityunopened)<=int(item.min_quantityunopened):
            newalert = alerts(item=item, category="Low Item Qty (Unopened)")
            newalert.save()
            itemqtyunopened.append(item)
    #check all kits and add to database
    for kit in kits.objects.all():
        if kit.nearest_expiry != None:
            if kit.nearest_expiry < datenow:
                newalert = alerts(kit=kit, category="Kit Expired")
                newalert.save()
                kitexpire.append(kit)
            elif kit.nearest_expiry <= datenow + datetime.timedelta(days=1):
                newalert = alerts(kit=kit, category="Kit Expiring", urgent=False)
                newalert.save()
                kitwarn.append(kit)
    #send message for expired loans
    for expiringloan in loanexpire:
        messagecart=""
        for cartitem in expiringloan.loancart.filter(loan=True, expanded = False):
            quantity = int(cartitem.quantityopen) + int(cartitem.quantityunopened)
            messagecart += " •  "+str(quantity)+ " " + cartitem.item.name +"\n"
        message="\U000026A0<u><b>Loan "+ str(expiringloan.id) + " has Expired!</b></u>\U000026A0\n\n" + str(messagecart)+"\n<code>Loaned to " + str(expiringloan.loanee_name) + " expired on " +str(expiringloan.loan_end_date)+"</code>"
        telegram_bot_sendpmphoto(message, expiringloan.ordering_account.username, False)
    #send message for expiring loans
    for expiringloan in loanwarn:
        messagecart=""
        for cartitem in expiringloan.loancart.filter(loan=True, expanded = False):
            quantity = int(cartitem.quantityopen) + int(cartitem.quantityunopened)
            messagecart += " •  "+str(quantity)+ " " + cartitem.item.name +"\n"
        message="\U000026A0<u><b>Loan "+ str(expiringloan.id) + " Will Expire Tomorrow!</b></u>\U000026A0\n\n" + str(messagecart)+"\n<code>Loaned to " + str(expiringloan.loanee_name) + " expiring on " +str(expiringloan.loan_end_date)+"</code>"
        telegram_bot_sendpmphoto(message, expiringloan.ordering_account.username, False)
    #send message for expired items
    for expired in itemexpire:
        messagecart=""
        message="\U000026A0<u><b>One set of "+ str(expired.item.name)+ " has Expired!</b></u>\U000026A0\n\n" + "Type: "+str(expired.item.type)+"\nQuantity Opened: "+str(expired.quantityopen)+"\nQuantity Unopened: "+str(expired.quantityunopened)+"\n\n<code>Expired on " +str(expired.expirydate)+"</code>"
        telegram_bot_sendpmphoto(message, "Jonas", "https://playground.nhhs-sjb.org/uploaded/inventoryitemimages/"+expired.image)
    #send message for expiring items
    for expiring in itemwarn:
        messagecart=""
        message="\U000026A0<u><b>"+ str(expiring.name)+ " Will Expire Tomorrow!</b></u>\U000026A0\n\n" + "Type: "+str(expiring.type)+"\nQuantity Opened: "+str(expiring.quantityopen)+"\nQuantity Unopened: "+str(expiring.quantityunopened)+"\n\n<code>Expiring on " +str(expiring.expirydate)+"</code>"
        if expiring.image == None:
            telegram_bot_sendpmphoto(message, "Jonas", False)
        else:
            telegram_bot_sendpmphoto(message, "Jonas", "https://playground.nhhs-sjb.org/uploaded/inventoryitemimages/"+expiring.image)
    #send message for expired kits
    for expired in kitexpire:
        messagecart=""
        message="\U000026A0<u><b>"+ str(expired.name)+ " has Expired!</b></u>\U000026A0\n\n" + "Status: "+str(expired.status)+"\n\n<code>Expired on " +str(expired.nearest_expiry)+"</code>"
        telegram_bot_sendpmphoto(message, "Jonas", "https://playground.nhhs-sjb.org/static/inventoryresource/"+expired.image)
    #send message for expiring kits
    for expiring in kitwarn:
        messagecart=""
        message="\U000026A0<u><b>"+ str(expiring.name)+ " Will Expire Tomorrow!</b></u>\U000026A0\n\n" + "Status: "+str(expired.status)+"\n\n<code>Expiring on " +str(expiring.nearest_expiry)+"</code>"
        if expiring.image == None:
            telegram_bot_sendpmphoto(message, "Jonas", False)
        else:
            telegram_bot_sendpmphoto(message, "Jonas", "https://playground.nhhs-sjb.org/static/inventoryresource/"+expiring.image)
    #send message for low qty opened
    for item in itemqtyopened:
        message="\U0001F4C9<u><b>Quantity of "+ str(item.name)+ " is Low!</b></u>\U0001F4C9\n\n" + "Type: "+str(item.type)+"\nQuantity Opened: "+str(item.total_quantityopen)+"\nMin Quantity Opened: "+str(item.min_quantityopen)
        if item.image:
            telegram_bot_sendpmphoto(message, "Jonas", "https://playground.nhhs-sjb.org/uploaded/inventoryitemimages/"+item.image)
        else:
            telegram_bot_sendpmphoto(message, "Jonas", False)
    #send message for low qty unopened
    for item in itemqtyunopened:
        message="\U0001F4C9<u><b>Quantity of "+ str(item.name)+ " is Low!</b></u>\U0001F4C9\n\n" + "Type: "+str(item.type)+"\nQuantity Unopened: "+str(item.total_quantityunopened)+"\nMin Quantity Unopened: "+str(item.min_quantityunopened)
        if item.image:
            telegram_bot_sendpmphoto(message, "Jonas", "https://playground.nhhs-sjb.org/uploaded/inventoryitemimages/"+item.image)
        else:
            telegram_bot_sendpmphoto(message, "Jonas", False)
    #send message for low qty unopened and opened
    for item in itemqty:
        message="\U0001F4C9<u><b>Quantity of "+ str(item.name)+ " is Low!</b></u>\U0001F4C9\n\n" + "Type: "+str(item.type)+"\nQuantity Opened: "+str(item.total_quantityopen)+"\nMin Quantity Opened: "+str(item.min_quantityopen)+"\nQuantity Unopened: "+str(item.total_quantityunopened)+"\nMin Quantity Unopened: "+str(item.min_quantityunopened)
        if item.image:
            telegram_bot_sendpmphoto(message, "Jonas", "https://playground.nhhs-sjb.org/uploaded/inventoryitemimages/"+item.image)
        else:
            telegram_bot_sendpmphoto(message, "Jonas", False)

    telegram_bot_sendtext("<code>Daily Report Complete</code>")

@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def error(request, error):
    return render (request, "inventory/error.html",{
        "message": error
    })

@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def inventory_index(request):
    return render (request, "inventory/home.html")


def pagination(request, x):
    page = request.GET.get('page', 1)
    paginator = Paginator(x, 5)
    try:
        inv_list = paginator.page(page)
    except PageNotAnInteger:
        inv_list = paginator.page(1)
    except EmptyPage:
        inv_list = paginator.page(paginator.num_pages)
        # Get the index of the current page
    index = inv_list.number - 1  # edited to something easier without index
    # This value is maximum index of your pages, so the last page - 1
    max_index = len(paginator.page_range)
    # You want a range of 7, so lets calculate where to slice the list
    start_index = index - 7 if index >= 7 else 0
    end_index = index + 7 if index <= max_index - 7 else max_index
    # Get our new page range. In the latest versions of Django page_range returns 
    # an iterator. Thus pass it to list, to make our slice possible again.
    page_range = list(paginator.page_range)[start_index:end_index]
    return page_range, inv_list


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def item_list(request):
    all_inventory = orderfaitems()
    print(all_inventory, "here")
    all_itemsincart = list(cart.objects.filter(archived=False))
    #check if cart has both deposit and withdraw items
    #ascertain if it is a deposit/withdraw cart
    if len(all_itemsincart) > 0:
        if all_itemsincart[0].withdraw:
            for itemincart in all_itemsincart:
                if not itemincart.withdraw:
                    return render(request, "inventory/error.html",{
                        "message" : "Both deposit and withdraw items in cart!"
                    })
            cart_type = "withdraw"
        else:
            for itemincart in all_itemsincart:
                if itemincart.withdraw:
                    return render(request, "inventory/error.html",{
                        "message" : "Both deposit and withdraw items in cart!"
                    })
            cart_type = "deposit"
    else:
        cart_type = "empty"
    types=[]
    for typechoice in typechoices:
        types.append(typechoice[0])
    #pagination
    page_range, inv_list = pagination(request, all_inventory)

    #optional check to archive (remove for speed)
    #for item in all_inventory: 
        #for itemexpiry in item.expirydates.filter(archived = False):
            #if itemexpiry.quantityopen == 0 and itemexpiry.quantityunopened == 0:
                #itemexpiry.archived =True
                #itemexpiry.save()

    #optional check to maintain total qty integrity (remove for speed)
    for item in all_inventory: 
        total_qtyopened = 0
        total_qtyunopened = 0
        for itemexpiry in item.expirydates.filter(archived = False):
            total_qtyopened += itemexpiry.quantityopen
            total_qtyunopened += itemexpiry.quantityunopened
        if total_qtyopened != item.total_quantityopen or total_qtyunopened != item.total_quantityunopened:
            item.total_quantityopen = total_qtyopened
            item.total_quantityunopened = total_qtyunopened
            item.save()
    
    if request.method == "POST":
        items=[]
        searchresults=[]
        #get user click in categories
        itemtype = request.POST.get('itemtype', None)
        #get user search
        searchthis = request.POST.get('searchthis', None)
        #alert
        alert = request.POST.get('alert', None)
        #find max qty for item expiry
        findmax = request.POST.get('findmax', None)
        #user clicks categories
        if itemtype is not None:
            if itemtype == "all":
                items=all_inventory
            elif itemtype == "cart":
                return redirect(reverse('activecart'))
            else:
                for inventory in all_inventory:
                    #add item in results if type = selected
                    if inventory.type == itemtype:
                        items.append(inventory)
            #pagination
            page_range, inv_list = pagination(request, items)
            return render (request, "inventory/items.html", {
                "items" : inv_list,
                'page_range': page_range,
                "typechoices": types,
                "itemtype": itemtype,
                "cart_type" : cart_type,
                "all_inventory":all_inventory
            })
        #user searches
        elif searchthis is not None:
            #remove whitespaces in query
            query = searchthis.replace(" ","")
            itemtype=None
            #if query is empty redirect to mainpage
            if query == "":
                return render (request, "inventory/items.html", {
                    "items" : inv_list,
                    'page_range': page_range,
                    "typechoices": types,
                    "cart_type" : cart_type,
                    "all_inventory":all_inventory
                })
            else:
                for inventory in all_inventory:
                    #if only one result
                    if query.lower() == inventory.name.lower().replace(" ",""):
                        return redirect('itementryselection', item = inventory.id)
                    #append to results
                    elif query.lower() in inventory.name.lower().replace(" ",""):
                        searchresults.append(inventory)
                #pagination
                page_range, inv_list = pagination(request, searchresults)
            return render (request, "inventory/items.html", {
                "items" : inv_list,
                'page_range': page_range,
                "typechoices": types,
                "itemtype": itemtype,
                "cart_type" : cart_type,
                "all_inventory":all_inventory
            })
        if alert is not None:
            result = check()
            return JsonResponse({"success":True, "responseText":result}, status = 200)
        if findmax != None:
            targetitem_exp = ItemExpiry.objects.get(id=findmax)
            current_open_qty = 0
            current_unopened_qty = 0
            duplicates = cart.objects.filter(archived = False, item = targetitem_exp)
            if len(duplicates) > 0:
                current_open_qty = 0
                current_unopened_qty = 0
                for activeitem in duplicates:
                    current_open_qty = activeitem.quantityopen
                    current_unopened_qty = activeitem.quantityunopened
            return JsonResponse({"success":True, "max_open":targetitem_exp.quantityopen - int(current_open_qty), "max_unopened":targetitem_exp.quantityunopened - int(current_unopened_qty)}, status = 200)
    else:
        return render (request, "inventory/items.html", {
            "items" : inv_list,
            'page_range': page_range,
            "typechoices": types,
            "cart": all_itemsincart,
            "cart_type" : cart_type,
            "all_inventory":all_inventory
        })


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def itementryselection(request, item):
    target = Item.objects.get(id=item)
    all_itemsincart = list(cart.objects.filter(archived=False))
    if len(all_itemsincart) > 0:
        if all_itemsincart[0].withdraw:
            for itemincart in all_itemsincart:
                if not itemincart.withdraw:
                    return render(request, "inventory/error.html",{
                        "message" : "Both deposit and withdraw items in cart!"
                    })
            cart_type = "withdraw"
        else:
            for itemincart in all_itemsincart:
                if itemincart.withdraw:
                    return render(request, "inventory/error.html",{
                        "message" : "Both deposit and withdraw items in cart!"
                    })
            cart_type = "deposit"
    else:
        cart_type = "empty"
    if cart_type == "withdraw":
        return redirect('itemwithdraw', item = item)
    elif cart_type == "deposit":
        return redirect('itemdeposit', item = item)
    else:
        return render (request, "inventory/targetitem.html", {
            "target": target,
        })


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def itemwithdraw(request, item):
    target = Item.objects.get(id=item)
    expirydates = target.expirydates.filter(archived=False).order_by('expirydate')
    max_opened = expirydates[0].quantityopen
    max_unopened = expirydates[0].quantityunopened
    if request.method =="POST":
        expiry_id = request.POST.get('expiry_id', None)
        if expiry_id is not None:
            expiry = ItemExpiry.objects.get(id=expiry_id)
            duplicates = cart.objects.filter(archived = False, item = expiry)
            if len(duplicates) > 0:
                current_open_qty = 0
                current_unopened_qty = 0
                for activeitem in duplicates:
                    current_open_qty = activeitem.quantityopen
                    current_unopened_qty = activeitem.quantityunopened
            return render (request, "inventory/withdraw_deposit.html", {
                "target": target,
                "expirydates" : expirydates,
                "type" : "Withdraw",
                "max_opened":expiry.quantityopen - int(current_open_qty),
                "max_unopened":expiry.quantityunopened - int(current_unopened_qty),
                "selected":expiry_id
            })
        else:
            qtyopen = request.POST.get('qtyopen', 0)
            qtyunopened = request.POST.get('qtyunopened', 0)
            cfm_expiry_id = request.POST.get('expiry', None)
            if qtyopen == "":
                qtyopen = 0
            if qtyunopened =="":
                qtyunopened = 0
            if int(qtyopen) + int(qtyunopened) == 0:
                return redirect('item_list')
            newitemincart = cart(item=ItemExpiry.objects.get(id=cfm_expiry_id), quantityopen=qtyopen, quantityunopened=qtyunopened, withdraw=True)
            newitemincart.save()
            #combine dups in cart
            all_activeitemsincart = cart.objects.filter(archived=False)
            cartitems = []
            for activeitemsincart in all_activeitemsincart:
                    if len(cartitems) <= 0:
                        cartitems.append(activeitemsincart)
                    else:
                        for item in cartitems:
                            if item.item.id == activeitemsincart.item.id and item.withdraw == activeitemsincart.withdraw:
                                activeitemsincart.quantityopen += item.quantityopen
                                activeitemsincart.quantityunopened += item.quantityunopened
                                activeitemsincart.save()
                                item.delete()
                        cartitems.append(activeitemsincart)
            all_activeitemsincart = list(cart.objects.filter(archived=False))
            all_activeitemsincart.reverse()

            return redirect('item_list')
    else:
        all_itemsincart = list(cart.objects.filter(archived=False))
        if len(all_itemsincart) > 0:
            if all_itemsincart[0].withdraw:
                for itemincart in all_itemsincart:
                    if not itemincart.withdraw:
                        return render(request, "inventory/error.html",{
                            "message" : "Both deposit and withdraw items in cart!"
                        })
                cart_type = "withdraw"
            else:
                for itemincart in all_itemsincart:
                    if itemincart.withdraw:
                        return render(request, "inventory/error.html",{
                            "message" : "Both deposit and withdraw items in cart!"
                        })
                cart_type = "deposit"
        else:
            cart_type = "empty"
        if cart_type == "deposit":
            return render(request, "inventory/error.html",{
                "message" : "Withdraw function disabled when cart contains a deposit item"
            })
        else:
            return render (request, "inventory/withdraw_deposit.html", {
                "target": target,
                "expirydates" : expirydates,
                "type" : "Withdraw",
                "max_opened":max_opened,
                "max_unopened":max_unopened
            })


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def itemdeposit(request, item):
    target = Item.objects.get(id=item)
    expirydates = target.expirydates.filter(archived=False).order_by('expirydate')
    if request.method =="POST":
        cfm_expiry_id = request.POST.get('expiry', None)
        qtyopen = request.POST.get('qtyopen', 0)
        qtyunopened = request.POST.get('qtyunopened', 0)
        if qtyopen == "":
                qtyopen = 0
        if qtyunopened =="":
            qtyunopened = 0
        if int(qtyopen) + int(qtyunopened) == 0:
            return redirect('item_list')
        if cfm_expiry_id == "new":
            newexpiry = request.POST.get('newexpiry', None)
            #check if expiry is present currently
            if len(list(ItemExpiry.objects.filter(expirydate=newexpiry, archived=False, item=target)))>0:
                return render(request, "inventory/error.html",{
                    "message" : "Expiry alr present!"
                })
            #check if item was present before
            if len(list(ItemExpiry.objects.filter(expirydate=newexpiry, archived=True, item=target)))==1:
                new_itemexpiry = list(ItemExpiry.objects.filter(expirydate=newexpiry, archived=True, item=target))[0]
                new_itemexpiry.archived=False
                if new_itemexpiry.quantityopen != 0 or  new_itemexpiry.quantityunopened != 0:
                    return render(request, "inventory/error.html",{
                        "message" : "Uncaught Error 583"
                    })
                new_itemexpiry.quantityopen = qtyopen
                new_itemexpiry.quantityunopened = qtyunopened
                new_itemexpiry.save()
            elif len(list(ItemExpiry.objects.filter(expirydate=newexpiry, archived=True, item=target)))==0:
                new_itemexpiry = ItemExpiry(expirydate = newexpiry, quantityopen = qtyopen, quantityunopened = qtyunopened, item = target)
                new_itemexpiry.save()
            else:
                return render(request, "inventory/error.html",{
                    "message" : "Uncaught Error 587"
                })
            new_order = order(ordering_account=request.user, reason="Replenishment of Supplies", ordertype = "Deposit")
            new_order.save()
            new_cart = cart(item=new_itemexpiry, order=new_order, quantityopen=qtyopen, quantityunopened=qtyunopened, withdraw=False, archived=True)
            new_cart.save()
            return redirect('item_list')
        newitemincart = cart(item=ItemExpiry.objects.get(id=cfm_expiry_id), quantityopen=qtyopen, quantityunopened=qtyunopened, withdraw=False)
        newitemincart.save()
        #combine dups in cart
        all_activeitemsincart = cart.objects.filter(archived=False)
        cartitems = []
        for activeitemsincart in all_activeitemsincart:
                if len(cartitems) <= 0:
                    cartitems.append(activeitemsincart)
                else:
                    for item in cartitems:
                        if item.item.id == activeitemsincart.item.id and item.withdraw == activeitemsincart.withdraw:
                            activeitemsincart.quantityopen += item.quantityopen
                            activeitemsincart.quantityunopened += item.quantityunopened
                            activeitemsincart.save()
                            item.delete()
                    cartitems.append(activeitemsincart)
        all_activeitemsincart = list(cart.objects.filter(archived=False))
        all_activeitemsincart.reverse()
        return redirect('item_list')
    else:
        all_itemsincart = list(cart.objects.filter(archived=False))
        if len(all_itemsincart) > 0:
            if all_itemsincart[0].withdraw:
                for itemincart in all_itemsincart:
                    if not itemincart.withdraw:
                        return render(request, "inventory/error.html",{
                            "message" : "Both deposit and withdraw items in cart!"
                        })
                cart_type = "withdraw"
            else:
                for itemincart in all_itemsincart:
                    if itemincart.withdraw:
                        return render(request, "inventory/error.html",{
                            "message" : "Both deposit and withdraw items in cart!"
                        })
                cart_type = "deposit"
        else:
            cart_type = "empty"
        if cart_type == "withdraw":
            return render(request, "inventory/error.html",{
                "message" : "Deposit function disabled when cart contains a withdraw item"
            })
        else:
            return render (request, "inventory/withdraw_deposit.html", {
                "target": target,
                "expirydates" : expirydates,
                "type" : "Deposit",
            })


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def activecart(request):
    all_activeitemsincart = list(cart.objects.filter(archived=False))
    all_activeitemsincart.reverse()
    all_kits = list(kits.objects.all())
    display_loans=[]
    replenish=True
    if len(all_activeitemsincart) > 0:
        #get active loans
        cartitems = []
        active_loans = loanorder.objects.filter(loan_active = True)
        active_loans = active_loans.reverse()
        for active_loan in active_loans:
            if active_loan.ordering_account == request.user :
                display_loans.append(active_loan)
        #ascertain cart type
        if all_activeitemsincart[0].withdraw:
            for itemincart in all_activeitemsincart:
                if not itemincart.withdraw:
                    return render(request, "inventory/error.html",{
                        "message" : "Both deposit and withdraw items in cart!"
                    })
            cart_type = "withdraw"
        else:
            for itemincart in all_activeitemsincart:
                if itemincart.withdraw:
                    return render(request, "inventory/error.html",{
                        "message" : "Both deposit and withdraw items in cart!"
                    })
            cart_type = "deposit"
        #combine duplicates
        for activeitemsincart in all_activeitemsincart:
            if len(cartitems) <= 0:
                cartitems.append(activeitemsincart)
            else:
                for item in cartitems:
                    if item.item.id == activeitemsincart.item.id and item.withdraw == activeitemsincart.withdraw:
                        activeitemsincart.quantityopen += item.quantityopen
                        activeitemsincart.quantityunopened += item.quantityunopened
                        activeitemsincart.save()
                        item.delete()
                cartitems.append(activeitemsincart)
        all_activeitemsincart = list(cart.objects.filter(archived=False))
        all_activeitemsincart.reverse()
        #check if replenish option is available
        replenish = True
        for activeitem in all_activeitemsincart:
            if activeitem.item.expirydate != None or cart_type !="deposit":
                replenish = False
    else:
        cart_type = "empty"


    if request.method == "POST":
        closethisitem = request.POST.get("closethis", None)
        loantarget = request.POST.get("loantarget", None)
        confirmeditsforthis = request.POST.get("confirmeditsforthis", None)

        #Remove item from cart
        if closethisitem is not None and closethisitem != "all":
            cartitem = cart.objects.filter(id=closethisitem)
            cartitem.delete()
            return redirect("activecart")

        #Remove all items from cart
        elif closethisitem == "all":
            for item in all_activeitemsincart:
                item.delete()
            return redirect("activecart")

        #cartedits
        if confirmeditsforthis != None:
            newqtyopen = request.POST.get("newqtyopen", None)
            newqtyunopened = request.POST.get("newqtyunopened", None)
            if newqtyopen == "":
                newqtyopen = 0
            if newqtyunopened == "":
                newqtyunopened = 0
            target = cart.objects.get(id=confirmeditsforthis)
            target.quantityopen = newqtyopen
            target.quantityunopened = newqtyunopened
            target.time = datetime.datetime.now()
            target.save()
            return redirect("activecart")

        #check loan
        elif loantarget is not None:
            targetloan = loanorder.objects.get(id=loantarget)
            if targetloan.ordering_account.username != request.user.username:
                return render(request, "inventory/error.html",{
                        "message" : "Target Loan is not yours! Fatal Filter Error"
                    }) 
            loanitems = list(targetloan.outstandingloan.all())
            cartitemid=[]
            loanitemid = []
            mismatch = []
            mismatchfatal = []
            message = []
            warn=[]
            for cartitem in all_activeitemsincart:
                cartitemid.append(cartitem.item.id)
            for loanitem in loanitems:
                loanitemid.append(loanitem.item.id)
                if loanitem.item.id not in cartitemid:
                    mismatch.append(loanitem)
            if len(mismatch) > 0:
                for m in mismatch:
                    messageappendthis = "Missing Item:"+ str(m.item.expirydate)+ ", " + m.item.item.name
                    message.append(messageappendthis)
            for cartitem in cartitemid:
                if cartitem not in loanitemid:
                    mismatchfatal.append(ItemExpiry.objects.get(id = cartitem))
            if len(mismatchfatal) > 0:
                itemerrorlist =""
                for m in mismatchfatal:
                    itemerrorlist = itemerrorlist + str(m.expirydate) + ", " + m.item.name
                return render(request, "inventory/error.html",{
                    "message" : itemerrorlist + " is not in selected loan but is present in your cart!"
                })
            for cartitem in all_activeitemsincart:
                for loanitem in loanitems:
                    warnappendthis=""
                    if cartitem.item.id == loanitem.item.id:
                        if cartitem.quantityopen > loanitem.quantityopen:
                            warnappendthis = str(loanitem.item.expirydate) + ", " + loanitem.item.item.name + " was loaned out as Unopened. You are returning it as Opened."
                            warn.append(warnappendthis)
                        if cartitem.quantityunopened > loanitem.quantityunopened:
                            return render(request, "inventory/error.html",{
                                "message" : str(cartitem.item.expirydate) + ", " + cartitem.item.item.name + " opened quantity in your cart is higher than loan quantity!"
                            })
                        cart_qty = cartitem.quantityopen + cartitem.quantityunopened
                        actual_qty = loanitem.quantityopen + loanitem.quantityunopened
                        if cart_qty < actual_qty:
                            messageappendthis = str(cart_qty)+" out of "+ str(actual_qty) + " "+ str(loanitem.item.expirydate) + ", " + loanitem.item.item.name + " in cart" +"."
                            message.append(messageappendthis)
                        elif cart_qty > actual_qty:
                            return render(request, "inventory/error.html",{
                                "message" : "Quantity of "+str(cartitem.item.expirydate) + ", " + cartitem.item.item.name + " in your cart is higher than loan quantity!"
                            })

            return render(request, "inventory/cart.html", {
                "items" : all_activeitemsincart,
                "typeofcart" : cart_type,
                "loans" : display_loans,
                "message": message,
                "check_completed" : True,
                "targetloan" : targetloan,
                "kits" : all_kits,
                "warn":warn
            })
                
        #submit order
        else:
            purposedeposit = request.POST.get("purposedeposit", None)
            purposewithdraw = request.POST.get("purposewithdraw", None)
            purposewithdrawothers = request.POST.get("purposewithdrawothers", None)
            purposedepositothers = request.POST.get("purposedepositothers", None)
            targetloantoreturn = request.POST.get("targetloantoreturn", None)
            discrepenciesselection = request.POST.get("discrepenciesselection", None)
            kit_to_stock_id = request.POST.get("kit_to_stock", None)
            #getting reason for withdraw/deposit
            if purposewithdraw == "Others":
                reasonwithdraw = purposewithdrawothers
            else:
                reasonwithdraw = purposewithdraw
            if purposedeposit == "Others":
                reasondeposit = purposedepositothers
            else:
                reasondeposit = purposedeposit
            
            if reasonwithdraw == "":
                reason = reasondeposit
                ordertype = "Deposit"
            else:
                reason = reasonwithdraw
                ordertype = "Withdraw"
            #check validity
            if len(all_activeitemsincart) ==0:
                return render(request, "inventory/error.html",{
                    "message" : "There are no items in cart!"
                })
            for activeitem in all_activeitemsincart:
                if activeitem.withdraw:
                    if activeitem.quantityopen > activeitem.item.quantityopen or activeitem.quantityunopened > activeitem.item.quantityunopened:
                        return render(request, "inventory/error.html",{
                            "message" : "Exceeded Maximum Qty for this item. Change Qty in cart."
                        })

            #saving order
            if reason == "Loan":
                #if loan, update loan model
                loaneename = request.POST.get("loaneename", None)
                loanenddate = request.POST.get("loanenddate", None)
                if loaneename == None or loanenddate ==None:
                    return render(request, "inventory/error.html",{
                        "message" : "Loanee Name and/or Loan end date is None"
                    })
                else:
                    newloan = loanorder(loanee_name = loaneename, ordering_account = request.user, loan_end_date = loanenddate, loan_active = True)
                    newloan.save()
            elif reason != "Loan Return":
                if reason == "Restocking of Pouches (Internal)":
                    kit_to_stock = kits.objects.get(id=kit_to_stock_id)
                    neworder = order(reason = reason, ordertype = ordertype, ordering_account = request.user, for_kit = kit_to_stock)
                    neworder.save()
                else:
                    neworder = order(reason = reason, ordertype = ordertype, ordering_account = request.user)
                    neworder.save()
            #deduct or add quantity in inventory
            loanreturncart = []
            for activeitem in all_activeitemsincart:
                if reason != "Loan" and reason != "Loan Return":
                    activeitem.order = neworder
                if activeitem.withdraw:
                    newquantityopen = int(activeitem.item.quantityopen) - int(activeitem.quantityopen)
                    newquantityunopened = int(activeitem.item.quantityunopened) - int(activeitem.quantityunopened)
                    if newquantityopen < 0 or newquantityunopened < 0:
                        return render(request, "inventory/error.html",{
                            "message" : "Error in active cart. Quantity below Zero. Report Error to developer"
                        })
                    else:
                        #check to archive or not
                        if newquantityopen == 0 and newquantityunopened == 0 and reason != "Loan":
                            activeitem.item.archived = True
                            for i in activeitem.item.loancartitem.filter(loan = True, expanded = False):
                                if i.order.loan_active:
                                    activeitem.item.archived = False
                else:
                    newquantityopen = int(activeitem.item.quantityopen) + int(activeitem.quantityopen)
                    newquantityunopened = int(activeitem.item.quantityunopened) + int(activeitem.quantityunopened)

                activeitem.item.quantityopen = newquantityopen
                activeitem.item.quantityunopened = newquantityunopened
                activeitem.archived = True
                activeitem.item.save()
                activeitem.save()
                #update total qty
                all_targetitem = list(activeitem.item.item.expirydates.all())
                total_qtyopen = 0
                total_qtyunopened = 0
                for targetitem in all_targetitem:
                    total_qtyopen += targetitem.quantityopen
                    total_qtyunopened += targetitem.quantityunopened
                activeitem.item.item.total_quantityopen = total_qtyopen
                activeitem.item.item.total_quantityunopened = total_qtyunopened
                activeitem.item.item.save()

                #update loan models
                #update loancart and outstanding loan upon new loan order
                if reason == "Loan":
                    newloancart = loancart(item = activeitem.item, order = newloan, quantityopen = activeitem.quantityopen, quantityunopened = activeitem.quantityunopened, loan = True, expanded = False)
                    updateoutstanding = loanoutstanding(order = newloan, item = activeitem.item,  quantityopen = activeitem.quantityopen, quantityunopened = activeitem.quantityunopened)
                    updateoutstanding.save()
                    newloancart.save()
                    activeitem.delete()
                #loan return
                elif reason == "Loan Return":
                    #update loancart
                    loan =  loanorder.objects.get(id=targetloantoreturn)
                    newloancart = loancart(item = activeitem.item, order = loan, quantityopen = activeitem.quantityopen, quantityunopened = activeitem.quantityunopened, loan = False)
                    loanreturncart.append(newloancart)
                    newloancart.save()
                    outstandingloans = loan.outstandingloan.all()
                    #close loan if cart and loan items match
                    if discrepenciesselection == None or discrepenciesselection == "":
                        for oustandingloan in outstandingloans:
                            oustandingloan.delete()
                        loan.loan_active = False
                        loan.save() 
                        activeitem.delete()
                    else:
                        #close loan as user selected remaining to have been expanded
                        if discrepenciesselection == "expanded":
                            for oustandingloan in outstandingloans:
                                if oustandingloan.item == activeitem.item:
                                    expanded_qtyopened = int(oustandingloan.quantityopen) - int(activeitem.quantityopen)
                                    expanded_qtyunopened = int(oustandingloan.quantityunopened) - int(activeitem.quantityunopened)
                                    expandedloancart = loancart(item = activeitem.item, order = loan, quantityopen = expanded_qtyopened, quantityunopened = expanded_qtyunopened, loan = True, expanded = True)
                                    expandedloancart.save()
                                    oustandingloan.delete()
                            loan.loan_active = False
                            loan.save()
                        #update outstanding loan, loan remains open
                        else:
                            for oustandingloan in outstandingloans:
                                if oustandingloan.item == activeitem.item:
                                    oustandingloan.quantityopen = int(oustandingloan.quantityopen) - int(activeitem.quantityopen)
                                    oustandingloan.quantityunopened = int(oustandingloan.quantityunopened) - int(activeitem.quantityunopened)
                                    if oustandingloan.quantityopen == 0 and oustandingloan.quantityunopened == 0:
                                        oustandingloan.delete()
                                    else:
                                        oustandingloan.save()
                            loan.save()
                        activeitem.delete()
            #update avg transaction time for item ordering
            update_transact_time(neworder, '')
            if reason == "Loan":
                #Report to TeleBot
                messagecart=""
                for cartitem in newloan.loancart.all():
                    quantity = int(cartitem.quantityopen) + int(cartitem.quantityunopened)
                    messagecart += " •  "+str(quantity)+ " " + cartitem.item.item.name + "; Expiry: " + str(cartitem.item.expirydate)+ "\n"
                    #check and report qty
                    target = cartitem.item
                    sendmessageforlowqty(target)
                messagetele = "\U00002796<u><b>Loan Request Processed</b></u>\U00002796\n\n<b>Loan No. "+ str(newloan.id)+"</b>\n\n"+str(messagecart)+"\n<code>For "+str(newloan.loanee_name)+" until "+ str(newloan.loan_end_date)+" authenticated by "+str(newloan.ordering_account.username)+"</code>\n\n <a href='https://playground.nhhs-sjb.org/home/receipt/loan/"+str(newloan.id)+"' >View Receipt Here</a>"
                telegram_bot_sendtext(messagetele)
                #Generate Receipt
                return redirect("receipt", type = "loan", ordernumber = newloan.id)
            elif reason == "Loan Return":
                #Report to TeleBot
                returnedmessagecart=""
                messagecart =""
                loanobject = loanorder.objects.get(id=targetloantoreturn)
                for returneditems in loanreturncart:
                    quantity = int(returneditems.quantityopen) + int(returneditems.quantityunopened)
                    returnedmessagecart += " •  "+str(quantity)+ " " + returneditems.item.item.name + "; Expiry: " + str(returneditems.item.expirydate)+ "\n"
                if loanobject.loan_active:
                    for cartitem in loanobject.outstandingloan.all():
                        quantity = int(cartitem.quantityopen) + int(cartitem.quantityunopened)
                        messagecart += " •  "+str(quantity)+ " " + cartitem.item.item.name + "; Expiry: " + str(cartitem.item.expirydate)+"\n"
                else:
                    messagecart = " •  "+"Loan Closed\n"
                messagetele = "\U00002795<u><b>Loan Return Request Processed</b></u>\U00002795\n\n<b>Order No. "+ str(loanobject.id)+"</b>\n\n<i>Returned:</i>\n"+str(returnedmessagecart)+"\n<i>Outstanding Items</i>\n"+str(messagecart)+"\n<code>For "+str(loanobject.loanee_name)+" until "+ str(loanobject.loan_end_date)+" authenticated by "+str(loanobject.ordering_account.username)+"</code>\n\n <a href='https://playground.nhhs-sjb.org/home/receipt/loan/"+str(loanobject.id)+"' >View Receipt Here</a>"
                telegram_bot_sendtext(messagetele)
                #Generate Receipt
                return redirect("receipt", type = "loan", ordernumber = targetloantoreturn)
            else:
                #Report to TeleBot
                messagecart=""
                for cartitem in neworder.cart.all():
                    quantity = int(cartitem.quantityopen) + int(cartitem.quantityunopened)
                    messagecart += " •  "+str(quantity)+ " " + cartitem.item.item.name + "; Expiry: " + str(cartitem.item.expirydate)+"\n"
                    #check and report qty
                    target = cartitem.item
                    sendmessageforlowqty(target)
                if neworder.ordertype =="Withdraw":
                    if neworder.for_kit is None:
                        messagetele = "\U00002796<u><b>Withdrawal Request Processed</b></u>\U00002796\n\n<b>Order No. "+ str(neworder.id)+"</b>\n"+"<i>"+str(neworder.reason)+"</i>\n\n"+str(messagecart)+"\n<code>Authenticated by "+str(neworder.ordering_account.username)+"</code>\n\n <a href='https://playground.nhhs-sjb.org/home/receipt/order/"+str(neworder.id)+"' >View Receipt Here</a>"
                    else:
                        messagetele = "\U00002796<u><b>Withdrawal Request Processed</b></u>\U00002796\n\n<b>Order No. "+ str(neworder.id)+"</b>\n"+"<i>"+str(neworder.reason)+" for Kit "+str(neworder.for_kit.name)+"</i>\n\n"+str(messagecart)+"\n<code>Authenticated by "+str(neworder.ordering_account.username)+"</code>\n\n <a href='https://playground.nhhs-sjb.org/home/receipt/order/"+str(neworder.id)+"' >View Receipt Here</a>"
                else:
                    messagetele = "\U00002795<u><b>Deposit Request Processed</b></u>\U00002795\n\n<b>Order No. "+ str(neworder.id)+"</b>\n"+"<i>"+str(neworder.reason)+"</i>\n\n"+str(messagecart)+"\n<code>Authenticated by "+str(neworder.ordering_account.username)+"</code>\n\n <a href='https://playground.nhhs-sjb.org/home/receipt/order/"+str(neworder.id)+"' >View Receipt Here</a>"
                telegram_bot_sendtext(messagetele)
                #Generate Receipt
                return redirect("receipt", type = "order", ordernumber = neworder.id)

    else:
        return render(request, "inventory/cart.html", {
            "items" : all_activeitemsincart,
            "typeofcart" : cart_type,
            "loans" : display_loans,
            "kits" : all_kits,
            "check_completed" : False,
            "replenish": replenish
        })


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def receipt(request, type, ordernumber):
    if type == "order":
        try:
            targetorder = order.objects.get(id=ordernumber)
        except order.DoesNotExist:
            raise Http404() 
    else:
        try:
            targetorder  = loanorder.objects.get(id=ordernumber)
        except loanorder.DoesNotExist:
            raise Http404()   
    return render(request, "inventory/receipt.html",{
        "targetorder" : targetorder,
        "type" : type
    })


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def orderlogs(request):
    all_orders = list(order.objects.all())
    all_orders_id = simplejson.dumps(list(order.objects.values_list('id', flat=True)))
    all_loans_id = simplejson.dumps(list(loanorder.objects.values_list('id', flat=True)))
    all_orders.reverse()
    all_active_loans_id = simplejson.dumps(list(loanorder.objects.filter(loan_active = True, ordering_account = request.user).values_list('id', flat=True)))
    all_loans = list(loanorder.objects.all())
    all_active_loans = list(loanorder.objects.filter(loan_active = True, ordering_account = request.user))
    all_active_loans.reverse()
    all_loans.reverse()
    unique_reason = (list(set(order.objects.values_list('reason', flat=True))))
    unique_loanee_name = (list(set(loanorder.objects.values_list('loanee_name', flat=True))))
    if request.method == "POST":
        selectedthis = request.POST.get("selectedthis", None)
        selectedthisloan = request.POST.get("selectedthisloan", None)
        orders_to_remove = request.POST.get("ordertoremove", None)
        loan_to_remove = request.POST.get("loantoremove", None)
        selectedthisactiveloan = request.POST.get("selectedthisactiveloan", None)
        expandedloan = request.POST.get("expandedloan", None)

        if selectedthis != None :
            try:
                selectedorder = order.objects.get(id=selectedthis)
            except order.DoesNotExist:
                return JsonResponse({"success":False, "responseText":"Order has already been removed. Refreshing your page."}, status = 200)
            if selectedorder.reason == "Restocking of Pouches":
                return render(request, "inventory/orderlogs.html", {
                    "message" : "You can't remove this order. Remove this order from the Kits Logs",
                    "targetorder" : selectedorder,
                    "allordersid" : all_orders_id,
                    "targetid" : selectedthis,
                    "allorders" : all_orders,
                    "allloans" : all_loans,
                    "all_active_loans" : all_active_loans,
                    "all_active_loans_id" : all_active_loans_id,
                    "allloansid" : all_loans_id,
                    "order_reasons" : unique_reason,
                    "loanee_names": unique_loanee_name,
                })
            cartitems = list(selectedorder.cart.all())
            return render(request, "inventory/orderlogs.html", {
                "targetorder" : selectedorder,
                "allordersid" : all_orders_id,
                "targetid" : selectedthis,
                "cartitems" : cartitems,
                "allorders" : all_orders,
                "allloans" : all_loans,
                "all_active_loans" : all_active_loans,
                "all_active_loans_id" : all_active_loans_id,
                "allloansid" : all_loans_id,
                "order_reasons" : unique_reason,
                "loanee_names": unique_loanee_name,
            })
        #user says loan expanded
        elif expandedloan != None:
            try:
                selectedloan = loanorder.objects.get(id=expandedloan)
            except loanorder.DoesNotExist:
                return JsonResponse({"success":False, "responseText":"Loan has been removed. Refreshing your page."}, status = 200)
            if not selectedloan.loan_active:
                return JsonResponse({"success":False, "responseText":"Loan is not active. Refreshing your page."}, status = 200)
            elif selectedloan.ordering_account != request.user:
                return JsonResponse({"success":False, "responseText":"You don't have permission to edit this loan"}, status = 200)
            else:
                messagecart = ""
                for loanitem in selectedloan.loancart.all():
                    newloancart = loancart(item = loanitem.item, order = loanitem.order, quantityopen = loanitem.quantityopen, quantityunopened = loanitem.quantityunopened, loan = False, expanded = True)
                    newloancart.save()
                    quantity = int(loanitem.quantityopen) + int(loanitem.quantityunopened)
                    messagecart += " •  "+str(quantity)+ " " + loanitem.item.item.name +"; Expiry: "+str(loanitem.item.expirydate)+"\n"
                #check to archive
                if loanitem.item.quantityopen == 0 and loanitem.item.quantityunopened == 0:
                    loanitem.item.archived = True
                    loanitem.item.save()
                selectedloan.loan_active = False
                selectedloan.save()
                messagetele = "\U00002796<u><b>Loan Expanded Request Processed</b></u>\U00002796\n\n<b>Loan No. "+ str(selectedloan.id)+"</b>\n\n"+str(messagecart)+"\n<code>For "+str(selectedloan.loanee_name)+" authenticated by "+str(selectedloan.ordering_account.username)+"</code>\n\n <a href='https://playground.nhhs-sjb.org/home/receipt/loan/"+str(selectedloan.id)+"' >View Receipt Here</a>"
                telegram_bot_sendtext(messagetele)
                return render(request, "inventory/orderlogs.html", {
                    "allorders" : all_orders,
                    "allordersid" : all_orders_id,
                    "allloans" : all_loans,
                    "all_active_loans" : all_active_loans,
                    "all_active_loans_id" : all_active_loans_id,
                    "order_reasons" : unique_reason,
                    "loanee_names": unique_loanee_name,
                    "allloansid" : all_loans_id
                })
        #to display loan items when user selects a loan in expanded loans
        elif selectedthisactiveloan != None:
            try:
                selectedloan = loanorder.objects.get(id=selectedthisactiveloan)
            except loanorder.DoesNotExist:
                return JsonResponse({"success":False, "responseText":"Loan has already been removed. Refreshing your page."}, status = 200)
            if not selectedloan.loan_active:
                return JsonResponse({"success":False, "responseText":"Loan is not active. Refreshing your page."}, status = 200)
            else:
                cartitems = list(selectedloan.loancart.filter(loan=True))
                outstandingloanitems = list(selectedloan.outstandingloan.all())
                return render(request, "inventory/orderlogs.html", {
                    "targetactiveloan" : selectedloan,
                    "allordersid" : all_orders_id,
                    "targetactiveloanid" : selectedthisactiveloan,
                    "outstandingactiveloanitems" : outstandingloanitems,
                    "loancartitems" : cartitems,
                    "allorders" : all_orders,
                    "allloans" : all_loans,
                    "all_active_loans" : all_active_loans,
                    "all_active_loans_id" : all_active_loans_id,
                    "order_reasons" : unique_reason,
                    "loanee_names": unique_loanee_name,
                    "allloansid" : all_loans_id
                })
        #to display loan items when user selects a loan in remove loans
        elif selectedthisloan!= None:
            try:
                selectedloan = loanorder.objects.get(id=selectedthisloan)
            except loanorder.DoesNotExist:
                return JsonResponse({"success":False, "responseText":"Loan has already been removed. Refreshing your page."}, status = 200)
            cartitems = list(selectedloan.loancart.filter(loan=True, expanded = False))
            outstandingloanitems = list(selectedloan.outstandingloan.all())
            return render(request, "inventory/orderlogs.html", {
                "targetloan" : selectedloan,
                "allordersid" : all_orders_id,
                "targetloanid" : selectedthisloan,
                "outstandingloanitems" : outstandingloanitems,
                "loancartitems" : cartitems,
                "allorders" : all_orders,
                "allloans" : all_loans,
                "all_active_loans" : all_active_loans,
                "all_active_loans_id" : all_active_loans_id,
                "order_reasons" : unique_reason,
                "loanee_names": unique_loanee_name,
                "allloansid" : all_loans_id
            })
        #user says remove this order
        elif orders_to_remove != None:
            try:
                orderremove = order.objects.get(id=orders_to_remove)
            except order.DoesNotExist:
                return JsonResponse({"success":False, "responseText":"Order has already been removed. Refresh your page."}, status = 200)
            returncart = list(orderremove.cart.all())
            for returnitems in returncart:
                if returnitems.withdraw:
                    returnitems.item.quantityopen+= int(returnitems.quantityopen)
                    returnitems.item.item.total_quantityopen += int(returnitems.quantityopen)
                    returnitems.item.quantityunopened += int(returnitems.quantityunopened)
                    returnitems.item.item.total_quantityunopened += int(returnitems.quantityunopened)
                    returnitems.item.archived = False
                else:
                    returnitems.item.quantityopen -= int(returnitems.quantityopen)
                    returnitems.item.item.total_quantityopen -= int(returnitems.quantityopen)
                    returnitems.item.quantityunopened -= int(returnitems.quantityunopened)
                    returnitems.item.item.total_quantityunopened -= int(returnitems.quantityunopened)
                    if returnitems.item.quantityopen == 0 and returnitems.item.quantityunopened == 0:
                        returnitems.item.archived = True
                if returnitems.item.quantityopen < 0 or returnitems.item.quantityunopened < 0:
                    return JsonResponse({"success":False, "responseText":"New qty will be below 0! Unable to remove order!"}, status = 200)
                else:
                    #update total quantity
                    returnitems.item.item.save()
                    returnitems.item.save()
            #reprt to telebot
            messagecart =""
            for cartitem in returncart:
                    if int(cartitem.quantityopen) > 0:
                        messagecart += " •  "+str(cartitem.quantityopen)+ " Opened " + cartitem.item.item.name + "; Expiry: "+str(cartitem.item.expirydate) + "\n"
                    if int(cartitem.quantityunopened) > 0:
                        messagecart += " •  "+str(cartitem.quantityunopened)+ " Unopened " + cartitem.item.item.name + "; Expiry: "+str(cartitem.item.expirydate) +"\n"
                    #check and report
                    if not cartitem.withdraw:
                        target = cartitem.item
                        sendmessageforlowqty(target)
            messagetele = "\U0000274C<u><b>Order " + str(orderremove.id)+" has been deleted</b></u>\U0000274C\n\n"+str(messagecart)+"\n<code>Ordered by "+str(orderremove.ordering_account)+"\nOrder Cancellation by: "+str(request.user.username)+"</code>"
            telegram_bot_sendtext(messagetele)
            #update avg transaction time for item ordering
            update_transact_time(orderremove, 'delete')
            orderremove.delete()
            return render(request, "inventory/orderlogs.html", {
                "allordersid" : all_orders_id,
                "targetid" : selectedthis,
                "allorders" : all_orders,
                "allloans" : all_loans,
                "all_active_loans" : all_active_loans,
                "all_active_loans_id" : all_active_loans_id,
                "order_reasons" : unique_reason,
                "loanee_names": unique_loanee_name,
                "allloansid" : all_loans_id
            })
        #user says remove this loan
        elif loan_to_remove != None:
            try:
                loanremove = loanorder.objects.get(id=loan_to_remove)
            except loanorder.DoesNotExist:
                return JsonResponse({"success":False, "responseText":"Loan has already been removed. Refresh your page."}, status = 200)
            returncart = list(loanremove.loancart.all())
            for returnitems in returncart:
                if returnitems.loan and not returnitems.expanded:
                    returnitems.item.quantityopen+= int(returnitems.quantityopen)
                    returnitems.item.item.total_quantityopen += int(returnitems.quantityopen)
                    returnitems.item.quantityunopened += int(returnitems.quantityunopened)
                    returnitems.item.item.total_quantityunopened += int(returnitems.quantityunopened)
                    returnitems.item.archived = False
                elif not returnitems.loan and not returnitems.expanded:
                    returnitems.item.quantityopen -= int(returnitems.quantityopen)
                    returnitems.item.item.total_quantityopen -= int(returnitems.quantityopen)
                    returnitems.item.quantityunopened -= int(returnitems.quantityunopened)
                    returnitems.item.item.total_quantityunopened -= int(returnitems.quantityunopened)
                    if returnitems.item.quantityopen == 0 and returnitems.item.quantityunopened == 0:
                        returnitems.item.archived = True
                #update total quantity
                returnitems.item.item.save()
                returnitems.item.save()
            messagecart =""
            for cartitem in loanremove.loancart.filter(loan=True, expanded = False):
                    if int(cartitem.quantityopen) > 0:
                        messagecart += str(cartitem.quantityopen)+ " Opened " + cartitem.item.item.name+ str(cartitem.item.expirydate) +"\n"
                    if int(cartitem.quantityunopened) > 0:
                        messagecart += str(cartitem.quantityunopened)+ " Unopened " + cartitem.item.item.name+ str(cartitem.item.expirydate) +"\n"
            messagetele = "\U0000274C<u><b>Loan " + str(loanremove.id)+" has been deleted</b></u>\U0000274C\n\n"+str(messagecart)+"\n<code>For "+str(loanremove.loanee_name)+" ordered by "+str(loanremove.ordering_account)+"\nOrder Cancellation by: "+str(request.user.username)+"</code>"
            telegram_bot_sendtext(messagetele)
            #update avg transaction time for item ordering
            update_transact_time(loanremove, 'delete')
            loanremove.delete()
            return render(request, "inventory/orderlogs.html", {
                "allordersid" : all_orders_id,
                "targetloanid" : selectedthisloan,
                "allorders" : all_orders,
                "allloans" : all_loans,
                "all_active_loans" : all_active_loans,
                "all_active_loans_id" : all_active_loans_id,
                "order_reasons" : unique_reason,
                "loanee_names": unique_loanee_name,
                "allloansid" : all_loans_id
            })
        else:
            datetosearch = request.POST.get("datetosearch", None)
            daterangefrom = request.POST.get("daterangefrom", None)
            daterangeto = request.POST.get("daterangeto", None)
            reason = request.POST.get("reason", None)
            loan_datetosearch = request.POST.get("loandatetosearch", None)
            loan_daterangefrom = request.POST.get("loandaterangefrom", None)
            loan_daterangeto = request.POST.get("loandaterangeto", None)
            loanee_name = request.POST.get("loaneename", None)
            if datetosearch != None:
                datetosearch_year =""
                datetosearch_month=""
                datetosearch_day=""
                for i in range(len(datetosearch)):
                    if i < 4:
                        datetosearch_year += datetosearch[i]
                    elif 4 < i < 7:
                        datetosearch_month += datetosearch[i]
                    elif 7 < i :
                        datetosearch_day += datetosearch[i]
            if loan_datetosearch != None:
                loan_datetosearch_year =""
                loan_datetosearch_month=""
                loan_datetosearch_day=""
                for i in range(len(loan_datetosearch)):
                    if i < 4:
                        loan_datetosearch_year += loan_datetosearch[i]
                    elif 4 < i < 7:
                        loan_datetosearch_month += loan_datetosearch[i]
                    elif 7 < i :
                        loan_datetosearch_day += loan_datetosearch[i]
            if datetosearch == '':
                datetosearch = None
            if daterangefrom == '':
                daterangefrom = None
            if daterangeto == '':
                daterangeto = None
            if reason == '':
                reason = None
            if loan_datetosearch == '':
                loan_datetosearch = None
            if loan_daterangefrom == '':
                loan_daterangefrom = None
            if loan_daterangeto == '':
                loan_daterangeto = None
            if loanee_name == '':
                loanee_name = None
            if datetosearch == None and daterangefrom == None and daterangeto == None and reason == None and loan_datetosearch == None and loan_daterangefrom == None and loan_daterangeto == None and loanee_name == None:
                return render(request, "inventory/orderlogs.html", {
                    "allorders" : all_orders,
                    "allordersid" : all_orders_id,
                    "allloans" : all_loans,
                    "all_active_loans" : all_active_loans,
                    "all_active_loans_id" : all_active_loans_id,
                    "order_reasons" : unique_reason,
                    "loanee_names": unique_loanee_name,
                    "allloansid" : all_loans_id
                })
            elif datetosearch == None and daterangefrom == None and daterangeto == None and reason == None:
                filtertype = "Loan"
            elif loan_datetosearch == None and loan_daterangefrom == None and loan_daterangeto == None and loanee_name == None:
                filtertype = "Order"
            else:
                return render(request, "inventory/error.html",{
                    "message" : "Uncaught Error at orderlogs"
                })
            #if filtering Loans only
            if filtertype == "Loan":
                #user select loan filter by loanee name
                if loan_datetosearch == None and loan_daterangefrom == None and loan_daterangeto == None and loanee_name != None:
                    all_loans = list(loanorder.objects.filter(loanee_name=loanee_name))
                    return render(request, "inventory/orderlogs.html", {
                        "allorders" : all_orders,
                        "allordersid" : all_orders_id,
                        "allloans" : all_loans,
                        "all_active_loans" : all_active_loans,
                        "all_active_loans_id" : all_active_loans_id,
                        "order_reasons" : unique_reason,
                        "loanee_names": unique_loanee_name,
                        "allloansid" : all_loans_id
                    })
                #user select loan filter by exact date
                elif loanee_name == None and loan_datetosearch != None and loan_daterangefrom == None and loan_daterangeto == None:
                    all_loans = list(loanorder.objects.filter(time__year=loan_datetosearch_year, time__month = loan_datetosearch_month, time__day = loan_datetosearch_day))
                    return render(request, "inventory/orderlogs.html", {
                        "allorders" : all_orders,
                        "allordersid" : all_orders_id,
                        "allloans" : all_loans,
                        "all_active_loans" : all_active_loans,
                        "all_active_loans_id" : all_active_loans_id,
                        "order_reasons" : unique_reason,
                        "loanee_names": unique_loanee_name,
                        "allloansid" : all_loans_id
                    })
                #user select loan filter by date range
                elif loanee_name == None and loan_datetosearch == None and loan_daterangefrom != None and loan_daterangeto != None:
                    if daterangefrom == daterangeto:
                        all_loans=list(loanorder.objects.filter(time__contains=loan_daterangefrom))
                    else:
                        all_loans=list(loanorder.objects.filter(time__range=[loan_daterangefrom, loan_daterangeto]))
                    return render(request, "inventory/orderlogs.html", {
                        "allorders" : all_orders,
                        "allordersid" : all_orders_id,
                        "allloans" : all_loans,
                        "all_active_loans" : all_active_loans,
                        "all_active_loans_id" : all_active_loans_id,
                        "order_reasons" : unique_reason,
                        "loanee_names": unique_loanee_name,
                        "allloansid" : all_loans_id
                    })
                #user select loan filter by date range and loanee name
                elif loan_datetosearch == None and loan_daterangefrom != None and loan_daterangeto != None and loanee_name != None:
                    if daterangefrom == daterangeto:
                        all_loans=list(loanorder.objects.filter(time__contains=loan_daterangefrom, loanee_name=loanee_name))
                    else:
                        all_loans=list(loanorder.objects.filter(time__range=[loan_daterangefrom, loan_daterangeto], loanee_name=loanee_name))
                    return render(request, "inventory/orderlogs.html", {
                        "allorders" : all_orders,
                        "allordersid" : all_orders_id,
                        "allloans" : all_loans,
                        "all_active_loans" : all_active_loans,
                        "all_active_loans_id" : all_active_loans_id,
                        "order_reasons" : unique_reason,
                        "loanee_names": unique_loanee_name,
                        "allloansid" : all_loans_id
                    })
                #user select loan filter by loanee name and exact date
                elif loan_datetosearch != None and loan_daterangefrom == None and loan_daterangeto == None and loanee_name != None:
                    all_loans = list(loanorder.objects.filter(loanee_name=loanee_name, time__year=loan_datetosearch_year, time__month = loan_datetosearch_month, time__day = loan_datetosearch_day))
                    return render(request, "inventory/orderlogs.html", {
                        "allorders" : all_orders,
                        "allordersid" : all_orders_id,
                        "allloans" : all_loans,
                        "all_active_loans" : all_active_loans,
                        "all_active_loans_id" : all_active_loans_id,
                        "order_reasons" : unique_reason,
                        "loanee_names": unique_loanee_name,
                        "allloansid" : all_loans_id
                    })
                #catch all errors 
                else:
                    return render(request, "inventory/error.html",{
                        "message": "Uncaught error at orderlogs check POST data for Loans"
                    })
            #filtering orders only
            elif filtertype == "Order":
                #user select order filter by reason
                if datetosearch == None and daterangefrom == None and daterangeto == None and reason != None:
                    all_orders = list(order.objects.filter(reason=reason))
                    return render(request, "inventory/orderlogs.html", {
                        "allorders" : all_orders,
                        "allordersid" : all_orders_id,
                        "allloans" : all_loans,
                        "all_active_loans" : all_active_loans,
                        "all_active_loans_id" : all_active_loans_id,
                        "order_reasons" : unique_reason,
                        "loanee_names": unique_loanee_name,
                        "allloansid" : all_loans_id
                    })
                #user select order filter by exact date
                elif datetosearch != None and daterangefrom == None and daterangeto == None and reason == None:
                    all_orders = list(order.objects.filter(time__year=datetosearch_year, time__month = datetosearch_month, time__day = datetosearch_day))
                    return render(request, "inventory/orderlogs.html", {
                        "allorders" : all_orders,
                        "allordersid" : all_orders_id,
                        "allloans" : all_loans,
                        "all_active_loans" : all_active_loans,
                        "all_active_loans_id" : all_active_loans_id,
                        "order_reasons" : unique_reason,
                        "loanee_names": unique_loanee_name,
                        "allloansid" : all_loans_id
                    })
                #user select order filter by date range
                elif datetosearch == None and daterangefrom != None and daterangeto != None and reason == None:
                    if daterangefrom == daterangeto:
                        all_orders = list(order.objects.filter(time__contains=daterangeto))
                    else:
                        all_orders = list(order.objects.filter(time__range=[daterangefrom, daterangeto]))
                    return render(request, "inventory/orderlogs.html", {
                        "allorders" : all_orders,
                        "allordersid" : all_orders_id,
                        "allloans" : all_loans,
                        "all_active_loans" : all_active_loans,
                        "all_active_loans_id" : all_active_loans_id,
                        "order_reasons" : unique_reason,
                        "loanee_names": unique_loanee_name,
                        "allloansid" : all_loans_id
                    })
                #user select order filter by date range and reason
                elif datetosearch == None and daterangefrom != None and daterangeto != None and reason != None:
                    if daterangeto == daterangefrom:
                        all_orders = list(order.objects.filter(time__contains=daterangefrom, reason = reason))
                    else:
                        all_orders = list(order.objects.filter(time__range=[daterangefrom, daterangeto], reason = reason))
                    return render(request, "inventory/orderlogs.html", {
                        "allorders" : all_orders,
                        "allordersid" : all_orders_id,
                        "allloans" : all_loans,
                        "all_active_loans" : all_active_loans,
                        "all_active_loans_id" : all_active_loans_id,
                        "order_reasons" : unique_reason,
                        "loanee_names": unique_loanee_name,
                        "allloansid" : all_loans_id
                    })
                #user select order filter by exact date and reason
                elif datetosearch != None and daterangefrom == None and daterangeto == None and reason != None:
                    all_orders = list(order.objects.filter(time__year=datetosearch_year, time__month = datetosearch_month, time__day = datetosearch_day, reason = reason))
                    return render(request, "inventory/orderlogs.html", {
                        "allorders" : all_orders,
                        "allordersid" : all_orders_id,
                        "allloans" : all_loans,
                        "all_active_loans" : all_active_loans,
                        "all_active_loans_id" : all_active_loans_id,
                        "order_reasons" : unique_reason,
                        "loanee_names": unique_loanee_name,
                        "allloansid" : all_loans_id
                    })
                #catch all errors
                else:
                    return render(request, "inventory/error.html",{
                        "message": "Uncaught error at orderlogs check POST data for Orders"
                    })
    else:
        return render(request, "inventory/orderlogs.html", {
            "allorders" : all_orders,
            "allordersid" : all_orders_id,
            "allloans" : all_loans,
            "all_active_loans" : all_active_loans,
            "all_active_loans_id" : all_active_loans_id,
            "order_reasons" : unique_reason,
            "loanee_names": unique_loanee_name,
            "allloansid" : all_loans_id
        })


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')    
def kits_list(request):
    all_kits = orderkits()
    all_itemsincart = list(kitloancart.objects.filter(archived=False))
    categories = ["Available", "Unstocked", "In Use"]
    if len(all_itemsincart) > 0:
        if all_itemsincart[0].loan:
            for itemincart in all_itemsincart:
                if not itemincart.loan:
                    return render(request, "inventory/error.html",{
                        "message" : "Both deposit and withdraw items in cart!"
                    })
            cart_type = "withdraw"
        else:
            for itemincart in all_itemsincart:
                if itemincart.loan:
                    return render(request, "inventory/error.html",{
                        "message" : "Both deposit and withdraw items in cart!"
                    })
            cart_type = "deposit"
    else:
        cart_type = "empty"
    #check kit expiry(slow)
    for kit in all_kits:
        kitexpiry = datetime.date.today() + datetime.timedelta(days=9999)
        for kit_item in kit.items.all():
            if len(list(kit_item.itemexpiry.filter(archived=False))) > 1:
                nearest_expiry_item = list(kit_item.itemexpiry.filter(archived=False).exclude(quantity=0).order_by('expirydate'))[-1]
            else:
                nearest_expiry_item = kit_item.itemexpiry.filter(archived=False).first()
            if nearest_expiry_item.expirydate.expirydate != None:
                if nearest_expiry_item.expirydate.expirydate < kitexpiry:
                    kitexpiry = nearest_expiry_item.expirydate.expirydate
        if kitexpiry != datetime.date.today() - datetime.timedelta(days=9999):
            kit.nearest_expiry = kitexpiry
            kit.save()
        c=True
        for kititem in kit.items.all():
            if c == True and kititem.quantity != kititem.quantity_max and not kit.forced:
                kit.status = "Unstocked"
                kit.save()
                c=False
    #pagination
    page_range, inv_list = pagination(request, all_kits)

    if request.method == "POST":
        items=[]
        searchresults=[]
        itemtype = request.POST.get('itemtype', None)
        searchthis = request.POST.get('searchthis', None)
        if itemtype is not None:
            if itemtype == "all":
                items=all_kits
            elif itemtype == "cart":
                return redirect(reverse('kits_activecart'))
            else:
                for inventory in all_kits:
                    if inventory.kit_type == itemtype:
                        items.append(inventory)
                    elif inventory.status == itemtype:
                        items.append(inventory)
            #pagination
            page_range, inv_list = pagination(request, items)
            return render (request, "inventory/kits.html", {
                "items" : inv_list,
                'page_range': page_range,
                "typechoices": categories,
                "itemtype": itemtype,
                "cart_type" : cart_type
            })

        elif searchthis is not None:
            query = searchthis.replace(" ","")
            itemtype=None
            if query == "":
                return render (request, "inventory/kits.html", {
                    "items" : inv_list,
                    'page_range': page_range,
                    "typechoices": categories,
                    "cart_type" : cart_type
                })
            else:
                for inventory in all_kits:
                    if query.lower() == inventory.name.lower().replace(" ",""):
                        return redirect('selectedkit', kit= inventory.id)
                    if query.lower() in inventory.name.lower().replace(" ",""):
                        searchresults.append(inventory)
                #pagination
                page_range, inv_list = pagination(request, searchresults)
            return render (request, "inventory/kits.html", {
                "items" : inv_list,
                'page_range': page_range,
                "typechoices": categories,
                "itemtype": itemtype,
                "cart_type" : cart_type
            })
    else:
        return render (request, "inventory/kits.html", {
            "items" : inv_list,
            'page_range': page_range,
            "typechoices": categories,
            "cart": all_itemsincart,
            "cart_type" : cart_type
        })


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')    
def kits_withdraw(request, item):
    item = kits.objects.get(name = item)
    all_kititems = list(item.items.all())
    #check if qty in two tables match and kit is stocked
    for kititem in all_kititems:
        if int(kititem.quantity) != int(kititem.itemexpiry.all().aggregate(Sum('quantity'))['quantity__sum']):
            return render(request, "inventory/error.html",{
                "message" : "Values Mismatch Error 12 "
            })
        if request.method!="POST":
            if int(kititem.quantity) != int(kititem.quantity_max):
                return render(request, "inventory/error.html",{
                    "message" : "Item is not fully stocked! Fatal Error"
                })
    #check if kit is alr been loaned out
    if item.status == "In Use":
        return render(request, "inventory/error.html",{
            "message" : "Kit is already loaned out"
        })
    #check if kit is alr in cart
    if len(item.kitloancartitem.all()) !=0:
        if item.kitloancartitem.last().archived == False:
            return render(request, "inventory/error.html",{
                "message" : "Kit is already in cart!"
            })
    if request.method=="POST":
        newcartitem = kitloancart(item = item, ordering_account = request.user, loan=True, archived = False)
        #unarchive temp cart
        tempcartitems_to_uncarchive=list(tempcart.objects.filter(kit=item, archived=True))
        tempcartitems_to_uncarchive.reverse()
        if len(tempcartitems_to_uncarchive) == 0:
            return JsonResponse({"error": "Filter Found Nothing!"}, status=200)
        tofollow=tempcartitems_to_uncarchive[0].batchnum
        if tofollow ==0:
            return JsonResponse({"error": "Batch Number Error"}, status=200)
        listtounarchive=[]
        for tempcartitem in tempcartitems_to_uncarchive:
            if tempcartitem.batchnum == tofollow:
                listtounarchive.append(tempcartitem)
            else:
                break
        for listindex in listtounarchive:
            listindex.archived=False
            listindex.compulsory=True
            listindex.save()
        item.forced=True
    else:
        newcartitem = kitloancart(item = item, ordering_account = request.user, loan=True, archived = False)
    item.status = "In Cart"
    item.save()
    newcartitem.save()
    return redirect('kits_list')


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')    
def kits_restock(request, item):
    item_object = kits.objects.get(name = item)
    if len(list(kitloancart.objects.filter(item = item_object))) > 0:
        last_user_cart = list(kitloancart.objects.filter(item = item_object))[-1]
    else:
        last_user_cart = None
    if item_object.status != "Unstocked":
        return render(request, "inventory/error.html",{
            "message" : "Status of Kit is not 'Unstocked'"
        })
    #find what is missing
    to_stock=[]
    all_kititems = list(item_object.items.all())
    for kititem in all_kititems:
        if kititem.quantity < kititem.quantity_max:
            to_stock.append(kititem)
        elif kititem.quantity > kititem.quantity_max:
            return render(request, "inventory/error.html",{
                "message" : "Failsafe Check 01 Failed (Max Q Exceeded)"
            })
    #if nothing to stock
    if len(to_stock) == 0:
        return render(request, "inventory/error.html",{
            "message" : "There is nothing to stock"
        })
    #check if qty in two tables match
    for kititem in all_kititems:
        if int(kititem.quantity) != int(kititem.itemexpiry.all().aggregate(Sum('quantity'))['quantity__sum']):
            return render(request, "inventory/error.html",{
                "message" : "Values Mismatch Error 12 "
            })
        
    if request.method == "POST":
        listkititems = request.POST.getlist('kit', None)
        listkititems_me = request.POST.getlist('itemexpiry', None)
        itemstopullopened_me = request.POST.getlist('valuetostockopened_me', None)
        itemstopullunopened_me = request.POST.getlist('valuetostockunopened_me', None)
        itemstopullopened = request.POST.getlist('valuetostockopened', None)
        itemstopullunopened = request.POST.getlist('valuetostockunopened', None)
        for idx, number in enumerate(itemstopullopened_me):
            if number == "":
                itemstopullopened_me[idx] = 0
        for idx, number in enumerate(itemstopullunopened_me):
            if number == "":
                itemstopullunopened_me[idx] = 0
        for idx, number in enumerate(itemstopullopened):
            if number == "":
                itemstopullopened[idx] = 0
        for idx, number in enumerate(itemstopullunopened):
            if number == "":
                itemstopullunopened[idx] = 0
        itemstopull_me = itemstopullopened_me + itemstopullunopened_me
        itemstopull = itemstopullopened + itemstopullunopened
        if len(itemstopull) > 0 or len(itemstopull_me) > 0:
            result = all(elem == 0 or elem=="0" for elem in itemstopull) and all(elem == 0 or elem=="0" for elem in itemstopull_me)
            if not result: 
                neworder = order(ordering_account = request.user, reason = "Restocking of Pouches", ordertype = "Withdraw", for_kit=item_object)
                neworder.save()
                #for one or no expiry only
                for i in range(len(listkititems)):
                    #if item is not stocked
                    if int(itemstopullopened[i]) == 0 and int(itemstopullunopened[i]) == 0:
                        pass
                    #if item is stocked
                    else:
                        kititem_obj = Item.objects.get(id=listkititems[i])
                        targetitem = list(kititems.objects.filter(item =kititem_obj, kit = item_object))[0]
                        if len(list(kititems.objects.filter(item =kititem_obj, kit = item_object)))>1:
                            return render(request, "inventory/error.html",{
                                "message" : "More than one object returned in targetitem"
                            })
                        first_kititemexpiry_obj = targetitem.itemexpiry.first()
                        first_kititemexpiry_obj.quantity += int(itemstopullopened[i]) + int(itemstopullunopened[i])
                        targetitem.quantity += int(itemstopullopened[i]) + int(itemstopullunopened[i])
                        if (targetitem.quantity_max < first_kititemexpiry_obj.quantity):
                            return render(request, "inventory/error.html",{
                                "message" : "Exceeded Maximumm; Error 1550"
                            })
                        first_kititemexpiry_obj.save()
                        targetitem.save()
                        kititem_obj.total_quantityopen -= int(itemstopullopened[i])
                        kititem_obj.total_quantityunopened -= int(itemstopullunopened[i])
                        kititem_obj.save()
                        first_itemexpiry_obj = kititem_obj.expirydates.first()
                        first_itemexpiry_obj.quantityopen -= int(itemstopullopened[i])
                        first_itemexpiry_obj.quantityunopened -= int(itemstopullunopened[i])
                        if first_itemexpiry_obj.quantityopen == 0 and first_itemexpiry_obj.quantityunopened == 0:
                            first_itemexpiry_obj.archived= True
                        first_itemexpiry_obj.save()
                        newcart = cart(item = kititem_obj.expirydates.first(), order=neworder, quantityopen = itemstopullopened[i], quantityunopened = itemstopullunopened[i], withdraw=True, time=datetime.datetime.now, archived=True)
                        newcart.save()
                #for multiple expiry
                for i in range(len(listkititems_me)):
                    if int(itemstopullopened_me[i]) == 0 and int(itemstopullunopened_me[i]) == 0:
                        pass
                    else:
                        itemexpiry_obj = ItemExpiry.objects.get(id=listkititems_me[i])
                        targetkititem = list(kititems.objects.filter(item =itemexpiry_obj.item, kit = item_object))[0]
                        check_this = list(kititemexpiry.objects.filter(expirydate=itemexpiry_obj, kit=item_object))
                        if len(check_this) == 0:
                            new_kititemexpiry = kititemexpiry(kititem = targetkititem, expirydate = itemexpiry_obj, quantity = 0, kit=item_object)
                            new_kititemexpiry.save()
                            kititemexpiry_obj = new_kititemexpiry
                        else:
                            kititemexpiry_obj = check_this[0]
                        kititemexpiry_obj.quantity += int(itemstopullopened_me[i]) + int(itemstopullunopened_me[i])
                        targetkititem.quantity += int(itemstopullopened_me[i]) + int(itemstopullunopened_me[i])
                        if (targetkititem.quantity_max < kititemexpiry_obj.quantity):
                            try:
                                new_kititemexpiry.delete()
                            except UnboundLocalError:
                                pass
                            return render(request, "inventory/error.html",{
                                "message" : "Exceeded Maximumm; Error 1550"
                            })
                        targetkititem.save()
                        kititemexpiry_obj.save()
                        itemexpiry_obj.quantityopen -= int(itemstopullopened_me[i])
                        itemexpiry_obj.quantityunopened -= int(itemstopullunopened_me[i])
                        if itemexpiry_obj.quantityopen == 0 and itemexpiry_obj.quantityunopened == 0:
                            itemexpiry_obj.archived= True
                        itemexpiry_obj.save()
                        itemexpiry_obj.item.total_quantityopen -= int(itemstopullopened_me[i])
                        itemexpiry_obj.item.total_quantityunopened -= int(itemstopullunopened_me[i])
                        itemexpiry_obj.item.save()
                        newcart = cart(item = itemexpiry_obj, order=neworder, quantityopen = itemstopullopened_me[i], quantityunopened = itemstopullunopened_me[i], withdraw=True, time=datetime.datetime.now, archived=True)
                        newcart.save()

                #add to transactions
                new_transaction = kit_transactions(type="Restocking", restock_order = neworder, ordering_account=request.user, kit = item_object)
                new_transaction.save()
                update_kit_transact_time(new_transaction, '')
                #check status of the newly stocked kit
                listitems = list(item_object.items.all())
                completereplenish= True
                for oneitem in listitems:
                    if (oneitem.quantity < oneitem.quantity_max):
                        completereplenish=False
                if completereplenish:
                    item_object.status = "Available"
                    item_object.save()
                    #check any entries to be archived
                    for kititemexpiry_instance in item_object.itemsexpiry.filter(archived = False):
                        if kititemexpiry_instance.quantity == 0:
                            kititemexpiry_instance.archived = True
                            kititemexpiry_instance.save()
                #report to telebot
                messagecart=""
                for replenished in neworder.cart.all():
                    sendmessageforlowqty(replenished.item)
                    quantity = str(replenished.quantityopen) + str(replenished.quantityunopened)
                    messagecart += " •  "+str(quantity)+ " " + replenished.item.item.name + "; Expiry: " + str(replenished.item.expirydate)+"\n"
                if completereplenish:
                    kitstatusmessage="\n<i>Kit is now Available</i>\n"
                else:
                    kitstatusmessage="\n<i>Kit is not fully stocked</i>\n"
                messagetele="\U0001F504<u><b>Kit "+item_object.name+" Restocked</b></u>\U0001F504\n"+kitstatusmessage+"\n"+messagecart+"\n\n<code>Kit Transaction No.: "+str(new_transaction.id)+"\nOrder Transaction No.: "+str(neworder.id)+"\nAuthorised by: "+ request.user.username+"</code>\n\n<a href='https://playground.nhhs-sjb.org/home/receipt/order/"+str(neworder.id)+"' >View Receipt Here</a>"
                telegram_bot_sendtext(messagetele)
                return redirect('kits_list')
            else:
                return render(request, "inventory/restock.html",{
                    "name" : item,
                    "item" : item_object,
                    "last" : last_user_cart,
                    "to_stock" : to_stock,
                    "message" : "All Fields are 0!"
                })
        else:
            return render(request, "inventory/error.html",{
                "message" : "No Values Receieved"
            })
    else:
        return render(request, "inventory/restock.html",{
            "name" : item,
            "item" : item_object,
            "last" : last_user_cart,
            "to_stock" : to_stock
        })


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def kits_return(request,item):
    kit_object = kits.objects.get(name = item)
    all_kititems = list(kit_object.items.all())
    #check if qty in two tables match
    for kititem in all_kititems:
        if int(kititem.quantity) != int(kititem.itemexpiry.all().aggregate(Sum('quantity'))['quantity__sum']):
            return render(request, "inventory/error.html",{
                "message" : "Values Mismatch Error 12 "
            })
    items_in_tempcart = list(tempcart.objects.filter(kit=kit_object, ordering_account = request.user, archived=False))
    items_in_tempcart.reverse()
    if kit_object.status != "In Use":
        return render(request, "inventory/error.html",{
            "message" : "Kit is Not In Use Now!"
        })
    else:
        if kit_object.kitloancartitem.last().ordering_account != request.user:
            return render(request, "inventory/error.html",{
                "message" : "You Do Not Have Permission (Error Code Pk1)"
            })
        else:
            if request.method == "POST":
                action = request.POST.get("action", None)
                if action == "noexpanded":
                    last_kitcart = kit_object.kitloancartitem.last()
                    last_kitcart.loan_active = False
                    if last_kitcart.other_reason:
                        newreturncart = kitloancart(item=kit_object, other_reason = last_kitcart.other_reason, ordering_account = request.user,
                        loan_active = False, loan = False, archived=True)
                    else:
                        newreturncart = kitloancart(item=kit_object, loanee_name=kit_object.kitloancartitem.last().loanee_name, ordering_account = request.user,
                        loan_end_date = kit_object.kitloancartitem.last().loan_end_date, loan_active = False, loan = False, archived=True)
                    newreturncart.save()
                    last_kitcart.save()
                    kit_object.status = "Available"
                    kit_object.save()
                    for tempobj in tempcart.objects.filter(archived=False, kit=kit_object):
                        tempobj.delete()
                    #add to transactions
                    new_transaction = kit_transactions(type="Returning", kitloancart = newreturncart, ordering_account=request.user, kit = kit_object)
                    new_transaction.save()
                    update_kit_transact_time(new_transaction, '')
                    #Report to telebot
                    messagetele="\U00002795<u><b>Kit "+kit_object.name+" Returned</b></u>\U00002795\n\nKit is now Available\nReturned by: "+request.user.username+"\n\n<code>Kit Transaction No.: "+str(new_transaction.id)+"</code>"
                    telegram_bot_sendtext(messagetele)
                    return redirect('kits_list')
                elif action == "expanded":
                    return render(request, "inventory/kitreturn.html",{
                        "item":kit_object,
                        "stage":"expanded",
                        "items_in_tempcart": items_in_tempcart
                    })
                elif action == "getkititem_max":
                    kititemexpiry_id = request.POST.get("kititemexpiry", None)
                    kititemexpiry_obj = kititemexpiry.objects.get(id=kititemexpiry_id)
                    max_qty=0
                    expanded_qty=0
                    #if kit is not forced
                    if not kititemexpiry_obj.kit.forced:
                        if len(kititemexpiry_obj.kititemsfortemp.all()) == 1 and not kititemexpiry_obj.kititemsfortemp.first().archived:
                            max_qty = int(kititemexpiry_obj.quantity) - int(kititemexpiry_obj.kititemsfortemp.first().expanded_qty)
                        else:
                            max_qty = int(kititemexpiry_obj.quantity)
                    #if kit is forced
                    else:
                        for tempcart_obj in kititemexpiry_obj.kititemsfortemp.all():
                            if not tempcart_obj.compulsory and not tempcart_obj.archived:
                                expanded_qty += int(tempcart_obj.expanded_qty)
                        max_qty = int(kititemexpiry_obj.quantity) - expanded_qty
                    #if max qty <0
                    if max_qty <0:
                        return render(request, "inventory/error.html",{
                            "message" : "Max Qty is less than 0!"
                        })
                    return render(request, "inventory/kitreturn.html",{
                        "item":kit_object,
                        "stage":"expanded",
                        "targetkititem":kititemexpiry_obj,
                        "max_qty" :max_qty,
                        "items_in_tempcart": items_in_tempcart
                    })
                elif action == "addtotempcart":
                    targetkititemexpiry_id = request.POST.get("targetkititemexpiry", None)
                    targetkititemexpiry = kititemexpiry.objects.get(id=targetkititemexpiry_id)
                    qtyexpanded = request.POST.get("qtyexpanded", None)
                    newtempcart = tempcart(item=targetkititemexpiry.expirydate, expanded_qty = qtyexpanded, kit=kit_object, ordering_account=request.user, item_in_kit=targetkititemexpiry)
                    newtempcart.save()
                    #check for duplicates in tempcart
                    tempcart_items_in_kit = tempcart.objects.filter(archived=False, compulsory=False).values_list('item_in_kit', flat=True)
                    item_in_kit_namelist =[]
                    for tempcart_item_in_kit in tempcart_items_in_kit:
                        if tempcart_item_in_kit in item_in_kit_namelist:
                            targetdupcarts = tempcart.objects.filter(item_in_kit = tempcart_item_in_kit, compulsory=False)
                            qty=0
                            item_newcart = targetdupcarts[0].item
                            kit_newcart = targetdupcarts[0].kit
                            item_in_kit_newcart = targetdupcarts[0].item_in_kit
                            for targetdupcart in targetdupcarts:
                                qty += int(targetdupcart.expanded_qty)
                                targetdupcart.delete()
                            totaltempcart = tempcart(item = item_newcart, expanded_qty = qty, kit=kit_newcart,ordering_account=request.user,item_in_kit=item_in_kit_newcart)
                            totaltempcart.save()
                        else:
                            item_in_kit_namelist.append(tempcart_item_in_kit)
                    items_in_tempcart = list(tempcart.objects.filter(kit=kit_object, ordering_account = request.user, archived = False))
                    items_in_tempcart.reverse()
                    return render(request, "inventory/kitreturn.html",{
                        "item":kit_object,
                        "stage":"expanded",
                        "targetkititem":None,
                        "items_in_tempcart": items_in_tempcart
                    })
                elif action == "removefromtempcart":
                    tempcart_id = request.POST.get("targetcart", None)
                    targetcart = tempcart.objects.get(id=tempcart_id)
                    if targetcart.compulsory:
                        return render(request, "inventory/error.html",{
                            "message" : "Can't remove this!"
                        })
                    targetcart.delete()
                    items_in_tempcart = list(tempcart.objects.filter(kit=kit_object, ordering_account = request.user, archived=False))
                    items_in_tempcart.reverse()
                    return render(request, "inventory/kitreturn.html",{
                        "item":kit_object,
                        "stage":"expanded",
                        "targetkititem":None,
                        "items_in_tempcart": items_in_tempcart
                    })
                elif action == "autostock":
                    #check validity
                    for item_in_tempcart in items_in_tempcart:
                        if item_in_tempcart.expanded_qty > item_in_tempcart.item.quantityunopened:
                            return render(request, "inventory/error.html",{
                                "message" : "Not Enough to restock! Refresh and resubmit return request."
                            })
                    #return kit
                    loaned_out_cart = kit_object.kitloancartitem.last()
                    loaned_out_cart.loan_active = False
                    if loaned_out_cart.other_reason:
                        newreturncart = kitloancart(item=kit_object, other_reason = loaned_out_cart.other_reason,ordering_account = request.user,
                        loan_active = False, loan = False, archived=True)
                    else:
                        newreturncart = kitloancart(item=kit_object, loanee_name=kit_object.kitloancartitem.last().loanee_name, ordering_account = request.user,
                        loan_end_date = kit_object.kitloancartitem.last().loan_end_date, loan_active = False, loan = False, archived=True)
                    newreturncart.save()
                    loaned_out_cart.save()
                    kit_object.status = "Available"
                    kit_object.forced=False
                    kit_object.save()
                    #withdraw from item list
                    neworder = order(ordering_account=request.user, reason = "Restocking of Pouches", ordertype = "Withdraw", for_kit=kit_object)
                    neworder.save()
                    #add batch no
                    tofollow=int(items_in_tempcart[-1].id)
                    for item_in_tempcart in items_in_tempcart:
                        item_in_tempcart.batchnum=tofollow
                        newordercart = cart(item = item_in_tempcart.item, order=neworder, quantityunopened=item_in_tempcart.expanded_qty, archived = True)
                        newordercart.save()
                        item_in_tempcart.item.quantityunopened -= item_in_tempcart.expanded_qty
                        if item_in_tempcart.item.quantityunopened == 0 and item_in_tempcart.item.quantityopened == 0:
                            item_in_tempcart.item.archived=True
                        item_in_tempcart.item.item.total_quantityunopened -= item_in_tempcart.expanded_qty
                        item_in_tempcart.item_in_kit.quantity += item_in_tempcart.expanded_qty
                        item_in_tempcart.item_in_kit.kititem.quantity += item_in_tempcart.expanded_qty
                        item_in_tempcart.item.save()
                        item_in_tempcart.item.item.save()
                        item_in_tempcart.archived=True
                        item_in_tempcart.save()
                        item_in_tempcart.item_in_kit.save()
                        item_in_tempcart.item_in_kit.kititem.save()
                    #add to transactions
                    new_transaction = kit_transactions(type="Returning and Stocking", kitloancart = newreturncart, restock_order=neworder, ordering_account=request.user, kit = kit_object)
                    new_transaction.save()
                    update_kit_transact_time(new_transaction, '')
                    #report to telebot
                    messagecart=""
                    for neworderitems in neworder.cart.all():
                        sendmessageforlowqty(neworderitems.item)
                        quantity = str(neworderitems.quantityopen) + str(neworderitems.quantityunopened)
                        messagecart += " •  "+str(quantity)+ " " + neworderitems.item.item.name + "; Expiry: " + str(neworderitems.item.expirydate)+"\n"
                    messagetele="\U00002795<u><b>Kit "+kit_object.name+" Returned</b></u>\U00002795\n\nKit is now Available\n\n"+messagecart+"\nReturned by: "+request.user.username+"\n\n<code>Kit Transaction No.: "+str(new_transaction.id)+"\nRestock Order No.: "+str(neworder.id)+"\nAuthorised by: "+ request.user.username+"</code>"
                    telegram_bot_sendtext(messagetele)
                    return redirect('kits_list')
                elif action == "stocklater":
                    #return kit
                    loaned_out_cart = kit_object.kitloancartitem.last()
                    loaned_out_cart.loan_active = False
                    if loaned_out_cart.other_reason:
                        newreturncart = kitloancart(item=kit_object, other_reason = loaned_out_cart.other_reason,ordering_account = request.user,
                        loan_active = False, loan = False, archived=True)
                    else:
                        newreturncart = kitloancart(item=kit_object, loanee_name=kit_object.kitloancartitem.last().loanee_name, ordering_account = request.user,
                        loan_end_date = kit_object.kitloancartitem.last().loan_end_date, loan_active = False, loan = False, archived=True)
                    newreturncart.save()
                    loaned_out_cart.save()
                    kit_object.status = "Unstocked"
                    kit_object.forced=False
                    kit_object.save()
                    tofollow=int(items_in_tempcart[-1].id)
                    #change kit items
                    for item_in_tempcart in items_in_tempcart:
                        item_in_tempcart.batchnum=tofollow
                        if not item_in_tempcart.compulsory:
                            item_in_tempcart.item_in_kit.quantity -= item_in_tempcart.expanded_qty
                            item_in_tempcart.item_in_kit.save()
                            item_in_tempcart.item_in_kit.kititem.quantity -= item_in_tempcart.expanded_qty
                            item_in_tempcart.item_in_kit.kititem.save()
                        item_in_tempcart.archived=True
                        item_in_tempcart.save()
                    #add to transactions
                    new_transaction = kit_transactions(type="Returning of Unstocked", kitloancart = newreturncart, ordering_account=request.user, kit = kit_object)
                    new_transaction.save()
                    update_kit_transact_time(new_transaction, '')
                    #report to telebot
                    messagetele="\U00002795<u><b>Kit "+kit_object.name+" Returned</b></u>\U00002795\n\nKit is now Returned but Unstocked\n\nReturned by: "+request.user.username+"\n\n<code>Kit Transaction No.: "+str(new_transaction.id)+"\nAuthorised by: "+ request.user.username+"</code>"
                    telegram_bot_sendtext(messagetele)
                    return redirect('kits_list')
            else:
                return render(request, "inventory/kitreturn.html",{
                    "item":kit_object,
                    "stage":"prechoice",
                })


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')    
def kits_activecart(request):
    all_itemsincart = list(kitloancart.objects.filter(archived=False))
    all_itemsincart.reverse()
    #check for duplicates
    for i in range(len(all_itemsincart)):
        if i != 0:
            if all_itemsincart[0].item == all_itemsincart[i].item:
                return render(request, "inventory/error.html",{
                    "message" : "Duplicate Kit in Cart! Report to admin"
                })
    empty=False
    if len(all_itemsincart) > 0:
        if all_itemsincart[0].loan:
            for itemincart in all_itemsincart:
                if not itemincart.loan:
                    return render(request, "inventory/error.html",{
                        "message" : "Both deposit and withdraw items in cart!"
                    })
            cart_type = "withdraw"
        else:
            for itemincart in all_itemsincart:
                if itemincart.loan:
                    return render(request, "inventory/error.html",{
                        "message" : "Both deposit and withdraw items in cart!"
                    })
            cart_type = "deposit"
    else:
        cart_type = "empty"
    
    if request.method == "POST":
        closethisitem = request.POST.get("closethis", None)
        purposewithdraw = request.POST.get("purposewithdraw", None)
        activecartitems = list(kitloancart.objects.filter(archived=False))
        if purposewithdraw is not None:
            if purposewithdraw == "Loan":
                loaneename = request.POST.get("loaneename", None)
                loanenddate = request.POST.get("loanenddate", None)
                if loaneename == "" or loanenddate=="":
                    return render(request, "inventory/error.html",{
                        "message" : "Ensure you have filled up all fields and try again."
                    })
                messagecart=""
                for activeitem in activecartitems:
                    activeitem.loanee_name = loaneename
                    activeitem.ordering_account = request.user
                    activeitem.loan_end_date = loanenddate
                    activeitem.loan_active =True
                    activeitem.archived = True
                    activeitem.save()
                    activeitem.item.status = "In Use"
                    activeitem.item.save()
                    #add to transactions
                    new_transaction = kit_transactions(type="Loaning", kitloancart = activeitem, ordering_account=request.user, kit = activeitem.item)
                    new_transaction.save()
                    update_kit_transact_time(new_transaction, '')
                    if activeitem.item.forced:
                        messagecart += " •  Kit " + activeitem.item.name +"(Forced Withdraw)\n"
                    else:
                        messagecart += " •  Kit " + activeitem.item.name +"\n"
                #report to telebot
                messagetele="\U00002796<u><b>Kit Loan Request Processed</b></u>\U00002796\n\n"+messagecart+"\nLoaned to: "+loaneename+" until "+loanenddate +"\nAuthorised by: "+request.user.username+"\n\n<code>Kit Transaction No.: "+str(new_transaction.id)+"</code>"
                telegram_bot_sendtext(messagetele)
                return redirect('kits_list')
            else:
                purposewithdrawothers = request.POST.get("purposewithdrawothers", None)
                if purposewithdrawothers == "":
                    return render(request, "inventory/error.html",{
                        "message" : "Ensure you have filled up all fields and try again."
                    })
                messagecart=""
                for activeitem in activecartitems:
                    activeitem.ordering_account = request.user
                    activeitem.loan_active =True
                    activeitem.other_reason = purposewithdrawothers
                    activeitem.archived = True
                    activeitem.save()
                    activeitem.item.status = "In Use"
                    activeitem.item.save()
                    #add to transactions
                    new_transaction = kit_transactions(type="Withdrawing", kitloancart = activeitem, ordering_account=request.user, kit = activeitem.item)
                    new_transaction.save()
                    update_kit_transact_time(new_transaction, '')
                    if activeitem.item.forced:
                        messagecart += " •  Kit " + activeitem.item.name +"(Forced Withdraw)\n"
                    else:
                        messagecart += " •  Kit " + activeitem.item.name +"\n"
                #report to telebot
                messagetele="\U00002796<u><b>Kit Withdrawal Request Processed</b></u>\U00002796\n\nReason for Withdrawal: "+purposewithdrawothers+"\n"+messagecart+"\n\nAuthorised by: "+request.user.username+"\n\n<code>Kit Transaction No.: "+str(new_transaction.id)+"</code>"
                telegram_bot_sendtext(messagetele)
                return redirect('kits_list')
            
        if closethisitem is not None:
            if closethisitem == "all":
                activecartitems = kitloancart.objects.filter(archived=False)
                for activecartitem in activecartitems:
                    activecartitem.item.status = "Available"
                    activecartitem.item.forced =False
                    activecartitem.item.save()
                    activecartitem.delete()
                return redirect('kits_list')
            else:
                closeitem = kitloancart.objects.get(id=closethisitem)
                closeitem.item.status = "Available"
                closeitem.item.forced=False
                closeitem.item.save()
                closeitem.delete()
                return redirect('kits_list')
    else:
        if len(all_itemsincart) == 0:
                empty = True
        return render(request, "inventory/kitscart.html", {
            "items" : all_itemsincart,
            "typeofcart" : cart_type,
            "empty" : empty
        })


@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def kitlogs(request):
    allorders = list(kit_transactions.objects.all())
    allorders.reverse()
    recent_transaction=[]
    all_transaction_id = simplejson.dumps(list(kit_transactions.objects.values_list('id', flat=True)))
    #get recent transactions of each kit
    for kit in kits.objects.all():
        recent_transaction.append(kit.transactions.last())
    if request.method=="POST":
        selectedthis = request.POST.get("selectedthis", None)
        orders_to_remove = request.POST.get("ordertoremove", None)

        #user selected this transaction
        if selectedthis != None :
            try:
                selectedorder = kit_transactions.objects.get(id=selectedthis)
            except kit_transactions.DoesNotExist:
                return JsonResponse({"success":False, "responseText":"Transaction has already been removed. Refreshing your page."}, status = 200)
            for transaction_of_kit in list(kit_transactions.objects.filter(kit=selectedorder.kit)):
                if transaction_of_kit.id > selectedorder.id:
                    return render(request, "inventory/kitlogs.html", {
                        "targetorder" : selectedorder,
                        "allordersid" : all_transaction_id,
                        "targetid" : selectedthis,
                        "allorders" : allorders,
                        "recent_transaction" : recent_transaction,
                        "message" : "You can't remove this order. You only can remove the most recent order of every kit."
                    })
            if selectedorder.kitloancart:
                return render(request, "inventory/kitlogs.html", {
                    "targetorder" : selectedorder,
                    "allordersid" : all_transaction_id,
                    "targetid" : selectedthis,
                    "cartitems" : selectedorder.kitloancart.item.name,
                    "allorders" : allorders,
                    "recent_transaction" : recent_transaction,
                })
            elif selectedorder.restock_order:
                return render(request, "inventory/kitlogs.html", {
                    "targetorder" : selectedorder,
                    "allordersid" : all_transaction_id,
                    "targetid" : selectedthis,
                    "cartitems" : selectedorder.restock_order.cart.all(),
                    "allorders" : allorders,
                    "recent_transaction" : recent_transaction,
                })

        #user says remove this transaction
        elif orders_to_remove != None:
            try:
                orderremove = kit_transactions.objects.get(id=orders_to_remove)
            except kit_transactions.DoesNotExist:
                return JsonResponse({"success":False, "responseText":"Transaction has already been removed. Refreshing your page."}, status = 200)
            #reversing a stocking kits action
            if orderremove.restock_order:
                returncart = list(orderremove.restock_order.cart.all())
                kit = orderremove.restock_order.for_kit
                for returnitems in returncart:
                    if returnitems.withdraw:
                        returnitems.item.quantityopen+= int(returnitems.quantityopen)
                        returnitems.item.item.total_quantityopen += int(returnitems.quantityopen)
                        returnitems.item.quantityunopened += int(returnitems.quantityunopened)
                        returnitems.item.item.total_quantityunopened += int(returnitems.quantityunopened)
                        if not orderremove.kitloancart:
                            kititemexpiry_obj = list(kititemexpiry.objects.filter(expirydate=returnitems.item, kit = kit))
                            if len(kititemexpiry_obj)!=1:
                                return JsonResponse({"success":False, "responseText":"Error 1890. Report to admin."}, status = 200)
                            kititemexpiry_obj =kititemexpiry_obj[0]
                            kititemexpiry_obj.quantity -= int(returnitems.quantityopen) + int(returnitems.quantityunopened)
                            kititemexpiry_obj.kititem.quantity -= int(returnitems.quantityopen) + int(returnitems.quantityunopened)
                    else:
                        return JsonResponse({"success":False, "responseText":"Order items appears to not be a restocking order"}, status = 200)
                    if returnitems.item.quantityopen < 0 or returnitems.item.quantityunopened < 0:
                        return JsonResponse({"success":False, "responseText":"Quantity Below 0!"}, status = 200)
                    else:
                        #update total quantity
                        if not orderremove.kitloancart:
                            kititemexpiry_obj.save()
                            kititemexpiry_obj.kititem.save()
                        returnitems.item.item.save()
                        returnitems.item.save()
                orderremove.restock_order.delete()

            if orderremove.kitloancart:
                kitcart = orderremove.kitloancart
                #reversing a loaning kit action
                if kitcart.loan:
                    kitcart.item.status = "Available"
                    for kititem in kitcart.item.items.all():
                        if kititem.quantity != kititem.quantity_max:
                            kitcart.item.status = "Unstocked"
                    #remove tempcarts
                    if kitcart.item.forced:
                        kitcart.item.forced=False
                        todelete=list(tempcart.objects.filter(kit=kitcart.item, archived=False, batchnum=0))
                        for d in todelete:
                            d.delete()
                        tempcartitems_to_uncarchive=list(tempcart.objects.filter(kit=kitcart.item, archived=False))
                        tempcartitems_to_uncarchive.reverse()
                        tofollow=tempcartitems_to_uncarchive[0].batchnum
                        if tofollow ==0:
                            return render(request, "inventory/error.html",{
                                "message" : "Batch Number Error"
                            })
                        listtounarchive=[]
                        for tempcartitem in tempcartitems_to_uncarchive:
                            if tempcartitem.batchnum == tofollow:
                                listtounarchive.append(tempcartitem)
                            else:
                                break
                        for listindex in listtounarchive:
                            listindex.archived=True
                            listindex.compulsory=False
                            listindex.save()
                else:
                    kit_status = "Available"
                    for kititem in kitcart.item.items.all():
                        if kititem.quantity != kititem.quantity_max:
                            kit_status = "Unstocked"
                    #reverse expanded action
                    tempcartitems_to_uncarchive=list(tempcart.objects.filter(kit=kitcart.item, archived=True))
                    tempcartitems_to_uncarchive.reverse()
                    tofollow=tempcartitems_to_uncarchive[0].batchnum
                    if tofollow ==0:
                        return render(request, "inventory/error.html",{
                            "message" : "Batch Number Error"
                        })
                    listtounarchive=[]
                    for tempcartitem in tempcartitems_to_uncarchive:
                        if tempcartitem.batchnum == tofollow:
                            listtounarchive.append(tempcartitem)
                        else:
                            break
                    #user indicated expanded items and did not restock them
                    if kit_status == "Unstocked":
                        for target_item in listtounarchive:
                            if target_item.compulsory:
                                kitcart.item.forced=True
                                target_item.archived=False
                                target_item.save()
                            else:
                                target_kit_itemexpiry = kititemexpiry.objects.filter(expirydate=target_item.item, kit=orderremove.kit)
                                if len(target_kit_itemexpiry)!=1:
                                    return JsonResponse({"success":False, "responseText":"Error 1932. Report to admin."}, status = 200)
                                target_kit_itemexpiry = target_kit_itemexpiry[0]
                                target_kit_itemexpiry.kititem.quantity += target_item.expanded_qty
                                target_kit_itemexpiry.quantity += target_item.expanded_qty
                                target_kit_itemexpiry.save()
                                target_kit_itemexpiry.kititem.save()
                                target_item.delete()
                        kititem.save()
                    #user indicated expanded items and restock them
                    else:
                        for target_item in listtounarchive:
                            if target_item.compulsory:
                                kitcart.item.forced=True
                                target_item.archived=False
                                target_item.save()
                        
                    #reversing a returning kit action
                    kitcart.item.status = "In Use"
                    orginal_kitcart = list(kitloancart.objects.filter(item=kitcart.item, loan=True))[-1]
                    orginal_kitcart.loan_active = True
                    orginal_kitcart.save()
                kitcart.item.save()
                kitcart.delete()
            #report to telebot
            messagetele="\U0000274C<u><b>Kit Transaction "+str(orderremove.id)+" Removed</b></u>\U0000274C\n\n<code>\nAuthorised by: "+request.user.username+"</code>"
            telegram_bot_sendtext(messagetele)
            update_kit_transact_time(orderremove, 'delete')
            orderremove.delete()
                        

        #filtering
        datetosearch = request.POST.get("datetosearch", None)
        daterangefrom = request.POST.get("daterangefrom", None)
        daterangeto = request.POST.get("daterangeto", None)
        reason = request.POST.get("reason", None)
        kits_id = request.POST.getlist("kit", None)
        if datetosearch != None:
            datetosearch_year =""
            datetosearch_month=""
            datetosearch_day=""
            for i in range(len(datetosearch)):
                if i < 4:
                    datetosearch_year += datetosearch[i]
                elif 4 < i < 7:
                    datetosearch_month += datetosearch[i]
                elif 7 < i :
                    datetosearch_day += datetosearch[i]

        if datetosearch == '':
            datetosearch = None
        if daterangefrom == '':
            daterangefrom = None
        if daterangeto == '':
            daterangeto = None
        if reason == '':
            reason = None
        if datetosearch == None and daterangefrom == None and daterangeto == None and reason == None and len(kits_id)==0:
            return render(request, "inventory/kitlogs.html", {
                "allorders" : allorders,
                "allordersid" : all_transaction_id,
                "recent_transaction" : recent_transaction,
            })
        #user select order filter by reason
        if datetosearch == None and daterangefrom == None and daterangeto == None and reason != None and len(kits_id)==0:
            all_orders = list(kit_transactions.objects.filter(type=reason))
            all_orders.reverse()
            return render(request, "inventory/kitlogs.html", {
                "allorders" : all_orders,
                "allordersid" : all_transaction_id,
                "recent_transaction" : recent_transaction,
            })
        #user select order filter by exact date
        elif datetosearch != None and daterangefrom == None and daterangeto == None and reason == None and len(kits_id)==0:
            all_orders = list(kit_transactions.objects.filter(time__year=datetosearch_year, time__month = datetosearch_month, time__day = datetosearch_day))
            all_orders.reverse()
            return render(request, "inventory/kitlogs.html", {
                "allorders" : all_orders,
                "allordersid" : all_transaction_id,
                "recent_transaction" : recent_transaction,
            })
        #user select order filter by date range
        elif datetosearch == None and daterangefrom != None and daterangeto != None and reason == None and len(kits_id)==0:
            if daterangefrom == daterangeto:
                all_orders = list(kit_transactions.objects.filter(time__contains=daterangeto))
            else:
                all_orders = list(kit_transactions.objects.filter(time__range=[daterangefrom, daterangeto]))
            all_orders.reverse()
            return render(request, "inventory/kitlogs.html", {
                "allorders" : all_orders,
                "allordersid" : all_transaction_id,
                "recent_transaction" : recent_transaction,
            })
        #user select order filter by date range and reason
        elif datetosearch == None and daterangefrom != None and daterangeto != None and reason != None and len(kits_id)==0:
            if daterangeto == daterangefrom:
                all_orders = list(kit_transactions.objects.filter(time__year=datetosearch_year, time__month = datetosearch_month, time__day = datetosearch_day, type = reason))
            else:
                all_orders = list(kit_transactions.objects.filter(time__range=[daterangefrom, daterangeto], type = reason))
            all_orders.reverse()
            return render(request, "inventory/kitlogs.html", {
                "allorders" : all_orders,
                "allordersid" : all_transaction_id,
                "recent_transaction" : recent_transaction,
            })
        #user select order filter by exact date and reason
        elif datetosearch != None and daterangefrom == None and daterangeto == None and reason != None and len(kits_id)==0:
            all_orders = list(kit_transactions.objects.filter(time__year=datetosearch_year, time__month = datetosearch_month, time__day = datetosearch_day, type = reason))
            all_orders.reverse()
            return render(request, "inventory/kitlogs.html", {
                "allorders" : all_orders,
                "allordersid" : all_transaction_id,
                "recent_transaction" : recent_transaction,
            })
        #user selects filter by kit only
        elif len(kits_id) > 0 and datetosearch == None and daterangefrom == None and daterangeto == None and reason == None:
            all_orders=[]
            for kit_id in kits_id:
                for x in list(kit_transactions.objects.filter(kit = kits.objects.get(id=kit_id))):
                    all_orders.append(x)
            all_orders.reverse()
            return render(request, "inventory/kitlogs.html", {
                "allorders" : all_orders,
                "allordersid" : all_transaction_id,
                "recent_transaction" : recent_transaction,
            })
        #user selects filter by kit and type
        elif len(kits_id) > 0 and datetosearch == None and daterangefrom == None and daterangeto == None and reason != None:
            all_orders=[]
            for kit_id in kits_id:
                for x in list(kit_transactions.objects.filter(kit = kits.objects.get(id=kit_id), type = reason)):
                    all_orders.append(x)
            all_orders.reverse()
            return render(request, "inventory/kitlogs.html", {
                "allorders" : all_orders,
                "allordersid" : all_transaction_id,
                "recent_transaction" : recent_transaction,
            })
        #user selects filter by kit and exact date
        elif len(kits_id) > 0 and datetosearch != None and daterangefrom == None and daterangeto == None and reason == None:
            all_orders=[]
            for kit_id in kits_id:
                for x in (kit_transactions.objects.filter(kit = kits.objects.get(id=kit_id), time__year=datetosearch_year, time__month = datetosearch_month, time__day = datetosearch_day)):
                    all_orders.append(x)
            all_orders.reverse()
            return render(request, "inventory/kitlogs.html", {
                "allorders" : all_orders,
                "allordersid" : all_transaction_id,
                "recent_transaction" : recent_transaction,
            })
        #user selects filter by kit and date range
        elif len(kits_id) > 0 and datetosearch == None and daterangefrom != None and daterangeto != None and reason == None:
            all_orders=[]
            for kit_id in kits_id:
                for x in list(kit_transactions.objects.filter(kit = kits.objects.get(id=kit_id), time__range=[daterangefrom, daterangeto])):
                    all_orders.append(x)
            all_orders.reverse()
            return render(request, "inventory/kitlogs.html", {
                "allorders" : all_orders,
                "allordersid" : all_transaction_id,
                "recent_transaction" : recent_transaction,
            })
        #user selects filter by kit exact date and reason
        elif len(kits_id) > 0 and datetosearch != None and daterangefrom == None and daterangeto == None and reason != None:
            all_orders=[]
            for kit_id in kits_id:
                for x in list(kit_transactions.objects.filter(kit = kits.objects.get(id=kit_id), time__year=datetosearch_year, time__month = datetosearch_month, time__day = datetosearch_day, type=reason)):
                    all_orders.append(x)
            all_orders.reverse()
            return render(request, "inventory/kitlogs.html", {
                "allorders" : all_orders,
                "allordersid" : all_transaction_id,
                "recent_transaction" : recent_transaction,
            })
        #user selects filter by kit date range and reason
        elif len(kits_id) > 0 and datetosearch == None and daterangefrom != None and daterangeto != None and reason != None:
            all_orders=[]
            for kit_id in kits_id:
                for x in list(kit_transactions.objects.filter(kit = kits.objects.get(id=kit_id), time__range=[daterangefrom, daterangeto], type=reason)):
                    all_orders.append(x)
            all_orders.reverse()
            return render(request, "inventory/kitlogs.html", {
                "allorders" : all_orders,
                "allordersid" : all_transaction_id,
                "recent_transaction" : recent_transaction,
            })
        #catch all errors
        else:
            return render(request, "inventory/error.html",{
                "message": "Uncaught error at kitlogs check POST data for kit_transactions"
            })
    else:
        return render(request, "inventory/kitlogs.html",{
            "allorders": allorders,
            "allordersid" : all_transaction_id,
            "recent_transaction" : recent_transaction,
        })

@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def selectedkit(request, kit):
    selected_kit = kits.objects.get(id=kit)
    if selected_kit.status == "In Use" and selected_kit.kitloancartitem.last().ordering_account == request.user:
        return redirect('kits_return', item = selected_kit.name)
    elif selected_kit.status == "Unstocked":
        return redirect('kits_restock', item = selected_kit.name)
    elif selected_kit.status == "In Cart":
        return redirect(reverse('kits_activecart'))
    else:
        all_itemsincart = list(kitloancart.objects.filter(archived=False))
        if len(all_itemsincart) > 0:
            if all_itemsincart[0].loan:
                for itemincart in all_itemsincart:
                    if not itemincart.loan:
                        return render(request, "inventory/error.html",{
                            "message" : "Both deposit and withdraw items in cart!"
                        })
                cart_type = "withdraw"
            else:
                for itemincart in all_itemsincart:
                    if itemincart.loan:
                        return render(request, "inventory/error.html",{
                            "message" : "Both deposit and withdraw items in cart!"
                        })
                cart_type = "deposit"
        else:
            cart_type = "empty"
        return render(request, "inventory/targetkit.html",{
            "selected_kit" : selected_kit,
            "cart_type" : cart_type
        })

@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def addnewkit(request):
    all_kitnames = simplejson.dumps(list(kits.objects.all().values_list('name', flat=True)))
    kit_items_generic = ["Sterile wash", "Crepe Bandage (5cm)", "Crepe Bandage (7.5cm)", "Crepe Bandage (10cm)", "Triangular Bandages",
    "Plasters", "Sterile Gauze", "Gloves (M)", "Micropore Tape", "Cotton balls", "Cotton buds", "Thermometer", "Thermometer Sheath", 
    "Scissors", "Tweezers", "Alcohol Swabs", "Surgical Mask", "Plastic Bags", "Poncho"]
    kit_items_generic_max_value_big=[6,2,1,1,3,20,10,3,2,10,10,1,15,1,1,10,4,5,2]
    kit_items_generic_max_value_small=[5,1,1,1,2,10,5,2,1,5,5,1,10,1,1,5,2,3,2]
    #[index,currentqty,max_qty,itemid,autofill]
    itemtotal_big=[]
    itemtotal_small=[]
    #{itemobj:[itemexpiryobj]}
    items = {}
    item_list=[]
    for idx, kit_item_generic in enumerate(kit_items_generic):
        item = Item.objects.get(name__iexact=kit_item_generic)
        item_list.append(item)
        express=False
        if len(item.expirydates.all()) == 1:
            express=True
        if express:
            itemtotal_big.append([idx, kit_items_generic_max_value_big[idx], kit_items_generic_max_value_big[idx], item.id, express])
            itemtotal_small.append([idx, kit_items_generic_max_value_small[idx], kit_items_generic_max_value_small[idx], item.id, express])
        else:
            itemtotal_big.append([idx, 0, kit_items_generic_max_value_big[idx], item.id, express])
            itemtotal_small.append([idx, 0, kit_items_generic_max_value_small[idx], item.id, express])
        
        items[item] = list(item.expirydates.all())
    if request.method == "POST":
        #{data:[itemexpiryid, qtychosen]}
        data = dict(request.POST)
        data.pop('csrfmiddlewaretoken')
        data.pop('kitnum')
        data.pop('kittype')
        data.pop('kitstatus')
        kitnum = request.POST.get('kitnum', None)
        kittype = request.POST.get('kittype', None)
        kitstatus = request.POST.get('kitstatus', None)
        if (len(kits.objects.filter(name=kittype+kitnum))):
            return render(request, "inventory/error.html",{
                "message" : "Kit is already in Database"
            })
        #create objs
        if kittype == "S":
            #create kit obj for S
            newkit = kits(name=kittype+kitnum, serial_no = kitnum, image="smallkit.png", kit_type ="S", status=kitstatus)
            newkit.save()
            for idx, item in enumerate(item_list):
                #create kititem obj for S
                newkititem= kititems(item=item, quantity=kit_items_generic_max_value_small[idx], quantity_max=kit_items_generic_max_value_small[idx], kit=newkit)
                newkititem.save()
                for datavalue in data.values():
                    if item.id == ItemExpiry.objects.get(id=datavalue[0]).item.id:
                        #create kititemexpiry obj for S
                        newkititemexpiry=kititemexpiry(kititem=newkititem,expirydate=ItemExpiry.objects.get(id=datavalue[0]), quantity=datavalue[1],kit=newkit)
                        newkititemexpiry.save()
        else:
            #create kit obj for B
            newkit = kits(name=kittype+kitnum, serial_no = kitnum, image="bigkit.png", kit_type ="B", status=kitstatus)
            newkit.save()
            for idx, item in enumerate(item_list):
                #create kititem obj for B
                newkititem= kititems(item=item, quantity=kit_items_generic_max_value_big[idx], quantity_max=kit_items_generic_max_value_big[idx], kit=newkit)
                newkititem.save()
                for datavalue in data.values():
                    if item.id == ItemExpiry.objects.get(id=datavalue[0]).item.id:
                        #create kititemexpiry obj for B
                        newkititemexpiry=kititemexpiry(kititem=newkititem,expirydate=ItemExpiry.objects.get(id=datavalue[0]), quantity=datavalue[1],kit=newkit)
                        newkititemexpiry.save()
        return redirect(reverse('kits_list')) 
    else:
        return render(request, "inventory/addnewkit.html",{
            "all_kitnames": all_kitnames,
            "items": items,
            "kit_items_generic_max_value_big": kit_items_generic_max_value_big,
            "kit_items_generic_max_value_small": kit_items_generic_max_value_small,
            "itemtotal_big":itemtotal_big,
            "itemtotal_small": itemtotal_small
        })

@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def addnewitem(request):
    types=[]
    for typechoice in typechoices:
        types.append(typechoice[0])
    if request.method == "POST":
        stage=request.POST.get('stage', None)
        if stage=="item":
            return render(request, "inventory/addnewitem.html",{
                "stage":"newitem",
                "typechoices":types
            })
        elif stage=="selectitem":
            return render(request, "inventory/addnewitem.html",{
                "stage":"selectitem",
                "items": Item.objects.all()
            })
        elif stage=="selecteditemforexpiry":
            newitem = Item.objects.get(name=request.POST.get('itemname', None))
            if len(newitem.expirydates.all()) != 0:
                if newitem.expirydates.first().expirydate == None:
                    return render(request, "inventory/error.html",{
                        "message" : "You cannot add an expiry to this item."
                    })
            return render(request, "inventory/addnewitem.html",{
                "stage":"newexpiry",
                "item":newitem
            })
        elif stage=="submititem":
            f = request.FILES.get('image', None)
            itemname = request.POST.get('itemname')
            itemtype = request.POST.get('itemtype')
            itemunit = request.POST.get('itemunit')
            min_qty_open = request.POST.get('min_qtyopen')
            min_qty_unopened = request.POST.get('min_qtyunopened')
            itemname = itemname.strip()
            if Item.objects.filter(name=itemname).count() > 0:
                return render(request, "inventory/error.html",{
                    "message" : "Item is already in Database"
                })
            newitem = Item(name=itemname, type=itemtype, unit=itemunit, min_quantityopen=min_qty_open, min_quantityunopened = min_qty_unopened, image=f)
            newitem.save()
            if f != None:
                handle_uploaded_file(f)
            return render(request, "inventory/addnewitem.html",{
                "stage":"newexpiry",
                "item":newitem
            })
        elif stage == "newexpiry":
            data = dict(request.POST)
            data.pop('csrfmiddlewaretoken')
            data.pop('stage')
            data.pop('itemid')
            targetitem = Item.objects.get(id=request.POST.get('itemid',None))
            for new_expiry in data.values():
                newexpirydate = new_expiry[0]
                newopenedqty = new_expiry[1]
                newunopenedqty = new_expiry[2]
                if int(newunopenedqty) == 0 and int(newopenedqty) == 0:
                    newexpiry = ItemExpiry(expirydate=newexpirydate, quantityopen=newopenedqty, quantityunopened=newunopenedqty, item=targetitem, archived=True)
                else:
                    newexpiry = ItemExpiry(expirydate=newexpirydate, quantityopen=newopenedqty, quantityunopened=newunopenedqty, item=targetitem, archived=False)
                newexpiry.save()
            return redirect(reverse('item_list')) 
    else:
        return render(request, "inventory/addnewitem.html",{
            "stage":"prechoice",
            "typechoices":types,
        })

@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def notifications(request):
    check()
    return render(request, "inventory/notifications.html",{
        "loanexpiry": alerts.objects.filter(category="Loan Expired"),
        "loanwarn": alerts.objects.filter(category="Loan Expiring"),
        "itemexpiry": list(alerts.objects.filter(category="Item Expired")) + list(alerts.objects.filter(category="Kit Expired")),
        "itemwarn": list(alerts.objects.filter(category="Item Expiring"))+ list(alerts.objects.filter(category="Kit Expiring")),
        "lowqtyalerts": alerts.objects.filter(category__contains="Low Item Qty"),
    })

@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def item_data(request):
    items=list(Item.objects.all())
    types=[]
    for typechoice in typechoices:
        types.append(typechoice[0])
    if request.method == "POST":
        name=request.POST.get('name', None)
        cat=request.POST.get('category', None)
        if name == "" and cat == "":
            return render(request, "inventory/itemlist.html",{
                "items": items,
                "names": list(Item.objects.values_list('name', flat=True)),
                "categories": types,
            })
        if name == "":
            items=list(Item.objects.filter(type=cat))
        elif cat == "":
            items=list(Item.objects.filter(name=name))
        else:
            items=list(Item.objects.filter(name=name, type=cat))
        return render(request, "inventory/itemlist.html",{
            "items": items,
            "names": Item.objects.values_list('name', flat=True),
            "categories": types,
        })
    else:
        return render(request, "inventory/itemlist.html",{
            "items": items,
            "names": list(Item.objects.values_list('name', flat=True)),
            "categories": types,
        })

@login_required(login_url="/r'^loginsjb/$'")
@group_required('sjb')
def csv_creator(request, mode):
    if mode =="itemdata":
        itemexp=ItemExpiry.objects.all()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="FAItemDataGen@'+ str(datetime.datetime.now())+'.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name','Type', 'Expiry Date', 'Unit', 'Qty Opened', 'Qty Unopened'])
        for iteme in itemexp:
            datarow=[iteme.item.name, iteme.item.type, iteme.expirydate, iteme.item.unit, iteme.quantityopen, iteme.quantityunopened]
            writer.writerow(datarow)
        return response
    elif mode == "kittransact":
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="KitTransactDataGen@'+ str(datetime.datetime.now())+'.xls"'
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Kit Transactions')
        col = 0
        font_style = xlwt.XFStyle()
        font_style.font.bold = True
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'mmm d yyyy hh:mm AM/PM'
        headers = ['Kit Transaction ID', 'Kit', 'Time', 'Type', 'Ordered By', 'Item(s)']
        for h in headers:
            worksheet.write(0, col, h, font_style)
            col+=1
        row=1
        col = 0
        font_style = xlwt.XFStyle()
        for t in kit_transactions.objects.all():
            worksheet.write(row, col, t.id)
            worksheet.write(row, col+1, str(t.kit.name))
            worksheet.write(row, col+2, t.time.replace(tzinfo=None), date_format)
            worksheet.write(row, col+3, t.type+' Kit '+str(t.kit.name))
            worksheet.write(row, col+4, t.ordering_account.username)
            if t.kitloancart:
                worksheet.write(row, col+5, 'Kit '+str(t.kitloancart.item.name))
            elif t.restock_order:
                itemdata=""
                for c in t.restock_order.cart.all():
                    itemdata+=(str(int(c.quantityopen)+int(c.quantityunopened))+'x '+c.item.item.name+ ';Expiry:'+ str(c.item.expirydate) +'\n')
                worksheet.write(row, col+5, itemdata)
            row+=1
        workbook.save(response)
        return response
    elif mode == "orders":
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="OrdersDataGen@'+ str(datetime.datetime.now())+'.xls"'
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Orders')
        col = 0
        font_style = xlwt.XFStyle()
        font_style.font.bold = True
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'mmm d yyyy hh:mm AM/PM'
        headers = ['Order ID', 'Time', 'Type', 'Ordered By', 'Reason', 'Item(s)']
        for h in headers:
            worksheet.write(0, col, h, font_style)
            col+=1
        row=1
        col = 0
        font_style = xlwt.XFStyle()
        for o in reversed(list(order.objects.all())):
            worksheet.write(row, col, o.id)
            worksheet.write(row, col+1, o.time.replace(tzinfo=None), date_format)
            worksheet.write(row, col+2, o.ordertype)
            worksheet.write(row, col+3, o.ordering_account.username)
            worksheet.write(row, col+4, o.reason)
            itemdata=""
            for c in o.cart.all():
                itemdata+=(str(int(c.quantityopen)+int(c.quantityunopened))+'x '+c.item.item.name+ ';Expiry:'+ str(c.item.expirydate) +'\n')
            worksheet.write(row, col+5, itemdata)
            row+=1
        workbook.save(response)
        return response
    elif mode == "loanorders":
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="LoanOrdersDataGen@'+ str(datetime.datetime.now())+'.xls"'
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Loan Orders')
        col = 0
        font_style = xlwt.XFStyle()
        font_style.font.bold = True
        datetime_format = xlwt.XFStyle()
        datetime_format.num_format_str = 'mmm d yyyy hh:mm AM/PM'
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'mmm d yyyy'
        headers = ['Loan ID', 'Status', 'Loanee', 'Time', 'Authenticator', 'Due Date', 'Item(s)', 'Outstanding Item(s)']
        for h in headers:
            worksheet.write(0, col, h, font_style)
            col+=1
        row=1
        col = 0
        font_style = xlwt.XFStyle()
        for o in reversed(list(loanorder.objects.all())):
            worksheet.write(row, col, o.id)
            if o.loan_active:
                worksheet.write(row, col+1, "Active")
            else:
                worksheet.write(row, col+1, "Closed")
            worksheet.write(row, col+2, o.loanee_name)
            worksheet.write(row, col+3, o.time.replace(tzinfo=None), datetime_format)
            worksheet.write(row, col+4, o.ordering_account.username)
            worksheet.write(row, col+5, o.loan_end_date, date_format)
            itemdata=""
            for c in o.loancart.all():
                itemdata+=(str(int(c.quantityopen)+int(c.quantityunopened))+'x '+c.item.item.name+ ';Expiry:'+ str(c.item.expirydate) +'\n')
            worksheet.write(row, col+6, itemdata)
            itemdata=""
            for c in o.outstandingloan.all():
                itemdata+=(str(int(c.quantityopen)+int(c.quantityunopened))+'x '+c.item.item.name+ ';Expiry:'+ str(c.item.expirydate) +'\n')
            worksheet.write(row, col+7, itemdata)
            row+=1
        workbook.save(response)
        return response

