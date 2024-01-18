from datetime import datetime, time
from django.utils import timezone
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import UserAccount
import random



class WorkOrder(models.Model):
    date = models.DateField(null=False,blank=False)
    start_time=models.TimeField(null=False,blank=False)
    duration = models.DurationField(null=False,blank=False)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    activity= models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    company = models.CharField(max_length=255)
    applicant = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='applicant')
    approver = models.ForeignKey(UserAccount, on_delete=models.CASCADE,null=True, blank=True, related_name='approver')
    pin = models.CharField(max_length=10,blank=True)
    
    def __str__(self):
        return f'Orden de Trabajo {self.id} - {self.applicant.username}'

    def clean_approver(self):
        # Validación personalizada para aprobador
        if not self.approver.is_staff:
            raise ValidationError('El usuario debe ser administrador.')

    def get_start_datetime(self):
        if self.start_time is not None and self.duration is not None:
            start_datetime = timezone.make_aware(datetime.combine(self.date, self.start_time), timezone=timezone.get_current_timezone())
            return start_datetime

    def calculate_end_datetime(self):
        # Calcular la fecha y hora de finalización sumando la duración al objeto de inicio
        return self.get_start_datetime() + self.duration

    def get_end_time(self):
        # Obtener la hora de finalización como un objeto de tiempo
        return timezone.localtime(self.calculate_end_datetime()).time()

    def get_end_datetime(self):
        # Obtener la fecha y hora de finalización como un objeto datetime
        return self.calculate_end_datetime()

    def is_overlap(self, check_date):
        start_time=datetime.combine(self.date,self.start_time)
        end_time = datetime.combine(self.date,self.start_time) + self.duration
        # Verificar si la fecha proporcionada se superpone con la orden de trabajo
        return start_time <= check_date <= end_time

    def check_pin(self, pin):
        # Verificar el PIN solo si la orden de trabajo está activa
        return self.is_active and self.pin == pin
    
    def get_actual_count(self):
        related_door_event=self.door_events.all().order_by('-date')
        if len(related_door_event)<1:
            return 0
        return related_door_event.last().actual_count
    
    def generate_pin(self):
        # Obtener la fecha y hora actual en la zona horaria actual
        current_datetime = timezone.now()

        # Obtener la fecha y hora de finalización como objeto "offset-aware"
        end_datetime = self.calculate_end_datetime()
        end_time = datetime.combine(self.date,self.start_time) + self.duration
        
        # Verificar que la fecha y hora actual sea menor que calculate_end_datetime()
        if current_datetime < end_time:
            # Generar un número aleatorio entre 11111 y 99999
            pin = random.randint(11111, 99999)

            # Verificar que el pin no esté asignado a ninguna otra WorkOrder
            while WorkOrder.objects.filter(pin=pin).exists():
                pin = random.randint(11111, 99999)

            # Asignar el pin generado
            self.pin = str(pin)
            self.save()
        else:
            raise ValidationError('No se puede generar el PIN después de la fecha de finalización.')

    @staticmethod
    def get_active_workorders_overlap(check_date):
        # Obtener las órdenes de trabajo activas que se superponen con la fecha proporcionada
        active_workorders = WorkOrder.objects.filter(is_active=True)
        overlapping_workorders = [workorder for workorder in active_workorders if workorder.is_overlap(check_date)]
        return overlapping_workorders
    
    
    @staticmethod
    def is_active_workorders_overlap(check_date):
        return WorkOrder.objects.filter(is_active=True, date__lte=check_date, get_end_datetime__gte=check_date).exists()
    

    """ @staticmethod
    def check_pin_workorders(pin):
        active_workorders = WorkOrder.objects.filter(is_active=True)
        for wo in active_workorders:
            if wo.check_pin(pin):
                return True
        return False """

        
class DoorEvent(models.Model):
    date = models.DateTimeField(primary_key=True, unique=True, auto_now_add=True)
    is_entry = models.BooleanField(default=True)
    work_order_pin_access = models.ForeignKey('WorkOrder', on_delete=models.CASCADE, related_name='door_events')
    count = models.IntegerField(default=0, validators=[MinValueValidator(-2147483648), MaxValueValidator(2147483647)])
    actual_count=models.IntegerField(default=0,validators=[MinValueValidator(0)])

    def __str__(self):
        action = 'Entrada' if self.is_entry else 'Salida'
        return f'{action} - {self.date}'
    
    def get_prev_actual_count(self):
        wo=self.work_order_pin_access

