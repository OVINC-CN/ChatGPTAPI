from rest_framework.routers import DefaultRouter

from apps.cos.views import COSViewSet

router = DefaultRouter()
router.register("cos", COSViewSet, basename="cos")

urlpatterns = router.urls
