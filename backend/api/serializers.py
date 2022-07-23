from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.serializers import (CurrentUserDefault,
                                        UniqueTogetherValidator)

from recipes.models import (Cart, Favorite, Ingredient,  # isort:skip
                            IngredientAmount, Recipe, Tag)
from users.models import Follow  # isort:skip


User = get_user_model()


class UserCreateSerializers(UserCreateSerializer):

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password')
        extra_kwargs = {'password':{'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


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


class IngredientRecipeCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientAmount
        fields = ('id', 'amount')


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
    tags = TagSerializers(many=True, read_only=True)
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

    def get_is_favorited(self, instans):
        if self.context['request'].user.is_anonymous:
            return False
        return Favorite.objects.filter(
            recipe=instans,
            user=self.context['request'].user
        ).exists()

    def get_is_in_shopping_cart(self, instans):
        if self.context['request'].user.is_anonymous:
            return False
        return Cart.objects.filter(
            recipe=instans, 
            user=self.context['request'].user
        ).exists()


class RecipeCreateSerializers(serializers.ModelSerializer):

    author = UserSerializers(read_only=True)
    ingredients = IngredientRecipeCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def validate(self, data):
        ingredients = data['ingredients']
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Необходимо ввести ингредиенты'}
            )
        ingredients_list = []
        for ingredient_value in ingredients:
            ingredient_id = ingredient_value['id']
            if ingredient_id in ingredients_list:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингридиенты должны быть уникальными'}
                )
            ingredients_list.append(ingredient_id)
            if int(ingredient_value['amount']) <= 0:
                raise serializers.ValidationError(
                    {'ingredients': 'Значение количества должно быть больше 0'}
                )
        return data

    def validate_cooking_time(self, data):
        if data <= 0:
            raise serializers.ValidationError(
                'Время приготовления не должно быть равно 0'
            )
        return data

    def ingredients_create(self, ingredients_data, recipe):
        IngredientAmount.objects.bulk_create([IngredientAmount(
            recipe=recipe,
            ingredient=ingredient['id'],
            amount=ingredient['amount']
        ) for ingredient in ingredients_data])

    def create(self, validated_data):
        image = validated_data.pop('image')
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(image=image, **validated_data)
        recipe.tags.set(tags_data)
        self.ingredients_create(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        instance.tags.clear()
        tags_data = validated_data.pop('tags')
        instance.tags.set(tags_data)
        IngredientAmount.objects.filter(recipe=instance).delete()
        self.ingredients_create(validated_data.pop('ingredients'), instance)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = RecipeSerializers(
            instance,
            context={'request':self.context.get('request')}
        ).data
        return data


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
        recipes_limit = request.GET.get('recipes_limit')
        queryset = Recipe.objects.filter(author=instans.following)
        if recipes_limit:
            queryset = queryset[:int(recipes_limit)]
        serializer = LiteRecipeSerializers(queryset, many=True)
        return serializer.data

    def get_recipe_count(self, instans):
        return Recipe.objects.filter(author=instans.following).count()


class FollowCreateSerializers(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field='id',
        queryset=User.objects.all(), 
        default=CurrentUserDefault())
    following = serializers.SlugRelatedField(
        slug_field='id',
        queryset=User.objects.all())

    class Meta:
        model = Follow
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=('user', 'following'),
                message='Вы уже подписаны на автора'
            )
        ]

    def validate(self, data):
        if (data['user'] == data['following']
                and self.context['request'].method == 'POST'):
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя'
            )
        return data


class CartCreateSerializers(serializers.ModelSerializer):

    class Meta:
        model = Cart
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Cart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в списке продуктов'
            )
        ]

    def to_representation(self, instance):
        request = self.context.get('request')
        return LiteRecipeSerializers(
            instance.recipe,
            context={'request':request}
        ).data


class FavoriteCreateSerializers(serializers.ModelSerializer):

    class Meta:
        model = Favorite
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в избранном'
            )
        ]

    def to_representation(self, instance):
        request = self.context.get('request')
        return LiteRecipeSerializers(
            instance.recipe,
            context={'request':request}
        ).data
