from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.core.validators import RegexValidator
name_validator = RegexValidator(regex=r'^[a-zA-ZàáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôốồổỗộơớờởỡợùúũụủưứừửữựỳỵỷỹýÀÁÃẠẢĂẮẰẲẴẶÂẤẦẨẪẬÈÉẸẺẼÊỀẾỂỄỆĐÌÍĨỈỊÒÓÕỌỎÔỐỒỔỖỘƠỚỜỞỠỢÙÚŨỤỦƯỨỪỬỮỰỲỴỶỸÝ\s]+$', message="Họ tên không được chứa số hoặc ký tự đặc biệt.")

from .models import CustomUser


from django.utils import timezone
import datetime

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(label='Email / Tên đăng nhập', widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg', 'placeholder': 'Nhập Email hoặc Mã SV/GV', 'autofocus': True,
    }))
    password = forms.CharField(label='Mật khẩu', widget=forms.PasswordInput(attrs={
        'class': 'form-control form-control-lg', 'placeholder': 'Mật khẩu',
    }))

    def clean(self):
        login_id = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        from django.db.models import Q
        user = CustomUser.objects.filter(Q(email=login_id) | Q(username=login_id)).first()

        if user:
            # Check lockout
            if user.locked_until and user.locked_until > timezone.now():
                raise forms.ValidationError(f"Tài khoản bị khóa do nhập sai nhiều lần. Vui lòng thử lại sau lúc {user.locked_until.strftime('%H:%M %d/%m/%Y')}")
            
            if user.locked_until and user.locked_until <= timezone.now():
                user.failed_login_attempts = 0
                user.locked_until = None
                user.save()

        try:
            cleaned_data = super().clean()
        except forms.ValidationError as e:
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts == 5:
                    user.locked_until = timezone.now() + datetime.timedelta(minutes=30)
                    try:
                        from django.core.mail import send_mail
                        from django.conf import settings
                        subject = 'Cảnh báo bảo mật: Tài khoản bị tạm khóa'
                        message = 'Bạn đã đăng nhập sai quá 5 lần. Hệ thống tạm thời đóng băng tài khoản của bạn trong 30 phút. Nếu bạn quên mật khẩu thì hãy liên hệ với thủ thư để được hỗ trợ.'
                        send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@lims.local'), [user.email])
                    except Exception:
                        pass
                elif user.failed_login_attempts > 5:
                    user.locked_until = timezone.now() + datetime.timedelta(minutes=30)
                user.save()
            raise e
            
        if user:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save()
            
        return cleaned_data


class CustomRegisterForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'Email',
    }))

    class Meta:
        model = CustomUser
        fields = ('email', 'phone_number')
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Số điện thoại (tùy chọn)'}),
        }


class UserCreateForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(validators=[name_validator], required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(validators=[name_validator], required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = CustomUser
        fields = ('email', 'role', 'phone_number', 'address', 'is_active')
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={
        'class': 'form-control form-control-lg', 'placeholder': 'Nhập email của bạn', 'autofocus': True,
    }))

class ResetPasswordForm(forms.Form):
    password = forms.CharField(label='Mật khẩu mới', widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Nhập mật khẩu mới',
    }), strip=True)
    confirm_password = forms.CharField(label='Xác nhận mật khẩu', widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Nhập lại mật khẩu mới',
    }), strip=True)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Mật khẩu xác nhận không khớp!")
        return cleaned_data


class UserExcelImportForm(forms.Form):
    excel_file = forms.FileField(
        label='Chọn file Excel (.xlsx)',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx'})
    )


class ProfileUpdateForm(forms.ModelForm):
    phone_number = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number', 'address')
        labels = {'username': 'Mã SV/GV'}
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class UserManageForm(forms.ModelForm):
    phone_number = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'role', 'is_active', 'phone_number', 'address')
        labels = {'username': 'Mã SV/GV'}
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].strip = True
        self.fields['new_password1'].strip = True
        self.fields['new_password2'].strip = True

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        if new_password1 and self.user.check_password(new_password1):
            raise forms.ValidationError("Mật khẩu mới không được trùng với mật khẩu cũ.")
        return cleaned_data
