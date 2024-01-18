from rest_framework import serializers
from .models import WorkOrder,DoorEvent
from django.utils import timezone
from datetime import datetime

class WorkOrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = ['date', 'start_time', 'duration', 'company', 'activity', 'capacity']

    def validate_date(self, value):
        # Validación de la fecha: la combinación de date y start_time no puede ser menor a la fecha actual
        start_time_str = self.initial_data.get('start_time')+":00"
        start_time = datetime.strptime(start_time_str, '%H:%M:%S').time() if start_time_str else None
        combined_datetime = datetime.combine(value, start_time)

        # Convertir combined_datetime a timestamp (datetime.timestamp) para comparar con la fecha y hora actuales
        combined_timestamp = combined_datetime.timestamp()
        now_timestamp = datetime.now().timestamp()

        if combined_timestamp < now_timestamp:
            raise serializers.ValidationError('La combinación de fecha y hora no puede ser menor a la fecha actual.')
        return value

    def validate_capacity(self, value):
        # Validación de la capacidad: no puede ser menor a 1
        if value < 1:
            raise serializers.ValidationError('La capacidad debe ser al menos 1.')
        return value
    
class WorkOrderListSerializer(serializers.ModelSerializer):
    applicant_username = serializers.ReadOnlyField(source='applicant.username')
    datetime = serializers.SerializerMethodField()
    class Meta:
        model=WorkOrder
        fields=['id','datetime','duration', 'activity', 'company', 'capacity','pin','is_active','applicant_username']

    def get_datetime(self, obj):
        # Método para combinar date y start_time en un solo campo datetime
        return datetime.combine(obj.date, obj.start_time) if obj.date and obj.start_time else None
    

class WorkOrderApprovalSerializer(serializers.Serializer):
    pass  # No need for additional fields for this case

class DoorEventSetCountSerializer(serializers.ModelSerializer):
    class Meta:
        model=DoorEvent
        fields=['date','count']
        read_only_fields=['date']