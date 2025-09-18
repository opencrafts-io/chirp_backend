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
from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

# Base URL patterns without prefix
base_urlpatterns = [
    path('admin/', admin.site.urls),
    path('ping/', views.PingView.as_view(), name='ping'),
    path('statuses/', include('posts.urls')),
    path('groups/', include('groups.urls')),
    path('conversations/', include('conversations.urls')),
    path('messages/', include('dmessages.urls')),
    path('chat/', include('websocket_chat.urls')),
    path('users/search/', views.UserSearchView.as_view(), name='user_search'),
    path('users/<str:user_id>/', views.UserInfoView.as_view(), name='user_info'),
    path('users/<str:user_id>/roles/', views.UserRolesView.as_view(), name='user_roles'),
    path('users/<str:user_id>/permissions/', views.UserPermissionsView.as_view(), name='user_permissions'),
    path('admin/maintenance/', views.AdminMaintenanceView.as_view(), name='admin_maintenance'),
]

# Add qa-chirp prefix for local testing
urlpatterns = [
    path('qa-chirp/', include(base_urlpatterns)),
]

# Also include base patterns for backward compatibility
urlpatterns += base_urlpatterns

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
