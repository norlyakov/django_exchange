# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 19.01.2020
"""
from .models import Currency, Stock, Transaction, TransactionTypes


def create_currency(code, name=''):
    name = name or code + ' name'
    currency = Currency(code=code, name=name)
    currency.save()
    return currency


def create_stock(user, currency, value=0):
    stock = Stock(user=user, currency=currency, value=value)
    stock.save()
    return stock


def create_transaction(stock_from, stock_to, value=0, tr_type=TransactionTypes.common, related_transaction=None):
    transaction = Transaction(
        stock_from=stock_from,
        stock_to=stock_to,
        value=value,
        type=tr_type,
        related_transaction=related_transaction
    )
    transaction.save()
    return transaction
