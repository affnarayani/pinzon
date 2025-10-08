import json
import re # Import the re module for regex operations

# ANSI escape codes for colors
COLOR_RESET = "\033[0m"
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_MAGENTA = "\033[95m"

def count_products(json_file_path):
    products_with_details_and_images = 0
    products_with_details_only = 0
    products_with_images_only = 0
    products_without_details_and_images = 0

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            products = json.load(f) # Load the entire JSON array

        if not isinstance(products, list):
            print(f"{COLOR_RED}Error: Expected a JSON array in {json_file_path}, but got {type(products)}{COLOR_RESET}")
            return

        total_products = len(products)

        for product in products:
            # Refine has_product_details check to account for empty HTML tags or whitespace
            product_details_content = product.get('product_details', '').strip()
            # Remove HTML tags
            clean_product_details = re.sub(r'<[^>]+>', '', product_details_content).strip()
            has_product_details = bool(clean_product_details)
            
            # Check for at least one image URL (image_url_1, image_url_2, etc.)
            has_image_urls = False
            for i in range(1, 11): # Check for image_url_1 to image_url_10
                if product.get(f'image_url_{i}'):
                    has_image_urls = True
                    break

            if has_product_details and has_image_urls:
                products_with_details_and_images += 1
            elif has_product_details and not has_image_urls:
                products_with_details_only += 1
            elif not has_product_details and has_image_urls:
                products_with_images_only += 1
            elif not has_product_details and not has_image_urls:
                products_without_details_and_images += 1

    except FileNotFoundError:
        print(f"{COLOR_RED}Error: File not found at {json_file_path}{COLOR_RESET}")
        return
    except json.JSONDecodeError as e:
        print(f"{COLOR_RED}Error: Could not decode JSON from {json_file_path}. Details: {e}{COLOR_RESET}")
        return
    except Exception as e:
        print(f"{COLOR_RED}An unexpected error occurred: {e}{COLOR_RESET}")
        return

    print(f"{COLOR_MAGENTA}Total number of products: {COLOR_YELLOW}{total_products}{COLOR_RESET}")
    print(f"{COLOR_MAGENTA}Total number of products with product_details and at least one image URL: {COLOR_YELLOW}{products_with_details_and_images}{COLOR_RESET}")
    print(f"{COLOR_MAGENTA}Total number of products with product_details but without any image URL: {COLOR_YELLOW}{products_with_details_only}{COLOR_RESET}")
    print(f"{COLOR_MAGENTA}Total number of products without product_details but with at least one image URL: {COLOR_YELLOW}{products_with_images_only}{COLOR_RESET}")
    print(f"{COLOR_MAGENTA}Total number of products without product_details and without any image URL: {COLOR_YELLOW}{products_without_details_and_images}{COLOR_RESET}")

if __name__ == "__main__":
    count_products('mobile_phones.json')
