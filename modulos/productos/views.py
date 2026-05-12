from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from modulos.utilitario.viewset import RestViewSet
from modulos.utilitario.response import SuccessResponse, ErrorResponse
from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoListSerializer, ProductoDetailSerializer

class CustomPagination(PageNumberPagination):
    """Paginación personalizada"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

class CategoriaViewSet(RestViewSet):
    """CRUD completo de categorías"""
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    pagination_class = CustomPagination
    
    def get_permissions(self):
        # Solo autenticados para crear, actualizar, eliminar
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Si no es admin, solo mostrar activas
        if self.action in ['list', 'retrieve'] and not self.request.user.is_authenticated:
            queryset = queryset.filter(activo=True)
        return queryset

class ProductoViewSet(RestViewSet):
    """CRUD completo de productos"""
    queryset = Producto.objects.all()
    pagination_class = CustomPagination
    
    def get_permissions(self):
        # Solo autenticados para crear, actualizar, eliminar
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductoDetailSerializer
        return ProductoListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros para el catálogo público
        if self.action in ['list', 'retrieve'] and not self.request.user.is_authenticated:
            queryset = queryset.filter(activo=True)
        
        # Filtro por categoría
        categoria_id = self.request.query_params.get('categoria', None)
        if categoria_id:
            queryset = queryset.filter(categorias__id=categoria_id)
        
        categoria_slug = self.request.query_params.get('categoria_slug', None)
        if categoria_slug:
            queryset = queryset.filter(categorias__slug=categoria_slug)
        
        # Búsqueda
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) | 
                Q(descripcion_corta__icontains=search) |
                Q(descripcion_larga__icontains=search)
            )
        
        # Filtros especiales
        if self.request.query_params.get('destacados') == 'true':
            queryset = queryset.filter(destacado=True)
        
        if self.request.query_params.get('ofertas') == 'true':
            queryset = queryset.filter(oferta=True)
        
        if self.request.query_params.get('nuevos') == 'true':
            queryset = queryset.filter(nuevo=True)
        
        # Ordenamiento
        orden = self.request.query_params.get('orden', '-fecha_creacion')
        queryset = queryset.order_by(orden)
        
        return queryset
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def publicos(self, request):
        """Endpoint público para el catálogo (con paginación)"""
        queryset = self.get_queryset().filter(activo=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def destacados(self, request):
        """Productos destacados para el home"""
        productos = self.get_queryset().filter(activo=True, destacado=True)[:8]
        serializer = self.get_serializer(productos, many=True)
        return SuccessResponse(data=serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def ofertas(self, request):
        """Productos en oferta"""
        productos = self.get_queryset().filter(activo=True, oferta=True)[:8]
        serializer = self.get_serializer(productos, many=True)
        return SuccessResponse(data=serializer.data)