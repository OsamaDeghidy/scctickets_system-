from django.db import models
import django.contrib.auth.models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import pytz

class Group(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class CustomUser(models.Model):
    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('supervisor', 'Supervisor'),
        ('service_provider', 'Service Provider')
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    user  = models.OneToOneField(User, on_delete=models.CASCADE)  # الرقم الوظيفي أو معرف الخدمة
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return self.user.username

class Ticket(models.Model):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    ON_HOLD = 'on_hold'
    RESOLVED = 'resolved'
    CLOSED = 'closed'

    STATUS_CHOICES = [
        (OPEN, 'Open'),
        (IN_PROGRESS, 'In Progress'),
        (ON_HOLD, 'On Hold'),
        (RESOLVED, 'Resolved'),
        (CLOSED, 'Closed'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('normal', 'عادي'),
        ('medium', 'متوسط'),
        ('high', 'مرتفع')
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=OPEN)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_tickets')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='assigned_tickets')
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, null=True, blank=True)
    time_started = models.DateTimeField(null=True, blank=True)
    time_resolved = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New fields to track on hold periods
    time_in_progress = models.DateTimeField(null=True, blank=True)
    on_hold_periods = models.JSONField(default=list, blank=True)  # List to track on-hold periods [(start_time, end_time), ...]
    notes = models.TextField(blank=True, null=True)  # Field to store notes

    def save(self, *args, **kwargs):
        # تحديد حالة التذكرة الجديدة
        new_status = self.status
        
        # إذا كانت التذكرة موجودة بالفعل، احصل على الحالة القديمة
        if self.pk:
            old_ticket = Ticket.objects.get(pk=self.pk)
            old_status = old_ticket.status
        else:
            old_status = None

        # إذا تغيرت الحالة، تحديث المنطق بناءً على الحالة الجديدة
        if old_status != new_status:
            if new_status == self.IN_PROGRESS:
                if old_status != self.IN_PROGRESS:
                    self.time_in_progress = timezone.now()  # ابدأ تتبع الوقت لـ In Progress
            elif new_status == self.ON_HOLD:
                if old_status == self.IN_PROGRESS:
                    # بدء فترة جديدة من On Hold
                    if not self.on_hold_periods or self.on_hold_periods[-1].get('end') is not None:
                        self.on_hold_periods.append({'start': timezone.now().isoformat(), 'end': None})
            elif new_status == self.RESOLVED:
                if old_status == self.ON_HOLD:
                    # إنهاء فترة On Hold الحالية إذا كانت التذكرة في حالة On Hold
                    if self.on_hold_periods and self.on_hold_periods[-1]['end'] is None:
                        self.on_hold_periods[-1]['end'] = timezone.now().isoformat()
                self.time_resolved = timezone.now()  # تحديد الوقت كحل

        # ضبط التوقيت إلى التوقيت السعودي عند الحفظ
        sa_tz = pytz.timezone('Asia/Riyadh')
        self.time_resolved = timezone.now().astimezone(sa_tz)

        self.status = new_status
        super(Ticket, self).save(*args, **kwargs)  # حفظ التغييرات بعد تنفيذ المنطق الخاص

    def get_total_in_progress_time(self):
        """
        Calculate the total time the ticket was in 'In Progress', excluding 'On Hold' periods.
        """
        if self.time_in_progress:
            end_time = self.time_resolved if self.time_resolved else timezone.now()
            total_time = end_time - self.time_in_progress

            # Subtract all "On Hold" periods from total time
            for period in self.on_hold_periods:
                start = period.get('start')
                end = period.get('end', timezone.now().isoformat())  # If still on hold, assume end is now
                if start and end:
                    start_time = timezone.datetime.fromisoformat(start)
                    end_time = timezone.datetime.fromisoformat(end)
                    total_time -= (end_time - start_time)
                    
            return total_time
        return timedelta()

    def get_total_work_time(self):
        if self.time_started and self.time_resolved:
            return self.time_resolved - self.time_started
        return None

    def auto_close(self):
        if self.status == self.RESOLVED and (timezone.now() - self.time_resolved) > timedelta(hours=24):
            self.status = self.CLOSED
            self.save()

    def total_time_spent(self):
        if self.time_resolved and self.time_started:
            return self.time_resolved - self.time_started
        return timedelta()  # القيمة الافتراضية هي 0 في حالة عدم الحل

    def can_edit(self, user):
        if user.customuser.role in ['supervisor', 'service_provider']:
            return True
        return False

    def __str__(self):
        return f"{self.title} ({self.status})"