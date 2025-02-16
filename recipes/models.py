from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.conf import settings
import openai
import requests
from bs4 import BeautifulSoup
import logging
import json

User = get_user_model()

logger = logging.getLogger(__name__)
client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

class Recipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructions = models.TextField()
    prep_time = models.IntegerField(
        help_text="Preparation time in minutes",
        validators=[MinValueValidator(0)],
        default=0
    )
    cook_time = models.IntegerField(
        help_text="Cooking time in minutes",
        validators=[MinValueValidator(0)],
        default=0
    )
    servings = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1
    )
    source_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @classmethod
    def from_url(cls, url, user):
        """Extract recipe data from URL using OpenAI"""
        try:
            # Fetch webpage content
            response = requests.get(url)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            text = ' '.join(line for line in lines if line)

            # Prepare prompt for OpenAI
            system_prompt = """You are a helpful assistant that extracts recipe information from web pages.
            Extract the following information in JSON format:
            - title: The recipe title
            - description: A brief description of the recipe
            - ingredients: An array of ingredients with quantities
            - instructions: Step by step cooking instructions
            - prep_time: Preparation time in minutes (integer)
            - cook_time: Cooking time in minutes (integer)
            - servings: Number of servings (integer)
            
            Format each ingredient as: "quantity unit ingredient"
            If any field is not found, use null."""

            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract recipe information from this webpage: {text[:4000]}"}
                ],
                temperature=0.7,
            )

            # Parse the response
            recipe_data = json.loads(response.choices[0].message.content)
            
            # Create recipe instance
            recipe = cls(
                user=user,
                title=recipe_data['title'],
                description=recipe_data.get('description', ''),
                instructions=recipe_data['instructions'],
                prep_time=recipe_data.get('prep_time', 0),
                cook_time=recipe_data.get('cook_time', 0),
                servings=recipe_data.get('servings', 1),
                source_url=url
            )
            recipe.save()

            # Process ingredients
            for ingredient_text in recipe_data['ingredients']:
                # Split ingredient text into parts
                parts = ingredient_text.split(' ', 2)
                if len(parts) >= 3:
                    quantity, unit, name = parts
                else:
                    quantity, unit, name = 1, 'unit', ingredient_text

                try:
                    quantity = float(quantity)
                except ValueError:
                    quantity = 1

                ingredient, created = Ingredient.objects.get_or_create(
                    name=name.strip()
                )
                
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    quantity=quantity,
                    unit=unit
                )

            return recipe, None

        except Exception as e:
            logger.error(f"Error extracting recipe from {url}: {str(e)}")
            return None, str(e)

class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, related_name='ingredients', on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=8, decimal_places=2)
    unit = models.CharField(max_length=50)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ['recipe', 'ingredient']

class MealPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    meal_type = models.CharField(max_length=20, choices=[
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack')
    ])
    servings = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'date', 'recipe', 'meal_type']

class GroceryList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class GroceryItem(models.Model):
    grocery_list = models.ForeignKey(GroceryList, related_name='items', on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=8, decimal_places=2)
    unit = models.CharField(max_length=50)
    purchased = models.BooleanField(default=False)
    notes = models.CharField(max_length=200, blank=True)
