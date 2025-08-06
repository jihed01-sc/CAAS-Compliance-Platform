from django.shortcuts import render, redirect
from django.views import View
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str, DjangoUnicodeDecodeError
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.template.loader import render_to_string
from .utils import account_activation_token
from django.urls import reverse
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

# Create your views here.


class EmailValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data['email']
        # Simple email validation (you can use a library if needed)
        if '@' not in email or '.' not in email:
            return JsonResponse({'email_error': 'Email is invalid'}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({'email_error': 'Sorry, email is already in use. Choose another one.'}, status=409)
        return JsonResponse({'email_valid': True})


class UsernameValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data['username']
        if not str(username).isalnum():
            return JsonResponse({'username_error': 'Username should only contain alphanumeric characters'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'username_error': 'Sorry, username is already in use. Choose another one.'}, status=409)
        return JsonResponse({'username_valid': True})


@method_decorator(csrf_protect, name='dispatch')
class RegistrationView(View):
    def get(self, request):
        return render(request, 'registration/register.html')

    def post(self, request):
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        context = {
            'fieldValues': request.POST
        }

        # Validation
        if not username:
            messages.error(request, 'Username is required')
            return render(request, 'registration/register.html', context)

        if not email:
            messages.error(request, 'Email is required')
            return render(request, 'registration/register.html', context)

        if not first_name:
            messages.error(request, 'First name is required')
            return render(request, 'registration/register.html', context)

        if not last_name:
            messages.error(request, 'Last name is required')
            return render(request, 'registration/register.html', context)

        if len(password1) < 6:
            messages.error(request, 'Password must be at least 6 characters')
            return render(request, 'registration/register.html', context)

        if password1 != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'registration/register.html', context)

        if not str(username).isalnum():
            messages.error(request, 'Username should only contain alphanumeric characters')
            return render(request, 'registration/register.html', context)

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username is already taken')
            return render(request, 'registration/register.html', context)

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email is already registered')
            return render(request, 'registration/register.html', context)

        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password1
            )
            user.is_active = True  # You can set to False if you want email verification
            user.save()

            messages.success(request, 'Account created successfully! Please sign in with your credentials.')
            return redirect('custom_login_view')

        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return render(request, 'registration/register.html', context)


@method_decorator(csrf_protect, name='dispatch')
class LoginView(View):
    def get(self, request):
        return render(request, 'registration/login.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')

        if username and password:
            user = authenticate(request, username=username, password=password)

            if user:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.first_name}!')
                    return redirect('compliance:dashboard_view')
                else:
                    messages.error(request, 'Account is disabled. Please contact support.')
            else:
                messages.error(request, 'Invalid username or password')
        else:
            messages.error(request, 'Please fill in all fields')

        return render(request, 'registration/login.html')


@login_required
def logout_view(request):
    auth.logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('custom_login_view')
