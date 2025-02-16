from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'recipes', views.RecipeViewSet, basename='recipe')
router.register(r'ingredients', views.IngredientViewSet, basename='ingredient')
router.register(r'meal-plans', views.MealPlanViewSet, basename='mealplan')
router.register(r'grocery-lists', views.GroceryListViewSet, basename='grocerylist')

urlpatterns = [
    path('', include(router.urls)),
] 