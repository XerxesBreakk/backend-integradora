from djoser.serializers import UserSerializer
from rest_framework.serializers import ModelSerializer
from .models import UserAccount
from djoser.conf import settings
from djoser.compat import get_user_email, get_user_email_field_name

class UserCustomListSerializer(UserSerializer):
    class Meta:
        model = UserAccount
        fields = tuple(UserAccount.REQUIRED_FIELDS) + (
            settings.USER_ID_FIELD,
            settings.LOGIN_FIELD,
            'is_active','is_staff','last_name'
        )
        read_only_fields = ['is_active','is_staff','last_name']
    
class WhoIAmSerializer(ModelSerializer):
    class Meta:
        model = UserAccount
        fields= ['username','email','last_name','first_name','is_staff']
        read_only_fields= ['is_staff','username','email']