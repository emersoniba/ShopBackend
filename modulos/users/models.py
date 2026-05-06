from django.db import models
from django.contrib.auth.models import AbstractUser
from modulos.utilitario.models import AuditoriaBase

class Persona(AuditoriaBase):
    ci = models.CharField("Carnet de la persona", max_length=20, unique=True, primary_key=True)
    nombres = models.CharField("Nombres de la persona", max_length=100, blank=False, null=False)
    apellido_paterno = models.CharField("Apellido paterno", max_length=100, blank=True, null=True)
    apellido_materno = models.CharField("Apellido materno", max_length=100, blank=True, null=True)
    cargo = models.CharField("Cargo que ocupa", max_length=100, blank=False, null=False)
    telefono = models.CharField("Telefono de usuario", max_length=20, blank=True, null=True)
    direccion = models.TextField("Direccion de persona", blank=True, null=True)
    correo = models.EmailField("Correo de persona", blank=True, null=True)
    unidad = models.CharField("Unidad en la que se encuentra", max_length=100, null=True, blank=True)
    imagen = models.ImageField("Imagen de perfil", upload_to='imagenes_perfil/', null=True, blank=True)

    class Meta:
        ordering = ['nombres']
        verbose_name = 'Persona'
        verbose_name_plural = 'Personas'

    def __str__(self):
        return f"{self.nombres} {self.apellido_paterno or ''} - {self.ci}"

class Rol(models.Model):
    nombre = models.CharField("Rol:", max_length=100, unique=True)
    
    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
    
    def __str__(self):
        return self.nombre

class Usuario(AbstractUser):
    first_name = None
    last_name = None
    
    persona = models.OneToOneField(
        Persona, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='usuario'
    )
    roles = models.ManyToManyField(Rol, through='UsuarioRol', related_name='usuarios')
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        if self.persona:
            return f"{self.username} - {self.persona.nombres} {self.persona.apellido_paterno or ''}"
        return self.username

class UsuarioRol(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='usuario_roles')
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, related_name='rol_usuarios')
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'rol')
        verbose_name = 'Asignación de Rol'
        verbose_name_plural = 'Asignaciones de Roles'
    
    def __str__(self):
        return f"{self.usuario.username} - {self.rol.nombre}"

class LoginAttempt(models.Model):
    """Registro de intentos de login para prevenir ataques de fuerza bruta"""
    username = models.CharField("Nombre de usuario", max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField("Dirección IP", null=True, blank=True)
    user_agent = models.TextField("User Agent", blank=True, null=True)
    success = models.BooleanField("¿Exitoso?", default=False)
    attempt_time = models.DateTimeField("Fecha y hora del intento", auto_now_add=True)
    
    class Meta:
        verbose_name = "Intento de Login"
        verbose_name_plural = "Intentos de Login"
        ordering = ['-attempt_time']
        indexes = [
            models.Index(fields=['username', 'attempt_time']),
            models.Index(fields=['ip_address', 'attempt_time']),
        ]
    
    def __str__(self):
        return f"{self.username} - {self.success} - {self.attempt_time}"