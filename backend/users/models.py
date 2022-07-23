from django.contrib.auth.models import AbstractUser
from django.db import models

USER = 'user'
ADMIN = 'admin'


class User(AbstractUser):
    USER_ROLE = (
        (USER, USER),
        (ADMIN, ADMIN)
    )
    username = models.CharField(
        max_length=150,
        unique=True,
    )
    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=150, verbose_name='Имя')
    last_name = models.CharField(max_length=150, verbose_name='Фамилия')
    role = models.CharField(max_length=25, choices=USER_ROLE, default=USER)

    @property
    def is_user(self):
        return self.role == USER

    @property
    def is_admin(self):
        return self.role == ADMIN

    def __str__(self):
        return self.username


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик'
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following_auth',
        verbose_name='Подписка'
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'following'),
                name='unique_followers'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('following')),
                name='not_sub'
            )
        ]
