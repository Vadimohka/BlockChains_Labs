# blockchain_gui.py
# Версия 2.1 — исправлена ошибка Tcl_AsyncDelete

import hashlib
import json
import time
import tkinter as tk
from collections import OrderedDict
from multiprocessing import Process
from tkinter import messagebox
from typing import List, Optional, Dict, Any

from ecdsa import SigningKey, VerifyingKey, SECP256k1


# ==============================
# Класс Transaction — транзакция
# ==============================
class Transaction:
    def __init__(self, sender: str, recipient: str, amount: float):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount

    def to_dict(self) -> Dict[str, Any]:
        return OrderedDict({
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount
        })

    def sign_transaction(self, private_key: SigningKey) -> bytes:
        transaction_data = json.dumps(self.to_dict(), sort_keys=True)
        return private_key.sign(transaction_data.encode())

    @staticmethod
    def verify_transaction(tx_dict: dict, signature: bytes, public_key: VerifyingKey) -> bool:
        try:
            data = json.dumps(tx_dict, sort_keys=True)
            return public_key.verify(signature, data.encode())
        except Exception as e:
            print(f"[Ошибка] Проверка подписи: {e}")
            return False


# ==============================
# Класс Block — блок
# ==============================
class Block:
    def __init__(
        self,
        index: int,
        previous_hash: str,
        timestamp: float,
        transactions: List[Transaction],
        nonce: int = 0
    ):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.transactions = transactions
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        block_data = {
            'index': self.index,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'nonce': self.nonce
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine(self, difficulty: int) -> None:
        while not self.hash.startswith('0' * difficulty):
            self.nonce += 1
            self.hash = self.compute_hash()


# ==============================
# Класс Blockchain — блокчейн
# ==============================
class Blockchain:
    def __init__(self, difficulty: int = 2):
        self.chain: List[Block] = [self.create_genesis_block()]
        self.difficulty = difficulty
        self.current_transactions: List[Transaction] = []

    def create_genesis_block(self) -> Block:
        return Block(index=0, previous_hash="0", timestamp=time.time(), transactions=[])

    def new_transaction(self, transaction: Transaction) -> None:
        if transaction.amount <= 0:
            raise ValueError("Сумма транзакции должна быть больше нуля")
        self.current_transactions.append(transaction)

    def create_block(self) -> Block:
        last_block = self.chain[-1]
        new_block = Block(
            index=last_block.index + 1,
            previous_hash=last_block.hash,
            timestamp=time.time(),
            transactions=self.current_transactions
        )
        new_block.mine(self.difficulty)
        self.chain.append(new_block)
        self.current_transactions = []
        return new_block

    def is_valid_chain(self) -> bool:
        prev_block = self.chain[0]
        for block in self.chain[1:]:
            if block.previous_hash != prev_block.hash:
                return False
            if not block.hash.startswith('0' * self.difficulty):
                return False
            prev_block = block
        return True

    def replace_chain(self, new_chain: List[Block]) -> None:
        if len(new_chain) > len(self.chain) and Blockchain.check_chain_validity(new_chain, self.difficulty):
            self.chain = new_chain

    @staticmethod
    def check_chain_validity(chain: List[Block], difficulty: int) -> bool:
        prev_block = chain[0]
        for block in chain[1:]:
            if block.previous_hash != prev_block.hash:
                return False
            if not block.hash.startswith('0' * difficulty):
                return False
            prev_block = block
        return True


# ==============================
# Графический интерфейс — GUI
# ==============================
class BlockchainApp:
    def __init__(self, root: tk.Tk, node_name: str, peer_node: Optional["BlockchainApp"] = None):
        self.root = root
        self.node_name = node_name
        self.blockchain = Blockchain()
        self.private_key = SigningKey.generate(curve=SECP256k1)
        self.public_key = self.private_key.get_verifying_key()
        self.peer_node = peer_node

        self.root.title(f"Блокчейн - {node_name}")

        # Поля ввода
        self.label = tk.Label(root, text="Транзакция:")
        self.label.pack()

        self.entry_sender = tk.Entry(root)
        self.entry_sender.insert(0, "Alice")
        self.entry_sender.pack()

        self.entry_recipient = tk.Entry(root)
        self.entry_recipient.insert(0, "Bob")
        self.entry_recipient.pack()

        self.entry_amount = tk.Entry(root)
        self.entry_amount.insert(0, "10")
        self.entry_amount.pack()

        # Кнопки
        self.send_button = tk.Button(root, text="Отправить", command=self.send_transaction)
        self.send_button.pack()

        self.mine_button = tk.Button(root, text="Майнить блок", command=self.mine_block)
        self.mine_button.pack()

        self.sync_button = tk.Button(root, text="Синхронизировать с другим узлом", command=self.sync_with_other_node)
        self.sync_button.pack()

        # Отображение цепочки
        self.chain_label = tk.Label(root, text="Цепочка блоков:")
        self.chain_label.pack()

        self.chain_text = tk.Text(root, height=10, width=80)
        self.chain_text.pack()

        self.update_chain_display()

    def send_transaction(self) -> None:
        try:
            sender = self.entry_sender.get()
            recipient = self.entry_recipient.get()
            amount = float(self.entry_amount.get())

            if amount <= 0:
                raise ValueError("Сумма должна быть положительной")

            tx = Transaction(sender, recipient, amount)
            signature = tx.sign_transaction(self.private_key)

            if Transaction.verify_transaction(tx.to_dict(), signature, self.public_key):
                self.blockchain.new_transaction(tx)
                messagebox.showinfo("Успех", "Транзакция добавлена.")
            else:
                messagebox.showerror("Ошибка", "Неверная подпись.")

            self.update_chain_display()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось отправить транзакцию:\n{str(e)}")

    def mine_block(self) -> None:
        if not self.blockchain.current_transactions:
            messagebox.showwarning("Предупреждение", "Нет транзакций для майнинга.")
            return
        self.blockchain.create_block()
        self.update_chain_display()
        messagebox.showinfo("Майнинг", "Блок успешно добыт!")

    def update_chain_display(self) -> None:
        self.chain_text.delete('1.0', tk.END)
        for block in self.blockchain.chain:
            self.chain_text.insert(tk.END, f"{block.index} | {block.hash[:20]}... | Транзакции: {len(block.transactions)}\n")

    def sync_with_other_node(self) -> None:
        if self.peer_node:
            other_blockchain = self.peer_node.blockchain
            self.blockchain.replace_chain(other_blockchain.chain)
            self.update_chain_display()
            messagebox.showinfo("Синхронизация", "Цепочка обновлена.")
        else:
            messagebox.showwarning("Ошибка", "Нет доступных узлов для синхронизации.")


# ==============================
# Запуск двух GUI-узлов (через multiprocessing)
# ==============================
def run_gui_node(name: str, peer_app: Optional[BlockchainApp] = None):
    root = tk.Tk()
    app = BlockchainApp(root, name, peer_app)
    root.mainloop()

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()

    p1 = Process(target=run_gui_node, args=("Node A",))
    p2 = Process(target=run_gui_node, args=("Node B",))

    p1.start()
    p2.start()

    p1.join()
    p2.join()