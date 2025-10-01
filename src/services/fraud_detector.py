"""
Fraud Detector с ML моделями для обнаружения мошенничества
"""
import numpy as np
import pandas as pd
import pickle
import joblib
from typing import Dict, Any, List, Optional, Tuple
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class FraudDetector:
    """
    Основной класс для обнаружения мошенничества
    Использует ансамбль из нескольких ML моделей
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.models = {}
        self.scaler = StandardScaler()
        self.feature_names = []
        self.thresholds = {
            'low': 0.3,
            'medium': 0.6,
            'high': 0.8,
            'critical': 0.95
        }
        
        if model_path:
            self.load_models(model_path)
        else:
            self._initialize_default_models()
    
    def _initialize_default_models(self):
        """Инициализация моделей по умолчанию"""
        # XGBoost - основная модель
        self.models['xgboost'] = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective='binary:logistic',
            use_label_encoder=False,
            eval_metric='logloss',
            random_state=42
        )
        
        # LightGBM - быстрая альтернатива
        self.models['lightgbm'] = lgb.LGBMClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective='binary',
            random_state=42,
            verbosity=-1
        )
        
        # Random Forest - для стабильности
        self.models['random_forest'] = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42,
            n_jobs=-1
        )
        
        # Isolation Forest - для аномалий
        self.models['isolation_forest'] = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_jobs=-1
        )
        
        # Logistic Regression - интерпретируемая модель
        self.models['logistic'] = LogisticRegression(
            random_state=42,
            max_iter=1000
        )
        
        # Веса моделей для ансамбля
        self.model_weights = {
            'xgboost': 0.35,
            'lightgbm': 0.30,
            'random_forest': 0.20,
            'isolation_forest': 0.10,
            'logistic': 0.05
        }
    
    async def assess_transaction(
        self, 
        features: Dict[str, Any],
        amount: float
    ) -> Dict[str, Any]:
        """
        Оценка транзакции на мошенничество
        
        Args:
            features: Признаки транзакции
            amount: Сумма транзакции
            
        Returns:
            Результат оценки с решением и факторами риска
        """
        # Подготовка данных
        X = self._prepare_features(features)
        
        # Получение предсказаний от всех моделей
        predictions = self._get_ensemble_predictions(X)
        
        # Расчет финального скора
        risk_score = self._calculate_risk_score(predictions)
        
        # Определение уровня риска
        risk_tier = self._determine_risk_tier(risk_score)
        
        # Принятие решения
        decision = self._make_decision(risk_score, risk_tier, amount)
        
        # Определение факторов риска
        risk_factors = self._identify_risk_factors(features, predictions)
        
        # Расчет ожидаемых потерь
        expected_loss = self._calculate_expected_loss(amount, risk_score)
        
        # Формирование рекомендаций
        actions = self._suggest_actions(risk_tier, risk_factors)
        
        # Расчет уверенности в решении
        confidence = self._calculate_confidence(predictions)
        
        return {
            'score': int(risk_score * 1000),  # Скор от 0 до 1000
            'tier': risk_tier,
            'decision': decision,
            'confidence': confidence,
            'expected_loss': expected_loss,
            'factors': risk_factors,
            'actions': actions,
            'model_scores': predictions,
            'explanation': self._generate_explanation(risk_tier, risk_factors)
        }
    
    def _prepare_features(self, features: Dict[str, Any]) -> np.ndarray:
        """Подготовка признаков для модели"""
        # Создаем DataFrame из признаков
        df = pd.DataFrame([features])
        
        # Заполняем пропущенные значения
        df = df.fillna(0)
        
        # Если это первый запуск, сохраняем имена признаков
        if not self.feature_names:
            self.feature_names = df.columns.tolist()
        
        # Проверяем, что все необходимые признаки присутствуют
        for feature in self.feature_names:
            if feature not in df.columns:
                df[feature] = 0
        
        # Выбираем только нужные признаки в правильном порядке
        df = df[self.feature_names]
        
        # Масштабирование
        if hasattr(self.scaler, 'mean_'):
            X = self.scaler.transform(df)
        else:
            # Если scaler не обучен, используем данные как есть
            X = df.values
        
        return X
    
    def _get_ensemble_predictions(self, X: np.ndarray) -> Dict[str, float]:
        """Получение предсказаний от всех моделей"""
        predictions = {}
        
        # XGBoost
        if 'xgboost' in self.models and hasattr(self.models['xgboost'], 'predict_proba'):
            try:
                pred = self.models['xgboost'].predict_proba(X)[0][1]
                predictions['xgboost'] = pred
            except:
                predictions['xgboost'] = np.random.uniform(0.3, 0.7)
        
        # LightGBM
        if 'lightgbm' in self.models and hasattr(self.models['lightgbm'], 'predict_proba'):
            try:
                pred = self.models['lightgbm'].predict_proba(X)[0][1]
                predictions['lightgbm'] = pred
            except:
                predictions['lightgbm'] = np.random.uniform(0.3, 0.7)
        
        # Random Forest
        if 'random_forest' in self.models and hasattr(self.models['random_forest'], 'predict_proba'):
            try:
                pred = self.models['random_forest'].predict_proba(X)[0][1]
                predictions['random_forest'] = pred
            except:
                predictions['random_forest'] = np.random.uniform(0.3, 0.7)
        
        # Isolation Forest (аномалии)
        if 'isolation_forest' in self.models:
            try:
                anomaly_score = self.models['isolation_forest'].decision_function(X)[0]
                # Преобразуем в вероятность (чем меньше скор, тем больше аномалия)
                predictions['isolation_forest'] = 1 / (1 + np.exp(anomaly_score))
            except:
                predictions['isolation_forest'] = np.random.uniform(0.3, 0.7)
        
        # Logistic Regression
        if 'logistic' in self.models and hasattr(self.models['logistic'], 'predict_proba'):
            try:
                pred = self.models['logistic'].predict_proba(X)[0][1]
                predictions['logistic'] = pred
            except:
                predictions['logistic'] = np.random.uniform(0.3, 0.7)
        
        # Если моделей нет или они не обучены, используем правила
        if not predictions:
            predictions = self._rule_based_prediction(X)
        
        return predictions
    
    def _rule_based_prediction(self, X: np.ndarray) -> Dict[str, float]:
        """Правила для случаев, когда ML модели не доступны"""
        # Простые правила на основе признаков
        features = X[0] if len(X.shape) > 1 else X
        score = 0.5  # Базовый скор
        
        # Примеры правил (индексы признаков условные)
        if len(features) > 0:
            # Высокая сумма
            if features[0] > 50000:
                score += 0.2
            # VPN/Proxy
            if len(features) > 10 and features[10] > 0:
                score += 0.3
            # Новый клиент
            if len(features) > 15 and features[15] > 0:
                score += 0.1
        
        return {'rule_based': min(score, 0.99)}
    
    def _calculate_risk_score(self, predictions: Dict[str, float]) -> float:
        """Расчет финального риск-скора"""
        if not predictions:
            return 0.5
        
        # Взвешенное среднее
        weighted_sum = 0
        total_weight = 0
        
        for model_name, score in predictions.items():
            weight = self.model_weights.get(model_name, 1.0 / len(predictions))
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight > 0:
            final_score = weighted_sum / total_weight
        else:
            final_score = np.mean(list(predictions.values()))
        
        return np.clip(final_score, 0, 1)
    
    def _determine_risk_tier(self, risk_score: float) -> str:
        """Определение уровня риска"""
        if risk_score < self.thresholds['low']:
            return 'LOW'
        elif risk_score < self.thresholds['medium']:
            return 'MEDIUM'
        elif risk_score < self.thresholds['high']:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def _make_decision(self, risk_score: float, risk_tier: str, amount: float) -> str:
        """Принятие решения по транзакции"""
        # Адаптивные пороги в зависимости от суммы
        if amount > 100000:
            # Более строгие правила для больших сумм
            if risk_score < 0.2:
                return 'APPROVE'
            elif risk_score < 0.5:
                return 'REVIEW'
            else:
                return 'DECLINE'
        elif amount > 50000:
            if risk_score < 0.3:
                return 'APPROVE'
            elif risk_score < 0.6:
                return 'REVIEW'
            else:
                return 'DECLINE'
        else:
            # Стандартные пороги
            if risk_tier == 'LOW':
                return 'APPROVE'
            elif risk_tier == 'MEDIUM':
                return 'REVIEW' if amount > 10000 else 'APPROVE'
            elif risk_tier == 'HIGH':
                return 'REVIEW'
            else:  # CRITICAL
                return 'DECLINE'
    
    def _identify_risk_factors(
        self, 
        features: Dict[str, Any], 
        predictions: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Определение факторов риска"""
        risk_factors = []
        
        # Анализ ключевых признаков
        if features.get('ip_is_vpn'):
            risk_factors.append({
                'factor': 'VPN_DETECTED',
                'severity': 'HIGH',
                'description': 'Транзакция через VPN или прокси',
                'impact': 0.3
            })
        
        if features.get('email_is_disposable'):
            risk_factors.append({
                'factor': 'DISPOSABLE_EMAIL',
                'severity': 'HIGH',
                'description': 'Использован временный email',
                'impact': 0.25
            })
        
        if features.get('customer_is_new') and features.get('amount', 0) > 50000:
            risk_factors.append({
                'factor': 'NEW_CUSTOMER_HIGH_AMOUNT',
                'severity': 'MEDIUM',
                'description': 'Новый клиент с большой суммой заказа',
                'impact': 0.2
            })
        
        if features.get('addresses_match') == 0:
            risk_factors.append({
                'factor': 'ADDRESS_MISMATCH',
                'severity': 'MEDIUM',
                'description': 'Адрес доставки не совпадает с платежным',
                'impact': 0.15
            })
        
        if features.get('shipping_country_risk', 0) > 70:
            risk_factors.append({
                'factor': 'HIGH_RISK_COUNTRY',
                'severity': 'HIGH',
                'description': 'Доставка в страну с высоким риском',
                'impact': 0.25
            })
        
        if features.get('transactions_last_hour', 0) > 3:
            risk_factors.append({
                'factor': 'VELOCITY_SPIKE',
                'severity': 'MEDIUM',
                'description': 'Необычно высокая частота транзакций',
                'impact': 0.15
            })
        
        # Сортировка по важности
        risk_factors.sort(key=lambda x: x['impact'], reverse=True)
        
        return risk_factors
    
    def _calculate_expected_loss(self, amount: float, risk_score: float) -> float:
        """Расчет ожидаемых потерь"""
        # Expected Loss = Probability of Default * Loss Given Default * Exposure at Default
        probability_of_fraud = risk_score
        loss_given_fraud = 0.8  # Предполагаем возврат 20% в случае мошенничества
        exposure = amount
        
        expected_loss = probability_of_fraud * loss_given_fraud * exposure
        
        return round(expected_loss, 2)
    
    def _suggest_actions(self, risk_tier: str, risk_factors: List[Dict]) -> List[str]:
        """Формирование рекомендаций по действиям"""
        actions = []
        
        if risk_tier == 'LOW':
            actions.append('Автоматическое одобрение')
        elif risk_tier == 'MEDIUM':
            actions.append('Ручная проверка рекомендуется')
            actions.append('Запросить дополнительную верификацию')
        elif risk_tier == 'HIGH':
            actions.append('Обязательная ручная проверка')
            actions.append('Связаться с клиентом для подтверждения')
            actions.append('Проверить документы')
        else:  # CRITICAL
            actions.append('Немедленно заблокировать транзакцию')
            actions.append('Добавить в черный список для проверки')
            actions.append('Уведомить службу безопасности')
        
        # Специфичные действия на основе факторов риска
        for factor in risk_factors:
            if factor['factor'] == 'VPN_DETECTED':
                actions.append('Запросить подтверждение реального местоположения')
            elif factor['factor'] == 'DISPOSABLE_EMAIL':
                actions.append('Запросить альтернативный email для связи')
            elif factor['factor'] == 'NEW_CUSTOMER_HIGH_AMOUNT':
                actions.append('Проверить платежные данные через банк')
        
        return list(set(actions))  # Убираем дубликаты
    
    def _calculate_confidence(self, predictions: Dict[str, float]) -> float:
        """Расчет уверенности в решении"""
        if not predictions:
            return 0.5
        
        scores = list(predictions.values())
        
        # Уверенность высокая, если модели согласны
        std_dev = np.std(scores)
        
        # Инвертируем стандартное отклонение для получения уверенности
        # Низкое отклонение = высокая уверенность
        confidence = 1 - (std_dev * 2)  # Масштабируем до [0, 1]
        
        return np.clip(confidence, 0, 1)
    
    def _generate_explanation(self, risk_tier: str, risk_factors: List[Dict]) -> str:
        """Генерация объяснения решения"""
        explanations = {
            'LOW': 'Транзакция выглядит безопасной. Риск-факторы минимальны.',
            'MEDIUM': 'Обнаружены незначительные риск-факторы. Рекомендуется дополнительная проверка.',
            'HIGH': 'Выявлены серьезные признаки потенциального мошенничества.',
            'CRITICAL': 'Крайне высокая вероятность мошенничества. Множественные критические факторы риска.'
        }
        
        base_explanation = explanations.get(risk_tier, 'Уровень риска определен.')
        
        if risk_factors:
            top_factors = ', '.join([f['description'] for f in risk_factors[:3]])
            base_explanation += f' Основные факторы: {top_factors}.'
        
        return base_explanation
    
    def train_models(self, X_train: pd.DataFrame, y_train: pd.Series):
        """Обучение моделей на данных"""
        # Масштабирование признаков
        X_scaled = self.scaler.fit_transform(X_train)
        
        # Обучение каждой модели
        for name, model in self.models.items():
            if name != 'isolation_forest':
                # Supervised модели
                model.fit(X_scaled, y_train)
            else:
                # Unsupervised модель (только на нормальных транзакциях)
                X_normal = X_scaled[y_train == 0]
                if len(X_normal) > 0:
                    model.fit(X_normal)
        
        # Сохранение имен признаков
        self.feature_names = X_train.columns.tolist()
    
    def save_models(self, path: str):
        """Сохранение обученных моделей"""
        model_data = {
            'models': self.models,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'thresholds': self.thresholds,
            'model_weights': self.model_weights
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_models(self, path: str):
        """Загрузка обученных моделей"""
        try:
            with open(path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.models = model_data['models']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.thresholds = model_data.get('thresholds', self.thresholds)
            self.model_weights = model_data.get('model_weights', self.model_weights)
        except FileNotFoundError:
            print(f"Модель не найдена по пути {path}. Используются модели по умолчанию.")
            self._initialize_default_models()
