# -*- coding: utf-8 -*-
"""
:Authors: norlyakov
:Date: 02.02.2020
"""
from decimal import Decimal

from cykooz.testing import ANY
from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from ..models import TransactionTypes, Transaction
from ..testing import create_currency, create_stock, create_transaction


@override_settings()
class TransactionAPITests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.password = 'password'
        cls.master = User.objects.create_user(
            username='master', email='master@test.com', password=cls.password)
        cls.owner = User.objects.create_user(
            username='owner', email='owner@test.com', password=cls.password)
        cls.other_user = User.objects.create_user(
            username='other', email='other@test.com', password=cls.password)

        usd = create_currency('USD')
        rub = create_currency('RUB')

        # master stocks
        cls.master_usd = create_stock(cls.master, usd)
        cls.master_rub = create_stock(cls.master, rub)
        settings.STOCKS_SETTINGS['MASTER_STOCKS'] = {
            'USD': cls.master_usd.pk,
            'RUB': cls.master_rub.pk
        }

        cls.owner_usd = create_stock(cls.owner, usd)
        cls.other_usd = create_stock(cls.other_user, usd)

        cls.owner_rub = create_stock(cls.owner, rub)
        cls.other_rub = create_stock(cls.other_user, rub)

        create_transaction(cls.owner_usd, cls.owner_rub, value=1)
        create_transaction(cls.owner_usd, cls.owner_rub, value=2)
        create_transaction(cls.owner_usd, cls.owner_rub, value=3)

    def tearDown(self):
        self.client.logout()

    def login(self, user=None):
        user = user or self.owner
        self.client.login(username=user.username, password=self.password)

    def test_get_list(self):
        url = reverse('transaction-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.login()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        self.assertEqual(data['count'], 3)
        self.assertListEqual(data['results'], [
            {
                'id': 1,
                'stock_from': self.owner_usd.pk,
                'stock_to': self.owner_rub.pk,
                'value': '1.00000',
                'type': TransactionTypes.common,
                'created': ANY,
                'updated': ANY
            },
            {
                'id': 2,
                'stock_from': self.owner_usd.pk,
                'stock_to': self.owner_rub.pk,
                'value': '2.00000',
                'type': TransactionTypes.common,
                'created': ANY,
                'updated': ANY
            },
            {
                'id': 3,
                'stock_from': self.owner_usd.pk,
                'stock_to': self.owner_rub.pk,
                'value': '3.00000',
                'type': TransactionTypes.common,
                'created': ANY,
                'updated': ANY
            },
        ])

        # by other user
        self.client.logout()
        self.login(user=self.other_user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        self.assertEqual(data['count'], 0)

    def test_get_detail(self):
        url = reverse('transaction-detail', args=[1])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.login()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertDictEqual(resp.data, {
            'id': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.owner_rub.pk,
            'value': '1.00000',
            'type': TransactionTypes.common,
            'created': ANY,
            'updated': ANY
        })

        # by other user
        self.client.logout()
        self.login(user=self.other_user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_common_transaction(self):
        url = reverse('transaction-list')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.login()
        # success
        self.owner_usd.value = 10
        self.owner_usd.save()

        params = {
            'type': TransactionTypes.common,
            'value': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.other_usd.pk,
        }
        resp = self.client.post(url, data=params)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(resp.data, {
            'id': ANY,
            'created': ANY,
            'updated': ANY,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.other_usd.pk,
            'value': '1.00000',
            'type': TransactionTypes.common,
        })
        orig_tr_pk = resp.data['id']

        self.owner_usd.refresh_from_db()
        self.assertEqual(self.owner_usd.value, Decimal('8.9500'))

        self.other_usd.refresh_from_db()
        self.assertEqual(self.other_usd.value, Decimal('1.0000'))

        self.master_usd.refresh_from_db()
        self.assertEqual(self.master_usd.value, Decimal('0.0500'))

        # check commission transaction
        commission_tr_pk = orig_tr_pk + 1
        resp = self.client.get(reverse('transaction-detail', args=[commission_tr_pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertDictEqual(resp.data, {
            'id': ANY,
            'created': ANY,
            'updated': ANY,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.master_usd.pk,
            'value': '0.05000',  # 5 % from config
            'type': TransactionTypes.commission,
        })

        commission_transaction = Transaction.objects.get(pk=commission_tr_pk)
        self.assertEqual(commission_transaction.related_transaction_id, orig_tr_pk)

        # no stock_to
        params = {
            'type': TransactionTypes.common,
            'value': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': '',
        }
        resp = self.client.post(url, data=params)
        self.assertContains(resp, 'Need to provide both stock_from and stock_to', status_code=400)

        # same stocks
        params = {
            'type': TransactionTypes.common,
            'value': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.owner_usd.pk,
        }
        resp = self.client.post(url, data=params)
        self.assertContains(resp, 'Need different stocks', status_code=400)

        # different currency
        params = {
            'type': TransactionTypes.common,
            'value': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.other_rub.pk,
        }
        resp = self.client.post(url, data=params)
        self.assertContains(resp, 'Stocks must have same currency', status_code=400)

        # don have enough money
        self.owner_usd.value = 10
        self.owner_usd.save()

        params = {
            'type': TransactionTypes.common,
            'value': 10,  # not enough for commission
            'stock_from': self.owner_usd.pk,
            'stock_to': self.other_usd.pk,
        }
        resp = self.client.post(url, data=params)
        self.assertContains(resp, "Don't have enough money on stock_from", status_code=400)

        # create for other user
        params = {
            'type': TransactionTypes.common,
            'value': 1,
            'stock_from': self.other_usd.pk,
            'stock_to': self.owner_usd.pk,
        }
        resp = self.client.post(url, data=params)
        self.assertContains(resp, "Stock don't belong to user.", status_code=400)

    def test_create_exchange_transaction(self):
        url = reverse('transaction-list')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.login()
        # success
        self.owner_usd.value = 1
        self.owner_usd.save()

        self.master_rub.value = 65
        self.master_rub.save()

        params = {
            'type': TransactionTypes.exchange,
            'value': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.owner_rub.pk,
        }
        resp = self.client.post(url, data=params)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(resp.data, {
            'id': ANY,
            'created': ANY,
            'updated': ANY,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.master_usd.pk,
            'value': '1.00000',
            'type': TransactionTypes.exchange,
        })
        from_tr_pk = resp.data['id']

        self.owner_usd.refresh_from_db()
        self.assertEqual(self.owner_usd.value, Decimal('0.00000'))

        self.owner_rub.refresh_from_db()
        self.assertEqual(self.owner_rub.value, Decimal('65.00000'))

        self.master_usd.refresh_from_db()
        self.assertEqual(self.master_usd.value, Decimal('1.00000'))

        self.master_rub.refresh_from_db()
        self.assertEqual(self.master_rub.value, Decimal('0.00000'))

        from_transaction = Transaction.objects.get(pk=from_tr_pk)
        to_tr_pk = from_tr_pk + 1
        self.assertEqual(from_transaction.related_transaction_id, to_tr_pk)

        # check to_transaction

        resp = self.client.get(reverse('transaction-detail', args=[to_tr_pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertDictEqual(resp.data, {
            'id': ANY,
            'created': ANY,
            'updated': ANY,
            'stock_from': self.master_rub.pk,
            'stock_to': self.owner_rub.pk,
            'value': '65.00000',
            'type': TransactionTypes.exchange,
        })

        to_transaction = Transaction.objects.get(pk=to_tr_pk)
        self.assertEqual(to_transaction.related_transaction_id, from_tr_pk)

        # no stock_to
        params = {
            'type': TransactionTypes.exchange,
            'value': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': '',
        }
        resp = self.client.post(url, data=params)
        self.assertContains(resp, 'Need to provide both stock_from and stock_to', status_code=400)

        # same stocks
        params = {
            'type': TransactionTypes.exchange,
            'value': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.owner_usd.pk,
        }
        resp = self.client.post(url, data=params)
        self.assertContains(resp, 'Need different stocks', status_code=400)

        # different users
        params = {
            'type': TransactionTypes.exchange,
            'value': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.other_rub.pk,
        }
        resp = self.client.post(url, data=params)
        self.assertContains(resp, 'Stocks must belong to same user', status_code=400)

        # don have enough money
        self.owner_usd.value = 0
        self.owner_usd.save()

        params = {
            'type': TransactionTypes.exchange,
            'value': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.owner_rub.pk,
        }
        resp = self.client.post(url, data=params)
        self.assertContains(resp, "Don't have enough money on stock_from", status_code=400)

        # don have enough money on master stock
        self.owner_usd.value = 1
        self.owner_usd.save()
        self.master_rub.value = 0
        self.master_rub.save()

        params = {
            'type': TransactionTypes.exchange,
            'value': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.owner_rub.pk,
        }
        resp = self.client.post(url, data=params)
        self.assertContains(resp, "Don't have enough money on master stock", status_code=400)

        # create for other user
        params = {
            'type': TransactionTypes.exchange,
            'value': 1,
            'stock_from': self.other_usd.pk,
            'stock_to': self.other_rub.pk,
        }
        resp = self.client.post(url, data=params)
        self.assertContains(resp, "Stock don't belong to user.", status_code=400)

    def test_revoke_transaction(self):
        self.login()
        # create_common transaction
        self.owner_usd.value = 10
        self.owner_usd.save()

        transaction_params = {
            'type': TransactionTypes.common,
            'value': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.other_usd.pk,
        }
        resp = self.client.post(reverse('transaction-list'), data=transaction_params)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        transaction_id = resp.data['id']

        self.client.logout()
        resp = self.client.post(reverse('transaction-revoke', args=[transaction_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # success
        self.login()
        resp = self.client.post(reverse('transaction-revoke', args=[transaction_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        revoke_tr_pk = transaction_id + 2  # also commission transaction exists
        resp = self.client.get(reverse('transaction-detail', args=[revoke_tr_pk]))
        self.assertDictEqual(resp.data, {
            'id': ANY,
            'created': ANY,
            'updated': ANY,
            'stock_from': self.other_usd.pk,
            'stock_to': self.owner_usd.pk,
            'value': '1.00000',
            'type': TransactionTypes.revoke,
        })

        revoke_transaction = Transaction.objects.get(pk=revoke_tr_pk)
        self.assertEqual(revoke_transaction.related_transaction_id, transaction_id)

        self.owner_usd.refresh_from_db()
        self.assertEqual(self.owner_usd.value, Decimal('9.95000'))

        self.other_usd.refresh_from_db()
        self.assertEqual(self.other_usd.value, Decimal('0.00000'))

        self.master_usd.refresh_from_db()
        self.assertEqual(self.master_usd.value, Decimal('0.05000'))

        # check transaction
        resp = self.client.get(reverse('transaction-detail', args=[transaction_id]))
        self.assertDictEqual(resp.data, {
            'id': transaction_id,
            'created': ANY,
            'updated': ANY,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.other_usd.pk,
            'value': '1.00000',
            'type': TransactionTypes.canceled,
        })

        # revoke again
        resp = self.client.post(reverse('transaction-revoke', args=[transaction_id]))
        self.assertContains(resp, 'Only common transactions can be revoked', status_code=400)

        # not enough money on foreign stock
        resp = self.client.post(reverse('transaction-list'), data=transaction_params)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        transaction_id = resp.data['id']

        self.other_usd.value = 0
        self.other_usd.save()

        resp = self.client.post(reverse('transaction-revoke', args=[transaction_id]))
        self.assertContains(resp, 'Not enough money on foreign stock', status_code=400)

        # revoke by user without rights
        self.client.logout()
        self.login(user=self.master)
        resp = self.client.post(reverse('transaction-revoke', args=[transaction_id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # revoke by other user (success)
        self.other_usd.value = 1
        self.other_usd.save()

        self.client.logout()
        self.login(user=self.other_user)
        resp = self.client.post(reverse('transaction-revoke', args=[transaction_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # revoke exchange transaction
        self.client.logout()
        self.login()
        self.owner_usd.value = 1
        self.owner_usd.save()
        self.master_rub.value = 65
        self.master_rub.save()

        params = {
            'type': TransactionTypes.exchange,
            'value': 1,
            'stock_from': self.owner_usd.pk,
            'stock_to': self.owner_rub.pk,
        }
        resp = self.client.post(reverse('transaction-list'), data=params)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        transaction_id = resp.data['id']

        resp = self.client.post(reverse('transaction-revoke', args=[transaction_id]))
        self.assertContains(resp, 'Only common transactions can be revoked', status_code=400)
