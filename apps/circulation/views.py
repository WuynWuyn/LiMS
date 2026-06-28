from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta

from .models import BorrowRecord, Reservation
from apps.catalog.models import Book


@login_required
def counter_borrow_view(request):
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, 'Không có quyền.')
        return redirect('home')
        
    if request.method == 'POST':
        student_code = request.POST.get('student_code')
        book_isbn = request.POST.get('book_isbn')
        
        try:
            from apps.accounts.models import CustomUser
            from apps.catalog.models import Book
            user = CustomUser.objects.get(username=student_code)
            book = Book.objects.get(isbn=book_isbn)
            
            if not user.can_borrow:
                messages.error(request, 'Sinh viên này đang bị khóa mượn sách.')
                return render(request, 'circulation/counter_borrow.html')
                
            if book.available_copies <= 0:
                messages.error(request, 'Sách này hiện không có sẵn.')
                return render(request, 'circulation/counter_borrow.html')
            
            BorrowRecord.objects.create(
                user=user, 
                book=book, 
                due_date=timezone.now() + timedelta(days=14),
                status='borrowed', 
                approved_by=request.user
            )
            
            book.available_copies -= 1
            book.save()
            
            messages.success(request, f'Đã cho {user.username} mượn sách {book.title}.')
        except CustomUser.DoesNotExist:
            messages.error(request, 'Không tìm thấy sinh viên (mã sinh viên không đúng).')
        except Book.DoesNotExist:
            messages.error(request, 'Không tìm thấy sách (ISBN không đúng).')
            
    return render(request, 'circulation/counter_borrow.html')


@login_required
def borrow_history_view(request):
    status_filter = request.GET.get('status', '')
    records = BorrowRecord.objects.filter(user=request.user).select_related('book')
    if status_filter:
        records = records.filter(status=status_filter)
    paginator = Paginator(records.order_by('-created_at'), 10)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'circulation/borrow_history.html', {'page_obj': page, 'status_filter': status_filter})


@login_required
def borrow_cancel_view(request, pk):
    if request.method == 'POST':
        record = get_object_or_404(BorrowRecord, pk=pk, user=request.user, status='pending')
        record.status = 'cancelled'
        record.save()
        messages.success(request, 'Đã hủy yêu cầu mượn sách.')
    return redirect('circulation:borrow_history')


@login_required
def renew_borrow_view(request, pk):
    record = get_object_or_404(BorrowRecord, pk=pk, user=request.user, status='borrowed')
    if request.method == 'POST':
        if record.is_overdue:
            messages.error(request, 'Sách đã quá hạn, không thể gia hạn. Vui lòng đến thư viện trả sách và nộp phạt.')
            return redirect('circulation:borrow_history')
            
        if record.days_until_due > 2:
            messages.error(request, f'Chỉ được phép gia hạn khi còn 2 ngày hoặc ít hơn (hiện tại còn {record.days_until_due} ngày).')
            return redirect('circulation:borrow_history')
            
        if getattr(record, 'renewal_count', 0) >= 1:
            messages.error(request, 'Bạn đã sử dụng hết lượt gia hạn cho cuốn sách này (tối đa 1 lần).')
            return redirect('circulation:borrow_history')
            
        has_reservation = Reservation.objects.filter(book=record.book, status='active').exists()
        if has_reservation:
            messages.error(request, 'Không thể gia hạn vì sách này đang có người khác xếp hàng đặt trước.')
            return redirect('circulation:borrow_history')
            
        record.due_date = record.due_date + timedelta(days=10)
        record.renewal_count = getattr(record, 'renewal_count', 0) + 1
        record.save()
        messages.success(request, f'Gia hạn thành công. Hạn trả sách mới: {timezone.localtime(record.due_date).strftime("%d/%m/%Y")}.')
    return redirect('circulation:borrow_history')


@login_required
def manage_borrows_view(request):
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, 'Bạn không có quyền truy cập.')
        return redirect('home')
    status_filter = request.GET.get('status', '')
    records = BorrowRecord.objects.all().select_related('user', 'book')
    if status_filter:
        records = records.filter(status=status_filter)
    paginator = Paginator(records.order_by('-created_at'), 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'circulation/manage_borrows.html', {'page_obj': page, 'status_filter': status_filter})





