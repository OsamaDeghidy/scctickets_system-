from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import pytz
from .models import CustomUser, Ticket
from .forms import UserRegistrationForm, CustomUserRegistrationForm, TicketCreationForm
from .utils import send_notification_email


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # إرسال كود التحقق للموظفين فقط
                if user.customuser.role == 'employee':
                    send_verification_code(user)
                    return redirect('verify_email')  # الانتقال إلى صفحة التحقق
                # توجيه المستخدم بناءً على دوره
                elif user.customuser.role == 'supervisor':
                    return redirect('supervisor_dashboard')
                elif user.customuser.role == 'service_provider':
                    return redirect('service_provider_dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

def register_view(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        custom_user_form = CustomUserRegistrationForm(request.POST)

        if user_form.is_valid() and custom_user_form.is_valid():
            # حفظ المستخدم الأساسي
            user = user_form.save(commit=False)
            role = request.POST.get('role')
            if role == 'employee':
                default_password = 'defaultpassword123'  # تعيين كلمة مرور افتراضية للموظفين
                user.set_password(default_password)
            else:
                user.set_password(user_form.cleaned_data['password'])
            user.save()

            # حفظ المستخدم المخصص وربطه بالمستخدم الأساسي
            custom_user = custom_user_form.save(commit=False)
            custom_user.user = user
            custom_user.role = role  # تعيين الدور من البيانات المخفية
            custom_user.save()

            # تسجيل دخول المستخدم مباشرة بعد التسجيل
            login(request, user)
            # توجيه المستخدم بناءً على دوره
            if custom_user.role == 'employee':
                return redirect('profile')
            elif custom_user.role == 'supervisor':
                return redirect('supervisor_dashboard')
            elif custom_user.role == 'service_provider':
                return redirect('service_provider_dashboard')
    else:
        user_form = UserRegistrationForm()
        custom_user_form = CustomUserRegistrationForm()

    return render(request, 'registration/register.html', {'user_form': user_form, 'custom_user_form': custom_user_form})

@login_required
def create_ticket_view(request):
    if request.method == 'POST':
        form = TicketCreationForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user.customuser  # ربط التذكرة بالمستخدم الحالي
            ticket.save()
            send_notification_email(
               'تم إنشاء تذكرة جديدة',
               f'تم إنشاء تذكرة جديدة بعنوان: {ticket.title}',
               [ticket.created_by.user.email]
           )
            
            
            return redirect('profile')  # الانتقال إلى صفحة البروفايل بعد الإنشاء
    else:
        form = TicketCreationForm()
    
    return render(request, 'ticket/create_ticket.html', {'form': form})

@login_required
def profile_view(request):
    user_tickets = request.user.customuser.created_tickets.all()  # جلب التذاكر التي أنشأها المستخدم الحالي
    return render(request, 'ticket/profile.html', {'tickets': user_tickets})

def logout_view(request):
    logout(request)
    return redirect('login')  # إعادة التوجيه إلى صفحة تسجيل الدخول بعد الخروج

@login_required
def close_ticket_view(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, created_by=request.user.customuser)

    # تحقق من أن التذكرة يمكن إغلاقها يدويًا فقط إذا كانت حالتها "Resolved"
    if ticket.status == Ticket.RESOLVED:
        ticket.status = Ticket.CLOSED
        ticket.time_resolved = timezone.now()  # تحديث وقت الحل عند الإغلاق اليدوي
        ticket.save()

    return redirect('profile')  # العودة إلى صفحة البروفايل بعد الإغلاق

@login_required
def reopen_ticket_view(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, created_by=request.user.customuser)

    # تحقق من أن التذكرة يمكن إعادة فتحها فقط إذا كانت حالتها "Resolved"
    if ticket.status == Ticket.RESOLVED:
        ticket.status = Ticket.OPEN
        ticket.save()

    return redirect('profile')  # العودة إلى صفحة البروفايل بعد إعادة الفتح

@login_required
def supervisor_dashboard(request):
    if request.user.customuser.role != 'supervisor':
        return redirect('dashboard')

    group_tickets = Ticket.objects.filter(group=request.user.customuser.group)
    return render(request, 'dashboard/supervisor_dashboard.html', {'tickets': group_tickets})

@login_required
def assign_ticket_view(request, ticket_id):
    if request.user.customuser.role != 'supervisor':
        return redirect('supervisor_dashboard')

    ticket = get_object_or_404(Ticket, id=ticket_id, group=request.user.customuser.group)
    if request.method == 'POST':
        assigned_to_id = request.POST.get('assigned_to')
        difficulty_level = request.POST.get('difficulty_level')
        assigned_to = get_object_or_404(CustomUser, id=assigned_to_id, role='service_provider')
        
        ticket.assigned_to = assigned_to
        ticket.difficulty_level = difficulty_level
        ticket.status = Ticket.IN_PROGRESS
        ticket.save()
        send_notification_email(
               'تم تعديل التذكره اذهب ل تفقدها ',
               f'تم تعديل التذكره اذهب ل تفقدها :{ticket.title}',
               [ticket.created_by.user.email]
           )
        return redirect('supervisor_dashboard')

    service_providers = CustomUser.objects.filter(role='service_provider', group=request.user.customuser.group)
    return render(request, 'dashboard/assign_ticket.html', {'ticket': ticket, 'service_providers': service_providers})

@login_required
def service_provider_dashboard(request):
    if request.user.customuser.role != 'service_provider':
        return redirect('service_provider_dashboard')

    assigned_tickets = Ticket.objects.filter(assigned_to=request.user.customuser)
    return render(request, 'dashboard/service_provider_dashboard.html', {'tickets': assigned_tickets})

@login_required
def update_ticket_status_view(request, ticket_id):
    if request.user.customuser.role != 'service_provider':
        return redirect('service_provider_dashboard')

    ticket = get_object_or_404(Ticket, id=ticket_id, assigned_to=request.user.customuser)
    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        if status in [Ticket.ON_HOLD, Ticket.RESOLVED, Ticket.IN_PROGRESS]:
            ticket.status = status
            ticket.notes = notes
            sa_tz = pytz.timezone('Asia/Riyadh')
            if status == Ticket.ON_HOLD:
                ticket.on_hold_periods.append({'start': timezone.now().astimezone(sa_tz).isoformat(), 'end': None})
            elif status == Ticket.RESOLVED:
                ticket.time_resolved = timezone.now().astimezone(sa_tz)
                if ticket.on_hold_periods and ticket.on_hold_periods[-1]['end'] is None:
                    ticket.on_hold_periods[-1]['end'] = timezone.now().astimezone(sa_tz).isoformat()
            elif status == Ticket.IN_PROGRESS:
                if ticket.on_hold_periods and ticket.on_hold_periods[-1]['end'] is None:
                    ticket.on_hold_periods[-1]['end'] = timezone.now().astimezone(sa_tz).isoformat()
            ticket.save()
            send_notification_email(
               'تم تعديل التذكره اذهب ل تفقدها ',
               f'تم تعديل التذكره اذهب ل تفقدها :{ticket.title}',
               [ticket.created_by.user.email]
           )
        return redirect('service_provider_dashboard')

    return render(request, 'dashboard/update_ticket_status.html', {'ticket': ticket})


from django.http import JsonResponse
from django.core import serializers

@login_required
def get_tickets_json(request):
    if request.user.customuser.role == 'supervisor':
        tickets = Ticket.objects.filter(group=request.user.customuser.group)
    elif request.user.customuser.role == 'service_provider':
        tickets = Ticket.objects.filter(assigned_to=request.user.customuser)
    else:
        tickets = Ticket.objects.filter(created_by=request.user.customuser)

    data = serializers.serialize('json', tickets)
    return JsonResponse(data, safe=False)




import random
from django.core.mail import send_mail
from django.conf import settings

def send_verification_code(user):
    code = str(random.randint(100000, 999999))
    user.customuser.verification_code = code
    user.customuser.save()
    try:
        send_mail(
            'Verification Code',
            f'Your verification code is: {code}',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        print(f"Verification code {code} sent to {user.email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import VerificationCodeForm

@login_required
def verify_email_view(request):
    if request.method == 'POST':
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            if code == request.user.customuser.verification_code:  # استخدم العلاقة العكسية
                request.user.customuser.is_verified = True
                request.user.customuser.save()
                return redirect('profile')  # الانتقال إلى الصفحة الرئيسية بعد التحقق
            else:
                form.add_error('code', 'Invalid verification code.')
    else:
        form = VerificationCodeForm()
    return render(request, 'registration/verify_email.html', {'form': form})

@login_required
def resend_verification_code_view(request):
    if request.user.customuser.role == 'employee':
        send_verification_code(request.user)
    return redirect('verify_email')


@login_required
def ticket_detail_view(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    return render(request, 'ticket/ticket_detail.html', {'ticket': ticket})