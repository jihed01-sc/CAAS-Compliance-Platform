from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def landing_view(request):
    """Landing page that shows the new CAAS/Fortress Plus homepage"""
    if request.user.is_authenticated:
        return redirect('compliance:dashboard_view')
    return render(request, 'landing_new.html')

def home_redirect(request):
    """Redirect to appropriate page based on authentication status"""
    if request.user.is_authenticated:
        return redirect('compliance:dashboard_view')
    else:
        return redirect('authentication:register')  # Show registration first for new users
