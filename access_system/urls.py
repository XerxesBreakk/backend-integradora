
from django.urls import path,include

urlpatterns = [
    path('auth/',include('djoser.urls')),
    path('auth/',include('djoser.urls.jwt')),
    path('work-order/',include('work_orders.urls')),
    #path("docs/",include_docs_urls(title="sistema acceso")),
]

#urlpatterns += [re_path(r'^.*',TemplateView.as_view(template_name='index.html'))]