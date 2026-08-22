from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status


class AuthenticationTests(TestCase):
    """
    Testes de autenticação via sessão (SessionAuthentication) e controle de acesso.
    """

    def setUp(self):
        self.client = Client()
        self.username = 'aluno_teste'
        self.password = 'SenhaForte123!'
        self.email = 'aluno@exemplo.com'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email=self.email,
            first_name='Aluno',
            last_name='Dev'
        )
        self.api_me_url = reverse('core:current_user')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')

    def test_acesso_anonimo_bloqueado(self):
        """
        Usuário não autenticado tentando acessar /api/me/ deve receber 403 Forbidden.
        """
        response = self.client.get(self.api_me_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('detail', response.json())

    def test_login_django_com_sucesso(self):
        """
        Login com credenciais corretas deve autenticar e criar a sessão.
        """
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password,
        })
        # Redirecionamento após login bem-sucedido (302 Found)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_com_credenciais_invalidas(self):
        """
        Login com senha incorreta não deve autenticar.
        """
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': 'SenhaErrada123!',
        })
        # Permanece na página com erro (200 OK no formulário)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_acesso_autenticado_retorna_dados_do_usuario(self):
        """
        Usuário autenticado via sessão deve acessar /api/me/ e receber 200 OK com seus dados.
        """
        self.client.login(username=self.username, password=self.password)
        
        response = self.client.get(self.api_me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['id'], self.user.id)
        self.assertEqual(data['username'], self.username)
        self.assertEqual(data['email'], self.email)
        self.assertEqual(data['first_name'], 'Aluno')
        self.assertEqual(data['last_name'], 'Dev')

    def test_logout_revoga_acesso_a_api(self):
        """
        Após logout, a sessão é destruída e o acesso à API volta a ser bloqueado (403 Forbidden).
        """
        self.client.login(username=self.username, password=self.password)
        
        # Confirma acesso autenticado
        response_auth = self.client.get(self.api_me_url)
        self.assertEqual(response_auth.status_code, status.HTTP_200_OK)

        # Executa logout
        self.client.post(self.logout_url)

        # Tenta acessar novamente
        response_after_logout = self.client.get(self.api_me_url)
        self.assertEqual(response_after_logout.status_code, status.HTTP_403_FORBIDDEN)


class OpenApiDocumentationTests(TestCase):
    """
    Testes dos endpoints de documentação OpenAPI 3.0 / Swagger (drf-spectacular).
    """

    def setUp(self):
        self.client = Client()
        self.schema_url = reverse('schema')
        self.swagger_url = reverse('swagger-ui')
        self.redoc_url = reverse('redoc')

    def test_schema_endpoint_retorna_200_com_openapi_spec(self):
        """
        /api/schema/ deve responder 200 OK com a especificação OpenAPI válida.
        """
        import yaml
        response = self.client.get(self.schema_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = yaml.safe_load(response.content)
        self.assertIn('openapi', content)
        self.assertEqual(content['info']['title'], 'AgendaPro API')
        self.assertEqual(content['info']['version'], '1.0.0')

    def test_schema_endpoint_json_format(self):
        """
        /api/schema/?format=json deve responder 200 OK no formato JSON.
        """
        import json
        response = self.client.get(self.schema_url, {'format': 'json'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))
        self.assertIn('openapi', content)
        self.assertEqual(content['info']['title'], 'AgendaPro API')


    def test_swagger_ui_endpoint_retorna_200_html(self):
        """
        /api/docs/ deve responder 200 OK carregando a interface interativa do Swagger UI.
        """
        response = self.client.get(self.swagger_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'swagger-ui')

    def test_redoc_endpoint_retorna_200_html(self):
        """
        /api/redoc/ deve responder 200 OK carregando a interface do Redoc.
        """
        response = self.client.get(self.redoc_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'redoc')

