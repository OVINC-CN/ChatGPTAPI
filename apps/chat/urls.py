from rest_framework.routers import DefaultRouter

from apps.chat.views import AIModelViewSet, ChatViewSet

router = DefaultRouter()
router.register("chat", ChatViewSet)
router.register("models", AIModelViewSet, basename="ai_model")

urlpatterns = router.urls
