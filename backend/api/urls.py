from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (FollowViewSet, IngredientViewSet, RecipeViewSet,
                    TagViewSet, UserViewSet)

router = SimpleRouter()
router.register(r'recipes', RecipeViewSet, basename='recipe')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'users', UserViewSet, basename='user')
router.register(r'users/subscriptions', FollowViewSet, basename='subs')

urlpatterns = [
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
