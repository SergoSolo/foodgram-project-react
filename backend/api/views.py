from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from recipes.models import (Ingredient, IngredientAmount, Recipe,  # isort:skip
                            Tag)
from .serializers import (CartCreateSerializers,  # isort:skip
                          FavoriteCreateSerializers, FollowCreateSerializers,
                          FollowSerializers, IngredientsSerializer,
                          RecipeCreateSerializers,
                          RecipeSerializers, TagSerializers, UserSerializers)
from .filters import RecipeFilters, IngredientSearchFilter  # isort:skip
from .pagination import PageLimitPagination  # isort:skip
from .permissions import AdminOrReadOnly, AuthorOrReadOnly  # isort:skip
from users.models import Follow  # isort:skip


User = get_user_model()


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = PageLimitPagination
    fillter_class = RecipeFilters
    permission_classes = (AuthorOrReadOnly,)

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PATCH', 'PUT']:
            return RecipeCreateSerializers
        return RecipeSerializers

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request':self.request})
        return context

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        related = self.request.user.favorites
        related_obj = related.filter(recipe=pk)
        if self.request.method == 'POST':
            return self.create_obj(
                request, 
                FavoriteCreateSerializers, 
                pk
            )
        elif self.request.method == 'DELETE':
            return self.obj_delete(related_obj)
        return None

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        related = self.request.user.carts
        related_obj = related.filter(recipe=pk)
        if self.request.method == 'POST':
            return self.create_obj(
                request, related,
                CartCreateSerializers,
                pk
            )
        elif self.request.method == 'DELETE':
            return self.obj_delete(related_obj)
        return None

    @action(
        methods=['GET'],
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        products_buy = {}
        ingredients = IngredientAmount.objects.filter(
            recipe__carts__user=request.user
        ).order_by('ingredient__name').values_list(
            'ingredient__name', 
            'ingredient__measurement_unit'
        ).annotate(amount_total=Sum('amount'))  
        for ingredient in ingredients:
            name = ingredient[0]
            products_buy[name] = {
                'measurement_unit': ingredient[1],
                'amount': ingredient[2]
            }
        final_list = (f"{name} - {value['amount']}"
                      f"{value['measurement_unit']}\n"
                      for name, value in products_buy.items())
        response = HttpResponse(final_list, 'Content-Type: text/plain')
        response['Content-Disposition'] = ('attachment; '
                                           'filename="products_list.txt"')
        return response

    def create_obj(self, request, main_serializer, pk):
        user = self.request.user
        data = {
            'user': user.id,
            'recipe':pk
        }
        # recipe = get_object_or_404(Recipe, id=pk)
        serializer = main_serializer(data=data, context={'request':request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # related.create(recipe=recipe)
        # serializer = LiteRecipeSerializers(
        #     recipe, 
        #     context={'request':request}
        # )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def obj_delete(self, related_obj):
        related_obj.delete()
        return Response(
            {'detail':'Рецепт удален'},
            status=status.HTTP_204_NO_CONTENT
        )


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientsSerializer
    filter_backends = (IngredientSearchFilter,)
    search_fields = ('^name',)
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
        methods=['POST']
    )
    def subscribe(self, request, id=None):
        user = self.request.user
        following = get_object_or_404(User, id=id)
        data = {
            'user':user.id,
            'following':id
        }
        serializer = FollowCreateSerializers(
            data=data,
            context={'request':request}
        )
        serializer.is_valid(raise_exception=True)
        follow = Follow.objects.create(user=user, following=following)
        serializer = FollowSerializers(follow, context={'request':request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id=None):
        user = self.request.user
        following = get_object_or_404(User, id=id)
        Follow.objects.filter(user=user, following=following).delete()
        return Response(
            {'detail': 'Вы отписались'},
            status=status.HTTP_204_NO_CONTENT
        )
