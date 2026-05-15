from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from modulos.utilitario.viewset import RestViewSet
from modulos.utilitario.response import SuccessResponse, ErrorResponse
from .models import Usuario, Persona, Rol, UsuarioRol
from .serializers import (
    UsuarioSerializer,
    PersonaSerializer,
    RolSerializer,
    RegistroUsuarioSerializer,
    LoginSerializer,
    UsuarioRolSerializer,
    PersonaCreateSerializer,
)


@extend_schema(tags=["Gestión de Users"])
class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def get_serializer_context(self):
        """Pasar request al serializer"""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            errors = serializer.errors
            error_message = "Error de autenticación"
            remaining_attempts = None
            wait_minutes = None

            # Extraer información del error
            if isinstance(errors, dict):
                if "non_field_errors" in errors:
                    error_detail = errors["non_field_errors"][0]
                    if isinstance(error_detail, dict):
                        # error_message = error_detail.get('message', 'Credenciales inválidas')
                        error_message = error_detail.get(
                            "message", "Usuario no encontrado"
                        )
                        remaining_attempts = error_detail.get("remaining_attempts")
                        wait_minutes = error_detail.get("wait_minutes")
                elif "username" in errors:
                    error_message = str(errors["username"][0])
                elif "password" in errors:
                    error_message = str(errors["password"][0])

            # Construir respuesta de error personalizada
            response_data = {"message": error_message, "errors": errors}

            if remaining_attempts is not None:
                response_data["remaining_attempts"] = remaining_attempts
            if wait_minutes is not None:
                response_data["wait_minutes"] = wait_minutes

            return ErrorResponse(
                message=error_message,
                errors=response_data,
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        user = serializer.validated_data["user"]

        # Actualizar último login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        # Generar tokens
        refresh = RefreshToken.for_user(user)

        # Serializar usuario
        user_serializer = UsuarioSerializer(user, context={"request": request})

        return SuccessResponse(
            message="Inicio de sesión exitoso",
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_serializer.data,
            },
        )

    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        serializer = RegistroUsuarioSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(
                message="Error en el registro",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()

        # Generar tokens
        refresh = RefreshToken.for_user(user)
        user_serializer = UsuarioSerializer(user, context={"request": request})

        return SuccessResponse(
            message="Usuario registrado exitosamente",
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_serializer.data,
            },
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="refresh")
    def refresh_token(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return ErrorResponse(
                message="Se requiere refresh token",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)

            return SuccessResponse(
                message="Token refrescado exitosamente", data={"access": access_token}
            )
        except Exception as e:
            return ErrorResponse(
                message="Token inválido o expirado",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

    @action(detail=False, methods=["post"], url_path="logout")
    def logout(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except TokenError:
                    # Token expirado o inválido
                    pass

            return SuccessResponse(message="Logout exitoso")
        except Exception as e:
            return ErrorResponse(message="Error en logout", errors=str(e))


@extend_schema(tags=["Gestion de Usuarioss"])
class UsuarioViewSet(RestViewSet):
    queryset = Usuario.objects.all().select_related("persona").prefetch_related("roles")
    serializer_class = UsuarioSerializer

    def get_permissions(self):
        if self.action in ["create", "list", "retrieve"]:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return ErrorResponse(
                message="Error de validación en los datos",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Guardar el usuario sin los campos de auditoría
            usuario = serializer.save()

            return SuccessResponse(
                message="Registro creado con éxito",
                data=self.get_serializer(usuario).data,
                status_code=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return ErrorResponse(
                message="Error interno del servidor",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial, context={"request": request}
        )

        if not serializer.is_valid():
            return ErrorResponse(
                message="Datos no válidos para actualización",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            usuario = serializer.save()
            return SuccessResponse(
                message="Registro actualizado con éxito",
                data=self.get_serializer(usuario).data,
            )
        except Exception as e:
            return ErrorResponse(
                message="Error interno al actualizar",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            # Soft delete si quieres, o delete real
            instance.delete()
            return SuccessResponse(message="Registro eliminado con éxito")
        except Exception as e:
            return ErrorResponse(message="Ocurrió un error", errors=str(e))

    @action(detail=True, methods=["post"], url_path="asignar-rol")
    def asignar_rol(self, request, pk=None):
        usuario = self.get_object()
        rol_id = request.data.get("rol_id")

        if not rol_id:
            return ErrorResponse(message="Se requiere rol_id")

        try:
            rol = Rol.objects.get(id=rol_id)
            # Verificar si ya tiene el rol
            if UsuarioRol.objects.filter(usuario=usuario, rol=rol).exists():
                return ErrorResponse(message="El usuario ya tiene este rol")

            usuario_rol = UsuarioRol.objects.create(usuario=usuario, rol=rol)

            serializer = UsuarioRolSerializer(usuario_rol)
            return SuccessResponse(
                message="Rol asignado exitosamente",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED,
            )
        except Rol.DoesNotExist:
            return ErrorResponse(message="Rol no encontrado")
        except Exception as e:
            return ErrorResponse(message="Error al asignar rol", errors=str(e))

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="rol_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
            )
        ]
    )
    @action(detail=True, methods=["delete"], url_path="quitar-rol/(?P<rol_id>[^/.]+)")
    def quitar_rol(self, request, pk=None, rol_id=None):
        usuario = self.get_object()

        try:
            usuario_rol = UsuarioRol.objects.get(usuario=usuario, rol_id=rol_id)
            usuario_rol.delete()

            return SuccessResponse(message="Rol removido exitosamente")
        except UsuarioRol.DoesNotExist:
            return ErrorResponse(message="El usuario no tiene este rol")
        except Exception as e:
            return ErrorResponse(message="Error al quitar rol", errors=str(e))

    @action(detail=True, methods=["get"], url_path="roles")
    def listar_roles(self, request, pk=None):
        usuario = self.get_object()
        usuario_roles = UsuarioRol.objects.filter(usuario=usuario).select_related("rol")
        serializer = UsuarioRolSerializer(usuario_roles, many=True)

        return SuccessResponse(message="Roles del usuario", data=serializer.data)

    # Agregar estos métodos al final de la clase UsuarioViewSet

    @action(detail=True, methods=["delete"])
    def soft_delete(self, request, pk=None):
        """Eliminación lógica de usuario"""
        usuario = self.get_object()
        usuario.soft_delete()
        return SuccessResponse(
            message=f"Usuario {usuario.username} eliminado lógicamente",
            data={
                "id": usuario.id,
                "username": usuario.username,
                "is_deleted": usuario.is_deleted,
            },
        )

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        """Restaurar usuario eliminado lógicamente"""
        usuario = self.get_object()
        usuario.restore()
        return SuccessResponse(
            message=f"Usuario {usuario.username} restaurado",
            data={
                "id": usuario.id,
                "username": usuario.username,
                "is_active": usuario.is_active,
            },
        )

    @action(detail=False, methods=["get"])
    def usuarios_eliminados(self, request):
        """Listar usuarios eliminados lógicamente"""
        usuarios = Usuario.objects.filter(is_deleted=True)
        serializer = self.get_serializer(usuarios, many=True)
        return SuccessResponse(message="Usuarios eliminados", data=serializer.data)

    @action(detail=False, methods=['post'])
    def crear_persona_con_usuario(self, request):
        """Endpoint para crear Persona y Usuario automáticamente"""
        serializer = PersonaCreateSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return ErrorResponse(
                message="Error en los datos",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        result = serializer.save()
        
        return SuccessResponse(
            message="Persona y Usuario creados exitosamente",
            data={
                "persona": PersonaSerializer(result['persona']).data,
                "usuario": {
                    "id": result['usuario'].id,
                    "username": result['username_generado'],
                    "password": result['password_generado']
                }
            },
            status_code=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Gestion de Personas"])
class PersonaViewSet(RestViewSet):
    queryset = Persona.objects.all()
    serializer_class = PersonaSerializer

    def perform_create(self, serializer):
        # Persona sí tiene campos de auditoría
        serializer.save(creado_por=self.request.user)

    def perform_update(self, serializer):
        serializer.save(
            modificado_por=self.request.user, fecha_modificacion=timezone.now()
        )

    def perform_destroy(self, instance):
        instance.eliminado_por = self.request.user
        instance.fecha_eliminacion = timezone.now()
        instance.save()


@extend_schema(tags=["Gestión de Roles"])
class RolViewSet(RestViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer

    def perform_create(self, serializer):
        serializer.save()
