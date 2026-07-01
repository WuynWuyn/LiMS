from django import forms
from .models import Book, Category, Publisher


class BookSearchForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Tìm theo tên sách, tác giả, ISBN...',
    }))
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(), required=False, empty_label='Tất cả thể loại',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'Tất cả trạng thái')] + Book.STATUS_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class BookForm(forms.ModelForm):

    publisher_name = forms.CharField(
        label='Nhà xuất bản',
        required=True,
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: NXB Trẻ', 'maxlength': '255'})
    )

    class Meta:
        model = Book
        fields = ('title', 'isbn', 'authors', 'category', 'publication_year', 'description', 
                  'cover_image', 'price', 'total_copies', 'available_copies', 'status')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '500'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50'}),
            'authors': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Nguyễn Nhật Ánh, Nam Cao', 'maxlength': '255'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'publication_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'maxlength': '2000'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_copies': forms.NumberInput(attrs={'class': 'form-control'}),
            'available_copies': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            if self.instance.publisher:
                self.initial['publisher_name'] = self.instance.publisher.name

    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title:
            if '<' in title or '>' in title:
                from django.core.exceptions import ValidationError
                raise ValidationError("Tên sách không được chứa ký tự đặc biệt (<, >).")
            qs = Book.objects.filter(title__iexact=title)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                from django.core.exceptions import ValidationError
                raise ValidationError(f"Sách có tên '{title}' đã tồn tại trong hệ thống.")
        return title

    def clean_authors(self):
        authors = self.cleaned_data.get('authors')
        if authors and ('<' in authors or '>' in authors):
            from django.core.exceptions import ValidationError
            raise ValidationError("Tên tác giả không được chứa ký tự đặc biệt (<, >).")
        return authors

    def clean_publisher_name(self):
        publisher_name = self.cleaned_data.get('publisher_name')
        if publisher_name and ('<' in publisher_name or '>' in publisher_name):
            from django.core.exceptions import ValidationError
            raise ValidationError("Tên nhà xuất bản không được chứa ký tự đặc biệt (<, >).")
        return publisher_name

    def clean_isbn(self):
        isbn = self.cleaned_data.get('isbn')
        if isbn:
            from django.core.exceptions import ValidationError
            qs = Book.objects.filter(isbn=isbn)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"Sách có mã ISBN '{isbn}' đã tồn tại trong hệ thống. Vui lòng tìm sách này và tăng 'Tổng số bản' thay vì tạo mới.")
        return isbn

    def save(self, commit=True):
        book = super().save(commit=False)
        pub_name = self.cleaned_data.get('publisher_name', '').strip()
        if pub_name:
            publisher, _ = Publisher.objects.get_or_create(name__iexact=pub_name, defaults={'name': pub_name.title()})
            book.publisher = publisher
            
        if commit:
            book.save()
        return book

class ExcelImportForm(forms.Form):
    excel_file = forms.FileField(
        label='Chọn file Excel (.xlsx)',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx'})
    )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên thể loại', 'maxlength': '100'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Mô tả', 'maxlength': '1000'}),
        }
        
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name and ('<' in name or '>' in name):
            from django.core.exceptions import ValidationError
            raise ValidationError("Tên thể loại không được chứa ký tự đặc biệt (<, >).")
        return name

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and ('<' in description or '>' in description):
            from django.core.exceptions import ValidationError
            raise ValidationError("Mô tả không được chứa ký tự đặc biệt (<, >).")
        return description
