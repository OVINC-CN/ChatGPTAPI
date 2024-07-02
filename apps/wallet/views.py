import base64
import datetime
import io
import json

import qrcode
from channels.db import database_sync_to_async
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext
from ovinc_client.core.auth import SessionAuthenticate
from ovinc_client.core.paginations import NumPagination
from ovinc_client.core.viewsets import MainViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.wallet.models import BillingHistory, Wallet
from apps.wallet.serializers import (
    BillingHistorySerializer,
    NotifySerializer,
    PreChargeSerializer,
)
from utils.wxpay.api import NaivePrePay
from utils.wxpay.constants import TradeStatus
from utils.wxpay.utils import WXPaySignatureTool


class WalletViewSet(MainViewSet):
    """
    Wallet
    """

    queryset = Wallet.objects.all()

    @action(methods=["GET"], detail=False, authentication_classes=[SessionAuthenticate])
    async def config(self, request, *args, **kwargs):
        """
        wallet config
        """

        return Response(
            data={
                "is_enabled": settings.WXPAY_ENABLED,
                "unit": settings.WXPAY_UNIT,
            }
        )

    @action(methods=["GET"], detail=False)
    async def mine(self, request, *args, **kwargs):
        """
        load user wallet
        """

        inst, _ = await database_sync_to_async(Wallet.objects.get_or_create)(user=request.user)
        return Response(data={"balance": float(inst.balance)})

    @action(methods=["POST"], detail=False)
    async def pre_charge(self, request, *args, **kwargs):
        """
        build charge image
        """

        # verify
        request_serializer = PreChargeSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        request_data = request_serializer.validated_data

        # build billing
        billing: BillingHistory = await database_sync_to_async(BillingHistory.objects.create)(
            user=request.user, amount=request_data["amount"]
        )

        # create wxpay charge
        expire_time = timezone.now() + datetime.timedelta(seconds=settings.WXPAY_ORDER_TIMEOUT)
        formatted_expire_time = expire_time.strftime(settings.WXPAY_TIME_FORMAT)
        prepay_data = await NaivePrePay().request(
            data={
                "appid": settings.WXPAY_APP_ID,
                "mchid": settings.WXPAY_MCHID,
                "description": gettext("Wallet Charge"),
                "out_trade_no": billing.id,
                "notify_url": settings.WXPAY_NOTIFY_URL,
                "amount": {"total": billing.amount * settings.WXPAY_UNIT_TRANS},
                "support_fapiao": settings.WXPAY_SUPPORT_FAPIAO,
                "time_expire": f"{formatted_expire_time[:-2]}:{formatted_expire_time[-2:]}",
            }
        )

        # build qrcode
        img = qrcode.make(prepay_data["code_url"])
        with io.BytesIO() as buffered:
            img.save(buffered, format="PNG")
            return Response(data=base64.b64encode(buffered.getvalue()).decode("utf-8"))

    @action(methods=["POST"], detail=False, authentication_classes=[SessionAuthenticate])
    async def wxpay_notify(self, request, *args, **kwargs):
        """
        wxpay callback
        """

        raw_content = request.body

        # verify
        request_serializer = NotifySerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        request_data = request_serializer.validated_data

        # verify header
        await WXPaySignatureTool.verify(headers=request.headers, content=raw_content)

        # decrypt data
        decrypt_data: bytes = WXPaySignatureTool.decrypt(
            nonce=request_data["resource"]["nonce"].encode(),
            data=base64.b64decode(request_data["resource"]["ciphertext"].encode()),
            associated_data=request_data["resource"]["associated_data"].encode(),
        )
        data = json.loads(decrypt_data.decode())

        # load billing
        billing: BillingHistory = await database_sync_to_async(get_object_or_404)(
            BillingHistory, id=data.get("out_trade_no")
        )
        billing.callback_data = data
        billing.is_success = data["trade_state"] == TradeStatus.SUCCESS
        billing.callback_at = timezone.now()
        billing.state = data["trade_state"]
        await database_sync_to_async(billing.save_to_wallet)(
            update_fields=["is_success", "callback_at", "state", "callback_data"]
        )

        return HttpResponse(status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False)
    async def billing_history(self, request, *args, **kwargs):
        """
        Billing History
        """

        # load billings
        queryset = BillingHistory.objects.filter(user=request.user).order_by("-created_at").prefetch_related("user")

        # page
        paginator = NumPagination()
        page_queryset = await database_sync_to_async(paginator.paginate_queryset)(
            queryset=queryset, request=request, view=self
        )

        serializer = BillingHistorySerializer(instance=page_queryset, many=True)
        return paginator.get_paginated_response(data=await serializer.adata)
