from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register(r'search-visitors', views.VisitorViewSet, basename='search-visitor')

urlpatterns = [
    # Built-in Django login/logout views
    path('login-success/', views.login_redirect, name='login_redirect'),
    path('login/', auth_views.LoginView.as_view(template_name='visitors/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Our custom views
    path('guard/dashboard/', views.dashboard, name='dashboard'),
    path('', views.index, name='index'),
    path('resident/register/', views.resident_register, name='resident_register'),
    path('check-in/', views.check_in_visitor, name='check_in'),
    path('check-out/<int:visitor_id>/', views.check_out_visitor, name='check_out'),

    # API urls
    path('api/dashboard/', views.api_dashboard, name='api_dashboard'),
    path('api/check-in/', views.api_check_in, name='api_check_in'),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/guest-pass/create/', views.api_create_guest_pass, name='api_create_guest_pass'),
    path('api/analytics/daily/', views.api_daily_analytics, name='api_daily_analytics'),
    path('api/', include(router.urls)),
    path('resident/dashboard/', views.resident_dashboard, name='resident_dashboard'),
    path('verify-otp/', views.verify_otp_checkin, name='verify_otp'),
]