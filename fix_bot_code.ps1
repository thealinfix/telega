# fix_bot_code.ps1
# PowerShell скрипт для исправления проблем в коде бота

param(
    [string]$FilePath = "paste.txt",
    [string]$OutputPath = "bot_fixed.py"
)

Write-Host "🔧 Запуск исправления кода бота..." -ForegroundColor Green
Write-Host "📄 Входной файл: $FilePath" -ForegroundColor Cyan
Write-Host "📄 Выходной файл: $OutputPath" -ForegroundColor Cyan

# Проверяем существование файла
if (-not (Test-Path $FilePath)) {
    Write-Host "❌ Файл $FilePath не найден!" -ForegroundColor Red
    exit 1
}

# Читаем содержимое файла
$content = Get-Content $FilePath -Raw -Encoding UTF8

Write-Host "`n🔍 Анализ проблем..." -ForegroundColor Yellow

# 1. Находим полное определение класса ContentAnalyzer
Write-Host "  1️⃣ Поиск полного определения ContentAnalyzer..." -ForegroundColor White

# Ищем класс ContentAnalyzer с наибольшим количеством методов
$classPattern = '(?s)(class ContentAnalyzer:.*?)(?=\nclass\s|\nasync\s+def\s|\ndef\s+[^_]|\n# ==|\z)'
$matches = [regex]::Matches($content, $classPattern)

$fullClass = ""
$maxMethods = 0

foreach ($match in $matches) {
    $classContent = $match.Value
    # Считаем количество методов def внутри класса
    $methodCount = ([regex]::Matches($classContent, '\n\s+def\s+')).Count
    
    if ($methodCount -gt $maxMethods) {
        $maxMethods = $methodCount
        $fullClass = $classContent
    }
}

Write-Host "    ✓ Найден полный класс с $maxMethods методами" -ForegroundColor Green

# Удаляем все определения ContentAnalyzer
$content = $content -replace '(?s)class ContentAnalyzer:.*?(?=\nclass\s|\nasync\s+def\s|\ndef\s+[^_]|\n# ==|\z)', ''

# Вставляем полный класс в начало после импортов
$importEndPattern = '(?s)(.*?bot_coordinator = SmartBotCoordinator\(\)\s*\n)'
if ($content -match $importEndPattern) {
    $imports = $matches[1]
    $afterImports = $content.Substring($imports.Length)
    $content = $imports + "`n" + $fullClass + "`n" + $afterImports
}

# 2. Удаляем дублированные функции analyze_post вне класса
Write-Host "  2️⃣ Удаление дублированных функций..." -ForegroundColor White

# Удаляем отдельные определения методов ContentAnalyzer вне класса
$methodsToRemove = @(
    'analyze_post',
    '_extract_brands', 
    '_extract_models',
    '_extract_colors',
    '_extract_materials',
    '_extract_price_context',
    '_has_price',
    '_get_release_type',
    '_is_news',
    '_get_main_topic',
    '_analyze_sentiment'
)

foreach ($method in $methodsToRemove) {
    # Удаляем def method(self, ...) вне класса
    $pattern = "(?m)^def $method\(self[^)]*\):(?:\n(?!def |class |async def ).*)*"
    $content = $content -replace $pattern, ''
}

# 3. Исправляем enhanced_main - удаляем дублирование внутри функции
Write-Host "  3️⃣ Исправление enhanced_main..." -ForegroundColor White

