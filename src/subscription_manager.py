import sys
from src.processor import Processor

class SubscriptionManager:
    def __init__(self, processor):
        self.processor = processor

    def display_menu(self):
        print("\n=== Управление подписками на рассылки ===")
        print("1. Показать все подписки")
        print("2. Отписаться от конкретной рассылки")
        print("3. Отписаться от всех рассылок")
        print("4. Выход")
        print("=======================================")

    def show_newsletters(self):
        newsletters = self.processor.get_newsletters()
        if not newsletters:
            print("\nПодписки не найдены")
            return newsletters
        
        print("\nСписок найденных рассылок:")
        print("-------------------")
        for i, (email, info) in enumerate(newsletters.items(), 1):
            print(f"{i}. {info['name']} ({email})")
            print(f"   Количество писем: {info['count']}")
            print("-------------------")
        return newsletters

    def unsubscribe_specific(self):
        newsletters = self.show_newsletters()
        if not newsletters:
            return

        while True:
            try:
                choice = input("\nВведите номер рассылки для отписки (или 'q' для возврата): ")
                if choice.lower() == 'q':
                    return

                index = int(choice) - 1
                if 0 <= index < len(newsletters):
                    email, info = list(newsletters.items())[index]
                    print(f"\nОтписываемся от: {info['name']} ({email})")
                    
                    if self.processor.unsubscribe_from_newsletter(info['example_message_id']):
                        print("✓ Успешно отписались")
                    else:
                        print("✗ Не удалось отписаться автоматически")
                    break
                else:
                    print("Неверный номер. Попробуйте снова.")
            except ValueError:
                print("Пожалуйста, введите число или 'q'")

    def unsubscribe_all_newsletters(self):
        newsletters = self.processor.get_newsletters()
        if not newsletters:
            print("\nПодписки не найдены")
            return

        confirm = input(f"\nВы уверены, что хотите отписаться от всех рассылок ({len(newsletters)} шт.)? (y/n): ")
        if confirm.lower() != 'y':
            print("Операция отменена")
            return

        results = self.processor.unsubscribe_all()
        print("\nРезультаты:")
        print(f"✓ Успешно отписались: {results['success']}")
        print(f"✗ Не удалось отписаться: {results['failed']}")

    def run(self):
        while True:
            self.display_menu()
            choice = input("Выберите действие (1-4): ")

            if choice == '1':
                self.show_newsletters()
            elif choice == '2':
                self.unsubscribe_specific()
            elif choice == '3':
                self.unsubscribe_all_newsletters()
            elif choice == '4':
                print("\nДо свидания!")
                sys.exit(0)
            else:
                print("\nНеверный выбор. Попробуйте снова.")

            input("\nНажмите Enter для продолжения...") 