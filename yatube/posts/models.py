from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
MAX_TEXT_LEN: int = 15


class Group(models.Model):
    title = models.CharField(
        max_length=200, help_text='Заголовок группы')
    slug = models.SlugField(
        max_length=100, unique=True, help_text='Слаг группы')
    description = models.TextField(help_text='Описание группы')

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(help_text='Текст поста')
    pub_date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        help_text='Автор'
    )
    group = models.ForeignKey(
        Group,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='posts',
        help_text='Группа'
    )
    image = models.ImageField(
        upload_to='posts/',
        blank=True,
        help_text='Картинка'
    )

    def __str__(self):
        return self.text[:MAX_TEXT_LEN]


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        blank=True,
        null=False,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text='Пост'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text='Автор'
    )
    text = models.TextField(help_text='Текст комментария')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.text[:MAX_TEXT_LEN]


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        help_text='Пользователь'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        help_text='Автор'
    )

    def __str__(self):
        return 'Подписка'
