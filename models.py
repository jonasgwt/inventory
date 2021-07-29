from django.db import models
from tagging.models import User

typechoices = (
        ('Bandages', 'Bandages'),
        ('Solution', 'Solution'),
        ('Dressing', 'Dressing' ),
        ('Universal Precaution', 'Universal Precaution'),
        ('General', 'General'),
    )
# Create your models here.

class Item(models.Model):
    name =  models.CharField(max_length=50)
    type = models.CharField(max_length=50, choices=typechoices, default='General')
    unit = models.CharField(max_length=50, default="units")
    image = models.CharField(max_length=100, null=True, blank=True)
    total_quantityopen = models.IntegerField(null=False, blank=False, default=0)
    total_quantityunopened = models.IntegerField(null=False, blank=False, default=0)
    min_quantityopen = models.IntegerField(null=True, blank=True, default=0)
    min_quantityunopened = models.IntegerField(null=True, blank=True, default=0)
    def __str__(self):
        return self.name

class ItemExpiry(models.Model):
    expirydate = models.DateField(null=True, blank=True)
    quantityopen =  models.IntegerField(null=False, blank=False, default=0)
    quantityunopened =  models.IntegerField(null=False, blank=False, default=0)
    item = models.ForeignKey(Item, related_name="expirydates", on_delete=models.CASCADE, null=True)
    archived = models.BooleanField(default=False)
    def __str__(self) -> str:
        return f"{self.expirydate}, {self.item}"

class kits(models.Model):
    name = models.CharField(max_length=5, null=False, blank=False)
    serial_no = models.IntegerField(blank=False, null=False)
    image = models.CharField(max_length=100, null=True, blank=True)
    kit_type = models.CharField(max_length=1, blank=False, null=False)
    status = models.CharField(max_length=100, blank=False, null=False)
    nearest_expiry = models.DateField(null=True, blank=True)
    forced=models.BooleanField(default=False)
    def __str__(self) -> str:
        return f"Kit {self.name}, {self.status}"

class order(models.Model):
    ordering_account = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    reason = models.CharField(max_length=50, blank=False, null=True)
    for_kit = models.ForeignKey(kits, on_delete=models.CASCADE, related_name="replenishmentorders", blank=True, null=True)
    ordertype = models.CharField(max_length=50, blank=False, null=False, default="Withdraw")
    time = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Order {self.id}"

class cart(models.Model):
    item = models.ForeignKey(ItemExpiry, on_delete=models.CASCADE, related_name="cartitem", null=True)
    order = models.ForeignKey(order, on_delete=models.CASCADE, related_name="cart", null=True)
    quantityopen = models.IntegerField(blank=False, null=False, default=0)
    quantityunopened = models.IntegerField(blank=False, null=False, default=0)
    withdraw  = models.BooleanField(default=True)
    time = models.DateTimeField(auto_now_add=True)
    archived = models.BooleanField(default=False)
    def __str__(self) -> str:
        return f"{self.item}, {self.order}"

class loanorder(models.Model):
    loanee_name = models.CharField(max_length=50, blank=False, null=False)
    ordering_account = models.ForeignKey(User, on_delete=models.CASCADE, related_name="loanorders")
    loan_end_date = models.DateField()
    loan_active = models.BooleanField(default=True)
    time = models.DateTimeField(auto_now_add=True)
    def __str__(self) -> str:
        return f"Loan {self.id}, to {self.loanee_name}, until {self.loan_end_date}"

class loancart(models.Model):
    item = models.ForeignKey(ItemExpiry, on_delete=models.CASCADE, related_name="loancartitem", null=True)
    order = models.ForeignKey(loanorder, on_delete=models.CASCADE, related_name="loancart", null=True)
    quantityopen = models.IntegerField(blank=False, null=False, default=0)
    quantityunopened = models.IntegerField(blank=False, null=False, default=0)
    time = models.DateTimeField(auto_now_add=True)
    loan = models.BooleanField(default=True)
    expanded = models.BooleanField(default=False)
    def __str__(self) -> str:
        return f"{self.item}, {self.order}"

