import random
import time
from tkinter import *
from tkinter import scrolledtext, messagebox

import matplotlib.pyplot as plt


# ==============================
# Узел (валидатор)
# ==============================
class Validator:
    def __init__(self, name: str, balance: float):
        self.name = name
        self.balance = balance  # текущий баланс
        self.deposit = 0.0      # сумма депозита
        self.blocks_created = 0
        self.slashed = False

    def get_weight(self):
        """Возвращает вес для выбора валидатора"""
        if self.slashed:
            return 0
        penalty = self.blocks_created * 5
        weight = max(1, self.deposit + self.balance - penalty)
        return weight

    def deposit_stake(self, amount: float):
        if amount <= 0 or self.slashed:
            return False
        self.balance -= amount
        self.deposit += amount
        print(f"[Validator {self.name}] Депозит увеличен на {amount:.2f}")
        return True

    def create_block(self):
        if self.slashed:
            raise RuntimeError("Слэшированный узел не может создавать блоки")
        self.blocks_created += 1
        reward = 1.0
        self.balance += reward
        print(f"[Validator {self.name}] Создан блок | Баланс: {self.balance}, Блоков: {self.blocks_created}")
        return {
            "validator": self.name,
            "blocks_created": self.blocks_created,
            "balance": self.balance,
            "timestamp": time.time()
        }

    def slash(self, penalty: float):
        """Применяет штраф к валидатору"""
        actual_penalty = min(penalty, self.deposit)
        self.deposit -= actual_penalty
        self.balance += actual_penalty * 0.5
        self.slashed = True
        print(f"[Validator {self.name}] Слэш: -{actual_penalty} из депозита")


# ==============================
# Блокчейн с PoS, слэшингом и защитой от долгосрочных атак
# ==============================
class BlockchainPoS:
    def __init__(self, validators: list):
        self.validators = validators
        self.chain = []

    def select_validator(self):
        weights = [(v, v.get_weight()) for v in self.validators]
        total_weight = sum(w[1] for w in weights)
        if total_weight == 0:
            raise RuntimeError("Нет активных валидаторов")
        threshold = random.uniform(0, total_weight)
        current_sum = 0
        for validator, weight in weights:
            current_sum += weight
            if current_sum >= threshold and not validator.slashed:
                return validator
        return None

    def add_block(self):
        selected = self.select_validator()
        if selected:
            block = selected.create_block()
            self.chain.append(block)
            self.check_long_range_attack(selected)
            return block
        else:
            raise RuntimeError("Не выбран валидатор")

    def check_long_range_attack(self, latest_validator):
        """Обнаруживает долгосрочные атаки"""
        if len(self.chain) < 3:
            return
        recent_blocks = self.chain[-3:]
        names = [b["validator"] for b in recent_blocks]
        if all(name == latest_validator.name for name in names):
            print(f"[Предупреждение] Обнаруженная долгосрочная атака от {latest_validator.name}")
            latest_validator.slash(latest_validator.deposit * 0.75)

    def simulate_attack(self, attacker_name: str, rounds=100):
        attack_blocks = 0
        honest_blocks = 0
        for _ in range(rounds):
            selected = self.select_validator()
            if selected.name == attacker_name:
                attack_blocks += 1
            else:
                honest_blocks += 1
        print(f"\n[+] === Результаты симуляции атаки ===")
        print(f"[+] Злоумышленник: {attack_blocks} из {rounds} ({attack_blocks / rounds * 100:.2f}%)")
        print(f"[+] Честные узлы: {honest_blocks} из {rounds} ({honest_blocks / rounds * 100:.2f}%)")
        if attack_blocks / rounds > 0.5:
            print("[!] ⚠️ Злоумышленник контролирует сеть!")
        else:
            print("[+] ✅ Сеть стабильна.")
        return attack_blocks, honest_blocks

    def get_validator_stats(self):
        stats = {
            v.name: {
                "weight": v.get_weight(),
                "blocks": v.blocks_created,
                "balance": v.balance,
                "deposit": v.deposit,
                "slashed": v.slashed
            } for v in self.validators
        }
        return stats


