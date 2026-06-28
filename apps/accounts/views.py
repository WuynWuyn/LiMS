from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .forms import CustomLoginForm, CustomRegisterForm, ProfileUpdateForm, UserManageForm, UserCreateForm, UserExcelImportForm, CustomPasswordChangeForm
from .models import CustomUser
import openpyxl


class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        user = form.get_user()
        # Tạm thời tắt xác thực OTP 2FA cho admin và thủ thư để tiện test & demo
        if False and (user.role in ['admin', 'librarian'] or user.is_superuser):
            import random
            from django.utils import timezone
            import datetime
            otp = f"{random.randint(100000, 999999)}"
            self.request.session['pre_2fa_user_id'] = user.pk
            self.request.session['pre_2fa_otp'] = otp
            self.request.session['pre_2fa_expire'] = (timezone.now() + datetime.timedelta(seconds=30)).timestamp()
            
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                send_mail(
                    'Mã xác thực OTP (2FA) - VietNhatLiMS',
                    f'Xin chào {user.username},\n\nMã xác thực OTP của bạn là: {otp}\n\nMã này sẽ hết hạn trong 30 giây.\nNếu bạn không thực hiện thao tác này, vui lòng đổi mật khẩu ngay lập tức.',
                    getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@lims.local'),
                    [user.email]
                )
            except Exception:
                pass
            
            return redirect('accounts:otp_verify')
            
        return super().form_valid(form)

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        email = self.request.POST.get('username')
        if email:
            from .models import CustomUser
            from django.utils import timezone
            user = CustomUser.objects.filter(email=email).first()
            if user and user.locked_until and user.locked_until > timezone.now():
                context['locked_until'] = user.locked_until.timestamp()
        return self.render_to_response(context)


