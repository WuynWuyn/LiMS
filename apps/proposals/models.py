from django.db import models
from django.conf import settings


class BookProposal(models.Model):
    """Đề xuất mua sách mới."""
    STATUS_CHOICES = [
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
        ('purchased', 'Đã mua'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='proposals',
        verbose_name='Người đề xuất',
    )
    title = models.CharField(max_length=500, verbose_name='Tên sách đề xuất')
    author_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Tên tác giả',
    )
    isbn = models.CharField(
        max_length=13,
        default='0000000000000',
        verbose_name='Mã ISBN',
    )
    reason = models.TextField(verbose_name='Lý do đề xuất')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Trạng thái',
    )
    admin_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Ghi chú của admin',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_proposals',
        verbose_name='Người duyệt',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')

    class Meta:
        verbose_name = 'Đề xuất sách'
        verbose_name_plural = 'Đề xuất sách'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username} ({self.get_status_display()})"
