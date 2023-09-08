from rest_framework.routers import DefaultRouter

from apps.trace.views import RUMViewSet

router = DefaultRouter()
router.register("rum", RUMViewSet, basename="rum")

urlpatterns = router.urls
