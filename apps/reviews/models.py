"""
моделі відгуків клієнтів про рейси.
один відгук на одного користувача для одного рейсу (UniqueConstraint).
можна залишити тільки після завершення поїздки (перевіряю у view).
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    """відгук клієнта про конкретний рейс."""

    trip = models.ForeignKey(
        'routes.Trip',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Рейс',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviews',
        verbose_name='Автор',
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        verbose_name='Замовлення',
    )

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оцінка',
    )
    title = models.CharField(max_length=120, blank=True, verbose_name='Заголовок')
    comment = models.TextField(blank=True, verbose_name='Коментар')

    is_published = models.BooleanField(default=True, verbose_name='Опубліковано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')

    class Meta:
        verbose_name = 'Відгук'
        verbose_name_plural = 'Відгуки'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['trip', 'user'],
                name='one_review_per_user_per_trip',
            ),
        ]

    def __str__(self):
        return f'{self.rating}★ {self.user} -> {self.trip}'

    @property
    def stars(self):
        return '★' * self.rating + '☆' * (5 - self.rating)
