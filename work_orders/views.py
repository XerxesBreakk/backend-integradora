import random
from rest_framework.generics import ListCreateAPIView, UpdateAPIView
from rest_framework.views import APIView
from .serializers import WorkOrderCreateSerializer, WorkOrderListSerializer, WorkOrderApprovalSerializer,DoorEventSetCountSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework import filters
from .models import WorkOrder, DoorEvent
from django.core.mail import send_mail
from django.conf import settings
from accounts.models import UserAccount
from datetime import datetime

class WorkOrderListCreateView(ListCreateAPIView):
    permission_classes=[IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date']

    def get_queryset(self):
        user = self.request.user
        is_active_param = self.request.query_params.get('is_active', None)
        if is_active_param is not None:
            # Convierte el valor de 'is_active' a un booleano
            is_active_param = is_active_param.lower() == 'true'
            if user.is_staff:
                return WorkOrder.objects.all().filter(is_active=is_active_param)
            
        if user.is_staff:
            return WorkOrder.objects.all()
        return WorkOrder.objects.filter(applicant=user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return WorkOrderCreateSerializer
        elif self.request.method == 'GET':
            return WorkOrderListSerializer
        return WorkOrderCreateSerializer  # Fallback si no es GET ni POST 
    
    def perform_create(self, serializer):
        # Establecemos el solicitante automáticamente basándonos en el usuario autenticado
        serializer.save(applicant=self.request.user, is_active=False)


class WorkOrderApprovalView(UpdateAPIView):
    queryset = WorkOrder.objects.all()
    serializer_class = WorkOrderApprovalSerializer
    permission_classes = [IsAdminUser]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Validate and update the serializer data (even though there are no fields)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Check if the user is an administrator
        if not request.user.is_staff:
            return Response(
                {'detail': 'No tienes permisos para aprobar ordenes de trabajo.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Set is_active to True, set approver to the authenticated user, and generate a random 5-digit PIN
        instance.is_active = True
        instance.approver = request.user
        instance.generate_pin()
        instance.save()
        
        # Send emails to the applicant and administrators
        self.send_approval_emails(instance)

        return Response({'detail': 'WorkOrder approved successfully.'})
    
    
    def send_approval_emails(self, work_order):
        # Send email to the applicant
        subject_applicant = 'Orden de trabajo aprobada'
        message_applicant = f'Tu orden de trabajo (ID: {work_order.id}) ha sido aprobada para la fecha {work_order.date} y la compañia {work_order.company}.'
        send_mail(subject_applicant, message_applicant, settings.DEFAULT_FROM_EMAIL, [work_order.applicant.email])

        # Send email to administrators
        subject_admin = 'Nueva orden de trabajo aprobada'
        message_admin = f'Se aprobo una orden de trabajo (ID: {work_order.id}).\n\nDETALLES:\n{work_order}'
        admin_emails = UserAccount.objects.filter(is_staff=True).values_list('email', flat=True)
        send_mail(subject_admin, message_admin, settings.DEFAULT_FROM_EMAIL, admin_emails)


class ConsumePinView(APIView):
    permission_classes=[AllowAny] #TODO Restringir para que solo los equipos puedan enviar esto

    def post(self, request, *args, **kwargs):
        # Obtener el pin de los datos de la solicitud
        pin = request.data.get('pin', None)
        is_entry=request.data.get('is_entry',None)

        if pin is None:
            return Response({'detail': 'El parámetro "pin" es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        # Obtener la fecha y hora actual en la zona horaria actual
        current_datetime = datetime.now()
        print(current_datetime)
        # Filtrar las WorkOrders activas que contengan el pin y tengan un overlap con el tiempo actual
        overlapping_workorders = WorkOrder.get_active_workorders_overlap(current_datetime)
        print(overlapping_workorders)
        for wo in overlapping_workorders:
            if wo.check_pin(pin):
                wo.generate_pin()
                # Crear DoorEvent
                actual_count=wo.get_actual_count()
                do=DoorEvent.objects.create(work_order_pin_access=wo,is_entry=is_entry,actual_count=actual_count)
                return Response({'detail': 'Código 200: PIN válido.','event':do.date}, status=status.HTTP_200_OK)
        return Response({'detail': 'Código 404: PIN no válido o no hay WorkOrders activas que cumplan con los criterios.'}, status=status.HTTP_404_NOT_FOUND)
    
class UpdateCountDoorEventView(UpdateAPIView):
    queryset=DoorEvent.objects.all()
    permission_classes=[AllowAny]
    serializer_class=DoorEventSetCountSerializer

    def update(self, request, *args, **kwargs):
        instance=DoorEvent.objects.get(date=request.data['date'])
        wo=instance.work_order_pin_access

        if instance.actual_count+int(request.data['count']) <0:
            return Response({'detail': 'El parámetro "pin" es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate and update the serializer data (even though there are no fields)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        serializer.save(actual_count=instance.actual_count+int(request.data['count']))

        if instance.actual_count+int(request.data['count']) > wo.capacity:
            self.send_warning_emails(work_order=wo)
        return Response({'detail': 'Count updated for door event.'})

    def send_warning_emails(self, work_order):

        # Send email to administrators
        subject_admin = 'Mayor aforo al permitido'
        message_admin = f'Existe un exceso en el aforo permitido para la orden de trabajo (ID: {work_order.id}).\n\nDETALLES:\n{work_order}'
        admin_emails = UserAccount.objects.filter(is_staff=True).values_list('email', flat=True)
        send_mail(subject_admin, message_admin, settings.DEFAULT_FROM_EMAIL, admin_emails)

