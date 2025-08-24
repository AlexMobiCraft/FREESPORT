#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functional testing for Product Detail API 2.5 with real data
QA test to verify all requirements from AC
"""

import requests
import json
import sys
from decimal import Decimal


class ProductDetailAPITester:
    """Class for functional testing of Product Detail API"""
    
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, passed, details=""):
        """Test results logging"""
        result = "PASS" if passed else "FAIL"
        self.test_results.append({
            'test': test_name,
            'result': result,
            'details': details
        })
        print(f"{result} - {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def create_test_data(self):
        """Create test data via Django shell"""
        print("Creating test data...")
        
        script = '''
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings")
django.setup()

from apps.products.models import Product, Category, Brand
from apps.users.models import User
from decimal import Decimal

# Create brand
brand, _ = Brand.objects.get_or_create(
    slug="nike-test",
    defaults={
        "name": "Nike Test",
        "description": "Test sports brand"
    }
)

# Create category
category, _ = Category.objects.get_or_create(
    slug="football-boots",
    defaults={
        "name": "Football Boots",
        "description": "Football shoes"
    }
)

# Create product with full data
product, created = Product.objects.get_or_create(
    sku="NIKE-PHANTOM-GT2",
    defaults={
        "name": "Nike Phantom GT2 Elite FG",
        "slug": "nike-phantom-gt2-elite-fg",
        "brand": brand,
        "category": category,
        "description": "Professional football boots for firm ground",
        "short_description": "Professional Nike Phantom GT2 football boots",
        "retail_price": Decimal("18999.00"),
        "opt1_price": Decimal("15999.00"),
        "opt2_price": Decimal("14999.00"),
        "opt3_price": Decimal("13999.00"),
        "trainer_price": Decimal("12999.00"),
        "federation_price": Decimal("11999.00"),
        "recommended_retail_price": Decimal("20999.00"),
        "max_suggested_retail_price": Decimal("22999.00"),
        "stock_quantity": 50,
        "min_order_quantity": 1,
        "specifications": {
            "Upper Material": "Synthetic leather FlyTouch Lite",
            "Sole": "Chevron and bladed studs for firm ground",
            "Sizes": "39, 40, 41, 42, 43, 44, 45",
            "Color": "Blue/Silver/Black",
            "Weight": "210g (size 43)",
            "Technologies": "Phantom GT2, FlyTouch Lite, All Conditions Control"
        },
        "gallery_images": [
            "https://static.nike.com/a/images/t_PDP_1728_v1/f_auto,q_auto:eco/phantom-gt2-1.jpg",
            "https://static.nike.com/a/images/t_PDP_1728_v1/f_auto,q_auto:eco/phantom-gt2-2.jpg",
            "https://static.nike.com/a/images/t_PDP_1728_v1/f_auto,q_auto:eco/phantom-gt2-3.jpg"
        ],
        "is_active": True,
        "is_featured": True
    }
)

# Create related products
related_product1, _ = Product.objects.get_or_create(
    sku="NIKE-MERCURIAL-VAPOR",
    defaults={
        "name": "Nike Mercurial Vapor 15 Elite FG",
        "slug": "nike-mercurial-vapor-15",
        "brand": brand,
        "category": category,
        "description": "Speed football boots",
        "short_description": "Speed game boots",
        "retail_price": Decimal("16999.00"),
        "trainer_price": Decimal("11999.00"),
        "stock_quantity": 30,
        "is_active": True
    }
)

related_product2, _ = Product.objects.get_or_create(
    sku="NIKE-TIEMPO-LEGEND",
    defaults={
        "name": "Nike Tiempo Legend 10 Elite FG",
        "slug": "nike-tiempo-legend-10",
        "brand": brand,
        "category": category,
        "description": "Classic leather boots",
        "short_description": "Premium leather boots",
        "retail_price": Decimal("19999.00"),
        "trainer_price": Decimal("13999.00"),
        "stock_quantity": 25,
        "is_active": True
    }
)

# Create test users
retail_user, _ = User.objects.get_or_create(
    email="retail@test.com",
    defaults={
        "first_name": "Ivan",
        "last_name": "Retail",
        "role": "retail",
        "is_verified": True
    }
)

trainer_user, _ = User.objects.get_or_create(
    email="trainer@test.com",
    defaults={
        "first_name": "Petr",
        "last_name": "Trainer",
        "role": "trainer",
        "is_verified": True
    }
)

b2b_user, _ = User.objects.get_or_create(
    email="wholesale@test.com",
    defaults={
        "first_name": "Andrey",
        "last_name": "Wholesale",
        "role": "wholesale_level2",
        "is_verified": True,
        "company_name": "Sports School Spartak"
    }
)

print(f"Product created: {product.name} (ID: {product.id})")
print(f"Related products: {related_product1.name}, {related_product2.name}")
print(f"Users created: retail, trainer, b2b")
'''
        
        import subprocess
        result = subprocess.run([
            'python', 'manage.py', 'shell', '-c', script
        ], cwd='backend', capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("Test data created successfully")
            print(result.stdout)
            return True
        else:
            print("Error creating test data:")
            print(result.stderr)
            return False
    
    def get_auth_token(self, email, password="testpass123"):
        """Get JWT token for user"""
        # First set password for user
        script = f'''
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings")
django.setup()

from apps.users.models import User
try:
    user = User.objects.get(email="{email}")
    user.set_password("{password}")
    user.save()
    print(f"Password set for {email}")
except User.DoesNotExist:
    print(f"User {email} not found")
'''
        
        import subprocess
        subprocess.run([
            'python', 'manage.py', 'shell', '-c', script
        ], cwd='backend', capture_output=True, text=True)
        
        # Now get token
        login_url = f"{self.base_url}/api/v1/auth/login/"
        response = self.session.post(login_url, json={
            "email": email,
            "password": password
        })
        
        if response.status_code == 200:
            token = response.json().get('access')
            return token
        else:
            print(f"Auth error for {email}: {response.text}")
            return None
    
    def test_ac1_product_detail_endpoint(self):
        """AC1: GET /products/{id}/ returns full product information"""
        print("\nAC1: Testing main Product Detail API endpoint")
        
        product_id = self.get_test_product_id()
        if not product_id:
            self.log_test("AC1: Product Detail Endpoint", False, "Failed to get product ID")
            return
        
        url = f"{self.base_url}/api/v1/products/{product_id}/"
        response = self.session.get(url)
        
        if response.status_code != 200:
            self.log_test("AC1: Product Detail Endpoint", False, f"Status: {response.status_code}")
            return
        
        data = response.json()
        
        # Check required fields
        required_fields = [
            'id', 'name', 'slug', 'sku', 'brand', 'category',
            'description', 'current_price', 'stock_quantity',
            'specifications', 'images', 'related_products',
            'category_breadcrumbs'
        ]
        
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            self.log_test("AC1: Product Detail Endpoint", False, f"Missing fields: {missing_fields}")
        else:
            self.log_test("AC1: Product Detail Endpoint", True, f"All required fields present")
            
        # Additional data structure check
        if 'specifications' in data and isinstance(data['specifications'], dict):
            self.log_test("AC1: Specifications Structure", True, f"Specifications: {len(data['specifications'])} fields")
        else:
            self.log_test("AC1: Specifications Structure", False, "Invalid specifications structure")
    
    def test_ac2_role_based_pricing(self):
        """AC2: RRP/MSRP displayed for B2B users"""
        print("\nAC2: Testing role-based pricing")
        
        product_id = self.get_test_product_id()
        if not product_id:
            return
        
        url = f"{self.base_url}/api/v1/products/{product_id}/"
        
        # Test without auth (retail price)
        response = self.session.get(url)
        if response.status_code == 200:
            data = response.json()
            retail_price = data.get('current_price')
            self.log_test("AC2: Unauthenticated user", True, f"Retail price: {retail_price}")
        
        # Test B2B user
        b2b_token = self.get_auth_token("wholesale@test.com")
        if b2b_token:
            headers = {'Authorization': f'Bearer {b2b_token}'}
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                rrp = data.get('recommended_retail_price')
                msrp = data.get('max_suggested_retail_price')
                
                if rrp and msrp:
                    self.log_test("AC2: B2B pricing", True, f"RRP: {rrp}, MSRP: {msrp}")
                else:
                    self.log_test("AC2: B2B pricing", False, "RRP/MSRP not displayed for B2B")
        
        # Test trainer
        trainer_token = self.get_auth_token("trainer@test.com")
        if trainer_token:
            headers = {'Authorization': f'Bearer {trainer_token}'}
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                trainer_price = data.get('current_price')
                discount = data.get('discount_percent')
                
                self.log_test("AC2: Trainer price", True, f"Price: {trainer_price}, Discount: {discount}%")
    
    def get_test_product_id(self):
        """Get test product ID"""
        script = '''
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings")
django.setup()

from apps.products.models import Product
try:
    product = Product.objects.get(sku="NIKE-PHANTOM-GT2")
    print(product.id)
except Product.DoesNotExist:
    print("NOT_FOUND")
'''
        
        import subprocess
        result = subprocess.run([
            'python', 'manage.py', 'shell', '-c', script
        ], cwd='backend', capture_output=True, text=True)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if output != "NOT_FOUND":
                return int(output)
        return None
    
    def run_all_tests(self):
        """Run all tests"""
        print("Starting functional testing of Product Detail API 2.5")
        print("=" * 60)
        
        # Create test data
        if not self.create_test_data():
            print("Failed to create test data. Testing aborted.")
            return
        
        # Run tests for each AC
        self.test_ac1_product_detail_endpoint()
        self.test_ac2_role_based_pricing()
        
        # Output summary
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed_tests = sum(1 for test in self.test_results if test['result'] == "PASS")
        total_tests = len(self.test_results)
        
        for test in self.test_results:
            print(f"{test['result']} - {test['test']}")
            if test['details']:
                print(f"    └─ {test['details']}")
        
        print(f"\nRESULT: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
        
        if passed_tests == total_tests:
            print("ALL TESTS PASSED SUCCESSFULLY!")
        else:
            print("ISSUES FOUND. REQUIRES FIXES.")


if __name__ == "__main__":
    tester = ProductDetailAPITester()
    
    try:
        response = requests.get("http://localhost:8001/api/v1/products/", timeout=5)
        print("Django server is available")
    except requests.exceptions.RequestException:
        print("Django server unavailable. Start server with:")
        print("cd backend && python manage.py runserver")
        sys.exit(1)
    
    tester.run_all_tests()