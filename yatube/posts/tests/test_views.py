import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.urls import reverse
from django import forms

from ..models import Comment, Follow, Post, Group

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
PAGINATOR_POSTS_LEN: int = 10
SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='NoNameClient')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'
        )
        small_gif = SMALL_GIF
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='LOL',
        )
        cls.templates_pages_names = {
            reverse('posts:main_page'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': cls.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': cls.post.author}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': cls.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': cls.post.id}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон"""
        cache.clear()
        for reverse_name, template in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_home_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом"""
        cache.clear()
        response = self.authorized_client.get(reverse('posts:main_page'))
        expected = list(Post.objects.all()[:PAGINATOR_POSTS_LEN])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_group_list_show_correct_context(self):
        """Список постов в шаблоне group_list равен ожидаемому контексту"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        expected = list(Post.objects.filter(
            group_id=self.group.id)[:PAGINATOR_POSTS_LEN])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_profile_show_correct_context(self):
        """Список постов в шаблоне profile равен ожидаемому контексту."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.post.author})
        )
        expected = list(Post.objects.filter(
            author_id=self.user.id)[:PAGINATOR_POSTS_LEN])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом"""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context['post'].text, self.post.text)
        self.assertEqual(response.context['post'].author, self.post.author)
        self.assertEqual(response.context['post'].group, self.post.group)
        self.assertEqual(response.context['post'].image, self.post.image)

    def test_post_create_and_post_edit_show_correct_context(self):
        """
        Шаблон post_create и post_edit
        сформирован с правильным контекстом
        """
        responses = (
            self.authorized_client.get(reverse('posts:post_create')),
            self.authorized_client.get(
                reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField,
        }
        for response in responses:
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context['form'].fields[value]
                    self.assertIsInstance(form_field, expected)

    def test_new_post_exist_at_expected_pages(self):
        """
        Новый пост появляется на главной странице,
        странице группы и в профиле
        """
        cache.clear()
        responses = (
            self.authorized_client.get(reverse('posts:main_page')),
            self.authorized_client.get(
                reverse('posts:group_list', kwargs={'slug': self.group.slug})
            ),
            self.authorized_client.get(
                reverse('posts:profile', kwargs={'username': self.post.author})
            )
        )
        expected = self.post
        for response in responses:
            post_object = response.context['post']
            self.assertEqual(post_object, expected)

    def test_new_comment_exist_at_post_detail_page(self):
        """Новый комментарий появляется на странице информации о посте"""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        expected = self.comment
        comment_object = response.context['comments'].get(id=self.post.id)
        self.assertEqual(comment_object, expected)

    def test_cache_posts_on_main_page(self):
        """Проверка кэша на главной странице"""
        new_post = Post.objects.create(
            author=self.user,
            text='Просто текст',
            group=self.group,
        )
        response_1 = self.authorized_client.get(reverse('posts:main_page'))
        new_post.delete()
        response_2 = self.authorized_client.get(reverse('posts:main_page'))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:main_page'))
        self.assertNotEqual(response_2.content, response_3.content)


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='NoNameClient')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовый текст'
        )
        cls.post = [Post.objects.create(
            author=cls.user, text='Тестовое описание поста', group=cls.group)
            for _ in range(13)]

    def test_first_and_second_page_contains_expected_records(self):
        """
        Количество постов на первой странице main_page равно 10
        Количество постов на второй странице main_page равно 3
        """
        posts_count_number_pages = {
            10: {'page': 1},
            3: {'page': 2}
        }
        for post_count, number_page in posts_count_number_pages.items():
            with self.subTest(number_page=number_page):
                response = self.authorized_client.get(
                    reverse('posts:main_page'), number_page)
                self.assertEqual(
                    len(response.context['page_obj']), post_count
                )


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.another_user = User.objects.create_user(username='Anton')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.another_user,
        )

    def test_authorized_client_follow_and_unfollow(self):
        """
        Авторизованный пользователь может
        подписаться и отписаться от автора
        """
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.another_user.username})
        )
        self.assertTrue(Follow.objects.filter(
            user=self.user,
            author=self.another_user).exists()
        )
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.another_user.username}))
        self.assertFalse(Follow.objects.filter(
            user=self.user,
            author=self.another_user).exists()
        )

    def test_new_post_doesnt_shown_to_follower(self):
        """
        Новая запись пользователя не появляется
        в ленте тех, кто не подписан на него
        """
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(self.post, response.context['posts'])

    def test_new_post_shown_to_follower(self):
        """
        Новая запись пользователя появляется
        в ленте тех, кто подписан на него
        """
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.another_user.username}))
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn(self.post, response.context['posts'])
