from rest_framework import serializers
from django.utils.text import slugify
from .models import Categoria, Producto, ProductoImagen

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'slug', 'descripcion', 'imagen', 'orden', 'activo']
        read_only_fields = ['id', 'slug']

class ProductoImagenSerializer(serializers.ModelSerializer):
    imagen_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductoImagen
        fields = ['id', 'imagen', 'imagen_url', 'orden', 'activo']
        read_only_fields = ['id']
    
    def get_imagen_url(self, obj):
        if obj.imagen:
            return obj.imagen.url
        return None

class ProductoListSerializer(serializers.ModelSerializer):
    categoria_nombres = serializers.SerializerMethodField()
    categoria_ids = serializers.SerializerMethodField()
    precio_actual = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    descuento_porcentaje = serializers.IntegerField(read_only=True)
    tiene_stock = serializers.BooleanField(read_only=True)
    imagen_principal_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'slug', 'descripcion_corta',
            'precio', 'precio_oferta', 'precio_actual', 'descuento_porcentaje',
            'stock', 'stock_minimo', 'activo', 'imagen_principal_url',
            'destacado', 'oferta', 'nuevo', 'mas_vendido',
            'calificacion_promedio', 'total_resenas', 'tiene_stock',
            'categoria_nombres', 'categoria_ids'
        ]
    
    def get_categoria_nombres(self, obj):
        return [cat.nombre for cat in obj.categorias.all()]
    
    def get_categoria_ids(self, obj):
        return [cat.id for cat in obj.categorias.all()]
    
    def get_imagen_principal_url(self, obj):
        if obj.imagen_principal:
            return obj.imagen_principal.url
        return None

class ProductoDetailSerializer(serializers.ModelSerializer):
    categorias = CategoriaSerializer(many=True, read_only=True)
    categoria_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Categoria.objects.filter(activo=True),
        source='categorias',
        write_only=True,
        required=False
    )
    imagenes = ProductoImagenSerializer(many=True, read_only=True)
    imagen_principal_url = serializers.SerializerMethodField()
    precio_actual = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    descuento_porcentaje = serializers.IntegerField(read_only=True)
    tiene_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'slug', 'descripcion_corta', 'descripcion_larga',
            'precio', 'precio_oferta', 'stock', 'stock_minimo',
            'imagen_principal', 'imagen_principal_url', 'imagenes',
            'categorias', 'categoria_ids',
            'destacado', 'oferta', 'nuevo', 'mas_vendido',
            'calificacion_promedio', 'total_resenas', 'activo',
            'precio_actual', 'descuento_porcentaje', 'tiene_stock',
            'creado_por', 'modificado_por', 'fecha_creacion', 'fecha_modificacion',
        ]
        read_only_fields = [
            'id', 'slug', 'creado_por', 'modificado_por',
            'fecha_creacion', 'fecha_modificacion'
        ]
    
    def get_imagen_principal_url(self, obj):
        if obj.imagen_principal:
            return obj.imagen_principal.url
        return None
    
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
            instance.slug = slugify(validated_data['nombre'])
        
        # Actualizar campos incluyendo imagen_principal
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        if categorias is not None:
            instance.categorias.set(categorias)
        
        return instance