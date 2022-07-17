from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (Cart, Favorite, Ingredient,  # isort:skip
                            IngredientAmount, Recipe, Tag)
from users.models import Follow, User  # isort:skip


class UserCreateSerializers(UserSerializer):

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password')


class UserSerializers(UserSerializer):

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed'
        )

    def get_is_subscribed(self, instans):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(following=instans, user=user).exists()


class IngredientsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientAmountSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientAmount
        fields = ('id', 'name', 'measurement_unit', 'amount')


class TagSerializers(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class RecipeSerializers(serializers.ModelSerializer):

    author = UserSerializers(read_only=True)
    ingredients = IngredientAmountSerializer(
        source='ingredientamount',
        many=True,
        read_only=True
    )
    tags = TagSerializers(read_only=True, many=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def validate(self, data):
        ingredients = self.initial_data.get('ingredients')
        if not ingredients:
            raise ValidationError(
                {'ingredients': 'Необходимо ввести ингредиенты'}
            )
        ingredients_list = []
        for ingredient_value in ingredients:
            ingredient = get_object_or_404(Ingredient,
                                           id=ingredient_value['id'])
            if ingredient in ingredients_list:
                raise ValidationError(
                    {'ingredients': 'Ингридиенты должны быть уникальными'}
                )
            ingredients_list.append(ingredient)
            if int(ingredient_value['amount']) <= 0:
                raise ValidationError(
                    {'ingredients': 'Значение количества должно быть больше 0'}
                )
        data['ingredients'] = ingredients
        return data

    def validate_cooking_time(self, data):
        if data <= 0:
            raise ValidationError('Время приготовления не должно быть равно 0')
        return data

    def ingredients_create(self, ingredients_data, recipe):
        for ingredient in ingredients_data:
            IngredientAmount.objects.create(
                recipe=recipe,
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount')
            )

    def tags_create(self, recipe):
        tags_data = self.initial_data.get('tags')
        recipe.tags.set(tags_data)

    def create(self, validated_data):
        image = validated_data.pop('image')
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(image=image, **validated_data)
        self.ingredients_create(ingredients_data, recipe)
        self.tags_create(recipe)
        return recipe

    def update(self, instance, validated_data):
        instance.image = validated_data.get('image', instance.image)
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time',
            instance.cooking_time
        )
        instance.tags.clear()
        self.tags_create(instance)
        IngredientAmount.objects.filter(recipe=instance).delete()
        self.ingredients_create(validated_data.get('ingredients'), instance)
        instance.save()
        return instance

    def get_is_favorited(self, instans):
        if self.context['request'].user.is_anonymous:
            return False
        return Favorite.objects.filter(
            recipe=instans,
            user=self.context['request'].user
        ).exists()

    def get_is_in_shopping_cart(self, instans):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Cart.objects.filter(recipe=instans, user=user).exists()


class LiteRecipeSerializers(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FollowSerializers(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='following.id')
    email = serializers.ReadOnlyField(source='following.email')
    username = serializers.ReadOnlyField(source='following.username')
    first_name = serializers.ReadOnlyField(source='following.first_name')
    last_name = serializers.ReadOnlyField(source='following.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipe = serializers.SerializerMethodField()
    recipe_count = serializers.SerializerMethodField()

    class Meta:
        model = Follow
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipe',
            'recipe_count'
        )

    def get_is_subscribed(self, instans):
        user = self.context['request'].user
        return Follow.objects.filter(
            following=instans.following,
            user=user
        ).exists()

    def get_recipe(self, instans):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        queryset = Recipe.objects.filter(author=instans.following)
        if limit:
            queryset = queryset[:int(limit)]
        serializer = LiteRecipeSerializers(queryset, many=True)
        return serializer.data

    def get_recipe_count(self, instans):
        return Recipe.objects.filter(author=instans.following).count()
