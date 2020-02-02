# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 11.12.2019
"""
from decimal import Decimal

from rest_framework import serializers

from .models import Currency, Stock, TransactionTypes
from .utils import UserTransactionService


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'name', 'code']

    def create(self, validated_data):
        return NotImplementedError('Currency can not be created')

    def update(self, instance, validated_data):
        raise NotImplementedError('Currency can not be updated')


class StockSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user = serializers.ReadOnlyField(source='user.username')
    currency = serializers.CharField(max_length=10, source='currency.code')
    value = serializers.DecimalField(max_digits=100, decimal_places=5, read_only=True)

    def create(self, validated_data):
        currency_code = validated_data.pop('currency')['code']
        currency = Currency.objects.filter(code=currency_code).first()
        if not currency:
            raise serializers.ValidationError('Currency with such code does not exist')
        return Stock.objects.create(currency=currency, **validated_data)

    def update(self, instance, validated_data):
        raise NotImplementedError('Stock can not be updated')

    def validate(self, attrs):
        stock = Stock.objects.filter(
            currency__code=attrs['currency']['code'],
            user=self.context['request'].user
        ).first()
        if stock:
            raise serializers.ValidationError('User already have stock with this currency')
        return attrs


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
    value = serializers.DecimalField(max_digits=100, decimal_places=5, min_value=Decimal('0.00001'))
    type = serializers.ChoiceField(choices=TYPE_CHOICES)

    def create(self, validated_data):
        return UserTransactionService.make_transaction(validated_data)

    def update(self, instance, validated_data):
        raise NotImplementedError('Transaction can not be updated')

    def validate_stock_from(self, value):
        if value.user != self.context['request'].user:
            raise serializers.ValidationError("Stock don't belong to user.")
        return value
