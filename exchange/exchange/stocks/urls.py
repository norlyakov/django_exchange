# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 15.12.2019
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'stocks', views.StockViewSet)
router.register(r'currencies', views.CurrencyViewSet)
router.register(r'transactions', views.TransactionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
