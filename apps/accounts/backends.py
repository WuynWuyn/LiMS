from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

UserModel = get_user_model()

class EmailAuthBackend(ModelBackend):
    """
    Xác thực người dùng dựa trên cột 'email' hoặc 'username'.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = UserModel.objects.get(Q(email=username) | Q(username=username))
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            user = UserModel.objects.filter(Q(email=username) | Q(username=username)).first()
            
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
