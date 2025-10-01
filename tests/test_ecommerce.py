"""
Тесты для модуля электронной коммерции
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import uuid

from src.main import app

client = TestClient(app)


class TestTransactionScoring:
    """Тесты оценки транзакций"""
    
    def test_score_valid_transaction(self):
        """Тест оценки валидной транзакции"""
        request_data = {
            "amount": 5000.0,
            "currency": "RUB",
            "customer_id": str(uuid.uuid4()),
            "customer_email": "test@example.com",
            "ip_address": "192.168.1.1",
            "device_fingerprint": "fp_test_123"
        }
        
        response = client.post("/api/v1/ecommerce/score", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "risk_score" in data
        assert "decision" in data
        assert data["decision"] in ["APPROVE", "REVIEW", "DECLINE"]
        assert 0 <= data["risk_score"] <= 1000
        assert data["processing_time_ms"] < 300  # Должно быть быстро
    
    def test_score_high_risk_transaction(self):
        """Тест транзакции с высоким риском"""
        request_data = {
            "amount": 150000.0,  # Большая сумма
            "currency": "RUB",
            "customer_id": str(uuid.uuid4()),
            "customer_email": "suspicious@temp-mail.com",  # Подозрительный email
            "ip_address": "45.142.120.1",  # VPN/Proxy IP
            "device_fingerprint": "fp_blacklisted"  # Черный список
        }
        
        response = client.post("/api/v1/ecommerce/score", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["risk_tier"] in ["HIGH", "CRITICAL"]
        assert data["decision"] in ["REVIEW", "DECLINE"]
        assert len(data["risk_factors"]) > 0
    
    def test_missing_required_fields(self):
        """Тест с отсутствующими обязательными полями"""
        request_data = {
            "amount": 5000.0
            # Отсутствуют обязательные поля
        }
        
        response = client.post("/api/v1/ecommerce/score", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_invalid_amount(self):
        """Тест с невалидной суммой"""
        request_data = {
            "amount": -100.0,  # Отрицательная сумма
            "currency": "RUB",
            "customer_id": str(uuid.uuid4()),
            "customer_email": "test@example.com",
            "ip_address": "192.168.1.1"
        }
        
        response = client.post("/api/v1/ecommerce/score", json=request_data)
        assert response.status_code == 422


class TestReturnAbuse:
    """Тесты обнаружения злоупотребления возвратами"""
    
    def test_check_normal_return(self):
        """Тест нормального возврата"""
        request_data = {
            "customer_id": str(uuid.uuid4()),
            "order_id": str(uuid.uuid4()),
            "items": [{"product_id": "123", "price": 1000}],
            "reason": "Не подошел размер",
            "return_amount": 1000.0,
            "days_since_purchase": 5
        }
        
        response = client.post("/api/v1/ecommerce/return-abuse/check", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["classification"] == "NORMAL"
        assert data["recommendation"] == "APPROVE"
    
    def test_serial_returner_detection(self):
        """Тест обнаружения серийного возвратчика"""
        request_data = {
            "customer_id": "serial_returner_123",
            "order_id": str(uuid.uuid4()),
            "items": [{"product_id": "expensive_item", "price": 50000}],
            "reason": "Не понравилось",
            "return_amount": 50000.0,
            "days_since_purchase": 29  # Возврат в последний день
        }
        
        response = client.post("/api/v1/ecommerce/return-abuse/check", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "abuse_score" in data
        assert "indicators" in data


class TestPromoAbuse:
    """Тесты обнаружения злоупотребления промокодами"""
    
    def test_detect_multi_account_abuse(self):
        """Тест обнаружения множественных аккаунтов"""
        request_data = {
            "customer_id": str(uuid.uuid4()),
            "promo_code": "FIRST50",
            "device_fingerprint": "fp_shared_device",
            "email": "test+1@gmail.com",  # Email с модификатором
            "ip_address": "192.168.1.1"
        }
        
        response = client.post("/api/v1/ecommerce/promo-abuse/detect", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "risk_level" in data
        assert "signals" in data
        assert "linked_accounts" in data
    
    def test_legitimate_promo_use(self):
        """Тест легитимного использования промокода"""
        request_data = {
            "customer_id": str(uuid.uuid4()),
            "promo_code": "SALE20",
            "device_fingerprint": "fp_unique_" + str(uuid.uuid4()),
            "email": "legitimate@company.com",
            "ip_address": "85.26.146.100"
        }
        
        response = client.post("/api/v1/ecommerce/promo-abuse/detect", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation"] == "ALLOW"
        assert data["abuse_detected"] is False


class TestCustomerRiskProfile:
    """Тесты профиля риска клиента"""
    
    def test_get_customer_risk_profile(self):
        """Тест получения профиля риска клиента"""
        customer_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/ecommerce/customer/{customer_id}/risk-profile")
        
        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == customer_id
        assert "fraud_risk" in data
        assert "return_abuse_risk" in data
        assert "promo_abuse_risk" in data
        assert "overall_risk" in data
        assert "customer_lifetime_value" in data


class TestAnalytics:
    """Тесты аналитики"""
    
    def test_get_analytics_summary(self):
        """Тест получения аналитической сводки"""
        response = client.get("/api/v1/ecommerce/analytics/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert "fraud_prevention" in data
        assert "returns" in data
        assert "promo_abuse" in data
        assert "performance" in data
    
    def test_analytics_with_date_range(self):
        """Тест аналитики с диапазоном дат"""
        params = {
            "start_date": "2025-09-01T00:00:00Z",
            "end_date": "2025-09-30T23:59:59Z"
        }
        
        response = client.get("/api/v1/ecommerce/analytics/summary", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert data["period"]["start"] == params["start_date"]
        assert data["period"]["end"] == params["end_date"]


class TestPerformance:
    """Тесты производительности"""
    
    def test_response_time_under_300ms(self):
        """Тест времени ответа < 300мс"""
        import time
        
        request_data = {
            "amount": 5000.0,
            "currency": "RUB",
            "customer_id": str(uuid.uuid4()),
            "customer_email": "test@example.com",
            "ip_address": "192.168.1.1"
        }
        
        start_time = time.time()
        response = client.post("/api/v1/ecommerce/score", json=request_data)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) * 1000 < 300  # Менее 300мс
    
    def test_concurrent_requests(self):
        """Тест параллельных запросов"""
        import concurrent.futures
        
        def make_request():
            request_data = {
                "amount": 5000.0,
                "currency": "RUB",
                "customer_id": str(uuid.uuid4()),
                "customer_email": f"test_{uuid.uuid4()}@example.com",
                "ip_address": "192.168.1.1"
            }
            return client.post("/api/v1/ecommerce/score", json=request_data)
        
        # Запускаем 10 параллельных запросов
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]
        
        # Все должны быть успешными
        for response in results:
            assert response.status_code == 200


class TestIntegration:
    """Интеграционные тесты"""
    
    def test_end_to_end_fraud_detection(self):
        """Сквозной тест обнаружения мошенничества"""
        # 1. Создаем подозрительную транзакцию
        transaction_data = {
            "amount": 75000.0,
            "currency": "RUB",
            "customer_id": "suspicious_customer",
            "customer_email": "hack@temp-mail.ru",
            "ip_address": "45.142.120.1",  # VPN
            "device_fingerprint": "fp_suspicious",
            "shipping_address": {
                "country": "NG"  # Нигерия - высокий риск
            }
        }
        
        # 2. Оцениваем транзакцию
        response = client.post("/api/v1/ecommerce/score", json=transaction_data)
        assert response.status_code == 200
        
        result = response.json()
        assert result["decision"] in ["REVIEW", "DECLINE"]
        assert result["risk_tier"] in ["HIGH", "CRITICAL"]
        
        # 3. Проверяем профиль клиента
        profile_response = client.get(
            f"/api/v1/ecommerce/customer/suspicious_customer/risk-profile"
        )
        assert profile_response.status_code == 200
        
        profile = profile_response.json()
        assert profile["fraud_risk"]["score"] > 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
