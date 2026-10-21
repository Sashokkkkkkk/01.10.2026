########################################################################
#   Подготовка окружения и загрузка данных
#   Импортируем базовые библиотеки для работы с данными и визуализации
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Настройка графиков
%matplotlib inline
sns.set_theme(style="whitegrid")

# 1. Загрузите датасет (укажите правильный путь к файлу, например 'churn.csv')
# ВАШ КОД ЗДЕСЬ:
df = pd.read_csv('churn.csv')

# 2. Выведите первые 5 строк датасета, чтобы убедиться, что он загрузился корректно
# ВАШ КОД ЗДЕСЬ:
df.head()
########################################################################
#   Разведочный анализ данных (EDA)
# 1. Выведите общую информацию о датасете (типы данных, количество строк, пропуски)
# ВАШ КОД ЗДЕСЬ:
df.info()

# 2. Проверьте баланс классов целевой переменной (столбец 'Exited' или 'Churn')
# Посчитайте, сколько клиентов ушло (1), а сколько осталось (0)
# ВАШ КОД ЗДЕСЬ:
df['Exited'].value_counts()

# 3. Визуализация: Постройте график распределения возраста (Age) для ушедших и оставшихся клиентов
plt.figure(figsize=(10, 5))
# ВАШ КОД ЗДЕСЬ (используйте sns.histplot или sns.kdeplot с параметром hue):
sns.histplot(data=df, x='Age', hue='Exited', multiple='stack', bins=30)
plt.title('Распределение возраста клиентов в зависимости от оттока')
plt.show()
########################################################################
#   Предобработка данных (Data Preprocessing)
# 1. Удаление неинформативных признаков (например, RowNumber, CustomerId, Surname)
# ВАШ КОД ЗДЕСЬ:
df_cleaned = df.drop(columns=['RowNumber', 'CustomerId', 'Surname'])

# 2. Обработка пропущенных значений (если они есть)
# ВАШ КОД ЗДЕСЬ (заполните пропуски медианой или удалите, если их мало):
# Подсказка: df_cleaned = df_cleaned.fillna(...)

# 3. Кодирование категориальных признаков (например, Geography, Gender) с помощью One-Hot Encoding
# ВАШ КОД ЗДЕСЬ:
df_encoded = pd.get_dummies(df_cleaned, columns=['Geography', 'Gender'], drop_first=True)

# Выведите обновленный вид таблицы
df_encoded.head()
########################################################################
#   Разделение данных на обучающую и тестовую выборки
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# 1. Отделите матрицу признаков X от целевого вектора y
# ВАШ КОД ЗДЕСЬ:
X = df_encoded.drop(columns=['Exited'])
y = df_encoded['Exited']

# 2. Разделите данные на train и test в соотношении 80:20 с random_state=42
# ВАШ КОД ЗДЕСЬ:
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# 3. Масштабирование признаков (StandardScaler)
scaler = StandardScaler()

# Обучите скалер на X_train и трансформируйте X_train и X_test
# ВАШ КОД ЗДЕСЬ:
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
########################################################################
#    Логистическая регрессия (Logistic Regression)
from sklearn.linear_model import LogisticRegression

# 1. Создайте объект модели логистической регрессии
# ВАШ КОД ЗДЕСЬ:
model_lr = LogisticRegression()

# 2. Обучите модель на масштабированных тренировочных данных
# ВАШ КОД ЗДЕСЬ:
model_lr.fit(X_train_scaled, y_train)

# 3. Сделайте предсказания на тестовых данных
# ВАШ КОД ЗДЕСЬ:
preds_lr = model_lr.predict(X_test_scaled)
########################################################################
#    Дерево решений (Decision Tree)
from sklearn.tree import DecisionTreeClassifier

# 1. Создайте объект дерева решений с ограничением максимальной глубины (например, max_depth=5)
# ВАШ КОД ЗДЕСЬ:
model_dt = DecisionTreeClassifier(max_depth=5, random_state=42)

# 2. Обучите дерево решений на масштабированных тренировочных данных
# ВАШ КОД ЗДЕСЬ:
model_dt.fit(X_train_scaled, y_train)

# 3. Сделайте предсказания на тестовых данных
# ВАШ КОД ЗДЕСЬ:
preds_dt = model_dt.predict(X_test_scaled)
########################################################################
#    Оценка качества моделей и выводы
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay

# 1. Выведите отчет о метриках (classification_report) для Логистической регрессии
print("Метрики для Логистической регрессии:")
# ВАШ КОД ЗДЕСЬ:
print(classification_report(y_test, preds_lr))

# 2. Выведите отчет о метриках (classification_report) для Дерева решений
print("\nМетрики для Дерева решений:")
# ВАШ КОД ЗДЕСЬ:
print(classification_report(y_test, preds_dt))

# 3. Визуализируйте матрицу ошибок (Confusion Matrix) для лучшей модели
# ВАШ КОД ЗДЕСЬ:
cm = confusion_matrix(y_test, preds_dt) # или preds_lr
ConfusionMatrixDisplay(confusion_matrix=cm).plot()
plt.title("Матрица ошибок")
plt.show()
