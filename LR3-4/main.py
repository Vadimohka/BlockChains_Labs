import json
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext


# ==============================
# Класс для хранения истории действий
# ==============================
class ActionHistory:
    def __init__(self):
        self.history = []

    def add(self, action: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.history.append(f"[{timestamp}] {action}")

    def get_history(self) -> list:
        return self.history.copy()

    def save_to_file(self, filename="blockchain_actions.log"):
        with open(filename, "w") as f:
            for entry in self.history:
                f.write(entry + "\n")
        print(f"[История] История действий сохранена в {filename}")


# ==============================
# Базовый класс узла
# ==============================
class Node:
    def __init__(self, node_id: int):
        self.node_id = node_id
        self.log = []  # журнал команд
        self.state = {}  # текущее состояние
        self.leader = False  # является ли лидером
        self.active = True  # активен ли узел

    def apply_command(self, command: dict):
        key = command.get("key")
        value = command.get("value")
        if key and value is not None:
            self.state[key] = value
            return f"[Узел {self.node_id}] Обновлено состояние: {key}={value}"
        else:
            return f"[Узел {self.node_id}] Неверная команда"

    def append_log(self, command: dict):
        self.log.append(command)

    def get_state(self):
        return self.state.copy()

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "log": self.log,
            "state": self.state,
            "leader": self.leader
        }

    def set_leader(self, is_leader: bool):
        self.leader = is_leader

    def is_active(self):
        return self.active

    def deactivate(self):
        self.active = False

    def activate(self):
        self.active = True


