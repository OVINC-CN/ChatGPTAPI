from rest_framework.routers import DefaultRouter

from apps.wallet.views import WalletViewSet

router = DefaultRouter()
router.register("wallets", WalletViewSet)

urlpatterns = router.urls
