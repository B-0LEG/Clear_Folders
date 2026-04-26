import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from pathlib import Path
import time

class EmptyFolderCleaner:
    def __init__(self, root):
        self.root = root
        self.root.title("Очистка пустых папок")
        self.root.geometry("1000x800")
        
        # Переменные
        self.folder_path = tk.StringVar()
        self.include_subfolders = tk.BooleanVar(value=True)
        self.found_folders = []
        self.search_active = False
        self.search_paused = False
        self.search_thread = None
        
        # Создание виджетов
        self.create_widgets()
        
    def create_widgets(self):
        # Настройка стилей
        style = ttk.Style()
        style.theme_use('clam')
        
        # Основной контейнер
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Верхняя часть - управление
        control_frame = ttk.Frame(main_container)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Выбор папки
        tk.Label(control_frame, text="Целевая папка:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        folder_entry_frame = ttk.Frame(control_frame)
        folder_entry_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        folder_entry_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(folder_entry_frame, textvariable=self.folder_path, font=('Arial', 10)).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(folder_entry_frame, text="Обзор...", command=self.browse_folder, width=15).grid(row=0, column=1)
        
        # Опции - используем обычный tk.Checkbutton
        self.checkbox = tk.Checkbutton(control_frame, text="Проверять вложенные папки",
                                       variable=self.include_subfolders, font=('Arial', 10))
        self.checkbox.grid(row=2, column=0, sticky=tk.W, pady=5)
        
        # Кнопки управления поиском
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.search_btn = ttk.Button(button_frame, text="Найти пустые папки", 
                                    command=self.start_search, width=20)
        self.search_btn.grid(row=0, column=0, padx=5)
        
        self.pause_btn = ttk.Button(button_frame, text="Пауза", 
                                   command=self.pause_search, width=20, state='disabled')
        self.pause_btn.grid(row=0, column=1, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Остановить поиск", 
                                  command=self.stop_search, width=20, state='disabled')
        self.stop_btn.grid(row=0, column=2, padx=5)
        
        self.select_all_btn = ttk.Button(button_frame, text="Выделить все", 
                                        command=self.select_all_folders, width=20, state='disabled')
        self.select_all_btn.grid(row=0, column=3, padx=5)
        
        # Прогресс бар и статус
        self.progress = ttk.Progressbar(control_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(control_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, padding=(5, 5))
        status_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Список найденных папок
        list_frame = ttk.LabelFrame(main_container, text="Найденные пустые папки")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Дерево с прокруткой
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Создаем Treeview с колонками
        columns = ('#', 'path', 'size')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='extended')
        
        # Настраиваем заголовки
        self.tree.heading('#', text='№')
        self.tree.heading('path', text='Путь к папке')
        self.tree.heading('size', text='Размер')
        
        # Настраиваем колонки
        self.tree.column('#', width=50, anchor=tk.CENTER)
        self.tree.column('path', width=800)
        self.tree.column('size', width=100, anchor=tk.CENTER)
        
        # Добавляем прокрутку
        tree_vscrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_hscrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_vscrollbar.set, xscrollcommand=tree_hscrollbar.set)
        
        # Размещаем элементы
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_vscrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        tree_hscrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Настраиваем расширение
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Кнопки управления результатами
        result_buttons_frame = ttk.Frame(main_container)
        result_buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.delete_btn = ttk.Button(result_buttons_frame, text="Удалить выделенные", 
                                    command=self.delete_selected, width=20, state='disabled')
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(result_buttons_frame, text="Очистить список", 
                                   command=self.clear_list, width=20, state='disabled')
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Информационная строка
        self.info_var = tk.StringVar(value="Всего найдено: 0 | Выделено: 0")
        tk.Label(main_container, textvariable=self.info_var, font=('Arial', 9)).pack(anchor=tk.W)
        
        # Привязываем событие выделения
        self.tree.bind('<<TreeviewSelect>>', self.update_selection_info)
        
    def browse_folder(self):
        folder_selected = filedialog.askdirectory(title="Выберите папку для поиска")
        if folder_selected:
            self.folder_path.set(folder_selected)
            
    def is_folder_empty(self, folder_path):
        """Проверяет, пустая ли папка"""
        try:
            path = Path(folder_path)
            if not path.exists() or not path.is_dir():
                return False
                
            with os.scandir(folder_path) as it:
                for entry in it:
                    if entry.name.startswith('.'):
                        continue
                    return False
            return True
        except (PermissionError, OSError):
            return False
            
    def find_empty_folders(self, folder_path, recursive=True):
        """Рекурсивно ищет пустые папки"""
        empty_folders = []
        
        try:
            if recursive:
                for root, dirs, files in os.walk(folder_path, topdown=False):
                    # Проверка на паузу
                    while self.search_paused and self.search_active:
                        time.sleep(0.1)
                        
                    # Проверка на остановку
                    if not self.search_active:
                        return empty_folders
                    
                    current_path = Path(root)
                    
                    if not current_path.exists():
                        continue
                    
                    # Обновляем статус в GUI
                    self.root.after(0, self.update_status, f"Проверка: {os.path.basename(root)}")
                    
                    if self.is_folder_empty(root):
                        empty_folders.append(str(current_path))
            else:
                if self.is_folder_empty(folder_path):
                    empty_folders.append(folder_path)
                    
        except (PermissionError, OSError) as e:
            print(f"Ошибка доступа: {e}")
            
        return empty_folders
        
    def search_worker(self):
        """Поток для поиска пустых папок"""
        try:
            path = self.folder_path.get()
            
            if not path or not os.path.exists(path):
                self.root.after(0, lambda: messagebox.showerror("Ошибка", "Укажите существующую папку!"))
                self.root.after(0, self.reset_search_controls)
                return
                
            # Очищаем список
            self.found_folders = []
            self.root.after(0, self.clear_tree)
            
            # Начинаем поиск
            self.root.after(0, self.update_status, "Идет поиск пустых папок...")
            self.root.after(0, self.progress.start)
            
            # Поиск пустых папок
            recursive = self.include_subfolders.get()
            self.found_folders = self.find_empty_folders(path, recursive)
            
            # Обновляем GUI
            self.root.after(0, self.update_results)
            
        except Exception as e:
            print(f"Ошибка в потоке поиска: {e}")
            self.root.after(0, lambda: self.update_status(f"Ошибка при поиске: {str(e)}"))
            self.root.after(0, self.reset_search_controls)
        
    def start_search(self):
        """Запускает поиск в отдельном потоке"""
        if self.search_active:
            return
            
        self.search_active = True
        self.search_paused = False
        
        # Обновляем состояние кнопок
        self.search_btn.config(state='disabled')
        self.pause_btn.config(state='normal')
        self.stop_btn.config(state='normal')
        self.delete_btn.config(state='disabled')
        self.clear_btn.config(state='disabled')
        self.select_all_btn.config(state='disabled')
        
        # Запускаем поток
        self.search_thread = threading.Thread(target=self.search_worker, daemon=True)
        self.search_thread.start()
        
    def pause_search(self):
        """Ставит поиск на паузу или возобновляет"""
        if not self.search_active:
            return
            
        self.search_paused = not self.search_paused
        
        if self.search_paused:
            self.pause_btn.config(text="Продолжить")
            self.update_status("Поиск приостановлен")
            self.progress.stop()
        else:
            self.pause_btn.config(text="Пауза")
            self.update_status("Поиск продолжается...")
            self.progress.start()
            
    def stop_search(self):
        """Останавливает поиск"""
        self.search_active = False
        self.search_paused = False
        
        # Обновляем состояние кнопок
        self.search_btn.config(state='normal')
        self.pause_btn.config(state='disabled')
        self.stop_btn.config(state='disabled')
        self.pause_btn.config(text="Пауза")
        
        if len(self.found_folders) > 0:
            self.delete_btn.config(state='normal')
            self.clear_btn.config(state='normal')
            self.select_all_btn.config(state='normal')
        
        self.update_status("Поиск остановлен")
        self.progress.stop()
        
    def reset_search_controls(self):
        """Сбрасывает состояние кнопок управления поиском"""
        self.search_active = False
        self.search_paused = False
        
        self.search_btn.config(state='normal')
        self.pause_btn.config(state='disabled')
        self.stop_btn.config(state='disabled')
        self.pause_btn.config(text="Пауза")
        self.progress.stop()
        
    def update_results(self):
        """Обновляет список найденных папок"""
        try:
            # Останавливаем прогресс бар
            self.progress.stop()
            
            # Добавляем найденные папки в дерево
            for i, folder in enumerate(self.found_folders, 1):
                try:
                    size = os.path.getsize(folder)
                except:
                    size = 0
                    
                size_str = "0 Б" if size == 0 else f"{size} Б"
                
                # Добавляем в дерево с номером
                self.tree.insert('', tk.END, values=(i, folder, size_str))
                
            # Обновляем статус и сбрасываем кнопки
            count = len(self.found_folders)
            self.update_status(f"Поиск завершен. Найдено пустых папок: {count}")
            self.update_info_counter(count)
            
            # Обновляем состояние кнопок
            self.reset_search_controls()
            if count > 0:
                self.delete_btn.config(state='normal')
                self.clear_btn.config(state='normal')
                self.select_all_btn.config(state='normal')
                
        except Exception as e:
            print(f"Ошибка при обновлении результатов: {e}")
            self.update_status("Ошибка при отображении результатов")
            
    def update_info_counter(self, count=None):
        """Обновляет счетчик найденных папок"""
        try:
            if count is None:
                count = len(self.found_folders)
            selected = len(self.tree.selection())
            self.info_var.set(f"Всего найдено: {count} | Выделено: {selected}")
        except:
            pass
        
    def update_selection_info(self, event=None):
        """Обновляет информацию о выделенных элементах"""
        try:
            selected = len(self.tree.selection())
            total = len(self.found_folders)
            self.info_var.set(f"Всего найдено: {total} | Выделено: {selected}")
        except:
            pass
        
    def select_all_folders(self):
        """Выделяет все папки в списке"""
        try:
            items = self.tree.get_children()
            if items:
                self.tree.selection_set(items)
        except Exception as e:
            print(f"Ошибка при выделении всех: {e}")
            
    def clear_list(self):
        """Очищает список найденных папок"""
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.found_folders = []
            self.update_info_counter(0)
            self.delete_btn.config(state='disabled')
            self.clear_btn.config(state='disabled')
            self.select_all_btn.config(state='disabled')
            self.update_status("Список очищен")
        except Exception as e:
            print(f"Ошибка при очистке списка: {e}")
            
    def clear_tree(self):
        """Очищает дерево"""
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)
        except:
            pass
            
    def delete_selected(self):
        """Удаляет выбранные папки"""
        try:
            selected_items = self.tree.selection()
            
            if not selected_items:
                messagebox.showwarning("Предупреждение", "Выберите папки для удаления!")
                return
                
            # Подтверждение
            confirm = messagebox.askyesno(
                "Подтверждение",
                f"Вы уверены, что хотите удалить {len(selected_items)} выбранных папок?\n"
                "Это действие нельзя отменить!"
            )
            
            if not confirm:
                return
                
            # Удаляем выбранные папки
            deleted_count = 0
            failed_folders = []
            
            # Собираем пути для удаления
            folders_to_delete = []
            for item in selected_items:
                try:
                    folder_path = self.tree.item(item)['values'][1]
                    folders_to_delete.append((item, folder_path))
                except:
                    continue
            
            # Удаляем папки
            for item, folder_path in folders_to_delete:
                try:
                    if os.path.exists(folder_path):
                        os.rmdir(folder_path)
                    
                    self.tree.delete(item)
                    deleted_count += 1
                    
                    # Удаляем из списка найденных
                    if folder_path in self.found_folders:
                        self.found_folders.remove(folder_path)
                        
                except (OSError, PermissionError) as e:
                    print(f"Не удалось удалить {folder_path}: {e}")
                    failed_folders.append(folder_path)
                    
            # Обновляем номера в таблице
            items = self.tree.get_children()
            for i, item in enumerate(items, 1):
                try:
                    self.tree.item(item, values=(i, *self.tree.item(item)['values'][1:]))
                except:
                    pass
                    
            # Обновляем информацию
            message = f"Успешно удалено папок: {deleted_count}"
            if failed_folders:
                message += f"\nНе удалось удалить: {len(failed_folders)}"
                
            messagebox.showinfo("Результат", message)
            self.update_status(f"Удалено: {deleted_count}, ошибок: {len(failed_folders)}")
            
            # Обновляем счетчики
            self.update_info_counter()
            
            # Деактивируем кнопки если больше нет папок
            if len(self.found_folders) == 0:
                self.delete_btn.config(state='disabled')
                self.clear_btn.config(state='disabled')
                self.select_all_btn.config(state='disabled')
                
        except Exception as e:
            print(f"Ошибка при удалении папок: {e}")
            messagebox.showerror("Ошибка", f"Произошла ошибка при удалении: {str(e)}")
            
    def update_status(self, message):
        """Обновляет строку статуса"""
        try:
            self.status_var.set(message)
        except:
            pass

def main():
    try:
        root = tk.Tk()
        app = EmptyFolderCleaner(root)
        
        # Центрирование окна
        root.update_idletasks()
        width = 1000
        height = 800
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Минимальный размер окна
        root.minsize(900, 600)
        
        # Обработка закрытия окна
        def on_closing():
            if app.search_active:
                app.search_active = False
                time.sleep(0.1)
            root.destroy()
            
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        root.mainloop()
        
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    main()