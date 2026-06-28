from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.catalog.models import Book
from apps.accounts.models import CustomUser
from apps.circulation.models import BorrowRecord, Reservation
from apps.proposals.models import BookProposal

@login_required
def admin_dashboard_view(request):
    total_books = Book.objects.count()
    total_users = CustomUser.objects.count()
    total_borrowed = BorrowRecord.objects.filter(status='borrowed').count()
    total_overdue = BorrowRecord.objects.filter(status='overdue').count()
    
    # Chỉ số cảnh báo tín nhiệm
    total_violations = BorrowRecord.objects.filter(status__in=['overdue', 'lost']).count()
    locked_users = CustomUser.objects.filter(can_borrow=False).count()
    
    # Tỷ lệ duyệt mua sách theo ISBN
    total_proposals = BookProposal.objects.count()
    approved_proposals = BookProposal.objects.filter(status__in=['approved', 'purchased']).count()
    proposal_approval_rate = round((approved_proposals / total_proposals * 100), 1) if total_proposals > 0 else 0
    
    # Dữ liệu biểu đồ sách theo danh mục
    from apps.catalog.models import Category
    from django.db.models import Count
    categories_data = Category.objects.annotate(book_count=Count('book')).values('name', 'book_count')
    category_labels = [c['name'] for c in categories_data]
    category_counts = [c['book_count'] for c in categories_data]
    
    # Biểu đồ số lượng mượn sách theo ngày (7 ngày gần nhất)
    from django.utils import timezone
    from datetime import timedelta
    today = timezone.now().date()
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    borrows_by_date = []
    for d in dates:
        cnt = BorrowRecord.objects.filter(borrow_date__date=d).count()
        borrows_by_date.append(cnt)
    
    borrow_labels = [d.strftime('%d/%m') for d in dates]

    context = {
        'total_books': total_books,
        'total_users': total_users,
        'total_borrowed': total_borrowed,
        'total_overdue': total_overdue,
        'total_violations': total_violations,
        'locked_users': locked_users,
        'total_proposals': total_proposals,
        'approved_proposals': approved_proposals,
        'proposal_approval_rate': proposal_approval_rate,
        'category_labels': category_labels,
        'category_counts': category_counts,
        'borrow_labels': borrow_labels,
        'borrows_by_date': borrows_by_date,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

@login_required
def user_history_view(request):
    user = request.user
    
    # Sách đang mượn (BorrowRecord borrowed/overdue)
    borrowed_records = BorrowRecord.objects.filter(
        user=user, 
        status__in=['borrowed', 'overdue']
    )
    
    # Lịch sử trả (returned)
    returned_records = BorrowRecord.objects.filter(
        user=user, 
        status='returned'
    )
    
    # Đặt trước (Reservation)
    reservations = Reservation.objects.filter(user=user)
    
    # Vi phạm tín nhiệm (Overdue / Lost)
    violations = BorrowRecord.objects.filter(user=user, status__in=['overdue', 'lost'])

    context = {
        'borrowed_records': borrowed_records,
        'returned_records': returned_records,
        'reservations': reservations,
        'violations': violations,
    }
    return render(request, 'dashboard/user_history.html', context)

@login_required
def user_history_admin_view(request, pk):
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    from django.shortcuts import redirect
    
    if request.user.role not in ['admin', 'librarian']:
        messages.error(request, 'Bạn không có quyền truy cập.')
        return redirect('home')
        
    user = get_object_or_404(CustomUser, pk=pk)
    
    borrowed_records = BorrowRecord.objects.filter(user=user, status__in=['borrowed', 'overdue'])
    returned_records = BorrowRecord.objects.filter(user=user, status='returned')
    reservations = Reservation.objects.filter(user=user)
    violations = BorrowRecord.objects.filter(user=user, status__in=['overdue', 'lost'])

    context = {
        'borrowed_records': borrowed_records,
        'returned_records': returned_records,
        'reservations': reservations,
        'violations': violations,
        'viewed_user': user,
    }
    return render(request, 'dashboard/user_history.html', context)