# ==============================
# Графический интерфейс (GUI)
# ==============================
class PoSGUI:
    def __init__(self, root, blockchain: BlockchainPoS):
        self.root = root
        self.blockchain = blockchain

        self.root.title("PoS Блокчейн Симулятор с графиками")

        # Контроллеры
        self.controls_frame = Frame(root)
        self.controls_frame.pack(pady=10)

        self.add_block_button = Button(self.controls_frame, text="Добавить блок", command=self.add_block)
        self.add_block_button.pack(side=LEFT, padx=5)

        self.attack_frame = Frame(root)
        self.attack_frame.pack(pady=10)

        self.attack_validator = Entry(self.attack_frame, width=15)
        self.attack_validator.insert(END, "Имя злоумышленника")
        self.attack_validator.pack(side=LEFT, padx=5)

        self.attack_rounds = Entry(self.attack_frame, width=10)
        self.attack_rounds.insert(END, "100")
        self.attack_rounds.pack(side=LEFT, padx=5)

        self.attack_button = Button(self.attack_frame, text="Симуляция атаки", command=self.run_attack)
        self.attack_button.pack(side=LEFT, padx=5)

        # Графики
        self.plot_frame = Frame(root)
        self.plot_frame.pack(pady=10)

        self.plot_weight_button = Button(self.plot_frame, text="Показать веса", command=self.plot_weights)
        self.plot_weight_button.pack(side=LEFT, padx=5)

        self.plot_attack_button = Button(self.plot_frame, text="Анализ атаки", command=self.plot_attack_results)
        self.plot_attack_button.pack(side=LEFT, padx=5)

        # Логи
        self.log_area = scrolledtext.ScrolledText(root, width=60, height=10)
        self.log_area.pack(padx=10, pady=10)

        self.update_display()

    def update_display(self):
        stats = self.blockchain.get_validator_stats()
        self.log_area.delete('1.0', END)
        self.log_area.insert(END, "[Валидаторы]\n")
        for name, data in stats.items():
            status = "Слэш" if data["slashed"] else f"Блоков: {data['blocks']}"
            self.log_area.insert(END, f"{name}: Вес={data['weight']:.2f}, Баланс={data['balance']:.2f}, {status}\n")
        self.log_area.see(END)

    def add_block(self):
        try:
            block = self.blockchain.add_block()
            self.log_area.insert(END, f"[Блок] Создан: {block['validator']} | Баланс: {block['balance']}\n")
            self.update_display()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def run_attack(self):
        attacker_name = self.attack_validator.get()
        rounds = int(self.attack_rounds.get())
        attack_blocks, honest_blocks = self.blockchain.simulate_attack(attacker_name, rounds)
        self.update_display()

    def plot_weights(self):
        stats = self.blockchain.get_validator_stats()
        names = list(stats.keys())
        weights = [v.get_weight() for v in self.blockchain.validators]

        plt.figure(figsize=(8, 4))
        plt.bar(names, weights, color='skyblue')
        plt.title("Веса валидаторов")
        plt.xlabel("Валидатор")
        plt.ylabel("Вес")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    def plot_attack_results(self):
        attacker_name = self.attack_validator.get()
        rounds = int(self.attack_rounds.get())
        attack_blocks, honest_blocks = self.blockchain.simulate_attack(attacker_name, rounds)

        labels = ['Злоумышленник', 'Честные']
        counts = [attack_blocks, honest_blocks]

        plt.figure(figsize=(6, 4))
        plt.bar(labels, counts, color=['red', 'green'])
        plt.title("Результаты симуляции атаки")
        plt.ylabel("Количество блоков")
        plt.tight_layout()
        plt.show()


# ==============================
# Точка входа
# ==============================
if __name__ == "__main__":
    # Инициализация валидаторов
    honest_validators = [Validator(f"Node{i}", balance=100.0) for i in range(5)]
    attacker = Validator("Attacker", balance=300.0)
    all_validators = honest_validators + [attacker]

    # Внесение депозитов
    for v in all_validators:
        v.deposit_stake(50.0)

    # Инициализация блокчейна
    blockchain = BlockchainPoS(all_validators)

    # Запуск GUI
    root = Tk()
    app = PoSGUI(root, blockchain)
    root.mainloop()