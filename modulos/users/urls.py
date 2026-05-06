from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsuarioViewSet, PersonaViewSet, RolViewSet, AuthViewSet

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'personas', PersonaViewSet)
router.register(r'roles', RolViewSet)

# Router para auth (sin prefijo api porque ya lo tenemos en urls.py principal)
auth_router = DefaultRouter()
auth_router.register(r'auth', AuthViewSet, basename='auth')

urlpatterns = [
    # Incluir las rutas del router
    path('', include(router.urls)),
    path('', include(auth_router.urls)),
]