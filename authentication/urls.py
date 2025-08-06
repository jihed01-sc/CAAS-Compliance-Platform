from .views import RegistrationView, UsernameValidationView, EmailValidationView, LoginView, logout_view
from .password_reset_views import (
    PasswordResetRequestView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import HttpResponse

# Test view for forgot password functionality
def test_forgot_password(request):
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Forgot Password Link</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .test-link { 
                display: inline-block; 
                color: #007bff; 
                text-decoration: underline; 
                cursor: pointer; 
                padding: 10px; 
                margin: 10px;
                border: 1px solid #ccc;
            }
            .test-link:hover { background-color: #f8f9fa; }
        </style>
    </head>
    <body>
        <h1>Test - Forgot Password Link</h1>
        <p>Click the link below to test if password reset is working:</p>
        
        <a href="/auth/password-reset/" class="test-link">
            🔗 Forgot password? (Direct Link Test)
        </a>
        
        <br><br>
        
        <p><strong>Instructions:</strong></p>
        <ol>
            <li>Click the link above</li>
            <li>If it works, you should see a password reset form</li>
            <li>If it doesn't work, check the browser console (F12) for errors</li>
        </ol>
        
        <p><a href="/auth/login/">← Back to Login</a></p>
    </body>
    </html>
    """
    return HttpResponse(html_content)


urlpatterns = [
    path('register/', RegistrationView.as_view(), name="register"),
    path('login/', LoginView.as_view(), name="custom_login_view"),
    path('logout/', logout_view, name="custom_logout_view"),
    path('validate-username/', csrf_exempt(UsernameValidationView.as_view()),
         name="validate-username"),
    path('validate-email/', csrf_exempt(EmailValidationView.as_view()),
         name='validate_email'),

    # Password Reset URLs
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/done/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Test URL for forgot password functionality
    path('test-forgot-password/', test_forgot_password, name='test_forgot_password'),
]