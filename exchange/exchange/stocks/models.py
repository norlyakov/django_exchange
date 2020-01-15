from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError as CoreValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F

from .erros import TransactionAlreadyExecuted, TransactionCantBeRevoked


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


class TransactionTypes(models.TextChoices):
    common = 'CMN', 'Common'
    exchange = 'EXC', 'Exchange'
    commission = 'CMS', 'Commission'
    canceled = 'CNL', 'Canceled'
    revoke = 'RVK', 'Revoke'


class Transaction(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    stock_from = models.ForeignKey(Stock, on_delete=models.PROTECT, null=True, related_name='+')
    stock_to = models.ForeignKey(Stock, on_delete=models.PROTECT, null=True, related_name='+')
    value = models.DecimalField(default=0, max_digits=100, decimal_places=5,
                                validators=[MinValueValidator(Decimal('0'))])
    type = models.CharField(max_length=3, choices=TransactionTypes.choices,
                            default=TransactionTypes.common)
    related_transaction = models.ForeignKey('self', on_delete=models.PROTECT, null=True, default=None)

    def __str__(self):
        return f'{self.value} {self.stock_from.currency}'

    def execute_and_save(self, *args, **kwargs):
        if self.created:
            raise TransactionAlreadyExecuted()

        if self.stock_from:
            Stock.objects.filter(pk=self.stock_from.id).select_for_update()  # lock stock for transaction
            self.stock_from.refresh_from_db()
            self.stock_from.value -= self.value
            self.stock_from.clean_fields()  # check that stock's value not negative
            self.stock_from.save()

        if self.stock_to:
            self.stock_to.value = F('value') + self.value
            self.stock_to.save()

        self.save(*args, **kwargs)

    def revoke(self):
        Transaction.objects.filter(pk=self.pk).select_for_update()
        self.refresh_from_db()

        if not (self.type == TransactionTypes.common and self.stock_from and self.stock_to and self.pk):
            raise TransactionCantBeRevoked('Only common transactions can be revoked')

        with transaction.atomic():
            self.type = TransactionTypes.canceled
            self.save()

            revoke_transaction = Transaction(
                type=TransactionTypes.revoke,
                value=self.value,
                stock_from=self.stock_to,
                stock_to=self.stock_from,
                related_transaction=self,
            )
            try:
                revoke_transaction.execute_and_save()
            except CoreValidationError:
                raise TransactionCantBeRevoked('Not enough money on foreign stock')
