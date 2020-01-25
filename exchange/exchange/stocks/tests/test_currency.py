# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 19.01.2020
"""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from ..testing import create_currency


class CurrencyAPITests(APITestCase):
    currencies = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currencies.append(create_currency('USD'))
        cls.currencies.append(create_currency('RUB'))
        cls.currencies.append(create_currency('EUR'))
        cls.password = 'password'
        cls.user = User.objects.create_user(
            username='test', email='test@test.com', password=cls.password)

    def tearDown(self):
        self.client.logout()

    def login(self):
        self.client.login(username=self.user.username, password=self.password)

    def test_get_list(self):
        url = reverse('currency-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.login()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        self.assertEqual(data['count'], 3)
        self.assertListEqual(data['results'], [
            {'id': 1, 'name': 'USD name', 'code': 'USD'},
            {'id': 2, 'name': 'RUB name', 'code': 'RUB'},
            {'id': 3, 'name': 'EUR name', 'code': 'EUR'}
        ])

    def test_get_detail(self):
        url = reverse('currency-detail', args=[1])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.login()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertDictEqual(resp.data, {'id': 1, 'name': 'USD name', 'code': 'USD'})
