# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 11.12.2019
"""
from rest_framework import serializers

from . import models


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Currency
        fields = ['id', 'name', 'code']

    def create(self, validated_data):
        return RuntimeError('Currency can not be created')

    def update(self, instance, validated_data):
        raise RuntimeError('Currency can not be updated')


class StockSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user = serializers.ReadOnlyField(source='user.username')
    currency = serializers.PrimaryKeyRelatedField(queryset=models.Currency.objects.all())
    value = serializers.DecimalField(max_digits=100, decimal_places=5, read_only=True)

    def create(self, validated_data):
        return models.Stock.objects.create(**validated_data)

    def update(self, instance, validated_data):
        raise RuntimeError('Stock can not be updated')
