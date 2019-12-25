# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 23.12.2019
"""
from decimal import Decimal, getcontext

from django.conf import settings
from django.core.exceptions import ValidationError as CoreValidationError
from django.db import transaction
from rest_framework import serializers

from .models import TransactionTypes, Transaction, Stock


class UserTransactionMaker:

    def __init__(self):
        self._type_to_method = {
            TransactionTypes.common: self.common,
            TransactionTypes.exchange: self.exchange,
        }

    def __call__(self, validated_data):
        tr_type = validated_data['type']
        tr_value = validated_data['value']
        stock_from = validated_data.get('stock_from')
        stock_to = validated_data.get('stock_to')

        if not stock_from and not stock_to:
            raise serializers.ValidationError('Need to provide stocks')

        if stock_from == stock_to:
            raise serializers.ValidationError('Need different stocks')

        make_method = self._type_to_method.get(tr_type)
        if not make_method:
            raise ValueError('Unknown transaction type')

        return make_method(tr_value, stock_from, stock_to)

    @staticmethod
    def _get_master_stock(currency):
        master_stock_pk = settings.STOCKS_SETTINGS['MASTER_STOCKS'].get(currency.code)
        if not master_stock_pk:
            raise RuntimeError(f"Didn't find master stock for currency {currency.code}")
        master_stock = Stock.objects.get(pk=master_stock_pk)
        if master_stock.currency != currency:
            raise RuntimeError(f'Master stock for {currency.code} has another currency - {master_stock.currency.code}')

    def common(self, tr_value, stock_from, stock_to):
        if not stock_from or not stock_to:
            raise serializers.ValidationError('Need to provide both stock_from and stock_to for common transaction')

        if stock_from.currency != stock_to.currency:
            raise serializers.ValidationError('Provided stocks should have same currency')

        with transaction.atomic():
            try:
                orig_transaction = Transaction(
                    type=TransactionTypes.common,
                    value=tr_value,
                    stock_from=stock_from,
                    stock_to=stock_to,
                )
                orig_transaction.execute_and_save()

                getcontext().prec = 5
                commission_percent = settings.STOCKS_SETTINGS['COMMISSION_PERCENT']
                commission_value = Decimal(commission_percent) * tr_value
                master_stock = self._get_master_stock(stock_from.currency)
                commission_transaction = Transaction(
                    type=TransactionTypes.common,
                    value=commission_value,
                    stock_from=stock_from,
                    stock_to=master_stock,
                )
                commission_transaction.execute_and_save()
            except CoreValidationError as e:
                raise serializers.ValidationError("Don't have enough money on stock_from")

        return orig_transaction

    def exchange(self):
        pass
