# products/models.py - Versión corregida
from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings

# Importar tu AuditoriaBase
from modulos.utilitario.models import AuditoriaBase

class Categoria(AuditoriaBase):
    """Categoría de productos"""
    nombre = models.CharField("Nombre", max_length=100, unique=True)
    slug = models.SlugField("Slug", max_length=100, unique=True)
    descripcion = models.TextField("Descripción", blank=True)
    imagen = models.TextField("Imagen (base64)", blank=True, null=True)
    orden = models.IntegerField("Orden", default=0)
    activo = models.BooleanField("Activo", default=True)
    
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['orden', 'nombre']
    
    def __str__(self):
        return self.nombre
    
    def save(self, *args, **kwargs):
        # Generar slug automáticamente si no existe
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

class Producto(AuditoriaBase):
    """Producto para la tienda"""
    nombre = models.CharField("Nombre", max_length=200)
    slug = models.SlugField("Slug", max_length=200,blank=True)
    descripcion_corta = models.TextField("Descripción corta", max_length=500)
    descripcion_larga = models.TextField("Descripción larga", blank=True)
    precio = models.DecimalField("Precio", max_digits=10, decimal_places=2)
    precio_oferta = models.DecimalField("Precio oferta", max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField("Stock", default=0, validators=[MinValueValidator(0)])
    stock_minimo = models.IntegerField("Stock mínimo", default=5)
    imagen_principal = models.TextField("Imagen principal (base64)", blank=True, null=True)
    imagenes_adicionales = models.JSONField("Imágenes adicionales", default=list, blank=True)
    categorias = models.ManyToManyField(Categoria, related_name='productos')
    
    # Características
    destacado = models.BooleanField("Producto destacado", default=False)
    oferta = models.BooleanField("En oferta", default=False)
    nuevo = models.BooleanField("Producto nuevo", default=False)
    mas_vendido = models.BooleanField("Más vendido", default=False)
    
    # Calificaciones
    calificacion_promedio = models.DecimalField("Calificación", max_digits=3, decimal_places=2, default=0)
    total_resenas = models.IntegerField("Total reseñas", default=0)
    
    # Estado
    activo = models.BooleanField("Activo", default=True)
    
    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-destacado', '-fecha_creacion']
    
    def __str__(self):
        return self.nombre
    
    def save(self, *args, **kwargs):
        # Generar slug automáticamente si no existe
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)
    
    @property
    def precio_actual(self):
        if self.oferta and self.precio_oferta:
            return self.precio_oferta
        return self.precio
    
    @property
    def descuento_porcentaje(self):
        if self.oferta and self.precio_oferta:
            return int(((self.precio - self.precio_oferta) / self.precio) * 100)
        return 0
    
    @property
    def tiene_stock(self):
        return self.stock > 0