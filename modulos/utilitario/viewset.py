from django.shortcuts import render

from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from .response import SuccessResponse, ErrorResponse
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class RestViewSet(viewsets.ModelViewSet):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            logger.error(f"Error de validación: {serializer.errors}")
            return ErrorResponse(
                message="Error de validación en los datos",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return SuccessResponse(
                message="Registro creado con éxito",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            logger.error(f"Error de validación: {str(e)}")
            return ErrorResponse(
                message="Error al crear el registro",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
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
            logger.error(f"validación en actualización: {serializer.errors}")
            return ErrorResponse(
                message="Datos no válidos para actualización",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            self.perform_update(serializer)
            return SuccessResponse(
                message="Registro actualizado con éxito", data=serializer.data
            )
        except ValidationError as e:
            logger.error(f"Error de validación en actualización: {str(e)}")
            return ErrorResponse(
                message="Error al actualizar",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error inesperado en actualización: {str(e)}")
            return ErrorResponse(
                message="Error interno al actualizar",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(self, instance)

            return SuccessResponse(message="Registro eliminado con éxito", data={})
        except Exception as e:
            return ErrorResponse(message="Ocurrió un error", errors=str(e))

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user, fecha_creacion=timezone.now())

    def perform_update(self, serializer):
        serializer.save(modificado_por=self.request.user, fecha_modificacion=timezone.now())

    def perform_destroy(self, instance):
        instance.eliminado_por = self.request.user
        instance.fecha_eliminacion = timezone.now()
        instance.save()


class RestViewSetSimple(viewsets.ModelViewSet):
    """
    ViewSet base para modelos que NO tienen campos de auditoría.
    No intenta guardar creado_por ni fecha_creacion.
    """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            logger.error(f"Error de validación: {serializer.errors}")
            return ErrorResponse(
                message="Error de validación en los datos",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return SuccessResponse(
                message="Registro creado con éxito",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            logger.error(f"Error de validación: {str(e)}")
            return ErrorResponse(
                message="Error al crear el registro",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
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
            logger.error(f"Error de validación en actualización: {serializer.errors}")
            return ErrorResponse(
                message="Datos no válidos para actualización",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            self.perform_update(serializer)
            return SuccessResponse(
                message="Registro actualizado con éxito", data=serializer.data
            )
        except ValidationError as e:
            logger.error(f"Error de validación en actualización: {str(e)}")
            return ErrorResponse(
                message="Error al actualizar",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error inesperado en actualización: {str(e)}")
            return ErrorResponse(
                message="Error interno al actualizar",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return SuccessResponse(message="Registro eliminado con éxito")
        except Exception as e:
            return ErrorResponse(message="Ocurrió un error", errors=str(e))

    def perform_create(self, serializer):
        # Para modelos sin auditoría, simplemente guardamos
        serializer.save()

    def perform_update(self, serializer):
        # Para modelos sin auditoría, simplemente guardamos
        serializer.save()

    def perform_destroy(self, instance):
        # Eliminación real (no soft delete)
        instance.delete()
