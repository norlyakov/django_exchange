# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 23.12.2019
"""
from decimal import Decimal, getcontext

from django.conf import settings
from django.core.exceptions import ValidationError as CoreValidationError
from django.db import transaction
from django.db.models import F
from rest_framework import serializers

from .errors import TransactionCantBeRevoked, TransactionAlreadyExecuted
from .models import TransactionTypes, Transaction, Stock


class UserTransactionService:

    @staticmethod
    def _get_master_stock(currency):
        master_stock_pk = settings.STOCKS_SETTINGS['MASTER_STOCKS'].get(currency.code)
        if not master_stock_pk:
            raise RuntimeError(f"Didn't find master stock for currency {currency.code}")
        master_stock = Stock.objects.get(pk=master_stock_pk)
        if master_stock.currency != currency:
            raise RuntimeError(f'Master stock for {currency.code} has another currency - {master_stock.currency.code}')
        return master_stock

    @staticmethod
    def execute_and_save(transaction_model):
        with transaction.atomic():
            if transaction_model.created:
                raise TransactionAlreadyExecuted()

            if transaction_model.stock_from:
                # lock stock for transaction
                Stock.objects.filter(pk=transaction_model.stock_from.id).select_for_update()
                transaction_model.stock_from.refresh_from_db()
                transaction_model.stock_from.value -= transaction_model.value
                transaction_model.stock_from.clean_fields()  # check that stock's value not negative
                transaction_model.stock_from.save()

            if transaction_model.stock_to:
                transaction_model.stock_to.value = F('value') + transaction_model.value
                transaction_model.stock_to.save()

            transaction_model.save()

    @classmethod
    def make_transaction(cls, validated_data):
        tr_type = validated_data['type']
        tr_value = validated_data['value']
        stock_from = validated_data.get('stock_from')
        stock_to = validated_data.get('stock_to')

        if not stock_from or not stock_to:
            raise serializers.ValidationError('Need to provide both stock_from and stock_to')

        if stock_from == stock_to:
            raise serializers.ValidationError('Need different stocks')

        make_method = getattr(cls, tr_type.name, None)
        if not make_method:
            raise ValueError('Unknown transaction type')

        return make_method(tr_value, stock_from, stock_to)

    @classmethod
    def common(cls, tr_value, stock_from, stock_to):
        if stock_from.currency_id != stock_to.currency_id:
            raise serializers.ValidationError('Stocks must have same currency')

        with transaction.atomic():
            try:
                orig_transaction = Transaction(
                    type=TransactionTypes.common,
                    value=tr_value,
                    stock_from=stock_from,
                    stock_to=stock_to,
                )
                cls.execute_and_save(orig_transaction)

                getcontext().prec = 5
                commission = settings.STOCKS_SETTINGS['COMMISSION']
                commission_value = Decimal(commission) * tr_value
                master_stock = cls._get_master_stock(stock_from.currency)
                commission_transaction = Transaction(
                    type=TransactionTypes.commission,
                    value=commission_value,
                    stock_from=stock_from,
                    stock_to=master_stock,
                )
                cls.execute_and_save(commission_transaction)
            except CoreValidationError:
                raise serializers.ValidationError("Don't have enough money on stock_from")

        return orig_transaction

    @classmethod
    def exchange(cls, tr_value, stock_from, stock_to):
        if stock_from.user_id != stock_to.user_id:
            raise serializers.ValidationError('Stocks must belong to same user')

        if stock_from.currency_id == stock_to.currency_id:
            raise serializers.ValidationError('Stocks must have different currency')

        with transaction.atomic():
            try:
                master_stock_to = cls._get_master_stock(stock_from.currency)
                from_transaction = Transaction(
                    type=TransactionTypes.exchange,
                    value=tr_value,
                    stock_from=stock_from,
                    stock_to=master_stock_to,
                )
                cls.execute_and_save(from_transaction)
            except CoreValidationError:
                raise serializers.ValidationError("Don't have enough money on stock_from")

            try:
                getcontext().prec = 5
                rate = get_exchange_rate(stock_from.currency, stock_to.currency)
                converted_value = tr_value * Decimal(rate)
                master_stock_from = cls._get_master_stock(stock_to.currency)

                to_transaction = Transaction(
                    type=TransactionTypes.exchange,
                    value=converted_value,
                    stock_from=master_stock_from,
                    stock_to=stock_to,
                )
                cls.execute_and_save(to_transaction)
            except CoreValidationError:
                raise serializers.ValidationError("Don't have enough money on master stock")

        return from_transaction

    @classmethod
    def revoke(cls, orig_transaction):
        with transaction.atomic():
            Transaction.objects.filter(pk=orig_transaction.pk).select_for_update()
            orig_transaction.refresh_from_db()

            if not (orig_transaction.type == TransactionTypes.common and
                    orig_transaction.stock_from and orig_transaction.stock_to and orig_transaction.pk):
                raise TransactionCantBeRevoked('Only common transactions can be revoked')

            orig_transaction.type = TransactionTypes.canceled
            orig_transaction.save()

            revoke_transaction = Transaction(
                type=TransactionTypes.revoke,
                value=orig_transaction.value,
                stock_from=orig_transaction.stock_to,
                stock_to=orig_transaction.stock_from,
                related_transaction=orig_transaction,
            )
            try:
                cls.execute_and_save(revoke_transaction)
            except CoreValidationError:
                raise TransactionCantBeRevoked('Not enough money on foreign stock')


def get_exchange_rate(currency_from, currency_to):
    """Temp mock for exchange rates system"""
    currencies = {
        'USD': 65,
        'EUR': 75,
        'RUB': 1,
    }
    rate = currencies[currency_from.code] / currencies[currency_to.code]
    return rate
