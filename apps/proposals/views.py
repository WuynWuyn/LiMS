from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator

from .models import BookProposal
from .forms import ProposalCreateForm


@login_required
def proposal_list_view(request):
    proposals = BookProposal.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(proposals, 10)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'proposals/proposal_list.html', {'page_obj': page})


@login_required
def proposal_create_view(request):
    if request.method == 'POST':
        pending_count = BookProposal.objects.filter(user=request.user, status='pending').count()
        if pending_count >= 3:
            messages.error(request, 'Bạn đã đạt giới hạn 3 đề xuất đang chờ duyệt. Vui lòng chờ phản hồi trước khi gửi thêm.')
            return redirect('proposals:proposal_list')
            
        form = ProposalCreateForm(request.POST)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.user = request.user
            proposal.save()
            messages.success(request, 'Đề xuất đã được gửi thành công!')
            return redirect('proposals:proposal_list')
    else:
        form = ProposalCreateForm()
    return render(request, 'proposals/proposal_create.html', {'form': form})


@login_required
def proposal_detail_view(request, pk):
    proposal = get_object_or_404(BookProposal, pk=pk)
    if proposal.user != request.user and request.user.role not in ['librarian', 'admin']:
        messages.error(request, 'Không có quyền xem.')
        return redirect('home')
    return render(request, 'proposals/proposal_detail.html', {'proposal': proposal})


@login_required
def review_proposals_view(request):
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, 'Không có quyền.')
        return redirect('home')
    status_filter = request.GET.get('status', '')
    proposals = BookProposal.objects.all().select_related('user').order_by('-created_at')
    if status_filter:
        proposals = proposals.filter(status=status_filter)
        
    grouped = []
    seen = {}
    for p in proposals:
        key = p.isbn if p.isbn else f"nopk_{p.pk}"
        if key not in seen:
            p.grouped_count = 1
            p.grouped_users = [p.user.username]
            seen[key] = p
            grouped.append(p)
        else:
            rep = seen[key]
            rep.grouped_count += 1
            if p.user.username not in rep.grouped_users:
                rep.grouped_users.append(p.user.username)
                
    paginator = Paginator(grouped, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'proposals/review_proposals.html', {'page_obj': page, 'status_filter': status_filter})


@login_required
def review_proposal_action_view(request, pk):
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, 'Không có quyền.')
        return redirect('home')
    proposal = get_object_or_404(BookProposal, pk=pk, status='pending')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ['approved', 'rejected']:
            if proposal.isbn:
                target_proposals = BookProposal.objects.filter(isbn=proposal.isbn, status='pending').select_related('user')
            else:
                target_proposals = [proposal]
                
            admin_notes = request.POST.get('admin_notes', '')
            count = 0
            users_to_email = []
            for p in target_proposals:
                p.status = action
                p.admin_notes = admin_notes
                p.reviewed_by = request.user
                p.save()
                count += 1
                if p.user.email and (p.user, p.title) not in users_to_email:
                    users_to_email.append((p.user, p.title))
            
            label = 'phê duyệt' if action == 'approved' else 'từ chối'
            
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@lims.local')
                for u, book_title in users_to_email:
                    subject = f'Kết quả đề xuất sách: {book_title}'
                    if action == 'approved':
                        msg = f'Xin chào {u.username},\n\nĐề xuất mua cuốn sách "{book_title}" (ISBN: {proposal.isbn}) của bạn đã được thư viện phê duyệt gom nhóm và sẽ sớm được bổ sung vào kho sách. Cảm ơn sự đóng góp của bạn!'
                    else:
                        msg = f'Xin chào {u.username},\n\nRất tiếc, đề xuất mua cuốn sách "{book_title}" (ISBN: {proposal.isbn}) của bạn đã bị từ chối với lý do:\n"{admin_notes}"\n\nCảm ơn sự đóng góp của bạn!'
                    send_mail(subject, msg, from_email, [u.email], fail_silently=True)
            except Exception:
                pass
                
            if count > 1:
                messages.success(request, f'Đã {label} đồng loạt {count} đề xuất cho mã ISBN {proposal.isbn}.')
            else:
                messages.success(request, f'Đã {label} đề xuất "{proposal.title}".')
    return redirect('proposals:review_proposals')
