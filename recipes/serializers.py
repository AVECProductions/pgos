from rest_framework import serializers
from .models import Recipe, Ingredient, RecipeIngredient, MealPlan, GroceryList, GroceryItem

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'description']

class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    
    class Meta:
        model = RecipeIngredient
        fields = ['id', 'ingredient', 'ingredient_name', 'quantity', 'unit', 'notes']

class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(many=True, read_only=True)
    
    class Meta:
        model = Recipe
        fields = ['id', 'title', 'description', 'instructions', 'prep_time', 
                 'cook_time', 'servings', 'source_url', 'image_url', 'ingredients',
                 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class MealPlanSerializer(serializers.ModelSerializer):
    recipe_title = serializers.CharField(source='recipe.title', read_only=True)
    
    class Meta:
        model = MealPlan
        fields = ['id', 'date', 'recipe', 'recipe_title', 'meal_type', 
                 'servings', 'notes', 'created_at']
        read_only_fields = ['created_at']

class GroceryItemSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    
    class Meta:
        model = GroceryItem
        fields = ['id', 'ingredient', 'ingredient_name', 'quantity', 
                 'unit', 'purchased', 'notes']

class GroceryListSerializer(serializers.ModelSerializer):
    items = GroceryItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = GroceryList
        fields = ['id', 'name', 'start_date', 'end_date', 'items', 
                 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at'] 