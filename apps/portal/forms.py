"""
Форми публічного кабінету клієнта.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.orders.models import Ticket
from apps.reviews.models import Review


User = get_user_model()


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'title', 'comment')
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f'{i}') for i in range(1, 6)]),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Коротко: що вам сподобалось чи ні',
                'maxlength': 120,
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Розкажіть детальніше про поїздку...',
            }),
        }


class SearchForm(forms.Form):
    """Пошук рейсу: звідки, куди, дата."""
    origin = forms.CharField(
        label='Звідки',
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Місто відправлення',
            'class': 'form-control form-control-lg',
        }),
    )
    destination = forms.CharField(
        label='Куди',
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Місто призначення',
            'class': 'form-control form-control-lg',
        }),
    )
    date = forms.DateField(
        label='Дата',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control form-control-lg',
        }),
        required=False,
    )


class ClientRegisterForm(forms.Form):
    """Реєстрація клієнта."""
    first_name = forms.CharField(label='Ім\'я', max_length=64)
    last_name = forms.CharField(label='Прізвище', max_length=64)
    email = forms.EmailField(label='Email')
    phone = forms.CharField(label='Телефон', max_length=20)
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput,
        min_length=8,
        help_text='Мінімум 8 символів. Не можна використовувати лише цифри або поширені паролі.',
    )
    password2 = forms.CharField(label='Повторіть пароль', widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Користувач з таким email вже зареєстрований.')
        return email

    def clean_password1(self):
        # Прокидаємо пароль через стандартні AUTH_PASSWORD_VALIDATORS:
        # MinimumLength, CommonPassword, NumericPassword, UserAttributeSimilarity.
        password = self.cleaned_data.get('password1')
        if password:
            # Створюємо тимчасовий User-обєкт для UserAttributeSimilarityValidator
            tmp = User(
                username=self.cleaned_data.get('email', ''),
                email=self.cleaned_data.get('email', ''),
                first_name=self.cleaned_data.get('first_name', ''),
                last_name=self.cleaned_data.get('last_name', ''),
            )
            try:
                validate_password(password, tmp)
            except DjangoValidationError as e:
                raise forms.ValidationError(list(e.messages))
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Паролі не співпадають.')
        return cleaned

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['email'],
            email=data['email'],
            password=data['password1'],
            first_name=data['first_name'],
            last_name=data['last_name'],
        )
        user.role = User.Role.CLIENT
        user.phone = data['phone']
        user.save(update_fields=['role', 'phone'])
        return user


class PassengerForm(forms.Form):
    """Дані одного пасажира."""
    last_name = forms.CharField(
        label='Прізвище',
        max_length=64,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    first_name = forms.CharField(
        label='Ім\'я',
        max_length=64,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    document_type = forms.ChoiceField(
        label='Документ',
        choices=Ticket.DocumentType.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    document_number = forms.CharField(
        label='Номер документа',
        max_length=40,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    price_type = forms.ChoiceField(
        label='Тип квитка',
        choices=Ticket.PriceType.choices,
        initial=Ticket.PriceType.ADULT,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    seat_number = forms.CharField(
        label='Місце',
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '—'}),
    )


class BookingContactForm(forms.Form):
    """Контактні дані замовника."""
    last_name = forms.CharField(
        label='Прізвище',
        max_length=64,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    first_name = forms.CharField(
        label='Ім\'я',
        max_length=64,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    phone = forms.CharField(
        label='Телефон',
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        label='Email',
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    boarding_stop = forms.IntegerField(widget=forms.HiddenInput)
    alighting_stop = forms.IntegerField(widget=forms.HiddenInput)
