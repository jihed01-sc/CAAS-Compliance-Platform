from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator


@method_decorator(csrf_protect, name='dispatch')
class PasswordResetRequestView(View):
    """Handle password reset requests"""

    def get(self, request):
        return render(request, 'registration/password_reset_request.html')

    def post(self, request):
        email = request.POST.get('email')

        if not email:
            messages.error(request, 'Please enter your email address')
            return render(request, 'registration/password_reset_request.html')

        try:
            # Find user by email
            user = User.objects.get(email=email)

            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Get current site domain
            current_site = get_current_site(request)

            # Create reset link
            reset_link = f"http://{current_site.domain}/auth/password-reset-confirm/{uid}/{token}/"

            # Prepare email content
            subject = 'Password Reset Request - CAAS Compliance System'

            email_context = {
                'user': user,
                'reset_link': reset_link,
                'site_name': 'CAAS Compliance System',
                'domain': current_site.domain,
            }

            # Render email template
            html_message = render_to_string('registration/password_reset_email.html', email_context)
            plain_message = render_to_string('registration/password_reset_email.txt', email_context)

            # Send email
            try:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@caas.com'),
                    recipient_list=[email],
                    html_message=html_message,
                    fail_silently=False,
                )

                messages.success(request,
                    f'Password reset instructions have been sent to {email}. '
                    'Please check your email and follow the instructions to reset your password.')

                return redirect('password_reset_done')

            except Exception as e:
                messages.error(request, 'Failed to send email. Please try again later.')
                return render(request, 'registration/password_reset_request.html')

        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            messages.success(request,
                f'If an account with email {email} exists, '
                'password reset instructions have been sent.')
            return redirect('password_reset_done')


class PasswordResetDoneView(View):
    """Show confirmation that reset email was sent"""

    def get(self, request):
        return render(request, 'registration/password_reset_done.html')


@method_decorator(csrf_protect, name='dispatch')
class PasswordResetConfirmView(View):
    """Handle password reset confirmation with token"""

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            context = {
                'validlink': True,
                'uidb64': uidb64,
                'token': token,
                'user': user
            }
            return render(request, 'registration/password_reset_confirm.html', context)
        else:
            messages.error(request, 'The password reset link is invalid or has expired.')
            return render(request, 'registration/password_reset_invalid.html')

    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            context = {
                'validlink': True,
                'uidb64': uidb64,
                'token': token,
                'user': user
            }

            # Validation
            if not new_password1 or not new_password2:
                messages.error(request, 'Please fill in both password fields')
                return render(request, 'registration/password_reset_confirm.html', context)

            if new_password1 != new_password2:
                messages.error(request, 'Passwords do not match')
                return render(request, 'registration/password_reset_confirm.html', context)

            if len(new_password1) < 6:
                messages.error(request, 'Password must be at least 6 characters long')
                return render(request, 'registration/password_reset_confirm.html', context)

            # Set new password
            user.set_password(new_password1)
            user.save()

            messages.success(request, 'Your password has been successfully reset! You can now log in with your new password.')
            return redirect('password_reset_complete')
        else:
            messages.error(request, 'The password reset link is invalid or has expired.')
            return render(request, 'registration/password_reset_invalid.html')


class PasswordResetCompleteView(View):
    """Show confirmation that password was successfully reset"""

    def get(self, request):
        return render(request, 'registration/password_reset_complete.html')
