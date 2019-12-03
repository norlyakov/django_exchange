import enum

from django.conf import settings
from django.db import models


class Currency(models.Model):
    value = models.TextField(max_length=100)

    def __str__(self):
        return f'{self.value}'


class Stock(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    value = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'currency')

    def __str__(self):
        return f"{self.user}'s {self.currency}"


class TransactionTypes(enum.Enum):
    common = enum.auto()
    commission = enum.auto()
    canceled = enum.auto()
    revoke = enum.auto()


class Transaction(models.Model):
    TRANSACTION_CHOICES = [
        ('CMN', TransactionTypes.common.name),
        ('CMS', TransactionTypes.commission.name),
        ('CNL', TransactionTypes.canceled.name),
        ('RVK', TransactionTypes.revoke.name),
    ]
    stock_from = models.ForeignKey(Stock, on_delete=models.PROTECT, null=True, related_name='+')
    stock_to = models.ForeignKey(Stock, on_delete=models.PROTECT, null=True, related_name='+')
    value = models.IntegerField()
    type = models.TextField(max_length=3, choices=TRANSACTION_CHOICES,
                            default=TransactionTypes.common.name)
    related_transaction = models.ForeignKey('self', on_delete=models.CASCADE, null=True, default=None)

    def __str__(self):
        return f'{self.value} {self.stock_from.currency}'
