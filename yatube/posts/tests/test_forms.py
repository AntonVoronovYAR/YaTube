import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from ..models import Comment, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='NoNameClient')
        cls.authorized_client = Client()
        cls.guest_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовый текст'
        )
        cls.post = Post.objects.create(
            text='Первичный пост',
            author=cls.user,
            group=cls.group,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='LOL',
        )
        cls.small_gif = SMALL_GIF
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.form_data = {
            'text': cls.post.text,
            'group': cls.group.pk,
            'image': cls.uploaded,
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    # Комментарий для ревьювера:
    # Проверка создания картинки на соответсвующих страницах сайта
    # будет произведена путем добавления дополнительной проверки
    # контекста в test_views теста:
    # test_new_post_exist_at_expected_pages_with_correct_context
    def test_create_post_auth_user(self):
        """
        При создании поста авторизованным пользователем,
        формируется новая запись в базе данных
        """
        posts_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=self.form_data, follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)

    def test_create_post_guest_user(self):
        """
        При попытке создания поста неавторизованным пользователем
        пост не создается и происходит перенаправление на страницу login
        """
        posts_count = Post.objects.count()
        response = self.guest_client.post(
            reverse('posts:post_create'), data=self.form_data, follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/create/')
        self.assertEqual(Post.objects.count(), posts_count)

    def test_create_comment_guest_user(self):
        """Создавать комментарии могут только авторизованные пользователи"""
        response = self.guest_client.get(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id})
        )
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.id}/comment/'
        )

    def test_auth_user_edit_post_and_it_changes_in_base(self):
        """
        При редактировании поста авторизованным пользователем,
        изменения происходят и в базе данных
        """
        form_data = {
            'text': 'Отредактированный пост',
            'group': self.group.pk,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertTrue(
            Post.objects.filter(text='Отредактированный пост').exists()
        )

    def test_edit_post_changes_post_in_base_guest_user(self):
        """
        При редактировании поста неавторизованным пользователем,
        происходит перенаправление на страницу login
        """
        response = self.guest_client.post(
            reverse('posts:post_edit', kwargs={
                'post_id': self.post.id}), follow=True
        )
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.id}/edit/'
        )
