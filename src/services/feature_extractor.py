"""
Feature Engineering для обнаружения мошенничества
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import hashlib
import re
from sklearn.preprocessing import StandardScaler, LabelEncoder
import ipaddress
import phonenumbers
from email_validator import validate_email, EmailNotValidError


class FeatureExtractor:
    """Извлечение признаков для ML моделей"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_cache = {}
        
    async def extract_transaction_features(
        self, 
        transaction_data: Dict[str, Any],
        customer_id: str,
        db: Any = None
    ) -> Dict[str, Any]:
        """
        Извлечение признаков из транзакции
        
        Returns:
            Словарь с признаками для модели
        """
        features = {}
        
        # 1. Базовые признаки транзакции
        features.update(self._extract_basic_features(transaction_data))
        
        # 2. Признаки клиента
        features.update(await self._extract_customer_features(customer_id, db))
        
        # 3. Признаки устройства
        features.update(self._extract_device_features(transaction_data))
        
        # 4. Признаки IP адреса
        features.update(self._extract_ip_features(transaction_data.get('ip_address')))
        
        # 5. Email признаки
        features.update(self._extract_email_features(transaction_data.get('customer_email')))
        
        # 6. Адресные признаки
        features.update(self._extract_address_features(
            transaction_data.get('shipping_address'),
            transaction_data.get('billing_address')
        ))
        
        # 7. Временные признаки
        features.update(self._extract_temporal_features())
        
        # 8. Velocity признаки (скорость/частота)
        features.update(await self._extract_velocity_features(customer_id, db))
        
        # 9. Поведенческие признаки
        features.update(await self._extract_behavioral_features(customer_id, transaction_data, db))
        
        # 10. Cross-features (взаимодействие признаков)
        features.update(self._extract_cross_features(features))
        
        return features
    
    def _extract_basic_features(self, transaction_data: Dict[str, Any]) -> Dict[str, float]:
        """Базовые признаки транзакции"""
        features = {
            'amount': float(transaction_data.get('amount', 0)),
            'amount_log': np.log1p(float(transaction_data.get('amount', 0))),
            'amount_sqrt': np.sqrt(float(transaction_data.get('amount', 0))),
            'currency_is_rub': 1 if transaction_data.get('currency') == 'RUB' else 0,
            'has_items': 1 if transaction_data.get('items') else 0,
            'items_count': len(transaction_data.get('items', [])),
        }
        
        # Статистика по товарам
        if transaction_data.get('items'):
            prices = [item.get('price', 0) for item in transaction_data['items']]
            features.update({
                'max_item_price': max(prices) if prices else 0,
                'min_item_price': min(prices) if prices else 0,
                'avg_item_price': np.mean(prices) if prices else 0,
                'std_item_price': np.std(prices) if prices else 0,
                'items_total_value': sum(prices),
            })
        
        return features
    
    async def _extract_customer_features(self, customer_id: str, db: Any) -> Dict[str, float]:
        """Признаки клиента из истории"""
        features = {}
        
        if not db:
            return self._get_default_customer_features()
        
        # Получаем историю клиента
        customer_stats = await self._get_customer_stats(customer_id, db)
        
        features.update({
            'customer_age_days': customer_stats.get('age_days', 0),
            'customer_total_orders': customer_stats.get('total_orders', 0),
            'customer_total_spent': customer_stats.get('total_spent', 0),
            'customer_avg_order_value': customer_stats.get('avg_order_value', 0),
            'customer_return_rate': customer_stats.get('return_rate', 0),
            'customer_chargeback_count': customer_stats.get('chargeback_count', 0),
            'customer_days_since_last_order': customer_stats.get('days_since_last_order', 999),
            'customer_order_frequency': customer_stats.get('order_frequency', 0),
            'customer_lifetime_value': customer_stats.get('lifetime_value', 0),
            'customer_risk_score': customer_stats.get('risk_score', 0),
            'customer_is_new': 1 if customer_stats.get('total_orders', 0) == 0 else 0,
            'customer_is_returning': 1 if customer_stats.get('total_orders', 0) > 0 else 0,
        })
        
        return features
    
    def _extract_device_features(self, transaction_data: Dict[str, Any]) -> Dict[str, float]:
        """Признаки устройства"""
        features = {}
        
        fingerprint = transaction_data.get('device_fingerprint', '')
        user_agent = transaction_data.get('user_agent', '')
        
        features.update({
            'has_device_fingerprint': 1 if fingerprint else 0,
            'device_fingerprint_length': len(fingerprint),
            'has_user_agent': 1 if user_agent else 0,
        })
        
        if user_agent:
            features.update(self._parse_user_agent(user_agent))
        
        return features
    
    def _extract_ip_features(self, ip_address: Optional[str]) -> Dict[str, float]:
        """Признаки IP адреса"""
        features = {
            'has_ip': 0,
            'ip_is_private': 0,
            'ip_is_vpn': 0,
            'ip_is_tor': 0,
            'ip_is_proxy': 0,
            'ip_risk_score': 0,
        }
        
        if not ip_address:
            return features
        
        features['has_ip'] = 1
        
        try:
            ip = ipaddress.ip_address(ip_address)
            features['ip_is_private'] = 1 if ip.is_private else 0
            
            # Проверка на VPN/Proxy (упрощенная)
            vpn_ranges = [
                '45.142.120.0/24',  # Известный VPN диапазон
                '104.200.0.0/13',   # Proxy диапазон
            ]
            
            for range_str in vpn_ranges:
                if ip in ipaddress.ip_network(range_str):
                    features['ip_is_vpn'] = 1
                    features['ip_risk_score'] = 75
                    break
            
            # Проверка на Tor exit nodes (упрощенная)
            tor_exits = ['185.220.101.0/24', '199.87.154.255/32']
            for tor_range in tor_exits:
                if ip in ipaddress.ip_network(tor_range):
                    features['ip_is_tor'] = 1
                    features['ip_risk_score'] = 90
                    break
                    
        except ValueError:
            features['ip_risk_score'] = 50  # Некорректный IP
        
        return features
    
    def _extract_email_features(self, email: Optional[str]) -> Dict[str, float]:
        """Признаки email адреса"""
        features = {
            'has_email': 0,
            'email_is_valid': 0,
            'email_is_disposable': 0,
            'email_has_plus': 0,
            'email_domain_risk': 0,
            'email_length': 0,
            'email_numbers_count': 0,
        }
        
        if not email:
            return features
        
        features['has_email'] = 1
        features['email_length'] = len(email)
        
        # Проверка валидности
        try:
            valid = validate_email(email)
            features['email_is_valid'] = 1
            email = valid.email
        except EmailNotValidError:
            features['email_is_valid'] = 0
            return features
        
        # Проверка на + в email (Gmail trick)
        if '+' in email.split('@')[0]:
            features['email_has_plus'] = 1
            features['email_domain_risk'] += 20
        
        # Подсчет цифр в email
        features['email_numbers_count'] = sum(c.isdigit() for c in email)
        
        # Проверка на временные email домены
        disposable_domains = [
            'tempmail.com', 'guerrillamail.com', '10minutemail.com',
            'maildrop.cc', 'mailinator.com', 'temp-mail.org',
            'throwaway.email', 'yopmail.com'
        ]
        
        domain = email.split('@')[1].lower()
        if any(disp in domain for disp in disposable_domains):
            features['email_is_disposable'] = 1
            features['email_domain_risk'] = 90
        
        # Риск по домену
        high_risk_tlds = ['.tk', '.ml', '.ga', '.cf']
        for tld in high_risk_tlds:
            if domain.endswith(tld):
                features['email_domain_risk'] = max(features['email_domain_risk'], 70)
        
        return features
    
    def _extract_address_features(
        self, 
        shipping_addr: Optional[Dict[str, Any]], 
        billing_addr: Optional[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Признаки адресов"""
        features = {
            'has_shipping_address': 1 if shipping_addr else 0,
            'has_billing_address': 1 if billing_addr else 0,
            'addresses_match': 0,
            'shipping_country_risk': 0,
            'billing_country_risk': 0,
            'address_distance_km': 0,
        }
        
        # Проверка совпадения адресов
        if shipping_addr and billing_addr:
            features['addresses_match'] = 1 if shipping_addr == billing_addr else 0
            
            # Расстояние между адресами (упрощенно)
            if not features['addresses_match']:
                features['address_distance_km'] = self._calculate_address_distance(
                    shipping_addr, billing_addr
                )
        
        # Риск по странам
        high_risk_countries = ['NG', 'GH', 'PK', 'ID', 'VN', 'BD']
        
        if shipping_addr and shipping_addr.get('country') in high_risk_countries:
            features['shipping_country_risk'] = 80
            
        if billing_addr and billing_addr.get('country') in high_risk_countries:
            features['billing_country_risk'] = 80
        
        return features
    
    def _extract_temporal_features(self) -> Dict[str, float]:
        """Временные признаки"""
        now = datetime.utcnow()
        
        features = {
            'hour_of_day': now.hour,
            'day_of_week': now.weekday(),
            'day_of_month': now.day,
            'is_weekend': 1 if now.weekday() >= 5 else 0,
            'is_night': 1 if now.hour < 6 or now.hour > 22 else 0,
            'is_business_hours': 1 if 9 <= now.hour <= 18 and now.weekday() < 5 else 0,
            'minutes_since_midnight': now.hour * 60 + now.minute,
        }
        
        # Циклические признаки для времени
        features['hour_sin'] = np.sin(2 * np.pi * now.hour / 24)
        features['hour_cos'] = np.cos(2 * np.pi * now.hour / 24)
        features['day_sin'] = np.sin(2 * np.pi * now.weekday() / 7)
        features['day_cos'] = np.cos(2 * np.pi * now.weekday() / 7)
        
        return features
    
    async def _extract_velocity_features(self, customer_id: str, db: Any) -> Dict[str, float]:
        """Velocity признаки (частота/скорость операций)"""
        features = {
            'transactions_last_hour': 0,
            'transactions_last_day': 0,
            'transactions_last_week': 0,
            'unique_cards_last_day': 0,
            'unique_ips_last_day': 0,
            'unique_devices_last_week': 0,
            'amount_velocity_1h': 0,
            'amount_velocity_24h': 0,
        }
        
        if not db:
            return features
        
        # Здесь должны быть запросы к БД для подсчета velocity
        # Это заглушка для примера структуры
        
        return features
    
    async def _extract_behavioral_features(
        self, 
        customer_id: str, 
        transaction_data: Dict[str, Any],
        db: Any
    ) -> Dict[str, float]:
        """Поведенческие признаки"""
        features = {
            'amount_deviation_from_avg': 0,
            'time_deviation_from_pattern': 0,
            'new_shipping_address': 0,
            'new_device': 0,
            'unusual_category': 0,
            'unusual_amount': 0,
        }
        
        if not db:
            return features
        
        # Получаем историю клиента
        customer_stats = await self._get_customer_stats(customer_id, db)
        
        # Отклонение суммы от среднего
        if customer_stats.get('avg_order_value'):
            current_amount = transaction_data.get('amount', 0)
            avg_amount = customer_stats['avg_order_value']
            features['amount_deviation_from_avg'] = abs(current_amount - avg_amount) / (avg_amount + 1)
            features['unusual_amount'] = 1 if features['amount_deviation_from_avg'] > 3 else 0
        
        return features
    
    def _extract_cross_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """Cross-features (взаимодействие признаков)"""
        cross_features = {}
        
        # Комбинации признаков
        cross_features['amount_x_risk'] = features.get('amount', 0) * features.get('customer_risk_score', 0)
        cross_features['new_customer_high_amount'] = (
            features.get('customer_is_new', 0) * features.get('amount', 0)
        )
        cross_features['vpn_new_customer'] = (
            features.get('ip_is_vpn', 0) * features.get('customer_is_new', 0)
        )
        cross_features['disposable_email_high_amount'] = (
            features.get('email_is_disposable', 0) * features.get('amount', 0)
        )
        
        # Ratios
        if features.get('customer_total_orders', 0) > 0:
            cross_features['amount_per_order_ratio'] = (
                features.get('amount', 0) / features.get('customer_total_orders', 1)
            )
        
        if features.get('customer_age_days', 0) > 0:
            cross_features['orders_per_day'] = (
                features.get('customer_total_orders', 0) / features.get('customer_age_days', 1)
            )
        
        return cross_features
    
    def _parse_user_agent(self, user_agent: str) -> Dict[str, float]:
        """Парсинг User-Agent"""
        features = {
            'ua_is_mobile': 1 if 'Mobile' in user_agent else 0,
            'ua_is_tablet': 1 if 'Tablet' in user_agent or 'iPad' in user_agent else 0,
            'ua_is_bot': 1 if 'bot' in user_agent.lower() else 0,
            'ua_is_chrome': 1 if 'Chrome' in user_agent else 0,
            'ua_is_firefox': 1 if 'Firefox' in user_agent else 0,
            'ua_is_safari': 1 if 'Safari' in user_agent and 'Chrome' not in user_agent else 0,
        }
        
        # Определение ОС
        if 'Windows' in user_agent:
            features['ua_os_windows'] = 1
        elif 'Mac OS' in user_agent or 'macOS' in user_agent:
            features['ua_os_mac'] = 1
        elif 'Linux' in user_agent:
            features['ua_os_linux'] = 1
        elif 'Android' in user_agent:
            features['ua_os_android'] = 1
        elif 'iOS' in user_agent or 'iPhone' in user_agent:
            features['ua_os_ios'] = 1
        
        return features
    
    def _calculate_address_distance(
        self, 
        addr1: Dict[str, Any], 
        addr2: Dict[str, Any]
    ) -> float:
        """Расчет расстояния между адресами (упрощенно)"""
        # В реальности нужно использовать геокодирование
        # Это упрощенная версия
        if addr1.get('country') != addr2.get('country'):
            return 1000  # Разные страны
        if addr1.get('city') != addr2.get('city'):
            return 100   # Разные города
        if addr1.get('postal_code') != addr2.get('postal_code'):
            return 10    # Разные почтовые индексы
        return 0
    
    async def _get_customer_stats(self, customer_id: str, db: Any) -> Dict[str, Any]:
        """Получение статистики клиента из БД"""
        # Заглушка - в реальности здесь должны быть запросы к БД
        return {
            'age_days': np.random.randint(0, 365),
            'total_orders': np.random.randint(0, 50),
            'total_spent': np.random.uniform(0, 100000),
            'avg_order_value': np.random.uniform(1000, 10000),
            'return_rate': np.random.uniform(0, 0.3),
            'chargeback_count': np.random.randint(0, 3),
            'days_since_last_order': np.random.randint(0, 180),
            'order_frequency': np.random.uniform(0, 5),
            'lifetime_value': np.random.uniform(0, 500000),
            'risk_score': np.random.randint(0, 100),
        }
    
    def _get_default_customer_features(self) -> Dict[str, float]:
        """Признаки по умолчанию для нового клиента"""
        return {
            'customer_age_days': 0,
            'customer_total_orders': 0,
            'customer_total_spent': 0,
            'customer_avg_order_value': 0,
            'customer_return_rate': 0,
            'customer_chargeback_count': 0,
            'customer_days_since_last_order': 999,
            'customer_order_frequency': 0,
            'customer_lifetime_value': 0,
            'customer_risk_score': 50,
            'customer_is_new': 1,
            'customer_is_returning': 0,
        }
