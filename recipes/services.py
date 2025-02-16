import logging
from urllib.request import urlopen, Request
from recipe_scrapers import scrape_html
import openai
from bs4 import BeautifulSoup
import requests
import json
from django.conf import settings

logger = logging.getLogger(__name__)
client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

class RecipeExtractionService:
    # Common headers to mimic a real browser
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    @staticmethod
    def extract_with_scraper(url):
        """Try to extract recipe data using recipe-scrapers"""
        try:
            logger.info(f"Attempting to use recipe-scrapers on {url}")
            req = Request(url, headers=RecipeExtractionService.HEADERS)
            html = urlopen(req).read().decode("utf-8")
            scraper = scrape_html(html, org_url=url)
            
            # Get image URL from scraper
            image_url = None
            try:
                image_url = scraper.image()
            except Exception as e:
                logger.warning(f"Failed to extract image: {str(e)}")

            data = {
                'success': True,
                'data': {
                    'title': scraper.title(),
                    'description': scraper.description() if hasattr(scraper, 'description') else '',
                    'ingredients': scraper.ingredients(),
                    'instructions': scraper.instructions(),
                    'prep_time': scraper.prep_time() if hasattr(scraper, 'prep_time') else None,
                    'cook_time': scraper.cook_time() if hasattr(scraper, 'cook_time') else None,
                    'total_time': scraper.total_time() if hasattr(scraper, 'total_time') else None,
                    'servings': scraper.yields() if hasattr(scraper, 'yields') else None,
                    'image_url': image_url,
                    'source': 'recipe-scrapers'
                }
            }
            logger.info("Successfully extracted recipe with recipe-scrapers")
            return data
            
        except Exception as e:
            logger.error(f"Recipe scraper failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def extract_with_openai(url):
        """Extract recipe data using OpenAI as fallback"""
        try:
            logger.info(f"Attempting to extract recipe with OpenAI from {url}")
            response = requests.get(url, headers=RecipeExtractionService.HEADERS)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Enhanced image extraction strategy
            image_url = None
            potential_images = []

            # 1. Look for images in common recipe image containers
            common_selectors = [
                'img.recipe-image', 'img.hero-image', 'img.featured-image',
                '.recipe-header img', '.hero img', '.featured img',
                '[itemprop="image"]', '[property="og:image"]',
                '.post-image img', '.entry-image img'
            ]

            for selector in common_selectors:
                try:
                    img = soup.select_one(selector)
                    if img and (img.get('src') or img.get('data-src')):
                        potential_images.append(img.get('src') or img.get('data-src'))
                except Exception:
                    continue

            # 2. Check Open Graph and Twitter meta tags
            meta_selectors = {
                'og:image': 'property',
                'twitter:image': 'name',
                'thumbnail': 'name'
            }

            for property_value, attr_name in meta_selectors.items():
                meta_tag = soup.find('meta', {attr_name: property_value})
                if meta_tag and meta_tag.get('content'):
                    potential_images.append(meta_tag.get('content'))

            # 3. Find all images and score them based on various criteria
            all_images = soup.find_all('img')
            scored_images = []
            regular_images = []

            for img in all_images:
                src = img.get('src') or img.get('data-src')
                if not src:
                    continue

                score = 0
                img_url = str(src).lower()  # Ensure src is a string
                
                # Score based on URL keywords
                keywords = ['recipe', 'food', 'dish', 'meal', 'hero', 'featured', 'main']
                score += sum(2 for keyword in keywords if keyword in img_url)
                
                # Score based on size attributes
                try:
                    width = int(img.get('width', 0))
                    height = int(img.get('height', 0))
                    if width > 300 and height > 300:
                        score += 3
                    if width > 500 and height > 500:
                        score += 2
                except (ValueError, TypeError):
                    pass

                # Score based on alt text
                alt_text = img.get('alt', '').lower()
                if any(keyword in alt_text for keyword in ['recipe', 'food', 'dish']):
                    score += 2

                # Score based on image filename
                if any(ext in img_url for ext in ['.jpg', '.jpeg', '.png']):
                    score += 1

                # Penalize likely non-recipe images
                if any(keyword in img_url for keyword in ['avatar', 'logo', 'icon', 'ad', 'banner']):
                    score -= 3

                if score > 0:
                    scored_images.append((str(src), score))  # Ensure src is a string
                else:
                    regular_images.append(str(src))  # Ensure src is a string

            # Combine and prioritize images
            if scored_images:
                scored_images.sort(key=lambda x: x[1], reverse=True)
                image_url = scored_images[0][0]
            elif regular_images:
                image_url = regular_images[0]
            elif potential_images:
                image_url = str(potential_images[0])  # Ensure string type

            # Clean and validate image URL
            if image_url:
                try:
                    # Skip validation for data URLs
                    if image_url.startswith('data:'):
                        image_url = None
                    else:
                        # Handle relative URLs
                        if str(image_url).startswith('//'):
                            image_url = 'https:' + image_url
                        elif str(image_url).startswith('/'):
                            image_url = '/'.join(url.split('/')[:3]) + image_url
                        
                        # Validate image URL
                        img_response = requests.head(image_url, headers=RecipeExtractionService.HEADERS, timeout=5)
                        if not img_response.ok or 'image' not in img_response.headers.get('content-type', ''):
                            image_url = None
                except Exception as e:
                    logger.warning(f"Image validation failed: {str(e)}")
                    image_url = None  # Reset invalid image URL

            logger.info(f"Image extraction result: {'Success' if image_url else 'Failed'}")

            # Clean up text content for OpenAI
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            text = ' '.join(line for line in lines if line)

            system_prompt = """You are a helpful assistant that extracts recipe information from web pages.
            Extract the following information and return it in JSON format. For all time values, return integers only (no text).
            If you can't determine a specific time value, use 0. All fields are required.

            {
                "title": "Recipe title (required)",
                "description": "Brief description of the recipe",
                "ingredients": ["list", "of", "ingredients"],
                "instructions": "Step by step cooking instructions",
                "prep_time": integer (minutes, required, use 0 if unknown),
                "cook_time": integer (minutes, required, use 0 if unknown),
                "total_time": integer (minutes, optional),
                "servings": integer (required, use 1 if unknown)
            }

            Example response:
            {
                "title": "Spaghetti Carbonara",
                "description": "Classic Italian pasta dish",
                "ingredients": ["400g spaghetti", "200g pancetta", "4 large eggs"],
                "instructions": "1. Cook pasta...\n2. Fry pancetta...",
                "prep_time": 10,
                "cook_time": 20,
                "total_time": 30,
                "servings": 4
            }

            Always return numeric values for times and servings, never text. Use 0 for unknown times."""

            logger.info("Sending content to OpenAI for analysis")
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract recipe information from this webpage: {text[:4000]}"}
                ],
                temperature=0.7,
            )

            recipe_data = json.loads(response.choices[0].message.content)
            
            # Validate and clean up the data
            recipe_data = {
                'title': recipe_data.get('title', 'Untitled Recipe'),
                'description': recipe_data.get('description', ''),
                'ingredients': recipe_data.get('ingredients', []),
                'instructions': recipe_data.get('instructions', ''),
                'prep_time': max(0, int(recipe_data.get('prep_time', 0))),
                'cook_time': max(0, int(recipe_data.get('cook_time', 0))),
                'total_time': max(0, int(recipe_data.get('total_time', 0))),
                'servings': max(1, int(recipe_data.get('servings', 1))),
                'source': 'openai',
                'image_url': image_url
            }

            logger.info("Successfully extracted recipe with OpenAI")
            return {
                'success': True,
                'data': recipe_data
            }

        except Exception as e:
            logger.error(f"OpenAI extraction failed: {str(e)}")
            return {'success': False, 'error': str(e), 'data': None}  # Add empty data

    @classmethod
    def extract_from_url(cls, url):
        """Extract recipe data using scrapers with OpenAI fallback"""
        logger.info(f"Starting recipe extraction from {url}")
        
        # Try recipe-scrapers first
        result = cls.extract_with_scraper(url)
        
        # If recipe-scrapers fails, try OpenAI
        if not result['success']:
            logger.info(f"Recipe scraper failed for {url}, trying OpenAI")
            # Send status update before trying OpenAI
            result['status'] = 'Recipe-Scraper Failed - Searching with OpenAI...'
            # Try OpenAI
            result = cls.extract_with_openai(url)
            
        if result['success']:
            logger.info(f"Successfully extracted recipe from {url} using {result['data']['source']}")
            result['data']['status'] = (
                'Successfully extracted recipe using recipe-scraper!'
                if result['data']['source'] == 'recipe-scrapers'
                else 'Successfully extracted recipe using OpenAI!'
            )
        else:
            logger.error(f"Both extraction methods failed for {url}")
            if 'data' not in result:
                result['data'] = {
                    'error': result.get('error', 'Unknown error occurred'),
                    'status': 'Failed to extract recipe'
                }
            
        return result 