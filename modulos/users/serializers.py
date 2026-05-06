from rest_framework import serializers
from .models import Usuario, Persona, Rol, UsuarioRol
from django.contrib.auth.hashers import check_password
from .rate_limiter import LoginRateLimiter

class PersonaSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()
    
    class Meta:
        model = Persona
        fields = [
            'ci', 'nombres', 'apellido_paterno', 'apellido_materno', 
            'nombre_completo', 'cargo', 'telefono', 'direccion', 
            'correo', 'unidad', 'imagen'
        ]
        read_only_fields = ['creado_por', 'fecha_creacion', 'modificado_por', 'fecha_modificacion']
    
    def get_nombre_completo(self, obj)->str:
        return f"{obj.nombres} {obj.apellido_paterno or ''} {obj.apellido_materno or ''}".strip()

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
    password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'password', 'persona', 'persona_ci', 'roles',
            'is_active', 'date_joined', 'last_login','email'
        ]
        read_only_fields = ['date_joined', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def get_roles(self, obj)-> list[dict]:
        usuario_roles = UsuarioRol.objects.filter(usuario=obj).select_related('rol')
        return [{'id': ur.rol.id, 'nombre': ur.rol.nombre} for ur in usuario_roles]
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        persona = validated_data.pop('persona', None)
        
        if persona and persona.correo:
            validated_data['email'] = persona.correo
        
        usuario = Usuario.objects.create_user(
            username=validated_data['username'],
            password=password,
            email=validated_data.get('email', '') 
        )
        
        if persona:
            usuario.persona = persona
            usuario.save()
        
        return usuario
    
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
            user_exists = True
        except Usuario.DoesNotExist:
            user_exists = False
        
            raise serializers.ValidationError({
                #"message": "Credenciales inválidas",
                "message": "Usuario no encontrado",
                "code": "invalid_credentials"
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
    
