from django.db import models


class Category(models.Model):
    """Danh mục / Thể loại sách."""
    name = models.CharField(max_length=200, unique=True, verbose_name='Tên thể loại')
    description = models.TextField(blank=True, null=True, verbose_name='Mô tả')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')

    class Meta:
        verbose_name = 'Thể loại'
        verbose_name_plural = 'Thể loại'
        ordering = ['name']

    def __str__(self):
        return self.name


class Publisher(models.Model):
    """Nhà xuất bản."""
    name = models.CharField(max_length=255, unique=True, verbose_name='Tên NXB')
    address = models.TextField(blank=True, null=True, verbose_name='Địa chỉ')

    class Meta:
        verbose_name = 'Nhà xuất bản'
        verbose_name_plural = 'Nhà xuất bản'
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    """Đầu sách (Book Title) in the library."""
    STATUS_CHOICES = [
        ('available', 'Có sẵn'),
        ('borrowed', 'Đang mượn'),
        ('reserved', 'Đã đặt trước'),
        ('maintenance', 'Bảo trì'),
    ]

    title = models.CharField(max_length=500, verbose_name='Tên sách')
    isbn = models.CharField(
        max_length=13,
        unique=True,
        verbose_name='Mã ISBN',
    )
    authors = models.CharField(
        max_length=255,
        verbose_name='Tác giả',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='books',
        verbose_name='Thể loại',
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='books',
        verbose_name='Nhà xuất bản',
    )
    publication_year = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Năm xuất bản',
    )
    description = models.TextField(blank=True, null=True, verbose_name='Mô tả')
    cover_image = models.ImageField(
        upload_to='covers/',
        blank=True,
        null=True,
        verbose_name='Ảnh bìa',
    )
    price = models.PositiveIntegerField(
        default=100000,
        verbose_name='Giá bìa (VNĐ)',
    )
    total_copies = models.PositiveIntegerField(default=1, verbose_name='Tổng số bản')
    available_copies = models.PositiveIntegerField(default=1, verbose_name='Số bản có sẵn')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        verbose_name='Trạng thái',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')

    class Meta:
        verbose_name = 'Sách'
        verbose_name_plural = 'Sách'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_available(self):
        return self.available_copies > 0


class PDFDocument(models.Model):
    """Lưu trữ file PDF của Book và trạng thái nhúng."""
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Done', 'Done'),
        ('Failed', 'Failed'),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='pdf_documents', verbose_name='Sách')
    file_path = models.FileField(upload_to='books_pdf/', verbose_name='File PDF')
    embed_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', verbose_name='Trạng thái Embed')

    class Meta:
        verbose_name = 'Tài liệu PDF'
        verbose_name_plural = 'Tài liệu PDF'

    def __str__(self):
        return f"PDF of {self.book.title}"
