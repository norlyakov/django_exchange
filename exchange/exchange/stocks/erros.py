# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 29.12.2019
"""


class TransactionError(RuntimeError):
    pass


class TransactionAlreadyExecuted(TransactionError):
    pass


class TransactionCantBeRevoked(TransactionError):
    pass
