from rest_framework.routers import DefaultRouter

from apps.cos.views import COSViewSet

router = DefaultRouter()
router.register("cos", COSViewSet)

urlpatterns = router.urls
