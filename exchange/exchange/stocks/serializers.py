# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 11.12.2019
"""
from django.db import IntegrityError
from rest_framework import serializers

from .models import Currency, Stock


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
