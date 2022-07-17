
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from recipes.models import Ingredient, IngredientAmount, Recipe, Tag
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (FollowSerializers,  # isort:skip
                          IngredientsSerializer, LiteRecipeSerializers,
                          RecipeSerializers, TagSerializers, UserSerializers)
from .filters import RecipeFilters  # isort:skip
from .pagination import PageLimitPagination  # isort:skip
from .permissions import AdminOrReadOnly, AuthorOrReadOnly  # isort:skip
from users.models import Follow, User  # isort:skip


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializers
    pagination_class = PageLimitPagination
    fillter_class = RecipeFilters
    permission_classes = (AuthorOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        related = self.request.user.favorites
        object = related.filter(recipe=pk)
        if self.request.method == 'POST':
            return self.add_obj(related, object, pk)
        elif self.request.method == 'DELETE':
            return self.obj_delete(object)
        return None

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        related = self.request.user.carts
        object = related.filter(recipe=pk)
        if self.request.method == 'POST':
            return self.add_obj(related, object, pk)
        elif self.request.method == 'DELETE':
            return self.obj_delete(object)
        return None

    @action(
        methods=['GET'],
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        products_list = {}
        ingredients = IngredientAmount.objects.filter(
            recipe__carts__user=request.user
        ).values_list(
            'ingredient__name',
            'ingredient__measurement_unit',
            'amount'
        )
        for ingredient in ingredients:
            name = ingredient[0]
            if name not in products_list:
                products_list[name] = {
                    'measurement_unit': ingredient[1],
                    'amount': ingredient[2]
                }
            else:
                products_list[name]['amount'] += ingredient[2]
        final_list = (f"{name} - {value['amount']}"
                      f"{value['measurement_unit']}\n"
                      for name, value in products_list.items())
        response = HttpResponse(final_list, 'Content-Type: text/plain')
        response['Content-Disposition'] = ('attachment; '
                                           'filename="products_list.txt"')
        return response

    def add_obj(self, related, object, pk):
        if object.exists():
            return Response(
                {'errors': 'Рецепт уже добавлен.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        recipe = get_object_or_404(Recipe, id=pk)
        related.create(recipe=recipe)
        serializer = LiteRecipeSerializers(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def obj_delete(self, object):
        if object.exists():
            object.delete()
            return Response(
                {'errors': 'Рецепт удален.'},
                status=status.HTTP_204_NO_CONTENT
            )
        return Response(
            {'errors': 'Рецепт уже удален.'},
            status=status.HTTP_400_BAD_REQUEST
        )


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientsSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    permission_classes = (AdminOrReadOnly,)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializers
    permission_classes = (AdminOrReadOnly,)


class UserViewSet(UserViewSet):
    queryset = User.objects.all()
    pagination_class = PageLimitPagination
    serializer_class = UserSerializers

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        queryset = self.request.user.follower.all()
        page = self.paginate_queryset(queryset)
        serializer = FollowSerializers(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        permission_classes=(IsAuthenticated,),
        methods=['post']
    )
    def subscribe(self, request, id=None):
        user = self.request.user
        following = get_object_or_404(User, id=id)
        if following == user:
            return Response(
                {'errors': 'Вы не можете подписаться на себя'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if Follow.objects.filter(
            user=user,
            following=following
        ).exists():
            return Response(
                {'errors': 'Вы уже подписаны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        follow = Follow.objects.create(user=user, following=following)
        serializer = FollowSerializers(follow, context={'request': request})
        return Response(serializer.data)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id=None):
        user = self.request.user
        following = get_object_or_404(User, id=id)
        follow = Follow.objects.filter(user=user, following=following)
        if follow.exists():
            follow.delete()
            return Response({'ditail': 'Вы отписались'})
        return Response(
            {'errors': 'Вы не можете отписаться, т.к. не подписаны на автора'}
        )
