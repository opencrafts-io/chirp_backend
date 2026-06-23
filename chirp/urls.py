"""
URL configuration for chirp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import logging
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from urllib.parse import urlparse, urlunparse
from . import views

# Base URL patterns without prefix
urlpatterns = [
    path("admin/", admin.site.urls),
    path("ping", views.PingView.as_view(), name="ping"),
    path("posts/", include("posts.urls")),
    path("community/", include("communities.urls")),
    path("conversations/", include("conversations.urls")),
    path("messages/", include("dmessages.urls")),
    path("chat/", include("websocket_chat.urls")),
    path("interactions/", include("interactions.urls")),
    # path('users/search/', views.UserSearchView.as_view(), name='user_search'),
    # path('users/<str:user_id>/', views.UserInfoView.as_view(), name='user_info'),
    # path('users/<str:user_id>/roles/', views.UserRolesView.as_view(), name='user_roles'),
    # path('users/<str:user_id>/permissions/', views.UserPermissionsView.as_view(), name='user_permissions'),
    # path('maintenance/', views.AdminMaintenanceView.as_view(), name='admin_maintenance'),
    path("users/", include("users.urls")),
    path("silk/", include("silk.urls", namespace="silk")),
    # path('search/', views.UnifiedSearchView.as_view(), name='unified-search'),
]

# Add qa-chirp prefix for local testing
# urlpatterns = [
#     path('qa-chirp/', include(base_urlpatterns)),
# ]

# Also include base patterns for backward compatibility
# urlpatterns += base_urlpatterns
# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# urlpatterns += static('/qa-chirp' + settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

logger = logging.getLogger("chirp")
broker_url = getattr(settings, "CELERY_BROKER_URL", "")

if broker_url.endswith("//"):
    # If it fails, mask it cleanly using the parser fallback
    parsed = urlparse(broker_url)
    safe_netloc = f"{parsed.username}:******@{parsed.hostname}" + (
        f":{parsed.port}" if parsed.port else ""
    )
    bad_url = urlunparse(parsed._replace(netloc=safe_netloc))

    logger.error(f"[CRITICAL]: Malformed CELERY_BROKER_URL detected: {bad_url}")
else:
    # Safely isolate and mask the password segment structurally
    parsed = urlparse(broker_url)
    if parsed.password:
        safe_netloc = f"{parsed.username}:******@{parsed.hostname}"
        if parsed.port:
            safe_netloc += f":{parsed.port}"
        clean_url = urlunparse(parsed._replace(netloc=safe_netloc))
    else:
        clean_url = broker_url

    logger.info(f"Celery broker URL successfully validated: {clean_url}")
