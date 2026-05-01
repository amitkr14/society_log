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



# @login_required ensures nobody can see this page unless they are logged in
@login_required(login_url='/login/')
def dashboard(request):
    # Get today's date so we only see today's traffic
    today = timezone.now().date()
    
    # Active visitors are those who checked in today, but check_out_time is still empty (null)
    active_visitors = Visitor.objects.filter(check_in_time__date=today, check_out_time__isnull=True)
    
    # Past visitors are those who checked in today, and check_out_time is NOT empty
    past_visitors = Visitor.objects.filter(check_in_time__date=today, check_out_time__isnull=False)

    context = {
        'active_visitors': active_visitors,
        'past_visitors': past_visitors,
    }
    return render(request, 'visitors/dashboard.html', context)

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
    today = timezone.now().date()
    
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
        # 2. Look for a valid pass. If it doesn't exist, return a 404 error.
        # We also make sure is_used=False so a code can't be used twice!
        guest_pass = get_object_or_404(GuestPass, pass_code=pass_code, is_used=False)
        
        # 3. Create the Visitor record automatically using the data from the pass!
        visitor = Visitor.objects.create(
            name=guest_pass.visitor_name,
            phone_number=guest_pass.visitor_phone,
            person_to_meet=guest_pass.resident_name,
            purpose=guest_pass.purpose,
            checked_in_by=request.user.guard
        )
        
        # 4. Burn the pass so it can't be used again
        guest_pass.is_used = True
        guest_pass.save()
        
        return Response({
            'message': f'Success! {visitor.name} checked in via Guest Pass.',
            'visitor_id': visitor.id
        }, status=status.HTTP_201_CREATED)


    # 5. The fallback: If no pass_code was provided, just do a normal manual check-in
    serializer = VisitorSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(checked_in_by=request.user.guard)
        return Response({
            'message': 'Visitor successfully checked in manually!',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

