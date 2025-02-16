from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Recipe, Ingredient, MealPlan, GroceryList, RecipeIngredient
from .serializers import (RecipeSerializer, IngredientSerializer, 
                         MealPlanSerializer, GroceryListSerializer)
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import logging
from urllib.request import urlopen
from recipe_scrapers import scrape_html
import openai
from bs4 import BeautifulSoup
import requests
import json
from django.conf import settings
from .services import RecipeExtractionService
from django.http import StreamingHttpResponse

logger = logging.getLogger(__name__)
client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

# Create your views here.

class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['title', 'prep_time', 'cook_time']

    def get_queryset(self):
        return Recipe.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def extract_from_url(self, request):
        """Extract recipe data from URL using scrapers with OpenAI fallback"""
        logger.info("=== Starting recipe extraction ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request path: {request.path}")
        logger.info(f"Request data: {request.data}")
        
        url = request.data.get('url')
        
        if not url:
            return Response(
                {'error': 'URL is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            URLValidator()(url)
        except ValidationError:
            return Response(
                {'error': 'Invalid URL format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        def stream_response():
            # Try recipe-scrapers first
            result = RecipeExtractionService.extract_with_scraper(url)
            
            if not result['success']:
                # Send intermediate status
                yield json.dumps({
                    'status': 'Recipe-Scraper Failed - Searching with OpenAI...',
                    'intermediate': True
                }) + '\n'
                
                # Try OpenAI
                result = RecipeExtractionService.extract_with_openai(url)
            
            if result['success']:
                try:
                    # Clean up the data before saving
                    recipe_data = result['data']
                    
                    # Clean up servings - ensure it's an integer
                    servings = recipe_data.get('servings')
                    if isinstance(servings, str):
                        # Extract numbers from string (e.g., "4 servings" -> 4)
                        try:
                            servings = int(''.join(filter(str.isdigit, servings)))
                        except ValueError:
                            servings = 1
                    elif not isinstance(servings, (int, float)):
                        servings = 1
                    else:
                        servings = int(servings)  # Convert float to int if needed

                    # Create recipe instance
                    recipe = Recipe.objects.create(
                        user=request.user,
                        title=recipe_data['title'],
                        description=recipe_data.get('description', ''),
                        instructions=recipe_data['instructions'],
                        prep_time=recipe_data.get('prep_time', 0),
                        cook_time=recipe_data.get('cook_time', 0),
                        servings=max(1, servings),  # Ensure at least 1 serving
                        source_url=url,
                        image_url=recipe_data.get('image_url') or None  # Convert empty string to None
                    )

                    # Process ingredients
                    for ingredient_text in recipe_data['ingredients']:
                        # Split ingredient text into parts
                        parts = ingredient_text.split(' ', 2)
                        
                        if len(parts) >= 3:
                            quantity, unit, name = parts
                        elif len(parts) == 2:
                            quantity, name = parts
                            unit = ''
                        else:
                            quantity = '1'
                            unit = ''
                            name = ingredient_text

                        # Convert quantity to decimal
                        try:
                            if '/' in quantity:
                                if ' ' in quantity:  # Mixed number like "1 1/2"
                                    whole, frac = quantity.split()
                                    num, denom = frac.split('/')
                                    quantity = float(whole) + float(num)/float(denom)
                                else:  # Simple fraction like "1/2"
                                    num, denom = quantity.split('/')
                                    quantity = float(num)/float(denom)
                            else:
                                quantity = float(quantity)
                        except (ValueError, ZeroDivisionError):
                            quantity = 1.0

                        # Create or get ingredient
                        ingredient, _ = Ingredient.objects.get_or_create(
                            name=name.strip()
                        )
                        
                        # Create recipe ingredient
                        RecipeIngredient.objects.create(
                            recipe=recipe,
                            ingredient=ingredient,
                            quantity=quantity,
                            unit=unit.strip()
                        )

                    # Add recipe ID and success status to response
                    recipe_data['id'] = recipe.id
                    recipe_data['status'] = (
                        'Successfully saved recipe using recipe-scraper!'
                        if recipe_data['source'] == 'recipe-scrapers'
                        else 'Successfully saved recipe using OpenAI!'
                    )
                    
                except Exception as e:
                    logger.error(f"Error saving recipe: {str(e)}")
                    recipe_data['save_error'] = str(e)

            # Ensure we always have a data key with at least error info
            if not result.get('data'):
                result['data'] = {
                    'error': result.get('error', 'Unknown error occurred'),
                    'status': 'Failed to extract recipe'
                }

            # Send final result
            yield json.dumps(result['data'])

        response = StreamingHttpResponse(
            streaming_content=stream_response(),
            content_type='application/json'
        )
        return response

    @action(detail=False, methods=['post'])
    def check_url_exists(self, request):
        """Check if a recipe with the given URL already exists"""
        url = request.data.get('url')
        
        if not url:
            return Response(
                {'error': 'URL is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            URLValidator()(url)
        except ValidationError:
            return Response(
                {'error': 'Invalid URL format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        existing_recipe = Recipe.objects.filter(user=request.user, source_url=url).first()
        
        if existing_recipe:
            return Response({
                'exists': True,
                'recipe': {
                    'id': existing_recipe.id,
                    'title': existing_recipe.title
                }
            })
        
        return Response({'exists': False})

class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [permissions.IsAuthenticated]

class MealPlanViewSet(viewsets.ModelViewSet):
    serializer_class = MealPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['date', 'meal_type']

    def get_queryset(self):
        return MealPlan.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class GroceryListViewSet(viewsets.ModelViewSet):
    serializer_class = GroceryListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GroceryList.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def generate_from_meal_plan(self, request, pk=None):
        grocery_list = self.get_object()
        # Add logic to generate grocery list from meal plan
        return Response({'status': 'Grocery list generated'})
