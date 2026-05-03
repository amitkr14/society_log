from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Visitor
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import VisitorSerializer, GuestPassSerializer
from rest_framework import status
from .models import GuestPass
from django.db.models import Count
from django.db.models.functions import TruncHour
from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .permissions import IsAdminOrGuardCreateOnly
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login
from .models import Resident
from django.shortcuts import redirect

def login_redirect(request):
    """
    This view acts as a traffic cop to send residents to the resident dashboard
    and guards/admins to the guard dashboard.
    """
    if hasattr(request.user, 'resident'):
        return redirect('resident_dashboard')
    elif hasattr(request.user, 'guard') or request.user.is_staff or request.user.is_superuser:
        return redirect('dashboard')
    else:
        # Fallback if someone has neither profile
        return redirect('index')

def index(request):
    # If they are already logged in, don't show the landing page, send them to their dashboard!
    if request.user.is_authenticated:
        if hasattr(request.user, 'resident'):
            return redirect('resident_dashboard')
        elif hasattr(request.user, 'guard') or request.user.is_superuser:
            return redirect('dashboard')
            
    return render(request, 'visitors/index.html')

def resident_register(request):
    # If they submit the registration form
    if request.method == 'POST':
        u_name = request.POST.get('username')
        p_word = request.POST.get('password')
        flat = request.POST.get('flat_number')
        phone = request.POST.get('phone_number')

        # 1. Safety Check: Does this username already exist?
        if User.objects.filter(username=u_name).exists():
            messages.error(request, "Error: That username is already taken.")
            return redirect('resident_register')

        # 2. Create the base Django User (create_user automatically encrypts the password!)
        new_user = User.objects.create_user(username=u_name, password=p_word)
        
        # 3. Create the Society Resident profile and link it to the new user
        Resident.objects.create(
            user=new_user, 
            flat_number=flat, 
            phone_number=phone
        )

        messages.success(request, "Registration successful! You can now log in.")
        return redirect('login')

    # If it's a normal GET request, just show the empty form
    return render(request, 'visitors/resident_register.html')



# @login_required ensures nobody can see this page unless they are logged in
@login_required(login_url='/login/')
def dashboard(request):
    # Get today's date so we only see today's traffic
    today = timezone.localdate()
    
    # Active visitors are those who checked in today, but check_out_time is still empty (null)
    active_visitors = Visitor.objects.filter(check_in_time__date=today, check_out_time__isnull=True)
    
    # Past visitors are those who checked in today, and check_out_time is NOT empty
    past_visitors = Visitor.objects.filter(check_in_time__date=today, check_out_time__isnull=False)

    context = {
        'active_visitors': active_visitors,
        'past_visitors': past_visitors,
    }
    return render(request, 'visitors/dashboard.html', context)

@login_required
def resident_dashboard(request):
    # SECURITY: Ensure the logged-in user is actually a resident
    if not hasattr(request.user, 'resident'):
        messages.error(request, "Access Denied: Only residents can view this page.")
        return redirect('login') 

    if request.method == 'POST':
        v_name = request.POST.get('visitor_name')
        v_phone = request.POST.get('visitor_phone')
        v_purpose = request.POST.get('purpose')
        v_other = request.POST.get('other_purpose', '')

        new_pass = GuestPass.objects.create(
            resident=request.user.resident,
            visitor_name=v_name,
            visitor_phone=v_phone,
            purpose=v_purpose,
            other_purpose=v_other
        )
        
        messages.success(request, f"Pass generated successfully! The OTP is: {new_pass.pass_code}")
        return redirect('resident_dashboard')

    my_passes = GuestPass.objects.filter(resident=request.user.resident).order_by('-created_at')

    context = {
        'passes': my_passes,
    }
    return render(request, 'visitors/resident_dashboard.html', context)

@login_required(login_url='/login/')
def check_in_visitor(request):
    if request.method == 'POST':
        # Grab the data from the HTML form (we will build this in Step 4)
        name = request.POST.get('name')
        phone = request.POST.get('phone_number')
        person_to_meet = request.POST.get('person_to_meet')
        purpose = request.POST.get('purpose')
        other_purpose = request.POST.get('other_purpose')

        # Save it to the database, linking the logged-in guard!
        Visitor.objects.create(
            name=name,
            phone_number=phone,
            person_to_meet=person_to_meet,
            purpose=purpose,
            other_purpose=other_purpose,
            checked_in_by=request.user.guard
        )
        return redirect('dashboard')
    
    return render(request, 'visitors/check_in.html')

@login_required(login_url='/login/')
def check_out_visitor(request, visitor_id):
    # Find the specific visitor in the database
    visitor = get_object_or_404(Visitor, id=visitor_id)
    
    # Update their checkout time to right now, and record the guard
    visitor.check_out_time = timezone.now()
    visitor.checked_out_by = request.user.guard
    visitor.save()
    
    return redirect('dashboard')

# The @api_view decorator tells Django: "This is an API endpoint, expect to return JSON"
@api_view(['GET'])
def api_dashboard(request):
    today = timezone.localdate()
    
    # 1. Get the data from PostgreSQL (Exact same logic as your old view!)
    active_visitors = Visitor.objects.filter(check_in_time__date=today, check_out_time__isnull=True)
    past_visitors = Visitor.objects.filter(check_in_time__date=today, check_out_time__isnull=False)

    # 2. Translate the QuerySets into JSON using your new Serializer
    # We pass many=True because we are translating a list of objects, not just one.
    active_serializer = VisitorSerializer(active_visitors, many=True)
    past_serializer = VisitorSerializer(past_visitors, many=True)

    # 3. Return the pure data!
    return Response({
        'status': 'success',
        'date': today,
        'active_visitors': active_serializer.data,
        'past_visitors': past_serializer.data
    })

