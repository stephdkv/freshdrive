"""
URL configuration for fd project.

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
from django.contrib.auth.models import User, Group
from django.views.i18n import JavaScriptCatalog
from django.conf import settings
from django.conf.urls.static import static

# admin.site.unregister(User)
# admin.site.unregister(Group)

admin.site.site_header = 'Администрирование транспортной аренды'
admin.site.site_title = 'Портал администрирования аренды транспорта'
admin.site.index_title = 'Добро пожаловать в портал аренды транспорта'

urlpatterns = [
    path('jet/', include('jet.urls', 'jet')),  # Django Jet URLs
    path('summernote/', include('django_summernote.urls')),
    path('admin/', admin.site.urls),
    path('rentals/', include('rentals.urls')),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
