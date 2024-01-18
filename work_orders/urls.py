from django.urls import path
from .views import WorkOrderListCreateView,WorkOrderApprovalView,ConsumePinView,UpdateCountDoorEventView

urlpatterns = [
    path('', WorkOrderListCreateView.as_view(), name='crear_listar_ot'),
    path('approve/<int:pk>/', WorkOrderApprovalView.as_view(), name='aprobar_orden'),
    path('pin-consume/',ConsumePinView.as_view(),name='pin_update'),
    path('update-doorevent/',UpdateCountDoorEventView.as_view())
    #path('prueba/',VideoCreate.as_view())
]