# 📱 QR Toolkit — генератор и сканер QR-кодов

[English](#english) · **Русский**

**Создание и распознавание QR-кодов на Python — локально, без интернета и сторонних сервисов.**

Один файл, одна зависимость на каждую задачу: генерируй QR любой сложности (цветные, с логотипом, SVG), а затем распознавай их из обычных фотографий — в том числе наклонённых и снятых с искажением перспективы.

![Примеры](docs/hero.png)

---

## Русский

### 🎯 Что это

Утилита для двух вещей:

1. **Генерация** — сделать QR-код для ссылки, текста, Wi-Fi, визитки или Telegram.
2. **Распознавание** — достать данные из QR на картинке или целой папке картинок.

Всё работает офлайн: шифрование QR — чистая математика на Python, распознавание — OpenCV. Никаких API, аккаунтов и лимитов.

### 💡 Для чего пригодится

- Ссылка на сайт, канал или бота прямо на визитке или листовке
- Wi-Fi-пароль для гостей: сканируешь — сам подключается
- Контакт-визитка (vCard) для нетворкинга
- Платёжная ссылка или СБП-картинка
- Меню кафе, ссылка на отзыв, промо-акция
- Массовое распознавание QR из скриншотов и фотоотчётов

### ⚙️ Как работает

**Генерация:**
1. Данные кодируются в матрицу QR-кода (`qrcode`).
2. Выбирается версия (размер матрицы) под объём данных — автоматически.
3. Уровень коррекции ошибок `L/M/Q/H` определяет, сколько кода можно испортить, и он всё ещё прочитается.
4. Матрица рисуется в пикселях с нужным размером модуля и «тихой зоной» (белой рамкой).
5. Опционально в центр вставляется логотип на фирменной плашке — с уровнем `H` код остаётся читаемым.

**Распознавание:**
1. Картинка конвертируется в RGB и передаётся `cv2.QRCodeDetector`.
2. Детектор находит три угловых маркера, определяет перспективу и выравнивает квадрат.
3. Данные декодируются, проверяется контрольная сумма.
4. Режим `--draw` рисует найденные коды зелёным контуром на копии изображения.

### ✨ Возможности

- 🎨 **Цветные QR** — любой цвет текста и фона (`#6c8cff`, `10,20,30`, именованные)
- 🖼 **Логотип в центре** — с автоматическим снижением риска ошибок через уровень `H`
- 🗂 **SVG-вывод** — векторный файл для печати и макетов
- ⚙️ **Настройка плотности** — размер модуля (`--box`), тихая зона (`--border`), коррекция (`--ec`)
- 🔍 **Скан фото** — работает с наклоном, масштабом и перспективой
- 📁 **Скан папки** — `--all` пройдёт по всем картинкам и выведет содержимое каждой
- 🟩 **Аннотация** — сохранение превью с обведёнными найденными кодами
- 🖱 **Интерактивный режим** — меню, без запоминания флагов
- 🧪 **18 тестов** — цвета, генерация, распознавание, логотипы, SVG

### 🚀 Быстрый старт

```bash
git clone https://github.com/fffeeedka/qr-toolkit.git
cd qr-toolkit
pip install -r requirements.txt
```

**Сгенерировать (одной командой):**

```bash
python qr.py gen "https://homso.ru"                      # -> qr.png
python qr.py gen "https://t.me/hatuj" -o tg.png          # свой путь
python qr.py gen "hello" --fg "#6c8cff" --bg white       # цветной
python qr.py gen "hello" --ec H --box 14                 # плотнее, надёжнее
python qr.py gen "hello" --logo logo.png                 # с логотипом
python qr.py gen "hello" --svg out.svg                   # SVG
```

**Сканировать:**

```bash
python qr.py scan qr.png
python qr.py scan photo.jpg --draw scan.png              # с превью
python qr.py scan ./screenshots/                         # вся папка
```


### 🖱 Интерактивный режим

Запусти **без аргументов** — откроется меню:

```bash
python qr.py
```

```
========================================
 QR Toolkit - генератор и сканер кодов
========================================

Что сделать?
  1) Сгенерировать QR
  2) Сканировать изображение
  0) Выход
```

Дальше программа сама спрашивает всё нужное:

- **Что закодировать** — ссылка/текст, Telegram, Wi-Fi (SSID + пароль), контакт-визитка, email
- **Уровень коррекции, размер модуля**
- **Свои цвета** — цвет кода и фона
- **Логотип** — путь к картинке (уровень коррекции автоматически станет `H`)
- **SVG или PNG**, имя файла
- **Проверка** — сразу сканирует результат и показывает, что в нём зашифровано

Для сканирования достаточно указать файл или папку и, по желанию, сохранить превью с контуром.
Enter везде принимает значение по умолчанию.

### 📖 Параметры

| Параметр | По умолчанию | Описание |
| :--- | :--- | :--- |
| `--ec` | `M` | Уровень коррекции: `L` (7%), `M` (15%), `Q` (25%), `H` (30%) |
| `--box` | 10 | Размер модуля в пикселях |
| `--border` | 4 | Ширина «тихой зоны» в модулях |
| `--fg` | black | Цвет кода |
| `--bg` | white | Цвет фона |
| `--logo` | — | Картинка логотипа для центра |
| `--logo-ratio` | 0.22 | Размер логотипа относительно стороны |
| `--svg` | — | Писать SVG вместо PNG |
| `--draw` | — | Сохранить превью с контурами (скан) |

### 📁 Структура

```
qr-toolkit/
├── qr.py               # генератор + сканер + CLI
├── requirements.txt
├── tests/test_qr.py
└── docs/               # примеры картинок
```

### 📦 Зависимости

`qrcode` · `Pillow` · `opencv-python-headless` · `numpy`

### 📬 Контакты

Автор — **homso**: сайты, боты и автоматизация. [Telegram @hatuj](https://t.me/hatuj) · [homso.ru](https://homso.ru)

---

<a id="english"></a>
# 📱 QR Toolkit — QR Code Generator & Scanner · English

**Generate and decode QR codes in Python — fully offline, no third-party services.**

One file, a few lightweight dependencies: build any QR you need (colored, with a logo, as SVG), then decode them from ordinary photos — including tilted and perspective-distorted shots.

### What it does

1. **Generate** — QR codes for links, text, Wi-Fi, vCards or Telegram.
2. **Scan** — extract data from a QR in an image or an entire folder of images.

Everything runs locally: encoding is pure Python math, decoding is OpenCV. No APIs, accounts or limits.

### Use cases

- Link to your site, channel or bot on a business card or flyer
- Guest Wi-Fi credentials — scan and connect
- vCard contact for networking
- Payment links
- Café menus, review links, promo campaigns
- Batch decoding QR codes from screenshots and photo reports

### How it works

**Generation:**
1. Data is encoded into a QR matrix (`qrcode`).
2. The version (matrix size) is picked automatically for the payload.
3. Error-correction level `L/M/Q/H` controls how much damage the code can take.
4. The matrix is drawn at the chosen module size with a quiet zone.
5. Optionally a logo is placed in the center on a plate — with level `H` the code stays readable.

**Decoding:**
1. The image is converted to RGB and passed to `cv2.QRCodeDetector`.
2. The detector finds the three finder patterns, corrects perspective and straightens the grid.
3. Data is decoded and checksum-verified.
4. `--draw` outlines found codes in green.

### Features

- 🎨 **Colored QR** — any foreground/background (`#6c8cff`, `10,20,30`, named)
- 🖼 **Center logo** with error-correction safety
- 🗂 **SVG output** for print and design
- ⚙️ **Density control** — `--box`, `--border`, `--ec`
- 🔍 **Photo scanning** with tilt and perspective
- 📁 **Folder mode** — decode every image at once
- 🟩 **Annotated previews**
- 🖱 **Interactive menu mode**
- 🧪 **18 unit tests**

### Quick start

```bash
git clone https://github.com/fffeeedka/qr-toolkit.git
cd qr-toolkit
pip install -r requirements.txt

python qr.py gen "https://homso.ru"
python qr.py gen "hello" --logo logo.png --ec H
python qr.py scan photo.jpg --draw scan.png
```


### Interactive mode

Run with **no arguments** for a menu:

```bash
python qr.py
```

Pick generate or scan, then answer the prompts: what to encode (URL, Telegram, Wi-Fi, vCard, email), error-correction level, colors, logo, SVG/PNG, filename. The tool verifies the result by decoding it right away. Press Enter to accept defaults.

### Options

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--ec` | `M` | Error correction: `L`, `M`, `Q`, `H` |
| `--box` | 10 | Module size in pixels |
| `--border` | 4 | Quiet zone width in modules |
| `--fg` / `--bg` | black / white | Colors |
| `--logo` | — | Center logo image |
| `--logo-ratio` | 0.22 | Logo size relative to QR side |
| `--svg` | — | Write SVG instead of PNG |
| `--draw` | — | Save an annotated preview (scan) |

### Dependencies

`qrcode` · `Pillow` · `opencv-python-headless` · `numpy`

### Contact

Built by **homso** — websites, bots and automation. [Telegram @hatuj](https://t.me/hatuj) · [homso.ru](https://homso.ru)
