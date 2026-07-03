from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg

from .models import Book, Category, Publisher
from .forms import BookSearchForm, BookForm, CategoryForm, ExcelImportForm
import openpyxl


@login_required
def book_list_view(request):
    books = Book.objects.select_related('category').order_by('-created_at')
    cat = request.GET.get('category')
    if cat:
        books = books.filter(category_id=cat)
    paginator = Paginator(books, 12)
    page = paginator.get_page(request.GET.get('page'))
    categories = Category.objects.all()
    return render(request, 'catalog/book_list.html', {
        'page_obj': page, 'categories': categories, 'current_cat': cat,
    })


@login_required
def book_detail_view(request, pk):
    book = get_object_or_404(Book.objects.prefetch_related('reviews__user').select_related('category', 'publisher'), pk=pk)
    reviews = book.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
    user_has_reviewed = False
    user_has_borrowed = False
    if request.user.is_authenticated:
        user_has_reviewed = reviews.filter(user=request.user).exists()
        from apps.circulation.models import BorrowRecord
        user_has_borrowed = BorrowRecord.objects.filter(user=request.user, book=book, status='returned').exists()
    return render(request, 'catalog/book_detail.html', {
        'book': book, 'reviews': reviews, 'avg_rating': avg_rating,
        'user_has_reviewed': user_has_reviewed, 'user_has_borrowed': user_has_borrowed,
    })


@login_required
def book_search_view(request):
    form = BookSearchForm(request.GET)
    books = Book.objects.select_related('category')
    if form.is_valid():
        q = form.cleaned_data.get('q')
        category = form.cleaned_data.get('category')
        status = form.cleaned_data.get('status')
        if q:
            books = books.filter(
                Q(title__icontains=q) | Q(authors__icontains=q) | Q(isbn__icontains=q)
            ).distinct()
        if category:
            books = books.filter(category=category)
        if status:
            books = books.filter(status=status)
    paginator = Paginator(books.order_by('-created_at'), 12)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'catalog/book_search.html', {'form': form, 'page_obj': page})


def _check_staff(request):
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, 'Bạn không có quyền truy cập.')
        return False
    return True


@login_required
def book_manage_view(request):
    if not _check_staff(request):
        return redirect('home')
    q = request.GET.get('q', '')
    books = Book.objects.select_related('category')
    if q:
        books = books.filter(Q(title__icontains=q) | Q(isbn__icontains=q))
    paginator = Paginator(books.order_by('-created_at'), 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'catalog/book_manage.html', {'page_obj': page, 'q': q})


@login_required
def book_create_view(request):
    if not _check_staff(request):
        return redirect('home')
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thêm sách thành công!')
            return redirect('catalog:book_manage')
    else:
        form = BookForm()
    return render(request, 'catalog/book_form.html', {'form': form, 'title': 'Thêm sách mới'})


@login_required
def book_import_view(request):
    if not _check_staff(request):
        return redirect('home')
    if request.method == 'POST':
        form = ExcelImportForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            try:
                wb = openpyxl.load_workbook(excel_file)
                sheet = wb.active
                count = 0
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if not row[0]: continue
                    title = str(row[0]).strip()
                    isbn = str(row[1]).strip() if row[1] else None
                    price = int(row[2]) if row[2] else 100000
                    total_copies = int(row[3]) if row[3] else 1
                    author_names = str(row[4]).strip() if row[4] else 'Khuyết danh'
                    category_name = str(row[5]).strip() if row[5] else 'Khác'
                    publisher_name = str(row[6]).strip() if row[6] else ''
                    
                    if isbn and Book.objects.filter(isbn=isbn).exists():
                        continue
                        
                    category, _ = Category.objects.get_or_create(name__iexact=category_name, defaults={'name': category_name})
                    publisher = None
                    if publisher_name:
                        publisher, _ = Publisher.objects.get_or_create(name__iexact=publisher_name, defaults={'name': publisher_name.title()})
                        
                    book = Book.objects.create(
                        title=title,
                        isbn=isbn,
                        price=price,
                        total_copies=total_copies,
                        available_copies=total_copies,
                        category=category,
                        publisher=publisher,
                        authors=author_names
                    )
                    

                    count += 1
                if count > 0:
                    messages.success(request, f'Đã import thành công {count} cuốn sách!')
                else:
                    messages.warning(request, 'Không có cuốn sách mới nào được thêm (các sách trong file Excel đã tồn tại trong hệ thống).')
                return redirect('catalog:book_manage')
            except Exception as e:
                messages.error(request, f'Lỗi khi đọc file: {str(e)}')
    else:
        form = ExcelImportForm()
    return render(request, 'catalog/book_import.html', {'form': form})


@login_required
def book_edit_view(request, pk):
    if not _check_staff(request):
        return redirect('home')
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật sách thành công!')
            return redirect('catalog:book_manage')
    else:
        form = BookForm(instance=book)
    return render(request, 'catalog/book_form.html', {'form': form, 'title': f'Chỉnh sửa: {book.title}', 'book': book})


@login_required
def book_delete_view(request, pk):
    if not _check_staff(request):
        return redirect('home')
    if request.method == 'POST':
        book = get_object_or_404(Book, pk=pk)
        if book.borrow_records.filter(status__in=['borrowed', 'overdue']).exists():
            messages.error(request, 'Không thể xóa sách này vì đang có người mượn hoặc chưa trả.')
        else:
            book.delete()
            messages.success(request, 'Đã xóa sách thành công.')
    return redirect('catalog:book_manage')


@login_required
def category_manage_view(request):
    if not _check_staff(request):
        return redirect('home')
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thêm thể loại thành công!')
            return redirect('catalog:category_manage')
    else:
        form = CategoryForm()
    categories = Category.objects.all()
    paginator = Paginator(categories, 10)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'catalog/category_manage.html', {'form': form, 'page_obj': page})


@login_required
def category_edit_view(request, pk):
    if not _check_staff(request):
        return redirect('home')
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật thể loại thành công!')
            return redirect('catalog:category_manage')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'catalog/category_form.html', {'form': form, 'category': category})


@login_required
def category_delete_view(request, pk):
    if not _check_staff(request):
        return redirect('home')
    if request.method == 'POST':
        category = get_object_or_404(Category, pk=pk)
        if category.books.exists():
            messages.error(request, 'Không thể xóa danh mục này vì vẫn còn sách thuộc danh mục.')
        else:
            category.delete()
            messages.success(request, 'Đã xóa thể loại thành công.')
    return redirect('catalog:category_manage')
