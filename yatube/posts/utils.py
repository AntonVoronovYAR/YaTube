from django.core.paginator import Paginator

POSTS_LIMIT: int = 10


def paginator_create(request, model_objects):
    paginator = Paginator(model_objects, POSTS_LIMIT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