class loanoutstanding(models.Model):
    order = models.ForeignKey(loanorder, on_delete=models.CASCADE, related_name="outstandingloan", null=True)
    item = models.ForeignKey(ItemExpiry, on_delete=models.CASCADE, related_name="outstandingloancartitem", null=True)
    quantityopen = models.IntegerField(blank=False, null=False, default=0)
    quantityunopened = models.IntegerField(blank=False, null=False, default=0)
    def __str__(self) -> str:
        return f"Loan {self.order}, {self.item}"

class kititems(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="kititems", null=True)
    quantity = models.IntegerField(blank=False,null=False,default=0)
    quantity_max = models.IntegerField(blank=False,null=False,default=0)
    kit = models.ForeignKey(kits, on_delete=models.CASCADE, related_name="items")
    def __str__(self) -> str:
        return f"{self.quantity} out of {self.quantity_max} {self.item} in {self.kit}"

class kititemexpiry(models.Model):
    kititem = models.ForeignKey(kititems, on_delete=models.CASCADE, related_name="itemexpiry")
    expirydate = models.ForeignKey(ItemExpiry, on_delete=models.CASCADE, related_name="kititemexpiry")
    quantity = models.IntegerField(blank=False,null=False,default=0)
    kit = models.ForeignKey(kits, on_delete=models.CASCADE, related_name="itemsexpiry")
    archived = models.BooleanField(default=False)
    def __str__(self) -> str:
        return f"{self.quantity} of {self.expirydate}, {self.kititem}"

class kitloancart(models.Model):
    item = models.ForeignKey(kits, on_delete=models.CASCADE, related_name="kitloancartitem")
    loanee_name = models.CharField(max_length=50, blank=True, null=True)
    ordering_account = models.ForeignKey(User, on_delete=models.CASCADE, related_name="kitloanorders")
    loan_end_date = models.DateField(blank=True, null=True)
    loan_active = models.BooleanField(default=True)
    time = models.DateTimeField(auto_now_add=True)
    other_reason = models.CharField(max_length=50, blank=True, null=True)
    loan = models.BooleanField(default=True)
    archived = models.BooleanField(default=False)
    remarks = models.CharField(max_length=50, null=True, blank=True)
    def __str__(self) -> str:
        return f"{self.item}, {self.ordering_account}"

class tempcart(models.Model):
    item = models.ForeignKey(ItemExpiry, on_delete=models.CASCADE, related_name="kititemstemp", null=True)
    expanded_qty = models.IntegerField(blank=False,null=False)
    kit = models.ForeignKey(kits, on_delete=models.CASCADE, related_name="kititemstempcart")
    ordering_account = models.ForeignKey(User, on_delete=models.CASCADE, related_name="kititemscart")
    item_in_kit = models.ForeignKey(kititemexpiry, on_delete=models.CASCADE, related_name="kititemsfortemp", blank=True, null=True)
    archived = models.BooleanField(default=False)
    batchnum = models.IntegerField(blank=False,null=False, default=0)
    compulsory=models.BooleanField(default=False)
    def __str__(self) -> str:
        return f"{self.item}, {self.expanded_qty} Expanded in Kit {self.kit}"

class kit_transactions(models.Model):
    type = models.CharField(max_length=100)
    kitloancart = models.ForeignKey(kitloancart, null=True, blank=True, on_delete=models.CASCADE, related_name="transaction")
    restock_order = models.ForeignKey(order, null=True, blank=True, on_delete=models.CASCADE, related_name="kit_transaction")
    ordering_account = models.ForeignKey(User, on_delete=models.CASCADE, related_name="auth_transaction")
    time = models.DateTimeField(auto_now_add=True)
    kit = models.ForeignKey(kits, on_delete=models.CASCADE, related_name="transactions")
    def __str__(self) -> str:
        return f"{self.type}, on {self.time}"

class alerts(models.Model):
    loan = models.ForeignKey(loanorder, on_delete=models.CASCADE, related_name="loanalerts", null=True, blank=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="itemalerts", null=True, blank=True)
    itemexpiry =  models.ForeignKey(ItemExpiry, on_delete=models.CASCADE, related_name="itemexpiryalerts", null=True, blank=True)
    kit = models.ForeignKey(kits, on_delete=models.CASCADE, related_name="kitsalerts", null=True, blank=True)
    category = models.CharField(max_length=50, null=False, blank=False)
    urgent=models.BooleanField(default=True)
    def __str__(self) -> str:
        return f"{self.category}; {self.urgent}"

