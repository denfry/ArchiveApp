"""Веб-сервер для отображения информации о коробках через QR-коды."""
import http.server
import socketserver
import json
import logging
import os
import sqlite3
import urllib.parse
import html
from pathlib import Path

from data_manager import DataManager, get_category_description, get_app_dir

logger = logging.getLogger(__name__)


def get_base_url():
    """Получить базовый URL для QR-кодов."""
    # Проверяем переменные окружения (для Vercel, Railway и т.д.)
    base_url = os.environ.get('BASE_URL') or os.environ.get('VERCEL_URL')

    if base_url:
        # Если URL из переменной окружения, добавляем протокол
        if not base_url.startswith('http'):
            base_url = f'https://{base_url}'
        return base_url

    # Для локальной разработки
    return 'http://localhost:8080'


class BoxInfoHandler(http.server.SimpleHTTPRequestHandler):
    """Обработчик HTTP запросов для информации о коробках."""

    def __init__(self, *args, manager=None, **kwargs):
        self.manager = manager
        super().__init__(*args, **kwargs)

    def send_error(self, code, message=None, explain=None):
        """Переопределяем send_error для поддержки UTF-8."""
        try:
            # Получаем стандартные сообщения об ошибках
            if message is None:
                try:
                    message = self.responses.get(code, ['Unknown Error'])[0]
                except (AttributeError, KeyError, IndexError):
                    message = 'Unknown Error'
            if explain is None:
                try:
                    explain = self.responses.get(code, ['', ''])[1]
                except (AttributeError, KeyError, IndexError):
                    explain = ''

            # Экранируем HTML для безопасности
            msg_escaped = html.escape(str(message))
            exp_escaped = html.escape(str(explain)) if explain else ''

            # Формируем HTML ответ с ошибкой
            error_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ошибка {code}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }}
        .error-box {{
            background: white;
            color: #333;
            padding: 40px;
            border-radius: 15px;
            max-width: 600px;
            margin: 0 auto;
        }}
        h1 {{ color: #d32f2f; }}
    </style>
</head>
<body>
    <div class="error-box">
        <h1>Ошибка {code}</h1>
        <p>{msg_escaped}</p>
        {f'<p style="color: #666; font-size: 0.9em;">{exp_escaped}</p>' if exp_escaped else ''}
        <a href="/" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px;">На главную</a>
    </div>
</body>
</html>"""

            self.send_response(code, message)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(error_html.encode('utf-8'))
        except Exception as e:
            # Если не удалось отправить ошибку, пытаемся отправить простой текст
            try:
                self.send_response(code)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                error_msg = f"Error {code}: {str(message) if message else 'Unknown error'}"
                self.wfile.write(error_msg.encode('utf-8'))
            except:
                pass

    def do_GET(self):
        """Обработка GET запросов."""
        try:
            if self.path.startswith('/api/box/'):
                # JSON API для мобильного приложения
                box_id = self.path.split('/api/box/')[1].split('?')[0]
                self.send_box_info_json(box_id)
            elif self.path.startswith('/box/'):
                box_id = self.path.split('/box/')[1].split('?')[0]
                self.send_box_info(box_id)
            elif self.path == '/scanner' or self.path == '/scanner.html':
                self.send_scanner()
            elif self.path == '/' or self.path == '/index.html':
                self.send_index()
            elif self.path == '/manifest.json':
                self.send_manifest()
            elif self.path.startswith('/icon-'):
                self.send_icon(self.path)
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            logger.error(f"Ошибка обработки запроса: {e}")
            try:
                # Пытаемся отправить ошибку через наш переопределенный метод
                self.send_error(500, f"Internal Server Error: {str(e)}")
            except Exception as e2:
                # Если даже отправка ошибки не удалась, логируем
                logger.error(f"Критическая ошибка при отправке ошибки: {e2}")
                try:
                    # Последняя попытка - простой текст
                    self.send_response(500)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    error_msg = f"Error 500: {str(e)}"
                    self.wfile.write(error_msg.encode('utf-8'))
                except:
                    pass

    def send_manifest(self):
        """Отправка манифеста PWA."""
        try:
            app_dir = get_app_dir()
            manifest_path = os.path.join(app_dir, 'manifest.json')

            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(manifest_content.encode('utf-8'))
            else:
                self.send_error(404, "Manifest not found")
        except Exception as e:
            logger.error(f"Ошибка отправки манифеста: {e}")
            self.send_error(500, f"Error: {str(e)}")

    def send_icon(self, icon_path):
        """Отправка иконки."""
        try:
            app_dir = get_app_dir()
            # Пытаемся найти иконку
            icon_file = os.path.join(app_dir, icon_path.lstrip('/'))

            if os.path.exists(icon_file):
                with open(icon_file, 'rb') as f:
                    icon_data = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.end_headers()
                self.wfile.write(icon_data)
            else:
                # Если иконка не найдена, отправляем заглушку
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.end_headers()
                # Простая заглушка (1x1 прозрачный PNG)
                self.wfile.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
        except Exception as e:
            logger.error(f"Ошибка отправки иконки: {e}")
            self.send_error(500, f"Error: {str(e)}")

    def send_box_info_json(self, box_id):
        """Отправка информации о коробке в формате JSON для мобильного приложения."""
        try:
            # Получение информации о коробке
            box = self.manager.find_by_id(box_id)
            if not box:
                self.send_response(404)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Коробка с ID {box_id} не найдена"}, ensure_ascii=False).encode('utf-8'))
                return

            # Получение всех документов в коробке
            documents = self.manager.get_documents_in_box(box_id)

            # Формирование категорий
            category = box.get('Категория', '')
            category_descriptions = []
            if category:
                for cat in category.split(','):
                    cat = cat.strip()
                    desc = get_category_description(cat)
                    category_descriptions.append(desc)

            # Формирование расположения
            location_parts = []
            if box.get('Стеллаж'):
                location_parts.append(f"Стеллаж: {box['Стеллаж']}")
            if box.get('Полка'):
                location_parts.append(f"Полка: {box['Полка']}")
            location = ', '.join(location_parts) if location_parts else 'Не указано'

            # Формирование данных для JSON
            data = {
                "id": box["ID"],
                "name": box["Название"],
                "type": box.get("Тип", "Коробка"),
                "location": location,
                "shelf": box.get("Стеллаж", ""),
                "rack": box.get("Полка", ""),
                "category": category,
                "category_descriptions": category_descriptions,
                "documents_count": len(documents),
                "documents": [
                    {
                        "id": doc["ID"],
                        "name": doc["Название"],
                        "number": doc.get("Номер документа", ""),
                        "date": doc.get("Дата подписания", ""),
                        "category": doc.get("Категория", ""),
                        "category_description": get_category_description(doc.get("Категория", ""))
                    }
                    for doc in documents
                ]
            }

            # Отправка JSON ответа
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')  # Для CORS
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))

        except Exception as e:
            logger.error(f"Ошибка получения информации о коробке (JSON): {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode('utf-8'))

    def send_box_info(self, box_id):
        """Отправка информации о коробке."""
        try:
            # Получение информации о коробке
            box = self.manager.find_by_id(box_id)
            if not box:
                self.send_error(404, f"Коробка с ID {box_id} не найдена")
                return

            # Получение всех документов в коробке
            documents = self.manager.get_documents_in_box(box_id)

            # Генерация HTML
            html = self.generate_box_html(box, documents)

            # Отправка ответа
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))

        except Exception as e:
            logger.error(f"Ошибка получения информации о коробке: {e}")
            self.send_error(500, f"Ошибка: {str(e)}")

    def generate_box_html(self, box, documents):
        """Генерация HTML страницы с информацией о коробке."""
        # Получение категорий
        category = box.get('Категория', '')
        category_descriptions = []
        if category:
            for cat in category.split(','):
                cat = cat.strip()
                desc = get_category_description(cat)
                category_descriptions.append(desc)

        category_html = '<br>'.join(category_descriptions) if category_descriptions else 'Не указана'

        # Формирование расположения
        location_parts = []
        if box.get('Стеллаж'):
            location_parts.append(f"Стеллаж: {box['Стеллаж']}")
        if box.get('Полка'):
            location_parts.append(f"Полка: {box['Полка']}")
        location = ', '.join(location_parts) if location_parts else 'Не указано'

        # Формирование списка документов с улучшенным дизайном
        documents_html = ""
        if documents:
            # Добавляем поиск и фильтры
            documents_html = """
            <div class="documents-controls">
                <input type="text" id="searchDocs" placeholder="🔍 Поиск документов..." class="search-input">
                <select id="sortDocs" class="sort-select">
                    <option value="name">Сортировка: По названию</option>
                    <option value="number">По номеру документа</option>
                    <option value="date">По дате подписания</option>
                    <option value="category">По категории</option>
                </select>
            </div>
            <div class="documents-stats">
                <span>Всего документов: <strong>{}</strong></span>
            </div>
            <div class="documents-list">""".format(len(documents))

            for idx, doc in enumerate(documents):
                doc_category = get_category_description(doc.get('Категория', ''))
                doc_number = doc.get('Номер документа', 'Не указан')
                sign_date = doc.get('Дата подписания', 'Не указана')

                # Определяем иконку по категории
                icon = "📄"
                if "ТС" in doc_category or "ТО" in doc_category:
                    icon = "🔥"
                elif "ВО" in doc_category:
                    icon = "💧"
                elif "ВС" in doc_category:
                    icon = "🚰"
                elif "ЛК" in doc_category:
                    icon = "🌧️"
                elif "УУ" in doc_category:
                    icon = "📊"

                documents_html += f"""
                <div class="document-card" data-name="{doc['Название'].lower()}" data-number="{doc_number.lower()}" data-date="{sign_date.lower()}" data-category="{doc_category.lower()}">
                    <div class="doc-icon">{icon}</div>
                    <div class="doc-content">
                        <h3 class="doc-title">{doc['Название']}</h3>
                        <div class="doc-details">
                            <div class="doc-detail-item">
                                <span class="detail-label">Номер:</span>
                                <span class="detail-value">{doc_number}</span>
                            </div>
                            <div class="doc-detail-item">
                                <span class="detail-label">Дата:</span>
                                <span class="detail-value">{sign_date}</span>
                            </div>
                            <div class="doc-detail-item">
                                <span class="detail-label">Категория:</span>
                                <span class="detail-value">{doc_category}</span>
                            </div>
                        </div>
                    </div>
                </div>
                """

            documents_html += "</div>"

            # Добавляем JavaScript для поиска и сортировки
            documents_html += """
            <script>
                const searchInput = document.getElementById('searchDocs');
                const sortSelect = document.getElementById('sortDocs');
                const docCards = document.querySelectorAll('.document-card');

                function filterAndSort() {
                    const searchTerm = searchInput.value.toLowerCase();
                    const sortBy = sortSelect.value;
                    const cards = Array.from(docCards);

                    // Фильтрация
                    let visible = cards.filter(card => {
                        const name = card.dataset.name;
                        const number = card.dataset.number;
                        const date = card.dataset.date;
                        const category = card.dataset.category;
                        return name.includes(searchTerm) || number.includes(searchTerm) ||
                               date.includes(searchTerm) || category.includes(searchTerm);
                    });

                    // Сортировка
                    visible.sort((a, b) => {
                        let aVal, bVal;
                        switch(sortBy) {
                            case 'name':
                                aVal = a.dataset.name;
                                bVal = b.dataset.name;
                                break;
                            case 'number':
                                aVal = a.dataset.number;
                                bVal = b.dataset.number;
                                break;
                            case 'date':
                                aVal = a.dataset.date;
                                bVal = b.dataset.date;
                                break;
                            case 'category':
                                aVal = a.dataset.category;
                                bVal = b.dataset.category;
                                break;
                            default:
                                return 0;
                        }
                        return aVal.localeCompare(bVal);
                    });

                    // Скрыть все
                    docCards.forEach(card => card.style.display = 'none');

                    // Показать отсортированные
                    visible.forEach(card => card.style.display = 'flex');

                    // Обновить счетчик
                    document.querySelector('.documents-stats strong').textContent = visible.length;
                }

                searchInput.addEventListener('input', filterAndSort);
                sortSelect.addEventListener('change', filterAndSort);
            </script>
            """
        else:
            documents_html = "<div class='no-docs'><p>📭 В коробке нет документов</p></div>"

        html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#667eea">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Архив">
    <meta name="mobile-web-app-capable" content="yes">
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="/icon-192.png">
    <script>
        // Регистрация Service Worker
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', function() {
                navigator.serviceWorker.register('/sw.js')
                    .then(function(registration) {
                        console.log('SW registered: ', registration);
                    })
                    .catch(function(registrationError) {
                        console.log('SW registration failed: ', registrationError);
                    });
            });
        }
    </script>
    <title>Коробка: {box['Название']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            border: 1px solid #e0e0e0;
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .header .box-id {{
            opacity: 0.9;
            font-size: 0.9em;
            margin-bottom: 15px;
        }}
        .header .scanner-link {{
            display: inline-block;
            margin-top: 15px;
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            font-size: 0.9em;
            transition: background 0.3s;
        }}
        .header .scanner-link:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}
        .content {{
            padding: 30px;
        }}
        .info-section {{
            margin-bottom: 30px;
        }}
        .info-section h2 {{
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.3em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .info-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .info-item strong {{
            display: block;
            color: #667eea;
            margin-bottom: 5px;
            font-size: 0.9em;
        }}
        .info-item span {{
            color: #333;
            font-size: 1.1em;
        }}
        .documents-controls {{
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        .search-input {{
            flex: 1;
            min-width: 200px;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }}
        .search-input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .sort-select {{
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            background: white;
            cursor: pointer;
            transition: border-color 0.3s;
        }}
        .sort-select:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .documents-stats {{
            margin-bottom: 15px;
            color: #666;
            font-size: 14px;
        }}
        .documents-stats strong {{
            color: #667eea;
            font-size: 16px;
        }}
        .documents-list {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        .document-card {{
            display: flex;
            gap: 15px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            border-left: 4px solid #667eea;
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }}
        .document-card:hover {{
            transform: translateY(-2px);
            background: #f0f0f0;
        }}
        .doc-icon {{
            font-size: 2.5em;
            flex-shrink: 0;
        }}
        .doc-content {{
            flex: 1;
        }}
        .doc-title {{
            font-size: 1.2em;
            color: #333;
            margin-bottom: 12px;
            font-weight: 600;
        }}
        .doc-details {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .doc-detail-item {{
            display: flex;
            gap: 10px;
            font-size: 14px;
        }}
        .detail-label {{
            color: #666;
            font-weight: 500;
            min-width: 100px;
        }}
        .detail-value {{
            color: #333;
        }}
        .no-docs {{
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }}
        .no-docs p {{
            font-size: 1.2em;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 0.9em;
        }}
        @media (max-width: 768px) {{
            .info-grid {{
                grid-template-columns: 1fr;
            }}
            .documents-controls {{
                flex-direction: column;
            }}
            .search-input, .sort-select {{
                width: 100%;
            }}
            .document-card {{
                flex-direction: column;
                padding: 15px;
            }}
            .doc-icon {{
                font-size: 2em;
                text-align: center;
            }}
            .doc-detail-item {{
                flex-direction: column;
                gap: 5px;
            }}
            .detail-label {{
                min-width: auto;
                font-weight: 600;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px;">
                <a href="/" style="color: white; text-decoration: none; font-size: 1.1em; padding: 5px 10px; border-radius: 5px; background: rgba(255,255,255,0.2);">← Назад</a>
                <a href="/scanner" style="color: white; text-decoration: none; font-size: 0.9em; padding: 5px 10px; border-radius: 5px; background: rgba(255,255,255,0.2);">📱 Сканер</a>
            </div>
            <h1>📦 {box['Название']}</h1>
            <div class="box-id">ID: {box['ID']}</div>
        </div>
        <div class="content">
            <div class="info-section">
                <h2>📋 Информация о коробке</h2>
                <div class="info-grid">
                    <div class="info-item">
                        <strong>Расположение</strong>
                        <span>{location}</span>
                    </div>
                    <div class="info-item">
                        <strong>Категория</strong>
                        <span>{category_html}</span>
                    </div>
                    <div class="info-item">
                        <strong>Тип</strong>
                        <span>{box.get('Тип', 'Коробка')}</span>
                    </div>
                </div>
            </div>
            <div class="info-section">
                <h2>📄 Документы в коробке ({len(documents)})</h2>
                {documents_html}
            </div>
        </div>
        <div class="footer">
            Архив документов © 2025
        </div>
    </div>
</body>
</html>
        """
        return html

    def send_scanner(self):
        """Отправка страницы со сканером QR-кодов."""
        html = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#667eea">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Архив">
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="/icon-192.png">
    <title>Сканер QR-кодов - Архив</title>
    <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: white;
        }
        .container {
            max-width: 500px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            overflow: hidden;
            border: 1px solid #e0e0e0;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            text-align: center;
            position: relative;
            z-index: 1;
            flex-shrink: 0;
            width: 100%;
        }
        .header-nav {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .header-nav a {
            color: white;
            text-decoration: none;
            font-size: 1.2em;
            flex-shrink: 0;
        }
        .header h1 {
            font-size: 1.5em;
            margin: 0;
            flex: 1;
            text-align: center;
        }
        .header p {
            margin: 0;
            padding-top: 5px;
            font-size: 0.95em;
        }
        .scanner-section {
            padding: 20px;
            background: #000;
            position: relative;
            flex-shrink: 0;
        }
        #qr-reader {
            width: 100%;
            border-radius: 10px;
            overflow: hidden;
        }
        .scanner-overlay {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 250px;
            height: 250px;
            border: 3px solid #667eea;
            border-radius: 20px;
            pointer-events: none;
            box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);
        }
        .scanner-overlay::before,
        .scanner-overlay::after {
            content: '';
            position: absolute;
            width: 30px;
            height: 30px;
            border: 4px solid #667eea;
        }
        .scanner-overlay::before {
            top: -4px;
            left: -4px;
            border-right: none;
            border-bottom: none;
        }
        .scanner-overlay::after {
            bottom: -4px;
            right: -4px;
            border-left: none;
            border-top: none;
        }
        .controls {
            padding: 20px;
            background: white;
            flex-shrink: 0;
        }
        .btn {
            width: 100%;
            padding: 15px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-bottom: 10px;
            transition: background 0.3s;
        }
        .btn:hover {
            background: #5568d3;
        }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .btn-secondary {
            background: #6c757d;
        }
        .btn-secondary:hover {
            background: #5a6268;
        }
        .status {
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 10px;
            text-align: center;
            font-weight: 500;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .result {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            display: none;
        }
        .result.show {
            display: block;
        }
        .result-link {
            display: inline-block;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin-top: 10px;
            font-weight: 600;
        }
        .footer {
            text-align: center;
            padding: 15px;
            color: #999;
            font-size: 0.9em;
            flex-shrink: 0;
        }
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            .scanner-overlay {
                width: 200px;
                height: 200px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-nav">
                <a href="/">← Назад</a>
                <h1>📱 Сканер QR-кодов</h1>
                <div style="width: 60px; flex-shrink: 0;"></div>
            </div>
            <p>Наведите камеру на QR-код</p>
        </div>
        <div class="scanner-section">
            <div id="qr-reader"></div>
            <div class="scanner-overlay"></div>
        </div>
        <div class="controls">
            <div id="status" class="status info">Готов к сканированию</div>
            <button id="startBtn" class="btn">▶️ Запустить камеру</button>
            <button id="stopBtn" class="btn btn-secondary" disabled>⏹️ Остановить</button>
            <div id="result" class="result">
                <h3>QR-код распознан!</h3>
                <p id="resultText"></p>
                <a id="resultLink" href="#" class="result-link" target="_blank">Открыть информацию</a>
            </div>
        </div>
        <div class="footer">
            Архив документов © 2025
        </div>
    </div>
    <script>
        let html5QrcodeScanner = null;
        let isScanning = false;

        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const status = document.getElementById('status');
        const result = document.getElementById('result');
        const resultText = document.getElementById('resultText');
        const resultLink = document.getElementById('resultLink');

        function updateStatus(message, type = 'info') {
            status.textContent = message;
            status.className = 'status ' + type;
        }

        function showResult(url) {
            resultText.textContent = url;
            resultLink.href = url;
            result.classList.add('show');
        }

        function hideResult() {
            result.classList.remove('show');
        }

        async function startScanner() {
            try {
                updateStatus('Запуск камеры...', 'info');
                startBtn.disabled = true;

                html5QrcodeScanner = new Html5Qrcode("qr-reader");

                await html5QrcodeScanner.start(
                    { facingMode: "environment" },
                    {
                        fps: 10,
                        qrbox: { width: 250, height: 250 },
                        aspectRatio: 1.0
                    },
                    (decodedText, decodedResult) => {
                        // QR-код успешно распознан
                        let url = decodedText.trim();

                        // Нормализуем URL
                        if (!url.startsWith('http://') && !url.startsWith('https://')) {
                            // Если нет протокола, добавляем https://
                            if (url.includes('/box/')) {
                                url = 'https://' + url;
                            }
                        }

                        // Проверяем любой URL, который содержит /box/
                        if (url.includes('/box/')) {
                            updateStatus('✅ QR-код распознан! Открываю...', 'success');
                            stopScanner();
                            // Автоматически открываем страницу через 0.5 секунды
                            setTimeout(() => {
                                window.location.href = url;
                            }, 500);
                        } else if (url.startsWith('http://') || url.startsWith('https://')) {
                            // Это URL, но не наш формат
                            updateStatus('⚠️ Неверный формат QR-кода', 'error');
                            showResult(url);
                        } else {
                            updateStatus('⚠️ Неверный QR-код', 'error');
                        }
                    },
                    (errorMessage) => {
                        // Игнорируем ошибки сканирования
                    }
                );

                isScanning = true;
                stopBtn.disabled = false;
                updateStatus('📷 Камера активна. Наведите на QR-код', 'info');
                hideResult();
            } catch (err) {
                updateStatus('❌ Ошибка: ' + err.message, 'error');
                startBtn.disabled = false;
                console.error(err);
            }
        }

        async function stopScanner() {
            if (html5QrcodeScanner && isScanning) {
                try {
                    await html5QrcodeScanner.stop();
                    html5QrcodeScanner.clear();
                    isScanning = false;
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                    updateStatus('Камера остановлена', 'info');
                } catch (err) {
                    console.error(err);
                }
            }
        }

        startBtn.addEventListener('click', startScanner);
        stopBtn.addEventListener('click', stopScanner);

        // Автоматический запуск при загрузке (опционально)
        // startScanner();
    </script>
</body>
</html>
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def send_index(self):
        """Отправка главной страницы."""
        html = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#667eea">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Архив">
    <meta name="mobile-web-app-capable" content="yes">
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="/icon-192.png">
    <script>
        // Регистрация Service Worker
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', function() {
                navigator.serviceWorker.register('/sw.js')
                    .then(function(registration) {
                        console.log('SW registered: ', registration);
                    })
                    .catch(function(registrationError) {
                        console.log('SW registration failed: ', registrationError);
                    });
            });
        }
    </script>
    <title>Архив документов - QR сервер</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: white;
        }
        .container {
            background: white;
            color: #333;
            padding: 40px;
            border-radius: 20px;
            max-width: 600px;
            margin: 0 auto;
            border: 1px solid #e0e0e0;
        }
        .logo {
            text-align: center;
            font-size: 4em;
            margin-bottom: 20px;
        }
        h1 {
            color: #667eea;
            text-align: center;
            font-size: 2em;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        .features {
            margin: 30px 0;
            text-align: left;
        }
        .feature-item {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .feature-icon {
            font-size: 2em;
            margin-right: 15px;
        }
        .feature-text {
            flex: 1;
        }
        .feature-title {
            font-weight: 600;
            color: #667eea;
            margin-bottom: 5px;
        }
        .feature-desc {
            color: #666;
            font-size: 0.9em;
        }
        .links {
            margin-top: 30px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .link-btn {
            display: inline-block;
            padding: 18px 30px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 1.1em;
            transition: all 0.3s;
            text-align: center;
        }
        .link-btn:hover {
            background: #5568d3;
            transform: translateY(-2px);
        }
        .link-btn.secondary {
            background: #6c757d;
        }
        .link-btn.secondary:hover {
            background: #5a6268;
        }
        .info-box {
            background: #e3f2fd;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
        .info-box strong {
            color: #1976D2;
        }
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            h1 {
                font-size: 1.5em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">📦</div>
        <h1>Архив документов</h1>
        <p class="subtitle">Система управления архивом с QR-кодами</p>

        <div class="features">
            <div class="feature-item">
                <div class="feature-icon">📱</div>
                <div class="feature-text">
                    <div class="feature-title">Сканер QR-кодов</div>
                    <div class="feature-desc">Быстрый доступ к информации о коробках</div>
                </div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">📄</div>
                <div class="feature-text">
                    <div class="feature-title">Список документов</div>
                    <div class="feature-desc">Полная информация о содержимом коробки</div>
                </div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">🔍</div>
                <div class="feature-text">
                    <div class="feature-title">Поиск и фильтрация</div>
                    <div class="feature-desc">Быстрый поиск нужных документов</div>
                </div>
            </div>
        </div>

        <div class="info-box">
            <strong>💡 Совет:</strong> Добавьте это приложение на главный экран для быстрого доступа!
        </div>

        <div class="links">
            <a href="/scanner" class="link-btn">📱 Открыть сканер QR-кодов</a>
            <a href="javascript:void(0)" onclick="if('serviceWorker' in navigator) {navigator.serviceWorker.register('/sw.js').then(() => alert('PWA установлено!'))}" class="link-btn secondary">📲 Установить приложение</a>
        </div>
    </div>
</body>
</html>
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        """Переопределение логирования для использования нашего logger."""
        logger.info(f"{self.address_string()} - {format % args}")


def start_web_server(port=None):
    """Запуск веб-сервера для отображения информации о коробках."""
    try:
        # Получаем порт из переменной окружения (для Heroku, Railway и т.д.)
        if port is None:
            port = int(os.environ.get('PORT', 8080))

        manager = DataManager()

        # Создание обработчика с менеджером данных
        def handler(*args, **kwargs):
            return BoxInfoHandler(*args, manager=manager, **kwargs)

        # Для облачных платформ используем обычный TCPServer
        # Для локальной разработки можно использовать HTTPServer
        httpd = socketserver.TCPServer(("", port), handler)

        base_url = get_base_url()
        logger.info(f"Веб-сервер запущен на порту {port}")
        logger.info(f"Доступен по адресу: {base_url}")
        logger.info(f"Сканер QR-кодов: {base_url}/scanner")

        httpd.serve_forever()
    except Exception as e:
        logger.error(f"Ошибка запуска веб-сервера: {e}")
        raise


if __name__ == "__main__":
    start_web_server()
