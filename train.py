import numpy as np
import pandas as pd
import xgboost as xgb
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# 1. Generación de dataset sintético realista (20,000 transacciones, ~2% fraude)
np.random.seed(42)
n_samples = 20000

monto = np.random.exponential(scale=80, size=n_samples)
hora = np.random.randint(0, 24, size=n_samples)
tx_ultimas_24h = np.random.poisson(lam=2, size=n_samples)
distancia_ubicacion_km = np.random.exponential(scale=15, size=n_samples)
es_internacional = np.random.binomial(1, 0.1, size=n_samples)

# Regla latente de fraude para que el modelo aprenda patrones reales
prob_fraude = (
    (monto > 300).astype(int) * 0.35 +
    ((hora >= 1) & (hora <= 5)).astype(int) * 0.25 +
    (tx_ultimas_24h > 5).astype(int) * 0.25 +
    (distancia_ubicacion_km > 100).astype(int) * 0.30 +
    es_internacional * 0.20
)
fraude = (prob_fraude + np.random.normal(0, 0.15, n_samples) > 0.65).astype(int)

df = pd.DataFrame({
    'monto': monto,
    'hora': hora,
    'tx_ultimas_24h': tx_ultimas_24h,
    'distancia_ubicacion_km': distancia_ubicacion_km,
    'es_internacional': es_internacional,
    'fraude': fraude
})

X = df.drop('fraude', axis=1)
y = df['fraude']

# 2. División Train / Test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# 3. Entrenamiento del modelo XGBoost ajustando desbalanceo (scale_pos_weight)
ratio_desbalance = float(np.sum(y_train == 0)) / np.sum(y_train == 1)
modelo = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.1,
    scale_pos_weight=ratio_desbalance,
    random_state=42,
    eval_metric='logloss'
)
modelo.fit(X_train, y_train)

# 4. Evaluación de métricas para el informe técnico
y_pred = modelo.predict(X_test)
print("=== MÉTRICAS DEL MODELO FRAUDGUARD AI (XGBOOST) ===")
print(f"Accuracy:  {accuracy_score(y_test, y_pred):.4f}")
print(f"Precision: {precision_score(y_test, y_pred):.4f}")
print(f"Recall:    {recall_score(y_test, y_pred):.4f}")
print(f"F1-Score:  {f1_score(y_test, y_pred):.4f}")

# 5. Guardar artefacto del modelo
joblib.dump(modelo, 'modelo_fraude.pkl')
print("\n[OK] Modelo guardado exitosamente como 'modelo_fraude.pkl'")