@api_view(['POST'])
def api_check_in(request):
    # 1. Did the guard provide a pre-approved pass code?
    pass_code = request.data.get('pass_code')
    
    if pass_code:
        # Find the pass (don't check is_used here, we'll use our robust property)
        guest_pass = get_object_or_404(GuestPass, pass_code=pass_code)
        
        # SECURITY FIX: Use the property we built to check BOTH is_used and expires_at
        if not guest_pass.is_valid:
            return Response(
                {'error': 'This pass is either used or expired.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # MODEL FIX: Properly traverse the Resident ForeignKey to get the info
        resident_info = f"{guest_pass.resident.user.username} (Flat {guest_pass.resident.flat_number})"

        # Create the Visitor record automatically using the data from the pass!
        visitor = Visitor.objects.create(
            name=guest_pass.visitor_name,
            phone_number=guest_pass.visitor_phone,
            person_to_meet=resident_info,
            purpose=guest_pass.purpose,
            checked_in_by=request.user.guard
        )
        
        # Burn the pass so it can't be used again
        guest_pass.is_used = True
        guest_pass.save()
        
        return Response({
            'message': f'Success! {visitor.name} checked in via Guest Pass.',
            'visitor_id': visitor.id
        }, status=status.HTTP_201_CREATED)

    # The fallback: If no pass_code was provided, just do a normal manual check-in
    serializer = VisitorSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(checked_in_by=request.user.guard)
        return Response({
            'message': 'Visitor successfully checked in manually!',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def api_daily_analytics(request):
    today = timezone.now().date()
    
    # Base query: Get all visitors for today
    daily_visitors = Visitor.objects.filter(check_in_time__date=today)
    
    # 1. Total Count (Fastest way to count rows)
    total_visitors = daily_visitors.count()
    
    # 2. Group by Purpose (e.g., Deliveries vs. Meetings)
    # This translates to: SELECT purpose, COUNT(id) FROM visitors GROUP BY purpose;
    purpose_counts = daily_visitors.values('purpose').annotate(
        count=Count('id')
    )
    
    
    # 3. Busiest Hours of the Day
    # This groups the exact check_in timestamps into generic 1-hour blocks, 
    # counts them, and sorts them from busiest to quietest.
    busiest_hours = daily_visitors.annotate(
        hour=TruncHour('check_in_time')
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('-count')

    # Send the calculated data back as JSON
    return Response({
        'date': today,
        'total_visitors': total_visitors,
        'breakdown_by_purpose': purpose_counts,
        'busiest_hours': busiest_hours
    }, status=status.HTTP_200_OK)

class VisitorViewSet(viewsets.ModelViewSet):
    queryset = Visitor.objects.all()
    serializer_class = VisitorSerializer


    permission_classes = [IsAdminOrGuardCreateOnly]
    
    # Enable the backends
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # 1. Filter by exact matches 
    filterset_fields = ['purpose', 'person_to_meet'] 
    
    # 2. Search by partial text (e.g., typing "Smi" finds "Smith")
    search_fields = ['name', 'phone_number'] 
    
    # 3. Order the results 
    ordering_fields = ['check_in_time']
    ordering = ['-check_in_time'] # The '-' means descending order (newest first)

@api_view(['POST'])
def api_create_guest_pass(request):
    # This represents the Resident creating a pass from their mobile app
    serializer = GuestPassSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save()
        
        # Return a great UX response including the newly generated code
        return Response({
            'status': 'success',
            'message': 'Guest pass generated!',
            'pass_code': serializer.data['pass_code'],
            'details': serializer.data
        }, status=status.HTTP_201_CREATED)
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@login_required(login_url='/login/')
def verify_otp_checkin(request):
    if request.method == 'POST':
        # Grab the OTP and force it to uppercase just in case the guard typed lowercase
        entered_code = request.POST.get('pass_code', '').upper()

        try:
            # 1. Find the pass
            guest_pass = GuestPass.objects.get(pass_code=entered_code)
            
            # 2. Check validity using our custom property (checks is_used and expires_at)
            if not guest_pass.is_valid:
                messages.error(request, f"Error: The OTP '{entered_code}' has expired or was already used.")
            else:
                # 3. Format the resident's info nicely for the guard
                resident_info = f"{guest_pass.resident.user.username} (Flat {guest_pass.resident.flat_number})"
                
                # 4. Create the actual entry log automatically!
                Visitor.objects.create(
                    name=guest_pass.visitor_name,
                    phone_number=guest_pass.visitor_phone,
                    person_to_meet=resident_info,
                    purpose=guest_pass.purpose,
                    other_purpose=guest_pass.other_purpose,
                    checked_in_by=request.user.guard
                )
                
                # 5. Burn the OTP
                guest_pass.is_used = True
                guest_pass.save()
                
                messages.success(request, f"Success! {guest_pass.visitor_name} has been checked in using OTP.")

        except GuestPass.DoesNotExist:
            # 6. If the code literally doesn't exist in the database
            messages.error(request, f"Error: '{entered_code}' is not a valid OTP.")

    # Redirect right back to the dashboard whether it succeeded or failed
    return redirect('dashboard')