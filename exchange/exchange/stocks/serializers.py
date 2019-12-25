# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 11.12.2019
"""
from decimal import Decimal

from django.db import IntegrityError
from rest_framework import serializers

from .models import Currency, Stock, TransactionTypes
from .utils import UserTransactionMaker


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'name', 'code']

    def create(self, validated_data):
        return RuntimeError('Currency can not be created')

    def update(self, instance, validated_data):
        raise RuntimeError('Currency can not be updated')


class StockSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user = serializers.ReadOnlyField(source='user.username')
    currency = serializers.CharField(max_length=10, source='currency.code')
    value = serializers.DecimalField(max_digits=100, decimal_places=5, read_only=True)

    def create(self, validated_data):
        currency_code = validated_data.pop('currency')['code']
        try:
            currency = Currency.objects.get(code=currency_code)
        except Currency.DoesNotExist:
            message = 'Currency with such code does not exist'
            raise serializers.ValidationError(message)

        try:
            return Stock.objects.create(currency=currency, **validated_data)
        except IntegrityError as e:
            if 'UNIQUE' in e.args[0]:
                message = 'User already have stock with this currency'
                raise serializers.ValidationError(message)

    def update(self, instance, validated_data):
        raise RuntimeError('Stock can not be updated')


TYPE_CHOICES = [
    TransactionTypes.common,
    TransactionTypes.exchange,
]


class TransactionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    updated = serializers.DateTimeField(read_only=True)
    stock_from = serializers.PrimaryKeyRelatedField(allow_null=True, queryset=Stock.objects.filter(is_active=True))
    stock_to = serializers.PrimaryKeyRelatedField(allow_null=True, queryset=Stock.objects.filter(is_active=True))
    value = serializers.DecimalField(max_digits=100, decimal_places=5, min_value=Decimal('0'))
    type = serializers.ChoiceField(choices=TYPE_CHOICES)

    _transaction_maker = UserTransactionMaker()

    def create(self, validated_data):
        return self._transaction_maker(validated_data)

    def update(self, instance, validated_data):
        raise RuntimeError('Transaction can not be updated')
