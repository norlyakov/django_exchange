# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 15.12.2019
"""
from rest_framework import serializers

from . import models


class CurrencyCodeValidator(object):

    def __call__(self, value):
        if value not in models.Currency.objects.order_by('code').values_list('code').distinct():
            message = 'This field must be one of existing currency code'
            raise serializers.ValidationError(message)
