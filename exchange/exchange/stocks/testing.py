# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 19.01.2020
"""
from .models import Currency


def create_currency(code, name=''):
    name = name or code + ' name'
    currency = Currency(code=code, name=name)
    currency.save()
    return currency
