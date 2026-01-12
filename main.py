import pystray
from PIL import Image, ImageDraw, ImageGrab
import pytesseract
import mss
import tkinter as tk
from tkinter import messagebox
import pyperclip
import threading
import sys
import pyautogui
import time
import keyboard
import json
import os
import random
from config import configure_tesseract, OCR_LANG, APP_NAME, OCR_DELAY, SETTINGS_FILE, RANDOM_DELAY_MIN, RANDOM_DELAY_MAX, CLICK_DELAY_MIN, CLICK_DELAY_MAX, MOUSE_SPEED_MIN, MOUSE_SPEED_MAX

# Configure Tesseract on startup
configure_tesseract()


class RegionSelector:
    def __init__(self):
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.rect = None
        self.root = None
        self.canvas = None

    def select_region(self, callback):
        self.callback = callback
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-alpha', 0.3)
        self.root.attributes('-topmost', True)
        self.root.configure(background='black')

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        self.canvas = tk.Canvas(
            self.root,
            width=screen_width,
            height=screen_height,
            bg='black',
            highlightthickness=0,
            cursor='cross'
        )
        self.canvas.pack()

        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.root.bind('<Escape>', lambda e: self.cancel())

        instruction_text = "Выберите область для захвата. ESC - отмена"
        self.canvas.create_text(
            screen_width // 2,
            30,
            text=instruction_text,
            fill='white',
            font=('Arial', 14, 'bold')
        )

        self.root.mainloop()

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)

    def on_drag(self, event):
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            event.x,
            event.y,
            outline='red',
            width=2
        )

    def on_release(self, event):
        self.end_x = event.x
        self.end_y = event.y

        x1 = min(self.start_x, self.end_x)
        y1 = min(self.start_y, self.end_y)
        x2 = max(self.start_x, self.end_x)
        y2 = max(self.start_y, self.end_y)

        self.root.destroy()

        if self.callback:
            self.callback((x1, y1, x2, y2))

    def cancel(self):
        self.root.destroy()


class PointSelector:
    def __init__(self):
        self.points = []
        self.root = None
        self.canvas = None
        self.circles = []

    def select_three_points(self, callback):
        self.callback = callback
        self.points = []
        self.circles = []

        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-alpha', 0.3)
        self.root.attributes('-topmost', True)
        self.root.configure(background='black')

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        self.canvas = tk.Canvas(
            self.root,
            width=screen_width,
            height=screen_height,
            bg='black',
            highlightthickness=0,
            cursor='cross'
        )
        self.canvas.pack()

        self.canvas.bind('<Button-1>', self.on_click)
        self.root.bind('<Escape>', lambda e: self.cancel())

        self.instruction_label = self.canvas.create_text(
            screen_width // 2,
            30,
            text="Кликните на точку A (начало перетаскивания). ESC - отмена",
            fill='white',
            font=('Arial', 14, 'bold')
        )

        self.root.mainloop()

    def on_click(self, event):
        # Prevent clicks after 3 points are already selected
        if len(self.points) >= 3:
            return

        x, y = event.x, event.y
        self.points.append((x, y))

        # Рисуем круг в месте клика
        colors = ['green', 'red', 'blue']
        labels = ['A', 'B', 'C']
        point_idx = len(self.points) - 1

        color = colors[point_idx]
        circle = self.canvas.create_oval(
            x - 10, y - 10, x + 10, y + 10,
            outline=color,
            width=3,
            fill=color
        )
        self.circles.append(circle)

        # Показываем координаты
        self.canvas.create_text(
            x, y - 20,
            text=f"{labels[point_idx]}: ({x}, {y})",
            fill=color,
            font=('Arial', 12, 'bold')
        )

        if len(self.points) == 1:
            # Ожидаем выбора точки B
            self.canvas.itemconfig(
                self.instruction_label,
                text="Кликните на точку B (конец перетаскивания). ESC - отмена"
            )
        elif len(self.points) == 2:
            # Ожидаем выбора точки C
            self.canvas.itemconfig(
                self.instruction_label,
                text="Кликните на точку C (клик после перетаскивания). ESC - отмена"
            )
        elif len(self.points) == 3:
            # Все точки выбраны
            self.root.after(500, self.finish)

    def finish(self):
        point_a = self.points[0]
        point_b = self.points[1]
        point_c = self.points[2]
        self.root.destroy()

        if self.callback:
            self.callback(point_a, point_b, point_c)

    def cancel(self):
        self.root.destroy()


