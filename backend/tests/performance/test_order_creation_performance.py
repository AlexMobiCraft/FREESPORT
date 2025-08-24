"""
Performance тесты создания заказов
"""
import pytest
import time
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.products.models import Category, Brand, Product

User = get_user_model()


class OrderCreationPerformanceTest(TestCase):
    """Тестирование производительности создания заказов"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()

        # Создаем пользователей
        cls.retail_user = User.objects.create_user(
            email="perf_retail@example.com", password="testpass123", role="retail"
        )
        cls.wholesale_user = User.objects.create_user(
            email="perf_wholesale@example.com",
            password="testpass123",
            role="wholesale_level1",
            company_name="Performance Test Company",
        )

        # Создаем товары для тестов
        cls.category = Category.objects.create(
            name="Performance Category", slug="performance-category"
        )
        cls.brand = Brand.objects.create(
            name="Performance Brand", slug="performance-brand"
        )

        cls.products = []
        for i in range(20):
            product = Product.objects.create(
                name=f"Performance Product {i}",
                slug=f"performance-product-{i}",
                category=cls.category,
                brand=cls.brand,
                retail_price=100.00 + i * 10,
                wholesale_level1_price=80.00 + i * 8,
                stock_quantity=100,
                min_order_quantity=1,
                is_active=True,
            )
            cls.products.append(product)

    def setUp(self):
        """Очищаем корзину перед каждым тестом"""
        self.client.force_authenticate(user=self.retail_user)
        self.client.delete("/api/v1/cart/clear/")

    def test_single_item_order_performance(self):
        """Производительность создания заказа с одним товаром"""
        self.client.force_authenticate(user=self.retail_user)

        # Добавляем товар в корзину
        self.client.post(
            "/api/v1/cart/items/", {"product": self.products[0].id, "quantity": 1}
        )

        # Создаем заказ и измеряем время
        start_time = time.time()

        order_data = {
            "delivery_address": "Test Address 123",
            "delivery_method": "courier",
            "payment_method": "card",
            "notes": "Performance test order",
        }
        response = self.client.post("/api/v1/orders/", order_data)

        end_time = time.time()
        response_time = end_time - start_time

        self.assertLess(
            response_time,
            1.0,
            f"Single item order creation time {response_time:.2f}s exceeds 1s limit",
        )
        self.assertEqual(response.status_code, 201)

        # Проверяем, что заказ создался корректно
        self.assertIn("id", response.data)
        self.assertEqual(len(response.data["items"]), 1)

    def test_multiple_items_order_performance(self):
        """Производительность создания заказа с несколькими товарами"""
        self.client.force_authenticate(user=self.retail_user)

        # Добавляем 5 разных товаров в корзину
        for i in range(5):
            self.client.post(
                "/api/v1/cart/items/", {"product": self.products[i].id, "quantity": 2}
            )

        # Создаем заказ
        start_time = time.time()

        order_data = {
            "delivery_address": "Multi-item Address",
            "delivery_method": "pickup",
            "payment_method": "cash",
        }
        response = self.client.post("/api/v1/orders/", order_data)

        end_time = time.time()
        response_time = end_time - start_time

        self.assertLess(
            response_time,
            1.5,
            f"Multi-item order creation time {response_time:.2f}s exceeds 1.5s limit",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data["items"]), 5)

    def test_b2b_order_performance(self):
        """Производительность создания B2B заказа"""
        self.client.force_authenticate(user=self.wholesale_user)

        # Добавляем товар с минимальным B2B количеством
        self.client.post(
            "/api/v1/cart/items/", {"product": self.products[0].id, "quantity": 10}
        )

        start_time = time.time()

        order_data = {
            "delivery_address": "B2B Business Address",
            "delivery_method": "transport",
            "payment_method": "bank_transfer",
            "notes": "B2B order performance test",
        }
        response = self.client.post("/api/v1/orders/", order_data)

        end_time = time.time()
        response_time = end_time - start_time

        self.assertLess(
            response_time,
            1.2,
            f"B2B order creation time {response_time:.2f}s exceeds 1.2s limit",
        )
        self.assertEqual(response.status_code, 201)

    def test_large_quantity_order_performance(self):
        """Производительность заказа с большим количеством"""
        self.client.force_authenticate(user=self.wholesale_user)

        # Добавляем товар с большим количеством
        self.client.post(
            "/api/v1/cart/items/", {"product": self.products[0].id, "quantity": 50}
        )

        start_time = time.time()

        order_data = {
            "delivery_address": "Large Quantity Address",
            "delivery_method": "transport",
            "payment_method": "bank_transfer",
        }
        response = self.client.post("/api/v1/orders/", order_data)

        end_time = time.time()
        response_time = end_time - start_time

        self.assertLess(
            response_time,
            1.5,
            f"Large quantity order creation time {response_time:.2f}s exceeds 1.5s limit",
        )
        self.assertEqual(response.status_code, 201)

    def test_order_calculation_performance(self):
        """Производительность расчета итогов заказа"""
        self.client.force_authenticate(user=self.retail_user)

        # Добавляем товары с разными ценами
        for i in range(10):
            self.client.post(
                "/api/v1/cart/items/",
                {"product": self.products[i].id, "quantity": i + 1},
            )

        start_time = time.time()

        order_data = {
            "delivery_address": "Calculation Test Address",
            "delivery_method": "courier",
            "payment_method": "card",
        }
        response = self.client.post("/api/v1/orders/", order_data)

        end_time = time.time()
        response_time = end_time - start_time

        self.assertLess(
            response_time,
            2.0,
            f"Order calculation time {response_time:.2f}s exceeds 2s limit",
        )
        self.assertEqual(response.status_code, 201)

        # Проверяем корректность расчетов
        self.assertGreater(float(response.data["total_amount"]), 0)
        self.assertEqual(len(response.data["items"]), 10)

    @pytest.mark.slow
    def test_concurrent_order_creation_performance(self):
        """Имитация одновременного создания заказов"""
        import threading
        import queue

        results_queue = queue.Queue()

        def create_order(user, product_id, result_queue):
            client = APIClient()
            client.force_authenticate(user=user)

            # Добавляем товар
            client.post("/api/v1/cart/items/", {"product": product_id, "quantity": 1})

            # Создаем заказ
            start_time = time.time()

            order_data = {
                "delivery_address": f"Concurrent Address {threading.current_thread().ident}",
                "delivery_method": "pickup",
                "payment_method": "cash",
            }
            response = client.post("/api/v1/orders/", order_data)

            end_time = time.time()
            response_time = end_time - start_time

            result_queue.put(
                {
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "thread_id": threading.current_thread().ident,
                }
            )

        # Создаем 5 потоков
        threads = []
        for i in range(5):
            user = self.retail_user if i % 2 == 0 else self.wholesale_user
            product_id = self.products[i].id

            thread = threading.Thread(
                target=create_order, args=(user, product_id, results_queue)
            )
            threads.append(thread)

        # Запускаем все потоки
        start_time = time.time()
        for thread in threads:
            thread.start()

        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Анализируем результаты
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        self.assertEqual(len(results), 5)

        # Все заказы должны создаться успешно
        for result in results:
            self.assertEqual(result["status_code"], 201)
            self.assertLess(
                result["response_time"],
                3.0,
                f"Concurrent order creation time exceeds 3s",
            )

        avg_response_time = sum(r["response_time"] for r in results) / len(results)

        print(f"Concurrent order creation results:")
        print(f"Total time: {total_time:.3f}s")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Max response time: {max(r['response_time'] for r in results):.3f}s")

    def test_order_database_queries_optimization(self):
        """Оптимизация запросов к БД при создании заказа"""
        from django.test.utils import override_settings
        from django.db import connection

        self.client.force_authenticate(user=self.retail_user)

        # Добавляем товар в корзину
        self.client.post(
            "/api/v1/cart/items/", {"product": self.products[0].id, "quantity": 2}
        )

        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            order_data = {
                "delivery_address": "Query Optimization Address",
                "delivery_method": "courier",
                "payment_method": "card",
            }
            response = self.client.post("/api/v1/orders/", order_data)

        queries_count = len(connection.queries)

        # Создание заказа не должно генерировать слишком много запросов
        self.assertLess(
            queries_count,
            20,
            f"Order creation generates too many DB queries: {queries_count}",
        )
        self.assertEqual(response.status_code, 201)

        print(f"Order creation database queries count: {queries_count}")

    def test_order_memory_usage(self):
        """Использование памяти при создании заказа"""
        import tracemalloc

        self.client.force_authenticate(user=self.retail_user)

        # Добавляем несколько товаров
        for i in range(5):
            self.client.post(
                "/api/v1/cart/items/", {"product": self.products[i].id, "quantity": 2}
            )

        tracemalloc.start()

        order_data = {
            "delivery_address": "Memory Test Address",
            "delivery_method": "pickup",
            "payment_method": "cash",
        }
        response = self.client.post("/api/v1/orders/", order_data)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_mb = peak / 1024 / 1024
        self.assertLess(
            memory_mb,
            40,
            f"Order creation memory usage {memory_mb:.2f}MB exceeds 40MB limit",
        )

        self.assertEqual(response.status_code, 201)

        print(f"Order creation memory usage: {memory_mb:.2f}MB")
