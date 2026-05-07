from rest_framework import serializers
from .models import Usuario, Persona, Rol, UsuarioRol
from django.contrib.auth.hashers import check_password, make_password
from .rate_limiter import LoginRateLimiter
from django.utils import timezone

class PersonaSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()
    username_generado = serializers.SerializerMethodField()
    
    class Meta:
        model = Persona
        fields = [
            'ci', 'nombres', 'apellido_paterno', 'apellido_materno', 
            'nombre_completo', 'cargo', 'telefono', 'direccion', 
            'correo', 'unidad', 'imagen', 'username_generado'
        ]
        read_only_fields = ['creado_por', 'fecha_creacion', 'modificado_por', 'fecha_modificacion']
    
    def get_nombre_completo(self, obj)->str:
        return f"{obj.nombres} {obj.apellido_paterno or ''} {obj.apellido_materno or ''}".strip()
    
    def get_username_generado(self, obj):
        """Generar username basado en nombres y apellidos"""
        if obj.nombres and obj.apellido_paterno:
            nombre_partes = obj.nombres.split()
            primera_letra_nombre = nombre_partes[0][0].lower() if nombre_partes else ''
            apellido_paterno_completo = obj.apellido_paterno.lower()
            
            username_base = f"{primera_letra_nombre}{apellido_paterno_completo}"
            
            # Verificar si ya existe
            username = username_base
            contador = 1
            while Usuario.objects.filter(username=username).exists():
                username = f"{username_base}{contador}"
                contador += 1
            
            return username
        return None

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id', 'nombre']

class UsuarioRolSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source='rol.nombre', read_only=True)
    
    class Meta:
        model = UsuarioRol
        fields = ['id', 'usuario', 'rol', 'rol_nombre', 'fecha_asignacion']

class UsuarioSerializer(serializers.ModelSerializer):
    persona = PersonaSerializer(read_only=True)
    persona_ci = serializers.SlugRelatedField(
        slug_field='ci',
        queryset=Persona.objects.all(),
        source='persona',
        write_only=True,
        required=False,
        allow_null=True
    )
    roles = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'password', 'persona', 'persona_ci', 'roles',
            'is_active', 'is_deleted', 'date_joined', 'last_login', 'email'
        ]
        read_only_fields = ['date_joined', 'last_login', 'is_deleted']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def get_roles(self, obj)-> list[dict]:
        usuario_roles = UsuarioRol.objects.filter(usuario=obj).select_related('rol')
        return [{'id': ur.rol.id, 'nombre': ur.rol.nombre} for ur in usuario_roles]
    
    def create(self, validated_data):
        password = validated_data.pop('password', '123456')  # Contraseña por defecto
        persona = validated_data.pop('persona', None)
        
        # Si no hay username, generarlo de la persona
        if not validated_data.get('username') and persona:
            validated_data['username'] = self.generar_username(persona)
        
        # Encriptar contraseña
        validated_data['password'] = make_password(password)
        
        usuario = Usuario.objects.create(**validated_data)
        
        if persona:
            usuario.persona = persona
            usuario.save()
        
        return usuario
    
    def generar_username(self, persona):
        """Generar username único basado en persona"""
        nombre_partes = persona.nombres.split()
        primera_letra_nombre = nombre_partes[0][0].lower() if nombre_partes else ''
        apellido_paterno_completo = persona.apellido_paterno.lower()
        
        username_base = f"{primera_letra_nombre}{apellido_paterno_completo}"
        
        username = username_base
        contador = 1
        while Usuario.objects.filter(username=username).exists():
            username = f"{username_base}{contador}"
            contador += 1
        
        return username
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        persona = validated_data.pop('persona', None)
        
        if persona:
            instance.persona = persona
            if persona.correo:
                instance.email = persona.correo
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance

class RegistroUsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    persona_ci = serializers.SlugRelatedField(
        slug_field='ci',
        queryset=Persona.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Usuario
        fields = ['username', 'password', 'password2', 'persona_ci']
    
    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})
        return data
    
    def create(self, validated_data):
        validated_data.pop('password2')
        persona = validated_data.pop('persona_ci', None)
        password = validated_data.pop('password')
        
        usuario = Usuario.objects.create_user(
            username=validated_data['username'],
            password=password
        )
        
        if persona:
            usuario.persona = persona
            usuario.save()
        
        return usuario

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, style={'input_type': 'password'})
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        request = self.context.get('request')
        
        if not username or not password:
            raise serializers.ValidationError({
                "message": "Debe proporcionar username y password",
                "code": "missing_credentials"
            })
        
        try:
            user = Usuario.objects.get(username=username)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError({
                "message": "Usuario no encontrado",
                "code": "invalid_credentials"
            })
        
        # Verificar si fue eliminado lógicamente
        if user.is_deleted:
            raise serializers.ValidationError({
                "message": "Usuario eliminado. Contacte al administrador",
                "code": "user_deleted"
            })
        
        is_blocked, wait_minutes = LoginRateLimiter.is_blocked(username)
        
        if is_blocked:
            raise serializers.ValidationError({
                "message": f"Demasiados intentos fallidos. Espere {wait_minutes} minutos antes de volver a intentar",
                "code": "rate_limit_exceeded",
                "wait_minutes": wait_minutes
            })
        
        if not check_password(password, user.password):
            if request:
                LoginRateLimiter.register_attempt(request, username, success=False)
            
            remaining = LoginRateLimiter.get_remaining_attempts(username)
            
            raise serializers.ValidationError({
                "message": f"Contraseña incorrecta. Le quedan {remaining} intento(s)",
                "code": "invalid_password",
                "remaining_attempts": remaining
            })
        
        if not user.is_active:
            raise serializers.ValidationError({
                "message": "Usuario inactivo. Contacte al administrador",
                "code": "user_inactive"
            })
        
        if request:
            LoginRateLimiter.register_attempt(request, username, success=True)
            LoginRateLimiter.clear_attempts(username)
        
        data['user'] = user
        return data

class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UsuarioSerializer()

# Nuevo serializer para crear Persona + Usuario automáticamente
class PersonaCreateSerializer(serializers.Serializer):
    ci = serializers.CharField(max_length=20)
    nombres = serializers.CharField(max_length=100)
    apellido_paterno = serializers.CharField(max_length=100, required=False, allow_blank=True)
    apellido_materno = serializers.CharField(max_length=100, required=False, allow_blank=True)
    cargo = serializers.CharField(max_length=100)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    direccion = serializers.CharField(required=False, allow_blank=True)
    correo = serializers.EmailField(required=False, allow_blank=True)
    unidad = serializers.CharField(max_length=100, required=False, allow_blank=True)
    imagen = serializers.ImageField(required=False)
    roles = serializers.ListField(child=serializers.CharField(), required=False)
    
    def create(self, validated_data):
        roles_data = validated_data.pop('roles', [])
        request = self.context.get('request')
        
        # Crear Persona con campos de auditoría
        persona = Persona.objects.create(
            **validated_data,
            creado_por=request.user if request else None,  # IMPORTANTE: asignar el usuario que crea
            fecha_creacion=timezone.now()
        )
        
        # Generar username automático
        nombre_partes = persona.nombres.split()
        primera_letra_nombre = nombre_partes[0][0].lower() if nombre_partes else ''
        apellido_paterno_completo = (persona.apellido_paterno or '').lower()
        
        username_base = f"{primera_letra_nombre}{apellido_paterno_completo}"
        username = username_base
        contador = 1
        while Usuario.objects.filter(username=username).exists():
            username = f"{username_base}{contador}"
            contador += 1
        
        # Crear Usuario
        usuario = Usuario.objects.create_user(
            username=username,
            password='123456',
            email=persona.correo or '',
            is_active=True,
            persona=persona
        )
        
        # Asignar roles
        for rol_nombre in roles_data:
            try:
                rol = Rol.objects.get(nombre=rol_nombre)
                UsuarioRol.objects.create(usuario=usuario, rol=rol)
            except Rol.DoesNotExist:
                pass
        
        return {
            'persona': persona,
            'usuario': usuario,
            'username_generado': username,
            'password_generado': '123456'
        }