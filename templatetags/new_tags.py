from inventory.models import *
from django import template


register = template.Library()


@register.filter(name='sub')
def sub(value, arg):
    return int(value) - int(arg)


@register.filter(name='sort')
def listsort(value):
    return value.order_by('expirydate')

@register.filter(name='sortsq')
def listsort(value):
    v_list=[]
    v_list_raw=[]
    for v in value:
        v_list.append(v)
        v_list_raw.append(v.expirydate.expirydate)
    v_list_raw, v_list = (list(t) for t in zip(*sorted(zip(v_list_raw, v_list))))
    return v_list
        
@register.filter(name='itemsort')
def listsort(value):
    return value.order_by('kititem')

@register.filter(name='filternsort')
def listsort(value):
    value = value.filter(archived=False)
    return value.order_by('kititem')

@register.filter(name='findremainder')
def findremainder(value):
    target_item = value.item.item
    total_expanded_qty =0
    for q in target_item.expirydates.all():
        if len(list(tempcart.objects.filter(item=q, kit= value.kit, archived=False, compulsory=True))) != 0:
            total_expanded_qty += int(list(tempcart.objects.filter(item=q, kit= value.kit, archived=False, compulsory=True))[0].expanded_qty)
        if len(list(tempcart.objects.filter(item=q, kit= value.kit, archived=False, compulsory=False))) != 0:
            total_expanded_qty += int(list(tempcart.objects.filter(item=q, kit= value.kit, archived=False, compulsory=False))[0].expanded_qty)
    max_qty = int(value.item_in_kit.kititem.quantity_max)
    return max_qty - total_expanded_qty

@register.filter(name='uniquetype')
def getunique(value):
    v_list=[]
    for v in kit_transactions.objects.all():
        v_list.append(v.type)
    return list(set(v_list))

@register.filter(name='unique')
def getunique(value):
    v_list=[]
    for v in kit_transactions.objects.all():
        v_list.append(v.kit)
    return list(set(v_list))


@register.filter(name='sortrelevant')
def listsort(value):
    return value.filter(archived=False).order_by('expirydate')


@register.filter(name='check')
def checker(value):
    for tempcart in value:
        if tempcart.expanded_qty > tempcart.item.quantityunopened:
            return False
    return True



@register.filter(name='sortnfilter')
def listsort(value):
    return value.filter(archived=False).order_by('expirydate')

@register.filter
def index(indexable, i):
    return indexable[i]


@register.filter(name='doubleindex')
def index(value, arg):
    arg_list = [a.strip() for a in arg.split(',')]
    return value[int(arg_list[0])][int(arg_list[2])]

@register.filter(name='findidofexpiry')
def index(value, index):
    return Item.objects.get(id=value[index]).expirydates.first().id

@register.filter(name='getobjexpiry')
def fx(value):
    return Item.objects.get(id=value[3]).expirydates.first().expirydate

@register.filter(name='getobjname')
def fx(value):
    return Item.objects.get(id=value[3]).name

@register.filter(name='indexrange')
def fx(value, index):
    return range(int(value[index])+1)

@register.filter(name='stringify')
def stringify(value):
    return str(value)

@register.simple_tag
def setvar(val=None):
  return val


@register.filter(name='getitemobj')
def getitemobj(value):
    return Item.objects.get(id=value)


@register.filter(name='range')
def fx(value):
    return range(int(value+1))

@register.filter(name='subrange')
def fx(value, sub):
    return range(int((int(value)-int(sub))+1))


@register.filter(name='addlength')
def fx(value, add):
    return int(len(value)+len(add))


@register.filter(name='getfirstmax_open')
def fx(value):
    qtyopen_cart = 0
    dups = list(cart.objects.filter(item = list(value.filter(archived=False).order_by('expirydate'))[0], archived = False))
    if len(dups) == 1:
        qtyopen_cart = dups[0].quantityopen
    return int(value.filter(archived=False).order_by('expirydate').first().quantityopen) - int(qtyopen_cart)

@register.filter(name='getfirstmax_unopened')
def fx(value):
    qtyunopen_cart = 0
    dups = list(cart.objects.filter(item = list(value.filter(archived=False).order_by('expirydate'))[0], archived = False))
    if len(dups) == 1:
        qtyunopen_cart = dups[0].quantityunopened
    return int(value.filter(archived=False).order_by('expirydate').first().quantityunopened)- int(qtyunopen_cart)

@register.filter(name='toaddexpiry')
def fx(value):
    result=[]
    for v in value:
        if len(v.expirydates.all()) != 0:
            if v.expirydates.first().expirydate != None:
                result.append(v)
        else:
            result.append(v)
    return result

@register.filter(name='sortnfilterwithdraw')
def listsort(value):
    result=list(value.filter(archived=False).order_by('expirydate'))
    for v in result:
        if v.quantityopen == 0 and v.quantityunopened == 0:
            result.remove(v)
    return result
    
    