def register_view(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'reader'
            
            import random
            import string
            base_username = user.email.split('@')[0]
            suffix = ''.join(random.choices(string.digits, k=4))
            user.username = f"{base_username}_{suffix}"
            
            password = CustomUser.objects.make_random_password()
            user.set_password(password)
            user.save()
            
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                subject = 'Tài khoản LIMS của bạn đã được đăng ký'
                message = f'Xin chào {user.username},\n\nTài khoản của bạn đã được đăng ký thành công.\nEmail đăng nhập: {user.email}\nMật khẩu: {password}\n\nVui lòng đăng nhập và đổi mật khẩu trong phần Hồ sơ.'
                send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@lims.local'), [user.email])
            except Exception:
                pass
                
            messages.success(request, 'Đăng ký thành công! Mật khẩu đã được gửi qua email của bạn.')
            return redirect('accounts:login')
    else:
        form = CustomRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Bạn đã đăng xuất thành công.')
    return redirect('accounts:login')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật hồ sơ thành công!')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        messages.success(self.request, 'Đổi mật khẩu thành công!')
        return super().form_valid(form)


@login_required
def user_list_view(request):
    if request.user.role != 'admin':
        messages.error(request, 'Bạn không có quyền truy cập.')
        return redirect('home')
    from django.db.models import Count
    q = request.GET.get('q', '').strip()
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')
    
    users = CustomUser.objects.exclude(Q(role='admin') | Q(is_superuser=True))
    if q:
        users = users.filter(Q(username__icontains=q) | Q(email__icontains=q))
    if role:
        users = users.filter(role=role)
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
        
    users = users.annotate(borrowed_books_count=Count('borrow_records', filter=Q(borrow_records__status='borrowed')))
    paginator = Paginator(users.order_by('-created_at'), 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/user_list.html', {'page_obj': page, 'q': q, 'role': role, 'status': status})


@login_required
def user_create_view(request):
    if request.user.role != 'admin':
        messages.error(request, 'Bạn không có quyền truy cập.')
        return redirect('home')
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            import random
            import string
            base_username = user.email.split('@')[0]
            suffix = ''.join(random.choices(string.digits, k=4))
            user.username = f"{base_username}_{suffix}"
            
            password = CustomUser.objects.make_random_password()
            user.set_password(password)
            user.save()
            
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                subject = 'Tài khoản LIMS của bạn đã được tạo'
                message = f'Xin chào {user.username},\n\nTài khoản của bạn đã được quản trị viên tạo thành công.\nEmail đăng nhập: {user.email}\nMật khẩu: {password}\n\nVui lòng đăng nhập và đổi mật khẩu.'
                send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@lims.local'), [user.email])
            except Exception:
                pass
                
            messages.success(request, f'Tạo người dùng thành công! Mật khẩu đã được gửi qua email {user.email}.')
            return redirect('accounts:user_list')
    else:
        form = UserCreateForm()
    return render(request, 'accounts/user_create.html', {'form': form})


@login_required
def user_import_view(request):
    if request.user.role != 'admin':
        messages.error(request, 'Bạn không có quyền truy cập.')
        return redirect('home')
    if request.method == 'POST':
        form = UserExcelImportForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            try:
                wb = openpyxl.load_workbook(excel_file)
                sheet = wb.active
                count = 0
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if not row[0]: continue
                    username = str(row[0]).strip()
                    email = str(row[1]).strip() if row[1] else ''
                    password = str(row[2]).strip() if row[2] else CustomUser.objects.make_random_password()
                    role_input = str(row[3]).strip().lower() if row[3] else 'reader'
                    phone = str(row[4]).strip() if row[4] else ''
                    
                    role = 'reader'
                    if 'admin' in role_input or 'quản trị' in role_input:
                        role = 'admin'
                    elif 'librarian' in role_input or 'thủ thư' in role_input:
                        role = 'librarian'

                    if not CustomUser.objects.filter(username=username).exists():
                        user = CustomUser.objects.create_user(
                            username=username,
                            email=email,
                            password=password,
                            role=role,
                            phone_number=phone
                        )
                        count += 1
                        
                        if email:
                            try:
                                from django.core.mail import send_mail
                                from django.conf import settings
                                subject = 'Tài khoản LIMS của bạn đã được tạo'
                                message = f'Xin chào {user.username},\n\nTài khoản của bạn đã được tạo thành công.\nTên đăng nhập: {user.username}\nMật khẩu: {password}\n\nVui lòng đăng nhập và đổi mật khẩu.'
                                send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@lims.local'), [email])
                            except Exception:
                                pass
                                
                messages.success(request, f'Đã import thành công {count} người dùng! Mật khẩu đã được tự động sinh và gửi qua email.')
                return redirect('accounts:user_list')
            except Exception as e:
                messages.error(request, f'Lỗi khi đọc file: {str(e)}')
    else:
        form = UserExcelImportForm()
    return render(request, 'accounts/user_import.html', {'form': form})


@login_required
def user_edit_view(request, pk):
    if request.user.role != 'admin':
        messages.error(request, 'Bạn không có quyền truy cập.')
        return redirect('home')
    user_obj = get_object_or_404(CustomUser, pk=pk)
    if user_obj.role == 'admin' or user_obj.is_superuser:
        messages.error(request, 'Không thể thao tác trên tài khoản Quản trị viên từ giao diện này.')
        return redirect('accounts:user_list')
    if request.method == 'POST':
        form = UserManageForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cập nhật người dùng "{user_obj.username}" thành công!')
            return redirect('accounts:user_list')
    else:
        form = UserManageForm(instance=user_obj)
    return render(request, 'accounts/user_edit.html', {'form': form, 'user_obj': user_obj})


@login_required
def user_toggle_active_view(request, pk):
    if request.user.role != 'admin':
        messages.error(request, 'Bạn không có quyền truy cập.')
        return redirect('home')
    if request.method == 'POST':
        user_obj = get_object_or_404(CustomUser, pk=pk)
        if user_obj.role == 'admin' or user_obj.is_superuser:
            messages.error(request, 'Không thể thao tác trên tài khoản Quản trị viên từ giao diện này.')
            return redirect('accounts:user_list')
        user_obj.is_active = not user_obj.is_active
        user_obj.save()
        status = 'kích hoạt' if user_obj.is_active else 'vô hiệu hóa'
        messages.success(request, f'Đã {status} tài khoản "{user_obj.username}".')
    return redirect('accounts:user_list')


@csrf_exempt
def otp_verify_view(request):
    if 'pre_2fa_user_id' not in request.session:
        return redirect('accounts:login')
        
    if request.method == 'POST':
        otp_input = request.POST.get('otp', '').strip()
        expire_ts = request.session.get('pre_2fa_expire', 0)
        from django.utils import timezone
        
        if timezone.now().timestamp() > expire_ts:
            messages.error(request, 'Mã OTP đã hết hạn. Vui lòng bấm "Gửi lại mã OTP mới" để lấy mã khác.')
            return redirect('accounts:otp_verify')
            
        if otp_input == request.session.get('pre_2fa_otp'):
            user = CustomUser.objects.get(pk=request.session['pre_2fa_user_id'])
            login(request, user)
            del request.session['pre_2fa_user_id']
            del request.session['pre_2fa_otp']
            del request.session['pre_2fa_expire']
            messages.success(request, 'Xác thực 2 lớp thành công!')
            return redirect('home')
        else:
            messages.error(request, 'Mã OTP không chính xác.')
    return render(request, 'accounts/otp_verify.html', {
        'expire_ts': request.session.get('pre_2fa_expire', 0),
        'dev_otp': request.session.get('pre_2fa_otp'),
    })

def otp_resend_view(request):
    if 'pre_2fa_user_id' not in request.session:
        return redirect('accounts:login')
        
    user_id = request.session['pre_2fa_user_id']
    from .models import CustomUser
    import random
    from django.utils import timezone
    import datetime
    
    try:
        user = CustomUser.objects.get(pk=user_id)
        otp = f"{random.randint(100000, 999999)}"
        request.session['pre_2fa_otp'] = otp
        request.session['pre_2fa_expire'] = (timezone.now() + datetime.timedelta(seconds=30)).timestamp()
        
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                'Mã xác thực OTP (2FA) - VietNhatLiMS (Gửi lại)',
                f'Xin chào {user.username},\n\nMã xác thực OTP MỚI của bạn là: {otp}\n\nMã này sẽ hết hạn trong 30 giây.\nNếu bạn không thực hiện thao tác này, vui lòng đổi mật khẩu ngay lập tức.',
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@lims.local'),
                [user.email]
            )
        except Exception:
            pass
            
        messages.success(request, 'Mã OTP mới đã được gửi đến email của bạn. Vui lòng kiểm tra hộp thư.')
    except CustomUser.DoesNotExist:
        pass
        
    return redirect('accounts:otp_verify')

def forgot_password_view(request):
    from .forms import ForgotPasswordForm
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = CustomUser.objects.filter(email=email).first()
            if user:
                import random
                from django.utils import timezone
                import datetime
                otp = f"{random.randint(100000, 999999)}"
                request.session['reset_user_id'] = user.pk
                request.session['reset_otp'] = otp
                request.session['reset_expire'] = (timezone.now() + datetime.timedelta(seconds=30)).timestamp()
                
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    send_mail(
                        'Mã xác thực Quên Mật khẩu - VietNhatLiMS',
                        f'Xin chào {user.username},\n\nMã xác thực OTP của bạn là: {otp}\n\nMã này sẽ hết hạn trong 30 giây.\nNếu bạn không yêu cầu đổi mật khẩu, vui lòng bỏ qua email này.',
                        getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@lims.local'),
                        [user.email]
                    )
                except Exception:
                    pass
                return redirect('accounts:forgot_password_otp')
            else:
                messages.error(request, 'Email không tồn tại trong hệ thống.')
    else:
        form = ForgotPasswordForm()
    return render(request, 'accounts/forgot_password.html', {'form': form})

@csrf_exempt
def forgot_password_otp_view(request):
    if 'reset_user_id' not in request.session:
        return redirect('accounts:forgot_password')
        
    if request.method == 'POST':
        otp_input = request.POST.get('otp', '').strip()
        expire_ts = request.session.get('reset_expire', 0)
        from django.utils import timezone
        
        if timezone.now().timestamp() > expire_ts:
            messages.error(request, 'Mã OTP đã hết hạn. Vui lòng bấm "Gửi lại mã OTP mới".')
            return redirect('accounts:forgot_password_otp')
            
        if otp_input == request.session.get('reset_otp'):
            request.session['can_reset_password'] = True
            del request.session['reset_otp']
            del request.session['reset_expire']
            return redirect('accounts:reset_password')
        else:
            messages.error(request, 'Mã OTP không chính xác.')
            
    return render(request, 'accounts/forgot_password_otp.html', {
        'expire_ts': request.session.get('reset_expire', 0),
        'dev_otp': request.session.get('reset_otp'),
    })

def forgot_password_resend_view(request):
    if 'reset_user_id' not in request.session:
        return redirect('accounts:forgot_password')
        
    user_id = request.session['reset_user_id']
    from .models import CustomUser
    import random
    from django.utils import timezone
    import datetime
    
    try:
        user = CustomUser.objects.get(pk=user_id)
        otp = f"{random.randint(100000, 999999)}"
        request.session['reset_otp'] = otp
        request.session['reset_expire'] = (timezone.now() + datetime.timedelta(seconds=30)).timestamp()
        
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                'Mã xác thực Quên Mật khẩu - VietNhatLiMS (Gửi lại)',
                f'Xin chào {user.username},\n\nMã xác thực OTP MỚI của bạn là: {otp}\n\nMã này sẽ hết hạn trong 30 giây.',
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@lims.local'),
                [user.email]
            )
        except Exception:
            pass
        messages.success(request, 'Mã OTP mới đã được gửi. Vui lòng kiểm tra hộp thư.')
    except CustomUser.DoesNotExist:
        pass
        
    return redirect('accounts:forgot_password_otp')

