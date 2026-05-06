from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import LoginAttempt
from django.db import models

class LoginRateLimiter:
    """
    Limitador de intentos de login para prevenir ataques de fuerza bruta
    SOLO para usuarios que EXISTEN en el sistema
    """
    
    # Configuración por defecto
    MAX_ATTEMPTS = 5  # Máximo de intentos fallidos
    BLOCK_TIME_MINUTES = 15  # Tiempo de bloqueo en minutos
    WINDOW_MINUTES = 15  # Ventana de tiempo para contar intentos
    
    @classmethod
    def get_client_ip(cls, request):
        """Obtener IP real del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @classmethod
    def register_attempt(cls, request, username, success=False):
        """Registrar un intento de login SOLO para usuarios existentes"""
        try:
            LoginAttempt.objects.create(
                username=username,
                ip_address=cls.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                success=success
            )
            print(f"Intento registrado para {username}: success={success}")
        except Exception as e:
            print(f"Error registrando intento: {e}")
    
    @classmethod
    def get_failed_attempts(cls, username):
        """Obtener número de intentos fallidos recientes para un usuario existente"""
        since_time = timezone.now() - timedelta(minutes=cls.WINDOW_MINUTES)
        
        # Solo contar intentos del username específico (NO por IP)
        attempts = LoginAttempt.objects.filter(
            username=username,
            success=False,
            attempt_time__gte=since_time
        )
        
        return attempts.count()
    
    @classmethod
    def is_blocked(cls, username):
        """Verificar si el usuario existente está bloqueado"""
        since_time = timezone.now() - timedelta(minutes=cls.WINDOW_MINUTES)
        
        failed_attempts = LoginAttempt.objects.filter(
            username=username,
            success=False,
            attempt_time__gte=since_time
        ).count()
        
        print(f"Intentos fallidos para {username}: {failed_attempts}")
        
        if failed_attempts >= cls.MAX_ATTEMPTS:
            last_attempt = LoginAttempt.objects.filter(
                username=username,
                success=False,
                attempt_time__gte=since_time
            ).order_by('-attempt_time').first()
            
            if last_attempt:
                time_since_last = timezone.now() - last_attempt.attempt_time
                if time_since_last.total_seconds() < (cls.BLOCK_TIME_MINUTES * 60):
                    remaining = cls.BLOCK_TIME_MINUTES - (time_since_last.total_seconds() / 60)
                    print(f"Usuario {username} bloqueado. Tiempo restante: {remaining}")
                    return True, round(remaining)
        
        return False, 0
    
    @classmethod
    def get_remaining_attempts(cls, username):
        """Obtener intentos restantes para un usuario existente"""
        failed_attempts = cls.get_failed_attempts(username)
        return max(0, cls.MAX_ATTEMPTS - failed_attempts)
    
    @classmethod
    def clear_attempts(cls, username):
        """Limpiar intentos fallidos después de login exitoso"""
        deleted_count = LoginAttempt.objects.filter(username=username, success=False).delete()[0]
        print(f"Intentos fallidos limpiados para {username}: {deleted_count} registros eliminados")