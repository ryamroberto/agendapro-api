from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from drf_spectacular.utils import extend_schema, OpenApiResponse


class CurrentUserView(APIView):
    """
    Retorna os dados do usuário autenticado na sessão atual.
    Acesso restrito a usuários autenticados.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Dados do usuário atual",
        description="Retorna os dados cadastrais e o perfil de permissões (cliente comum vs staff) do usuário autenticado.",
        responses={200: OpenApiResponse(description="Dados do usuário autenticado")},
        tags=["Autenticação"]
    )
    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined,
        })

