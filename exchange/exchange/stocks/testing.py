# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 19.01.2020
"""
from .models import Currency, Stock


def create_currency(code, name=''):
    name = name or code + ' name'
    currency = Currency(code=code, name=name)
    currency.save()
    return currency


def create_stock(user, currency, value=0):
    stock = Stock(user=user, currency=currency, value=value)
    stock.save()
    return stock
