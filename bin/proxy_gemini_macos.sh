SITE_PACKAGES=$(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")

sed -i'.bak' '161a\
            from django.conf import settings\
' "$SITE_PACKAGES/google/ai/generativelanguage_v1beta/services/generative_service/transports/grpc.py"

sed -i'.bak2' '175a\
                    ("grpc.http_proxy", settings.OPENAI_HTTP_PROXY_URL),\
' "$SITE_PACKAGES/google/ai/generativelanguage_v1beta/services/generative_service/transports/grpc.py"

sed -i'.bak' '206a\
            from django.conf import settings\
' "$SITE_PACKAGES/google/ai/generativelanguage_v1beta/services/generative_service/transports/grpc_asyncio.py"

sed -i'.bak2' '220a\
                    ("grpc.http_proxy", settings.OPENAI_HTTP_PROXY_URL),\
' "$SITE_PACKAGES/google/ai/generativelanguage_v1beta/services/generative_service/transports/grpc_asyncio.py"