def reset_password_view(request):
    if not request.session.get('can_reset_password') or 'reset_user_id' not in request.session:
        return redirect('accounts:login')
        
    from .forms import ResetPasswordForm
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            user_id = request.session['reset_user_id']
            from .models import CustomUser
            try:
                user = CustomUser.objects.get(pk=user_id)
                user.set_password(form.cleaned_data['password'])
                # Reset lockout just in case
                user.failed_login_attempts = 0
                user.locked_until = None
                user.save()
                messages.success(request, 'Mật khẩu đã được đặt lại thành công. Vui lòng đăng nhập.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'Người dùng không tồn tại.')
                
            del request.session['can_reset_password']
            del request.session['reset_user_id']
            return redirect('accounts:login')
    else:
        form = ResetPasswordForm()
    return render(request, 'accounts/reset_password.html', {'form': form})
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import CustomUser

@login_required
def admin_reset_password_view(request, pk):
    if request.user.role != 'admin':
        messages.error(request, 'Bạn không có quyền truy cập.')
        return redirect('home')
        
    user_obj = get_object_or_404(CustomUser, pk=pk)
    if user_obj.role == 'admin' or user_obj.is_superuser:
        messages.error(request, 'Không thể thao tác trên tài khoản Quản trị viên.')
        return redirect('accounts:user_list')
        
    if request.method == 'POST':
        # Reset to default
        new_password = user_obj.username + '@123'
        user_obj.set_password(new_password)
        user_obj.failed_login_attempts = 0
        user_obj.locked_until = None
        user_obj.save()
        messages.success(request, f'Đã đặt lại mật khẩu cho {user_obj.username} thành: {new_password}')
        
    return redirect('accounts:user_edit', pk=pk)
