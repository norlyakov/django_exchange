# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 25.01.2020
"""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from ..testing import create_currency, create_stock


class StockAPITests(APITestCase):
    stocks = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.password = 'password'
        cls.owner = User.objects.create_user(
            username='owner', email='owner@test.com', password=cls.password)
        cls.other_user = User.objects.create_user(
            username='other', email='other@test.com', password=cls.password)

        usd = create_currency('USD')
        cls.stocks.append(create_stock(cls.owner, usd))
        rub = create_currency('RUB')
        cls.stocks.append(create_stock(cls.owner, rub))
        eur = create_currency('EUR')
        cls.stocks.append(create_stock(cls.owner, eur))

    def tearDown(self):
        self.client.logout()

    def login(self, user=None):
        user = user or self.owner
        self.client.login(username=user.username, password=self.password)

    def test_get_list(self):
        url = reverse('stock-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.login()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        self.assertEqual(data['count'], 3)
        self.assertListEqual(data['results'], [
            {'id': 1, 'user': self.owner.username, 'currency': 'USD', 'value': '0.00000'},
            {'id': 2, 'user': self.owner.username, 'currency': 'RUB', 'value': '0.00000'},
            {'id': 3, 'user': self.owner.username, 'currency': 'EUR', 'value': '0.00000'},
        ])

        # by other user
        self.client.logout()
        self.login(user=self.other_user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        self.assertEqual(data['count'], 0)

    def test_get_detail(self):
        url = reverse('stock-detail', args=[1])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.login()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertDictEqual(resp.data, {'id': 1, 'user': self.owner.username, 'currency': 'USD', 'value': '0.00000'})

        # by other user
        self.client.logout()
        self.login(user=self.other_user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_post(self):
        url = reverse('stock-list')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.login()
        create_currency('JPY')
        resp = self.client.post(url, data={'currency': 'JPY'})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(resp.data, {'id': 4, 'user': self.owner.username, 'currency': 'JPY', 'value': '0.00000'})

        resp = self.client.post(url, data={'currency': 'NONEXISTS'})
        self.assertContains(resp, 'Currency with such code does not exist', status_code=400)

        # by other user
        self.client.logout()
        self.login(user=self.other_user)
        resp = self.client.post(url, data={'currency': 'JPY'})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(resp.data,
                             {'id': 5, 'user': self.other_user.username, 'currency': 'JPY', 'value': '0.00000'})
