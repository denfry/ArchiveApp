# 📱 Гайд по созданию мобильного приложения для "Архив документов"

## 🎯 Обзор

Этот гайд покажет, как создать нативное мобильное приложение (Android/iOS), которое будет работать с вашим веб-сервером для сканирования QR-кодов и отображения информации о коробках.

## 📋 Варианты разработки

### Вариант 1: React Native (Рекомендуется - один код для Android и iOS)

### Вариант 2: Flutter (Dart)

### Вариант 3: Нативное Android (Kotlin/Java)

### Вариант 4: Нативное iOS (Swift)

---

## 🚀 Вариант 1: React Native (Рекомендуется)

### Преимущества:
- ✅ Один код для Android и iOS
- ✅ Быстрая разработка
- ✅ Большое сообщество
- ✅ Много готовых библиотек

### Шаг 1: Установка React Native

```bash
# Установка Node.js (если нет)
# Скачайте с nodejs.org

# Установка React Native CLI
npm install -g react-native-cli

# Установка Android Studio (для Android)
# Скачайте с developer.android.com/studio

# Установка Xcode (для iOS, только на Mac)
# Из App Store
```

### Шаг 2: Создание проекта

```bash
npx react-native init ArchiveApp
cd ArchiveApp
```

### Шаг 3: Установка зависимостей

```bash
npm install react-native-qrcode-scanner react-native-camera
npm install axios  # Для HTTP запросов
npm install @react-navigation/native @react-navigation/stack
```

### Шаг 4: Структура приложения

Создайте следующую структуру:

```
ArchiveApp/
├── src/
│   ├── screens/
│   │   ├── ScannerScreen.js      # Экран сканера QR
│   │   ├── BoxInfoScreen.js      # Информация о коробке
│   │   └── HomeScreen.js          # Главный экран
│   ├── services/
│   │   └── api.js                # API для работы с сервером
│   └── App.js                     # Главный компонент
├── package.json
└── ...
```

### Шаг 5: Код приложения

#### `src/services/api.js`

```javascript
import axios from 'axios';

// Замените на URL вашего развернутого сайта
const BASE_URL = 'https://your-app.railway.app';

export const api = {
  // Получить информацию о коробке
  getBoxInfo: async (boxId) => {
    try {
      const response = await axios.get(`${BASE_URL}/box/${boxId}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }
};
```

#### `src/screens/ScannerScreen.js`

```javascript
import React, { useState } from 'react';
import { View, Text, StyleSheet, Alert } from 'react-native';
import QRCodeScanner from 'react-native-qrcode-scanner';
import { RNCamera } from 'react-native-camera';
import { useNavigation } from '@react-navigation/native';
import { api } from '../services/api';

export default function ScannerScreen() {
  const navigation = useNavigation();
  const [scanned, setScanned] = useState(false);

  const onSuccess = async (e) => {
    if (scanned) return;
    setScanned(true);

    const url = e.data;

    // Извлекаем ID коробки из URL
    const boxIdMatch = url.match(/\/box\/([^/?]+)/);
    if (boxIdMatch) {
      const boxId = boxIdMatch[1];

      // Переходим на экран с информацией о коробке
      navigation.navigate('BoxInfo', { boxId });
    } else {
      Alert.alert('Ошибка', 'Неверный формат QR-кода');
      setScanned(false);
    }
  };

  return (
    <View style={styles.container}>
      <QRCodeScanner
        onRead={onSuccess}
        flashMode={RNCamera.Constants.FlashMode.off}
        topContent={
          <Text style={styles.centerText}>
            Наведите камеру на QR-код
          </Text>
        }
        bottomContent={
          <Text style={styles.textBold}>
            Сканирование QR-кода
          </Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centerText: {
    flex: 1,
    fontSize: 18,
    padding: 32,
    color: '#777',
  },
  textBold: {
    fontWeight: '500',
    color: '#000',
  },
});
```

#### `src/screens/BoxInfoScreen.js`

```javascript
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { api } from '../services/api';

export default function BoxInfoScreen({ route }) {
  const { boxId } = route.params;
  const [boxInfo, setBoxInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadBoxInfo();
  }, []);

  const loadBoxInfo = async () => {
    try {
      setLoading(true);
      // Используем JSON API
      const response = await fetch(`https://your-app.railway.app/api/box/${boxId}`);
      if (!response.ok) {
        throw new Error('Не удалось загрузить информацию');
      }
      const data = await response.json();
      setBoxInfo(data);
      setLoading(false);
    } catch (error) {
      Alert.alert('Ошибка', 'Не удалось загрузить информацию');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text>Загрузка...</Text>
      </View>
    );
  }

  if (!boxInfo) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text>Загрузка...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>📦 {boxInfo.name}</Text>
        <Text style={styles.subtitle}>ID: {boxInfo.id}</Text>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Расположение</Text>
          <Text style={styles.sectionText}>{boxInfo.location}</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Категория</Text>
          <Text style={styles.sectionText}>
            {boxInfo.category_descriptions.join(', ') || 'Не указана'}
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>
            Документы ({boxInfo.documents_count})
          </Text>
          {boxInfo.documents.map((doc, index) => (
            <View key={index} style={styles.documentCard}>
              <Text style={styles.documentName}>{doc.name}</Text>
              <Text style={styles.documentInfo}>
                Номер: {doc.number || 'Не указан'}
              </Text>
              <Text style={styles.documentInfo}>
                Дата: {doc.date || 'Не указана'}
              </Text>
            </View>
          ))}
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 5,
    color: '#333',
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    marginBottom: 20,
  },
  section: {
    marginBottom: 20,
    padding: 15,
    backgroundColor: '#f8f9fa',
    borderRadius: 10,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#667eea',
    marginBottom: 8,
  },
  sectionText: {
    fontSize: 14,
    color: '#333',
  },
  documentCard: {
    padding: 12,
    marginBottom: 10,
    backgroundColor: '#fff',
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#667eea',
  },
  documentName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 5,
    color: '#333',
  },
  documentInfo: {
    fontSize: 12,
    color: '#666',
    marginTop: 3,
  },
});
```

#### `src/screens/HomeScreen.js`

```javascript
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';

