import tinytuya

# Ваші дані
api_key = 's8kgd7783ra4yv55rekc'
api_secret = '12a043df2e244305b608ee2f36938508'
uid = 'eu1711792688281YR0nr'

# 1. Створюємо об'єкт Cloud (мінімально)
# Використовуємо старий добрий спосіб аргументів по черзі
cloud = tinytuya.Cloud(region='eu', apiKey=api_key, apiSecret=api_secret, uid=uid)

# 2. Прямий запит до API Tuya в обхід методу getdevices()
# Це найнадійніший спосіб отримати список пристроїв
try:
    print("Виконую прямий запит до Tuya API...")
    # Запит списку пристроїв через шлях API
    path = f'/v1.0/users/{uid}/devices'
    result = cloud.request(path)
    
    print("РЕЗУЛЬТАТ:")
    if result and 'result' in result:
        for dev in result['result']:
            print(f"Знайдено: {dev['name']} (ID: {dev['id']})")
    else:
        print("Помилка або порожній результат:", result)
        
except Exception as e:
    print(f"Навіть прямий запит не вдався: {e}")