# Находим функцию enhanced_main и исправляем её структуру
$enhancedMainPattern = '(?s)(async def enhanced_main\(\):.*?)(?=\nasync def|\ndef [^_]|\nclass|\z)'
if ($content -match $enhancedMainPattern) {
    $funcContent = $matches[1]
    
    # Проверяем на дублирование print statements
    if ($funcContent -match '(?s)(print.*?Запуск бота.*?\n)(.*?)(print.*?Запуск бота.*?\n)') {
        # Есть дублирование - исправляем
        $fixedFunc = @'
async def enhanced_main():
    """Основная функция с антидетект защитой"""
    print(f"\n🚀 Запуск бота с антидетект защитой - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Проверка папки sessions
    print("\n📁 Проверяю файлы в папке sessions:")
    if os.path.exists('sessions'):
        files = os.listdir('sessions')
        print(f"Найдено файлов: {len(files)}")
        for file in files:
            print(f"  - {file}")
    else:
        print("❌ Папка sessions не найдена!")
        print("📁 Создаю папку sessions...")
        os.makedirs('sessions', exist_ok=True)
    
    print(f"\n🔍 Ищу файл: {session_file}")
    print(f"📍 Файл существует: {os.path.exists(session_file)}")
    print(f"📢 Канал: @{channel_username}")
    print(f"💬 Чат обсуждения: @{discussion_chat}")
    print(f"👍 Реакции на посты: 100%")
    print(f"💭 Умные ответы на комментарии: включены")
    
    client = None
    
    try:
        # Проверяем время работы
        if not await should_work_now():
            print("💤 Не время для работы")
            return
        
        # Загружаем истории
        history = load_history()
        reactions_history = load_reactions_history()
        
        # Проверяем лимиты
        if not await check_and_limit_actions(history):
            return
        
        # Определяем длительность сессии
        session_duration = random.randint(*ANTIDETECT_CONFIG["session_duration"])
        session_end_time = datetime.now() + timedelta(seconds=session_duration)
        print(f"⏱ Длительность сессии: {session_duration//60} минут")
        
        client = TelegramClient(session_file, api_id, api_hash, proxy=proxy)
        
        # Подключаемся и проверяем авторизацию
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Сессия не найдена или недействительна")
            print("📱 Требуется авторизация...")
            phone = input("Введите номер телефона (с кодом страны): ")
            await client.send_code_request(phone)
            code = input("Введите код из Telegram: ")
            try:
                await client.sign_in(phone, code)
            except Exception as e:
                print(f"❌ Ошибка авторизации: {e}")
                password = input("Введите пароль 2FA (если есть): ")
                await client.sign_in(password=password)
        
        print("✅ Подключение установлено")
        
        # Обновляем статус онлайн
        await update_online_status(client, True)
        
        # Начальная пауза (имитация обычного поведения)
        await asyncio.sleep(random.uniform(5, 15))
        
        # Выполняем случайные действия
        await perform_random_actions(client)
        
        # Проверяем личные сообщения
        await monitor_private_messages(client)
        
        # Основная работа бота
        await main_bot_work(client, history, reactions_history)
        
        # Дополнительные случайные действия в конце
        if datetime.now() < session_end_time:
            await perform_random_actions(client)
        
        print("\n✅ Основная работа завершена")
        print("🔄 Переключаюсь в режим постоянного мониторинга...")
        
        # Обновляем статус (остаемся онлайн)
        await update_online_status(client, True)
        
        # Запускаем бесконечный цикл мониторинга
        await continuous_monitoring_loop(client, reactions_history)
        
    except asyncio.CancelledError:
        print("\n⚠️ Получен сигнал отмены, завершаю работу...")
    except KeyboardInterrupt:
        print("\n⚠️ Получено прерывание от пользователя (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Безопасное завершение
        if client and client.is_connected():
            try:
                await update_online_status(client, False)
                await client.disconnect()
            except Exception:
                pass
        print(f"\n👋 Полное завершение работы - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
'@
        
        $content = $content -replace [regex]::Escape($funcContent), $fixedFunc
        Write-Host "    ✓ Функция enhanced_main исправлена" -ForegroundColor Green
    }
}

# 4. Исправляем точку входа
Write-Host "  4️⃣ Исправление точки входа..." -ForegroundColor White

# Удаляем все блоки if __name__ == "__main__":
$content = $content -replace '(?s)if __name__ == "__main__":(?:\n(?!if |class |async def |def [^_]).*)*', ''

# Добавляем правильную точку входа в конец файла
$mainBlock = @'


if __name__ == "__main__":
    # Предлагаем выбрать бота
    selected_bot = select_bot()
    
    if selected_bot:
        # Переопределяем глобальные переменные из выбранного бота
        api_id = selected_bot['api_id']
        api_hash = selected_bot['api_hash']
        session_file = selected_bot['session_file']
        
        # Прокси - преобразуем из списка в кортеж
        if selected_bot.get('proxy'):
            proxy = tuple(selected_bot['proxy'])
        else:
            proxy = None
        
        print(f"\n📱 Запуск с настройками:")
        print(f"   Сессия: {session_file}")
        print(f"   API ID: {api_id}")
        if proxy:
            print(f"   Прокси: {proxy[1]}:{proxy[2]}")
    else:
        print("\n📱 Запуск со стандартными настройками")
    
    # Запускаем основную функцию
    if "--stats" in sys.argv:
        asyncio.run(show_coordination_stats())
    else:
        asyncio.run(enhanced_main())
'@

$content = $content.TrimEnd() + $mainBlock

# 5. Удаляем дублированные импорты
Write-Host "  5️⃣ Удаление дублированных импортов..." -ForegroundColor White

# Удаляем дублированные строки импорта bot_coordinator
$lines = $content -split "`n"
$seen = @{}
$cleanedLines = @()

foreach ($line in $lines) {
    if ($line -match 'from smart_bot_coordinator import') {
        if (-not $seen.ContainsKey('bot_coordinator')) {
            $seen['bot_coordinator'] = $true
            $cleanedLines += $line
        }
    }
    elseif ($line -match 'bot_coordinator = SmartBotCoordinator') {
        if (-not $seen.ContainsKey('bot_coordinator_init')) {
            $seen['bot_coordinator_init'] = $true
            $cleanedLines += $line
        }
    }
    else {
        $cleanedLines += $line
    }
}

$content = $cleanedLines -join "`n"

# 6. Исправляем handle_discussion_and_comments
Write-Host "  6️⃣ Исправление handle_discussion_and_comments..." -ForegroundColor White

# Находим место с проблемным кодом if not my_comment_id:
$problemPattern = '(?s)if not my_comment_id:(.*?)else:(.*?)(?=\n\nasync def|$)'
if ($content -match $problemPattern) {
    $fixedCode = @'
    
    # Обрабатываем реакции и ответы на другие комментарии
    await asyncio.sleep(random.randint(20, 60))
    
    if not my_comment_id:
        # Бот не комментировал - компенсируем реакциями
        print("🎯 Бот не комментировал - включаю усиленный режим реакций")
        
        # Создаем модифицированные настройки
        modified_config = {
            "comment_reaction_chance": REACTIONS_CONFIG["comment_reaction_chance"] * 1.5,
            "react_to_replies_chance": REACTIONS_CONFIG["react_to_replies_chance"],
            "reaction_delay": REACTIONS_CONFIG["reaction_delay"],
            "max_reactions_per_session": 8
        }
        
        await process_comment_reactions_and_replies_modified(
            client, discussion_chat, post_text, reactions_history,
            history, my_comment_id, modified_config
        )
    else:
        # Бот прокомментировал - обычный режим
        await process_comment_reactions_and_replies(
            client, discussion_chat, post_text, reactions_history, 
            history, my_comment_id
        )
'@
    
    $content = $content -replace [regex]::Escape($matches[0]), $fixedCode
}

# Сохраняем исправленный файл
Write-Host "`n💾 Сохранение исправленного файла..." -ForegroundColor Yellow
$content | Out-File -FilePath $OutputPath -Encoding UTF8

Write-Host "✅ Исправление завершено!" -ForegroundColor Green
Write-Host "📄 Результат сохранен в: $OutputPath" -ForegroundColor Cyan

# Показываем статистику
$originalSize = (Get-Item $FilePath).Length
$newSize = (Get-Item $OutputPath).Length
$reduction = [math]::Round((($originalSize - $newSize) / $originalSize) * 100, 2)

Write-Host "`n📊 Статистика:" -ForegroundColor Yellow
Write-Host "   Исходный размер: $([math]::Round($originalSize/1KB, 2)) KB" -ForegroundColor White
Write-Host "   Новый размер: $([math]::Round($newSize/1KB, 2)) KB" -ForegroundColor White
Write-Host "   Уменьшение: $reduction%" -ForegroundColor Green