@login_required
def return_book_view(request, pk):
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, 'Không có quyền.')
        return redirect('home')
    record = get_object_or_404(BorrowRecord, pk=pk)
    if record.status != 'borrowed':
        messages.warning(request, 'Không thể trả cuốn sách này (có thể đã trả hoặc báo mất).')
        return redirect('circulation:manage_borrows')
        
    if request.method == 'POST':
        return_date = timezone.now()
        days_late = 0
        if return_date > record.due_date:
            days_late = (return_date - record.due_date).days

        book_condition = request.POST.get('book_condition')

        if book_condition == 'damaged':
            record.status = 'lost'
            messages.warning(request, f'Trả sách "{record.book.title}" trong tình trạng hỏng/mất. Đã ghi nhận vi phạm tín nhiệm (Reported Lost).')
        elif days_late > 0:
            record.status = 'overdue'
            messages.warning(request, f'Trả sách "{record.book.title}" trễ hạn {days_late} ngày. Đã ghi nhận vi phạm tín nhiệm (Overdue).')
        else:
            record.status = 'returned'
            messages.success(request, f'Đã xử lý trả sách "{record.book.title}" thành công.')

        record.return_date = return_date
        record.notes = request.POST.get('notes', record.notes)
        record.save()
        book = record.book
        if record.status in ['returned', 'overdue']:
            book.available_copies += 1
            book.save()

            first_reservation = Reservation.objects.filter(book=book, status='active').order_by('reserved_at').first()
            if first_reservation:
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    subject = f'Sách "{book.title}" bạn đặt trước đã có sẵn'
                    msg = f'Xin chào {first_reservation.user.username},\n\nCuốn sách "{book.title}" mà bạn đặt trước đã được trả lại thư viện.\nBạn có 48 giờ để đến thư viện nhận sách kể từ bây giờ.\n\nTrân trọng!'
                    send_mail(subject, msg, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@lims.local'), [first_reservation.user.email])
                except Exception:
                    pass
    return redirect('circulation:manage_borrows')


@login_required
def report_lost_view(request, pk):
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, 'Không có quyền.')
        return redirect('home')
    record = get_object_or_404(BorrowRecord, pk=pk)
    if record.status != 'borrowed':
        messages.warning(request, 'Chỉ có thể báo mất những sách đang được mượn.')
        return redirect('circulation:manage_borrows')

    if request.method == 'POST':
        record.status = 'lost'
        record.save()
        book = record.book
        if book.total_copies > 0:
            book.total_copies -= 1
        if book.available_copies > 0:
            book.available_copies -= 1
        book.save()
        fine = int(book.price * 1.5)
        messages.warning(request, f'Đã ghi nhận vi phạm tín nhiệm: Báo mất sách "{book.title}". Độc giả cần bồi thường sách tương đương hoặc 150% giá bìa ({fine}đ).')
    return redirect('circulation:manage_borrows')



@login_required
def reservation_create_view(request, book_id):
    if not request.user.can_borrow:
        messages.error(request, 'Tài khoản của bạn đang bị khóa chức năng do vi phạm tín nhiệm.')
        return redirect('catalog:book_detail', pk=book_id)

    has_violation = BorrowRecord.objects.filter(user=request.user, status__in=['overdue', 'lost']).exists()
    if has_violation:
        messages.error(request, 'Tài khoản của bạn đang giữ sách quá hạn hoặc báo mất. Vui lòng hoàn tất xử lý trước khi đặt trước thêm.')
        return redirect('catalog:book_detail', pk=book_id)

    book = get_object_or_404(Book, pk=book_id)
    if request.method == 'POST':
        existing = Reservation.objects.filter(user=request.user, book=book, status='active').exists()
        if existing:
            messages.warning(request, 'Bạn đã đặt trước sách này rồi.')
        else:
            current_reservations = Reservation.objects.filter(user=request.user, status='active').count()
            limit = 5 if request.user.role == 'lecturer' else 3
            if current_reservations >= limit:
                messages.error(request, f'Bạn đã đạt giới hạn đặt trước tối đa ({limit} cuốn).')
                return redirect('catalog:book_detail', pk=book.pk)
                
            Reservation.objects.create(
                user=request.user, book=book, expires_at=timezone.now() + timedelta(days=3),
            )
            messages.success(request, f'Đã đặt trước sách "{book.title}". Hạn: 3 ngày.')
        return redirect('catalog:book_detail', pk=book.pk)
    return render(request, 'circulation/reserve_confirm.html', {'book': book})


