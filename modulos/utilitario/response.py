from rest_framework.response import Response
from rest_framework import status


class SuccessResponse(Response):
    def __init__(self, message, data=None, status_code=status.HTTP_200_OK):
        response_data = {
            "message": message,
            "data": data
        }
        super().__init__(response_data, status=status_code)


class ErrorResponse(Response):
    def __init__(self, message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        response_data = {
            "message": message,
            "errors": errors
        }
        super().__init__(response_data, status=status_code)