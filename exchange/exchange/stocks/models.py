import enum
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Currency(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.code}'


class Stock(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    value = models.DecimalField(default=0, max_digits=100, decimal_places=5,
                                validators=[MinValueValidator(Decimal('0'))])
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'currency')

    def __str__(self):
        return f"{self.user}'s {self.currency}"


class TransactionTypes(enum.Enum):
    common = enum.auto()
    exchange = enum.auto()
    commission = enum.auto()
    canceled = enum.auto()
    revoke = enum.auto()


class Transaction(models.Model):
    TRANSACTION_CHOICES = [
        ('CMN', TransactionTypes.common.name),
        ('EXC', TransactionTypes.exchange.name),
        ('CMS', TransactionTypes.commission.name),
        ('CNL', TransactionTypes.canceled.name),
        ('RVK', TransactionTypes.revoke.name),
    ]
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    stock_from = models.ForeignKey(Stock, on_delete=models.PROTECT, null=True, related_name='+')
    stock_to = models.ForeignKey(Stock, on_delete=models.PROTECT, null=True, related_name='+')
    value = models.DecimalField(default=0, max_digits=100, decimal_places=5,
                                validators=[MinValueValidator(Decimal('0'))])
    type = models.CharField(max_length=3, choices=TRANSACTION_CHOICES,
                            default=TransactionTypes.common.name)
    related_transaction = models.ForeignKey('self', on_delete=models.PROTECT, null=True, default=None)

    def __str__(self):
        return f'{self.value} {self.stock_from.currency}'
