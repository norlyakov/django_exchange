from rest_framework import viewsets, permissions, mixins, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from .erros import TransactionCantBeRevoked
from .models import Stock, Currency, Transaction
from .serializers import StockSerializer, CurrencySerializer, TransactionSerializer


class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [permissions.IsAuthenticated]


class StockViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(stock_from__user=self.request.user) | queryset.filter(stock_to__user=self.request.user)

    @action(methods=['post'], detail=True)
    def revoke(self, request, *args, **kwargs):
        orig_transaction = self.get_object()

        try:
            orig_transaction.revoke()
        except TransactionCantBeRevoked as e:
            raise serializers.ValidationError(str(e))

        return Response({'status': 'Transaction revoked'})
