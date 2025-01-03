from rest_framework.routers import DefaultRouter

from apps.chat.views import (
    AIModelViewSet,
    ChatMessageChangeLogView,
    ChatViewSet,
    SystemPresetViewSet,
)

router = DefaultRouter()
router.register("chat", ChatViewSet)
router.register("models", AIModelViewSet, basename="ai_model")
router.register("system_presets", SystemPresetViewSet)
router.register("message_log", ChatMessageChangeLogView)

urlpatterns = router.urls