@login_required
def reservation_list_view(request):
    reservations = Reservation.objects.filter(user=request.user).select_related('book').order_by('-reserved_at')
    paginator = Paginator(reservations, 10)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'circulation/reservation_list.html', {'page_obj': page})


@login_required
def reservation_cancel_view(request, pk):
    if request.method == 'POST':
        reservation = get_object_or_404(Reservation, pk=pk, user=request.user, status='active')
        reservation.status = 'cancelled'
        reservation.save()
        messages.success(request, 'Đã hủy đặt trước.')
    return redirect('circulation:reservation_list')


@login_required
def borrow_request_view(request, pk):
    from apps.catalog.models import Book
    book = get_object_or_404(Book, pk=pk)
    if not request.user.can_borrow:
        messages.error(request, 'Tài khoản của bạn đang bị khóa mượn sách.')
        return redirect('catalog:book_detail', pk=pk)
    if book.available_copies <= 0:
        messages.error(request, 'Cuốn sách này hiện không có sẵn để mượn.')
        return redirect('catalog:book_detail', pk=pk)
        
    existing = BorrowRecord.objects.filter(user=request.user, book=book, status__in=['pending', 'approved', 'borrowed']).first()
    if existing:
        messages.warning(request, 'Bạn đã mượn hoặc đang gửi yêu cầu mượn cuốn sách này rồi.')
        return redirect('catalog:book_detail', pk=pk)
        
    BorrowRecord.objects.create(
        user=request.user,
        book=book,
        due_date=timezone.now() + timedelta(days=14),
        status='pending'
    )
    messages.success(request, f'Đã gửi yêu cầu mượn sách "{book.title}" thành công! Vui lòng chờ thủ thư phê duyệt.')
    return redirect('circulation:borrow_history')


@login_required
def approve_borrow_view(request, pk):
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, 'Bạn không có quyền.')
        return redirect('home')
    record = get_object_or_404(BorrowRecord, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            if record.book.available_copies <= 0:
                messages.error(request, 'Sách này hiện đã hết bản sao có sẵn.')
                return redirect('circulation:manage_borrows')
            record.status = 'borrowed'
            record.borrow_date = timezone.now()
            record.due_date = timezone.now() + timedelta(days=14)
            record.approved_by = request.user
            record.save()
            record.book.available_copies -= 1
            record.book.save()
            messages.success(request, f'Đã duyệt cho {record.user.username} mượn sách.')
        elif action == 'reject':
            record.status = 'cancelled'
            record.approved_by = request.user
            record.save()
            messages.info(request, f'Đã từ chối yêu cầu mượn sách của {record.user.username}.')
    return redirect('circulation:manage_borrows')


@login_required
def resolve_violation_view(request, pk):
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, 'Bạn không có quyền.')
        return redirect('home')
    record = get_object_or_404(BorrowRecord, pk=pk)
    if request.method == 'POST':
        resolution_type = request.POST.get('resolution_type')
        resolution_notes = request.POST.get('resolution_notes', '')
        
        if record.status in ['overdue', 'lost']:
            record.status = 'returned'
            if not record.return_date:
                record.return_date = timezone.now()
                
            resolution_text = ""
            if resolution_type == 'returned_late':
                resolution_text = "Đã trả sách trễ hạn."
            elif resolution_type == 'replaced_book':
                resolution_text = "Đã đền bù sách mới cùng ISBN."
                # Tăng lại số lượng vì sách mới đã được bổ sung
                record.book.total_copies += 1
                record.book.available_copies += 1
                record.book.save()
            elif resolution_type == 'paid_150':
                resolution_text = "Đã thanh toán 150% giá bìa."
                
            final_note = f"[{resolution_text}] {resolution_notes}".strip()
            record.notes = ((record.notes or '') + f'\n{final_note}').strip()
            record.save()
            
            messages.success(request, f'Đã gỡ vi phạm cho {record.user.username} (sách "{record.book.title}"). Quyền mượn sách sẽ được khôi phục nếu không còn vi phạm khác.')
    return redirect('circulation:manage_borrows')

