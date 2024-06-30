from rest_framework.routers import DefaultRouter

from apps.chat.views import (
    AIModelViewSet,
    ChatViewSet,
    SystemPresetViewSet,
    ToolsViewSet,
)

router = DefaultRouter()
router.register("chat", ChatViewSet)
router.register("models", AIModelViewSet, basename="ai_model")
router.register("system_presets", SystemPresetViewSet)
router.register("tools", ToolsViewSet, basename="tools")

urlpatterns = router.urls