export default function HomeScreen() {
  const navigation = useNavigation();

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.logo}>📦</Text>
        <Text style={styles.title}>Архив документов</Text>
        <Text style={styles.subtitle}>Система управления архивом</Text>
      </View>

      <View style={styles.buttons}>
        <TouchableOpacity
          style={styles.button}
          onPress={() => navigation.navigate('Scanner')}
        >
          <Text style={styles.buttonIcon}>📱</Text>
          <Text style={styles.buttonText}>Сканер QR-кодов</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#667eea',
    padding: 40,
    alignItems: 'center',
  },
  logo: {
    fontSize: 60,
    marginBottom: 10,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.9)',
  },
  buttons: {
    padding: 20,
  },
  button: {
    backgroundColor: '#667eea',
    padding: 20,
    borderRadius: 12,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  buttonIcon: {
    fontSize: 30,
    marginRight: 15,
  },
  buttonText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
});
```

#### `src/App.js`

```javascript
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import HomeScreen from './src/screens/HomeScreen';
import ScannerScreen from './src/screens/ScannerScreen';
import BoxInfoScreen from './src/screens/BoxInfoScreen';

const Stack = createStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen
          name="Home"
          component={HomeScreen}
          options={{ title: 'Архив документов' }}
        />
        <Stack.Screen
          name="Scanner"
          component={ScannerScreen}
          options={{ title: 'Сканер QR-кодов' }}
        />
        <Stack.Screen
          name="BoxInfo"
          component={BoxInfoScreen}
          options={{ title: 'Информация о коробке' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
```

### Шаг 6: Настройка разрешений

#### Android (`android/app/src/main/AndroidManifest.xml`)

```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.INTERNET" />
```

#### iOS (`ios/ArchiveApp/Info.plist`)

```xml
<key>NSCameraUsageDescription</key>
<string>Нужен доступ к камере для сканирования QR-кодов</string>
```

### Шаг 7: Запуск

```bash
# Android
npx react-native run-android

# iOS (только на Mac)
npx react-native run-ios
```

---

## 🔧 Вариант 2: Улучшение веб-сервера для API

Для работы с мобильным приложением лучше добавить JSON API. Добавьте в `web_server.py`:

```python
def do_GET(self):
    """Обработка GET запросов."""
    try:
        if self.path.startswith('/api/box/'):
            box_id = self.path.split('/api/box/')[1].split('?')[0]
            self.send_box_info_json(box_id)
        elif self.path.startswith('/box/'):
            box_id = self.path.split('/box/')[1].split('?')[0]
            self.send_box_info(box_id)
        # ... остальной код
```

И добавьте метод:

```python
def send_box_info_json(self, box_id):
    """Отправка информации о коробке в формате JSON."""
    try:
        box = self.manager.find_by_id(box_id)
        if not box:
            self.send_error(404, f"Коробка с ID {box_id} не найдена")
            return

        documents = self.manager.get_documents_in_box(box_id)

        data = {
            "id": box["ID"],
            "name": box["Название"],
            "type": box.get("Тип", "Коробка"),
            "shelf": box.get("Стеллаж", ""),
            "rack": box.get("Полка", ""),
            "category": box.get("Категория", ""),
            "documents": [
                {
                    "name": doc["Название"],
                    "number": doc.get("Номер документа", ""),
                    "date": doc.get("Дата подписания", ""),
                    "category": doc.get("Категория", "")
                }
                for doc in documents
            ]
        }

        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    except Exception as e:
        logger.error(f"Ошибка получения информации о коробке: {e}")
        self.send_error(500, f"Ошибка: {str(e)}")
```

---

## 📱 Вариант 3: Простое решение - PWA (Уже реализовано)

Самое простое решение - использовать PWA, которое уже работает:

1. Разверните веб-сервер в облаке
2. Откройте на телефоне
3. Добавьте на главный экран
4. Готово!

**Преимущества:**
- ✅ Не нужно разрабатывать отдельное приложение
- ✅ Работает на Android и iOS
- ✅ Автоматические обновления
- ✅ Уже реализовано

---

## 🎯 Рекомендация

**Для вашего случая лучше всего использовать PWA**, которое уже реализовано:

1. Разверните веб-сервер в облаке (Railway, Render)
2. Откройте на телефоне
3. Добавьте на главный экран
4. Готово!

Если нужны дополнительные функции (офлайн-режим, push-уведомления), тогда можно создать нативное приложение.

---

## 📚 Дополнительные ресурсы

- [React Native Documentation](https://reactnative.dev/)
- [Flutter Documentation](https://flutter.dev/)
- [Android Development](https://developer.android.com/)
- [iOS Development](https://developer.apple.com/ios/)

---

**Готово!** Теперь у вас есть все варианты для создания мобильного приложения! 📱
