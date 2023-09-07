from rest_framework.routers import DefaultRouter

from apps.home.views import HomeView, I18nViewSet

router = DefaultRouter()
router.register("", HomeView)
router.register("i18n", I18nViewSet, basename="i18n")

urlpatterns = router.urls
