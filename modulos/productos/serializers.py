from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from django.utils.text import slugify
import base64
from django.core.files.base import ContentFile
from .models import Categoria, Producto
from drf_spectacular.utils import extend_schema_field

@extend_schema_field(serializers.CharField)
class Base64ImageField(serializers.Field):   
    """Campo personalizado para manejar imágenes en Base64"""
    def to_internal_value(self, data):
        """Convertir Base64 a archivo"""
        if not data:
            return None
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            img_data = base64.b64decode(imgstr)
            return ContentFile(img_data, name=f"image.{ext}")
        return data
    
    def to_representation(self, value):
        """Convertir archivo a Base64 para la respuesta"""
        if not value:
            return None
        try:
            with open(value.path, 'rb') as img_file:
                img_data = base64.b64encode(img_file.read()).decode('utf-8')
                return f"data:image/{value.path.split('.')[-1]};base64,{img_data}"
        except:
            return None

class CategoriaSerializer(serializers.ModelSerializer):
    imagen = Base64ImageField(required=False, allow_null=True)
    
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'slug', 'descripcion', 'imagen', 'orden', 'activo']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        if not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['nombre'])
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        if 'nombre' in validated_data and not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['nombre'])
        return super().update(instance, validated_data)

class ProductoListSerializer(serializers.ModelSerializer):
    """Serializer para listar productos (con paginación)"""
    categoria_nombres = serializers.SerializerMethodField()
    categoria_ids = serializers.SerializerMethodField()
    precio_actual = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    descuento_porcentaje = serializers.IntegerField(read_only=True)
    tiene_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'slug', 'descripcion_corta', 'precio', 'precio_oferta',
            'precio_actual', 'descuento_porcentaje', 'stock', 'imagen_principal',
            'destacado', 'oferta', 'nuevo', 'mas_vendido', 'calificacion_promedio',
            'total_resenas', 'tiene_stock', 'categoria_nombres', 'categoria_ids'
        ]
        
    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_categoria_nombres(self, obj):
        return [cat.nombre for cat in obj.categorias.all()]
    
    @extend_schema_field(serializers.ListField(child=serializers.IntegerField()))
    def get_categoria_ids(self, obj):
        return [cat.id for cat in obj.categorias.all()]

class ProductoDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalle de producto (completo)"""
    categorias = CategoriaSerializer(many=True, read_only=True)
    categoria_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Categoria.objects.all(),
        source='categorias', 
        required=False
    )
    precio_actual = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    descuento_porcentaje = serializers.IntegerField(read_only=True)
    tiene_stock = serializers.BooleanField(read_only=True)
    imagen_principal = Base64ImageField(required=False, allow_null=True)
    
    class Meta:
        model = Producto
        fields = '__all__'
        read_only_fields = [
            'id',
            'creado_por',
            'fecha_creacion',
            'fecha_modificacion',
            'modificado_por',
        ]
    def create(self, validated_data):
        categorias = validated_data.pop('categorias', [])
        if not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['nombre'])
        producto = Producto.objects.create(**validated_data)
        if categorias:
            producto.categorias.set(categorias)
        return producto
    
    def update(self, instance, validated_data):
        categorias = validated_data.pop('categorias', None)
        if 'nombre' in validated_data and not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['nombre'])
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if categorias is not None:
            instance.categorias.set(categorias)
        return instance