# ==============================
# Менеджер узлов и консенсуса
# ==============================
class SMRNetwork:
    def __init__(self, nodes_count: int = 5):
        self.nodes: list[Node] = [Node(i) for i in range(nodes_count)]
        self.nodes_count = nodes_count
        self.leader_index = 0
        self.nodes[self.leader_index].set_leader(True)

    def broadcast_command(self, command: dict):
        for node in self.nodes:
            if node.is_active() and not node.leader:
                node.append_log(command)

    def commit_commands(self):
        logs = [n.log for n in self.nodes if n.is_active()]
        log_lengths = [len(log) for log in logs]
        if not log_lengths:
            return

        min_len = min(log_lengths)
        commands_to_commit = []

        for i in range(min_len):
            current_commands = [log[i] for log in logs if len(log) > i]
            if all(cmd == current_commands[0] for cmd in current_commands):
                commands_to_commit.append(current_commands[0])

        for node in self.nodes:
            if not node.is_active():
                continue
            node.log = node.log[:len(commands_to_commit)]
            for cmd in commands_to_commit[len(node.state):]:
                msg = node.apply_command(cmd)

    def add_node(self):
        new_id = self.nodes_count
        self.nodes.append(Node(new_id))
        self.nodes_count += 1
        return new_id

    def change_leader(self):
        new_leader_idx = (self.leader_index + 1) % self.nodes_count
        while not self.nodes[new_leader_idx].is_active():
            new_leader_idx = (new_leader_idx + 1) % self.nodes_count
        old_leader = self.leader_index
        self.nodes[old_leader].set_leader(False)
        self.leader_index = new_leader_idx
        self.nodes[self.leader_index].set_leader(True)

    def network_partition(self, partitioned_nodes: list):
        for idx in partitioned_nodes:
            self.nodes[idx].deactivate()

    def recover_partitioned_node(self, node_idx: int):
        latest_state = self.nodes[self.leader_index].get_state()
        self.nodes[node_idx].state = latest_state.copy()
        self.nodes[node_idx].activate()

    def run_consensus(self, command: dict):
        try:
            leader = self.nodes[self.leader_index]
            if not leader.is_active():
                self.change_leader()
                leader = self.nodes[self.leader_index]

            self.broadcast_command(command)
            self.commit_commands()
        except Exception as e:
            print(f"[Ошибка] При выполнении консенсуса: {e}")

    def save_to_file(self, filename="blockchain_data.json"):
        data = {
            "nodes": [node.to_dict() for node in self.nodes],
            "leader_index": self.leader_index
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

    def load_from_file(self, filename="blockchain_data.json"):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            self.nodes = []
            for node_data in data["nodes"]:
                node = Node(node_data["node_id"])
                node.log = node_data["log"]
                node.state = node_data["state"]
                node.set_leader(node_data["leader"])
                node.activate() if node_data.get("active", True) else node.deactivate()
                self.nodes.append(node)
            self.leader_index = data["leader_index"]
            self.nodes_count = len(self.nodes)
        except FileNotFoundError:
            print("[Ошибка] Файл не найден при попытке загрузки")


# ==============================
# Графический интерфейс (GUI)
# ==============================
class BlockchainGUI:
    def __init__(self, root, network: SMRNetwork, history: ActionHistory):
        self.root = root
        self.network = network
        self.history = history
        self.root.title("DLT - Система SMR с историей")

        # Ввод команды
        self.label = tk.Label(root, text="Введите команду:")
        self.label.pack(pady=5)

        self.entry_key = tk.Entry(root)
        self.entry_key.insert(0, "ключ")
        self.entry_key.pack()

        self.entry_value = tk.Entry(root)
        self.entry_value.insert(0, "значение")
        self.entry_value.pack()

        self.send_button = tk.Button(root, text="Выполнить команду", command=self.run_command)
        self.send_button.pack(pady=5)

        self.status_text = scrolledtext.ScrolledText(root, width=60, height=10)
        self.status_text.pack(pady=5)

        self.history_text = scrolledtext.ScrolledText(root, width=60, height=8)
        self.history_text.pack(pady=5)

        self.save_button = tk.Button(root, text="Сохранить данные", command=self.save_data)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.load_button = tk.Button(root, text="Загрузить данные", command=self.load_data)
        self.load_button.pack(side=tk.LEFT, padx=5)

        self.add_node_button = tk.Button(root, text="Добавить узел", command=self.add_node)
        self.add_node_button.pack(side=tk.RIGHT, padx=5)

        self.reset_button = tk.Button(root, text="Сбросить узлы", command=self.reset_network)
        self.reset_button.pack(side=tk.RIGHT, padx=5)

        self.update_status()
        self.update_history()

    def run_command(self):
        key = self.entry_key.get()
        value = self.entry_value.get()
        try:
            value = int(value)
        except ValueError:
            pass
        command = {"key": key, "value": value}
        self.network.run_consensus(command)
        self.history.add(f"Выполнена команда: {command}")
        self.update_status()
        self.update_history()

    def update_status(self):
        self.status_text.delete('1.0', tk.END)
        self.status_text.insert(tk.END, "[Текущее состояние узлов]\n")
        for node in self.network.nodes:
            status = f"Узел {node.node_id} ({'Активен' if node.is_active() else 'Неактивен'}): {node.get_state()}\n"
            self.status_text.insert(tk.END, status)

    def update_history(self):
        self.history_text.delete('1.0', tk.END)
        self.history_text.insert(tk.END, "[История действий]\n")
        for entry in self.history.get_history():
            self.history_text.insert(tk.END, entry + "\n")

    def save_data(self):
        self.network.save_to_file()
        self.history.add("Данные сети сохранены в файл.")
        self.update_history()
        messagebox.showinfo("Сохранение", "Данные успешно сохранены в файл.")

    def load_data(self):
        self.network.load_from_file()
        self.history.add("Данные сети загружены из файла.")
        self.update_status()
        self.update_history()
        messagebox.showinfo("Загрузка", "Данные успешно загружены из файла.")

    def reset_network(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.network = SMRNetwork(nodes_count=5)
        self.history.add("Сеть была сброшена.")
        self.__init__(self.root, self.network, self.history)

    def add_node(self):
        new_id = self.network.add_node()
        self.history.add(f"Добавлен новый узел с ID: {new_id}")
        self.update_status()
        self.update_history()
        messagebox.showinfo("Новый узел", f"Добавлен новый узел с ID: {new_id}")


# ==============================
# Точка входа
# ==============================
def main():
    history = ActionHistory()
    network = SMRNetwork(nodes_count=5)

    root = tk.Tk()
    app = BlockchainGUI(root, network, history)
    root.mainloop()


if __name__ == "__main__":
    main()