class ScreenTextCapture:
    def __init__(self):
        self.selected_region = None
        self.icon = None
        self.drag_point_a = None
        self.drag_point_b = None
        self.drag_point_c = None
        self.loop_running = False
        self.loop_thread = None
        self.load_settings()

    def create_icon_image(self):
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)

        draw.rectangle([10, 10, 54, 54], fill='#2196F3', outline='#1976D2', width=2)
        draw.text((20, 20), 'OCR', fill='white')

        return image

    def load_settings(self):
        """Загружает сохраненные настройки из файла"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

                # Загружаем точки A, B, C
                if 'drag_point_a' in settings and settings['drag_point_a']:
                    self.drag_point_a = tuple(settings['drag_point_a'])
                if 'drag_point_b' in settings and settings['drag_point_b']:
                    self.drag_point_b = tuple(settings['drag_point_b'])
                if 'drag_point_c' in settings and settings['drag_point_c']:
                    self.drag_point_c = tuple(settings['drag_point_c'])

                # Загружаем область захвата
                if 'selected_region' in settings and settings['selected_region']:
                    self.selected_region = tuple(settings['selected_region'])

                print(f"Settings loaded from {SETTINGS_FILE}")
                if self.drag_point_a and self.drag_point_b and self.drag_point_c:
                    print(f"Points: A={self.drag_point_a}, B={self.drag_point_b}, C={self.drag_point_c}")
                if self.selected_region:
                    x1, y1, x2, y2 = self.selected_region
                    print(f"Region: {x2-x1}x{y2-y1} at ({x1},{y1})")
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        """Сохраняет текущие настройки в файл"""
        try:
            settings = {
                'drag_point_a': list(self.drag_point_a) if self.drag_point_a else None,
                'drag_point_b': list(self.drag_point_b) if self.drag_point_b else None,
                'drag_point_c': list(self.drag_point_c) if self.drag_point_c else None,
                'selected_region': list(self.selected_region) if self.selected_region else None
            }

            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            print(f"Settings saved to {SETTINGS_FILE}")
        except Exception as e:
            print(f"Error saving settings: {e}")

    def select_region_handler(self):
        selector = RegionSelector()
        selector.select_region(self.on_region_selected)

    def on_region_selected(self, region):
        self.selected_region = region
        x1, y1, x2, y2 = region
        self.save_settings()
        self.show_notification(
            f"Область выбрана: {x2-x1}x{y2-y1} пикселей\n"
            f"Используйте 'Захватить текст' для распознавания"
        )

    def capture_and_ocr(self):
        if not self.selected_region:
            self.show_notification("Сначала выберите область экрана!")
            return

        x1, y1, x2, y2 = self.selected_region

        try:
            with mss.mss() as sct:
                monitor = {
                    "top": y1,
                    "left": x1,
                    "width": x2 - x1,
                    "height": y2 - y1
                }
                screenshot = sct.grab(monitor)
                img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)

            text = pytesseract.image_to_string(img, lang=OCR_LANG)

            if text.strip():
                pyperclip.copy(text)
                self.show_notification(
                    f"Текст распознан и скопирован в буфер обмена!\n\n"
                    f"Первые 100 символов:\n{text[:100]}..."
                )
            else:
                self.show_notification("Текст не обнаружен в выбранной области")

        except Exception as e:
            self.show_notification(f"Ошибка: {str(e)}")

    def select_drag_points_handler(self):
        selector = PointSelector()
        selector.select_three_points(self.on_drag_points_selected)

    def on_drag_points_selected(self, point_a, point_b, point_c):
        self.drag_point_a = point_a
        self.drag_point_b = point_b
        self.drag_point_c = point_c
        self.save_settings()
        self.show_notification(
            f"Точки выбраны:\n"
            f"Точка A (начало перетаскивания): {point_a}\n"
            f"Точка B (конец перетаскивания): {point_b}\n"
            f"Точка C (клик после): {point_c}\n\n"
            f"Горячие клавиши:\n"
            f"F8 - F1 + перетаскивание + клик\n"
            f"F9 - F5 + перетаскивание + клик\n"
            f"F10 - Запустить/остановить автоцикл"
        )

    def execute_drag_action(self, from_loop=False):
        try:
            if not from_loop:
                print("F8 pressed - execute_drag_action called")

            if not self.drag_point_a or not self.drag_point_b or not self.drag_point_c:
                msg = "Сначала настройте точки A, B и C!"
                if from_loop:
                    print(msg)
                    return False
                else:
                    self.show_notification(msg)
                    return False

            # Отключаем защиту от случайных движений мыши в pyautogui
            pyautogui.FAILSAFE = False

            # Небольшая задержка для стабильности
            time.sleep(0.1)

            # Нажимаем клавишу F1 как настоящее нажатие (press → delay → release)
            keyboard.press('f1')
            time.sleep(random.uniform(CLICK_DELAY_MIN, CLICK_DELAY_MAX))
            keyboard.release('f1')
            time.sleep(0.3)

            # Получаем координаты точек
            x1, y1 = self.drag_point_a
            x2, y2 = self.drag_point_b
            x3, y3 = self.drag_point_c

            # Перемещаем мышь к точке A с рандомной скоростью
            move_duration_1 = random.uniform(MOUSE_SPEED_MIN, MOUSE_SPEED_MAX)
            pyautogui.moveTo(x1, y1, duration=move_duration_1)
            time.sleep(0.1)

            # Зажимаем левую кнопку мыши в точке A
            pyautogui.mouseDown()
            # Держим зажатой некоторое время перед началом перетаскивания
            time.sleep(0.4)

            # Перетаскиваем к точке B с рандомной скоростью
            move_duration_2 = random.uniform(MOUSE_SPEED_MIN + 0.2, MOUSE_SPEED_MAX + 0.3)
            pyautogui.moveTo(x2, y2, duration=move_duration_2)
            time.sleep(0.1)

            # Отпускаем левую кнопку мыши
            pyautogui.mouseUp()
            time.sleep(0.3)

            # Перемещаем мышь к точке C с рандомной скоростью
            move_duration_3 = random.uniform(MOUSE_SPEED_MIN, MOUSE_SPEED_MAX)
            pyautogui.moveTo(x3, y3, duration=move_duration_3)
            time.sleep(0.1)

            # Зажимаем и отпускаем мышь (эмулируем клик с рандомной задержкой)
            pyautogui.mouseDown()
            click_delay = random.uniform(CLICK_DELAY_MIN, CLICK_DELAY_MAX)
            time.sleep(click_delay)
            pyautogui.mouseUp()

            return True

        except Exception as e:
            msg = f"Ошибка при выполнении действия: {str(e)}"
            if from_loop:
                print(msg)
            else:
                self.show_notification(msg)
            return False

    def execute_drag_action_f5(self, from_loop=False):
        try:
            if not from_loop:
                print("F9 pressed - execute_drag_action_f5 called")

            if not self.drag_point_a or not self.drag_point_b or not self.drag_point_c:
                msg = "Сначала настройте точки A, B и C!"
                if from_loop:
                    print(msg)
                    return False
                else:
                    self.show_notification(msg)
                    return False

            # Отключаем защиту от случайных движений мыши в pyautogui
            pyautogui.FAILSAFE = False

            # Небольшая задержка для стабильности
            time.sleep(0.1)

            # Нажимаем клавишу F5 как настоящее нажатие (press → delay → release)
            keyboard.press('f5')
            time.sleep(random.uniform(CLICK_DELAY_MIN, CLICK_DELAY_MAX))
            keyboard.release('f5')
            time.sleep(0.3)

            # Получаем координаты точек
            x1, y1 = self.drag_point_a
            x2, y2 = self.drag_point_b
            x3, y3 = self.drag_point_c

            # Перемещаем мышь к точке A с рандомной скоростью
            move_duration_1 = random.uniform(MOUSE_SPEED_MIN, MOUSE_SPEED_MAX)
            pyautogui.moveTo(x1, y1, duration=move_duration_1)
            time.sleep(0.1)

            # Зажимаем левую кнопку мыши в точке A
            pyautogui.mouseDown()
            # Держим зажатой некоторое время перед началом перетаскивания
            time.sleep(0.4)

            # Перетаскиваем к точке B с рандомной скоростью
            move_duration_2 = random.uniform(MOUSE_SPEED_MIN + 0.2, MOUSE_SPEED_MAX + 0.3)
            pyautogui.moveTo(x2, y2, duration=move_duration_2)
            time.sleep(0.1)

            # Отпускаем левую кнопку мыши
            pyautogui.mouseUp()
            time.sleep(0.3)

            # Перемещаем мышь к точке C с рандомной скоростью
            move_duration_3 = random.uniform(MOUSE_SPEED_MIN, MOUSE_SPEED_MAX)
            pyautogui.moveTo(x3, y3, duration=move_duration_3)
            time.sleep(0.1)

            # Зажимаем и отпускаем мышь (эмулируем клик с рандомной задержкой)
            pyautogui.mouseDown()
            click_delay = random.uniform(CLICK_DELAY_MIN, CLICK_DELAY_MAX)
            time.sleep(click_delay)
            pyautogui.mouseUp()

            return True

        except Exception as e:
            msg = f"Ошибка при выполнении действия: {str(e)}"
            if from_loop:
                print(msg)
            else:
                self.show_notification(msg)
            return False

    def parse_ocr_result(self, text):
        """
        Парсит OCR текст и возвращает действие
        Возвращает: ('stop', None), ('f1', None), ('f5', None), ('unknown', N)
        """
        import re

        # Убираем знаки препинания и приводим к нижнему регистру
        clean_text = re.sub(r'[^\w\s+]', '', text.lower())

        # Проверяем на +10 в первую очередь (это цель!)
        # Ищем паттерн "+10" или "+ 10" или "10" после "now a"
        if re.search(r'\+\s*10|now\s+a\s+10', text.lower()):
            return ('stop', 10)

        # Проверяем на Failed
        if 'failed' in clean_text and ('you have obtained' in clean_text or 'youhaveobtained' in clean_text):
            return ('f1', None)

        # Проверяем на Success
        if 'success' in clean_text and ('the item is now a' in clean_text or 'theitemisnowa' in clean_text):
            # Ищем число после "the item is now a" или "now a"
            match = re.search(r'(?:the item is now a|now a)\s*\+?\s*(\d+)', clean_text)
            if match:
                n = int(match.group(1))
                if n >= 3:
                    return ('f5', n)
                else:
                    return ('f1', n)

        # Ничего не найдено - останавливаем
        return ('unknown', None)

    def capture_ocr_only(self):
        """Захватывает текст из выбранной области без копирования в буфер"""
        if not self.selected_region:
            return None

        x1, y1, x2, y2 = self.selected_region

        try:
            with mss.mss() as sct:
                monitor = {
                    "top": y1,
                    "left": x1,
                    "width": x2 - x1,
                    "height": y2 - y1
                }
                screenshot = sct.grab(monitor)
                img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)

            text = pytesseract.image_to_string(img, lang=OCR_LANG)
            return text.strip()

        except Exception as e:
            return None

    def run_loop(self):
        """Основной цикл выполнения"""
        print("Loop thread started")
        try:
            while self.loop_running:
                if not self.drag_point_a or not self.drag_point_b or not self.drag_point_c:
                    print("Цикл остановлен: точки A, B, C не настроены!")
                    self.loop_running = False
                    break

                if not self.selected_region:
                    print("Цикл остановлен: область OCR не выбрана!")
                    self.loop_running = False
                    break

                # Выполняем F1-флоу
                print("Executing F1 action in loop")
                if not self.execute_drag_action(from_loop=True):
                    print("Failed to execute F1 action, stopping loop")
                    self.loop_running = False
                    break

                # Ждем перед OCR
                time.sleep(OCR_DELAY)

                # Проверяем, не остановили ли цикл
                if not self.loop_running:
                    break

                # Захватываем и парсим текст
                ocr_text = self.capture_ocr_only()

                if ocr_text:
                    action, value = self.parse_ocr_result(ocr_text)
                    print(f"OCR результат: action={action}, value={value}")

                    if action == 'stop':
                        print(f"Цикл завершен! Достигнут +10!")
                        self.loop_running = False
                        break
                    elif action == 'unknown':
                        print(f"Цикл остановлен: текст не распознан. OCR: {ocr_text}")
                        self.loop_running = False
                        break
                    elif action == 'f1':
                        print("Продолжаем с F1-флоу")
                        # Случайная задержка перед следующим действием
                        random_delay = random.uniform(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX)
                        print(f"Случайная задержка: {random_delay:.2f} сек")
                        time.sleep(random_delay)
                        # Продолжаем цикл с F1-флоу (начнется со следующей итерации)
                        continue
                    elif action == 'f5':
                        # Случайная задержка перед F5-флоу
                        random_delay = random.uniform(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX)
                        print(f"Случайная задержка: {random_delay:.2f} сек")
                        time.sleep(random_delay)
                        # Запускаем подцикл F5
                        while self.loop_running and action == 'f5':
                            print(f"Запускаю F5-флоу для +{value}")
                            if not self.execute_drag_action_f5(from_loop=True):
                                print("Failed to execute F5 action, stopping loop")
                                self.loop_running = False
                                break
                            time.sleep(OCR_DELAY)

                            # Проверяем, не остановили ли цикл
                            if not self.loop_running:
                                break

                            # Захватываем и парсим текст после F5
                            ocr_text = self.capture_ocr_only()

                            if ocr_text:
                                action, value = self.parse_ocr_result(ocr_text)
                                print(f"OCR результат после F5: action={action}, value={value}")

                                if action == 'stop':
                                    print(f"Цикл завершен! Достигнут +10!")
                                    self.loop_running = False
                                    break
                                elif action == 'unknown':
                                    print(f"Цикл остановлен: текст не распознан после F5. OCR: {ocr_text}")
                                    self.loop_running = False
                                    break
                                elif action == 'f1':
                                    print("Выходим из F5-подцикла, переходим к F1")
                                    # Случайная задержка перед переходом к F1
                                    random_delay = random.uniform(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX)
                                    print(f"Случайная задержка: {random_delay:.2f} сек")
                                    time.sleep(random_delay)
                                    # Выходим из подцикла F5, продолжаем основной цикл
                                    break
                                # Если action == 'f5', подцикл продолжится
                                else:  # action == 'f5'
                                    # Случайная задержка перед следующим F5
                                    random_delay = random.uniform(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX)
                                    print(f"Случайная задержка: {random_delay:.2f} сек")
                                    time.sleep(random_delay)
                            else:
                                print("Цикл остановлен: не удалось прочитать OCR после F5")
                                self.loop_running = False
                                break
                else:
                    print("Цикл остановлен: не удалось прочитать OCR")
                    self.loop_running = False
                    break
        except Exception as e:
            print(f"Error in run_loop: {e}")
            import traceback
            traceback.print_exc()
            print(f"Ошибка в цикле: {str(e)}")
            self.loop_running = False

    def toggle_loop(self):
        """Включает/выключает цикл по F10"""
        try:
            print("F10 pressed - toggle_loop called")
            if self.loop_running:
                # Останавливаем цикл
                self.loop_running = False
                print("Loop stopped")
            else:
                # Запускаем цикл
                print("Attempting to start loop")
                if not self.drag_point_a or not self.drag_point_b or not self.drag_point_c:
                    print("Error: Points not configured")
                    return

                if not self.selected_region:
                    print("Error: Region not selected")
                    return

                self.loop_running = True
                print("Loop started successfully. Press F10 to stop.")

                # Запускаем цикл в отдельном потоке
                self.loop_thread = threading.Thread(target=self.run_loop, daemon=True)
                self.loop_thread.start()
        except Exception as e:
            print(f"Error in toggle_loop: {e}")
            import traceback
            traceback.print_exc()

    def show_notification(self, message):
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(APP_NAME, message)
            root.destroy()
        except Exception as e:
            # If Tkinter fails (e.g., called from non-main thread), print to console
            print(f"{APP_NAME}: {message}")

    def quit_app(self):
        keyboard.unhook_all()  # Отменяем все горячие клавиши
        self.icon.stop()
        sys.exit(0)

    def create_menu(self):
        return pystray.Menu(
            pystray.MenuItem('Выбрать область', self.select_region_handler),
            pystray.MenuItem('Захватить текст', self.capture_and_ocr),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Настроить точки A, B, C', self.select_drag_points_handler),
            pystray.MenuItem('F1 + Drag + Click (F8)', self.execute_drag_action),
            pystray.MenuItem('F5 + Drag + Click (F9)', self.execute_drag_action_f5),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Запустить/Остановить цикл (F10)', self.toggle_loop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Выход', self.quit_app)
        )

    def run(self):
        # Регистрируем горячие клавиши
        keyboard.add_hotkey('f8', self.execute_drag_action, suppress=False)
        keyboard.add_hotkey('f9', self.execute_drag_action_f5, suppress=False)
        keyboard.add_hotkey('f10', self.toggle_loop, suppress=False)

        image = self.create_icon_image()
        self.icon = pystray.Icon(
            'screen_text_capture',
            image,
            APP_NAME,
            menu=self.create_menu()
        )

        self.icon.run()


if __name__ == '__main__':
    app = ScreenTextCapture()
    app.run()
